from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from insightsql.errors import QueryExecutionError

MAX_COLUMN_COUNT = 100
MAX_RESULT_BYTES = 2_000_000
SCHEMA_TABLES = ("departments", "employees", "projects", "employee_projects")


@dataclass(frozen=True)
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    elapsed_ms: int


def _open_read_only(database_path: Path, timeout_seconds: int) -> sqlite3.Connection:
    if not database_path.is_file():
        raise QueryExecutionError(
            "The configured SQLite database was not found. Check "
            "INSIGHTSQL_DATABASE_PATH in the .env file."
        )
    connection = None
    try:
        connection = sqlite3.connect(
            f"{database_path.resolve().as_uri()}?mode=ro",
            uri=True,
            timeout=timeout_seconds,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 2_000_000)
        connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 10_000)
        connection.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, MAX_COLUMN_COUNT)
        connection.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
        return connection
    except sqlite3.Error as exc:
        if connection is not None:
            connection.close()
        raise QueryExecutionError(
            "Could not open the SQLite database. Check that the database file "
            "is valid and accessible."
        ) from exc


def get_schema(database_path: Path) -> list[dict[str, Any]]:
    try:
        with _open_read_only(database_path, timeout_seconds=1) as connection:
            available_tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            schema = []
            for table_name in SCHEMA_TABLES:
                if table_name not in available_tables:
                    continue
                quoted_name = '"' + table_name.replace('"', '""') + '"'
                columns = connection.execute(
                    f"PRAGMA table_info({quoted_name})"
                ).fetchall()
                schema.append(
                    {
                        "name": table_name,
                        "columns": [
                            {
                                "name": column["name"],
                                "type": column["type"],
                                "primary_key": bool(column["pk"]),
                                "required": bool(column["notnull"]),
                            }
                            for column in columns
                        ],
                    }
                )
            return schema
    except sqlite3.Error as exc:
        raise QueryExecutionError(
            "Could not read the SQLite database schema."
        ) from exc


def execute_select(
    database_path: Path,
    sql: str,
    *,
    timeout_seconds: int,
    max_rows: int,
) -> QueryResult:
    started_at = time.monotonic()
    deadline = started_at + timeout_seconds
    connection = _open_read_only(database_path, timeout_seconds)
    try:
        connection.set_progress_handler(
            lambda: 1 if time.monotonic() >= deadline else 0,
            1000,
        )
        cursor = connection.execute(sql)
        if cursor.description is None:
            raise QueryExecutionError("Only read-only SELECT queries can run.")
        if len(cursor.description) > MAX_COLUMN_COUNT:
            raise QueryExecutionError(
                f"Limit results to {MAX_COLUMN_COUNT} columns or fewer."
            )

        columns = [description[0] for description in cursor.description]
        rows = []
        result_bytes = 0
        truncated = False
        for row in cursor:
            if len(rows) >= max_rows:
                truncated = True
                break
            values = [
                value.hex() if isinstance(value, bytes) else value
                for value in tuple(row)
            ]
            row_bytes = len(
                json.dumps(values, ensure_ascii=True, separators=(",", ":")).encode(
                    "utf-8"
                )
            )
            if row_bytes > MAX_RESULT_BYTES:
                raise QueryExecutionError(
                    "A result row is too large to display. Select fewer or smaller columns."
                )
            if result_bytes + row_bytes > MAX_RESULT_BYTES:
                truncated = True
                break
            rows.append(values)
            result_bytes += row_bytes

        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            elapsed_ms=round((time.monotonic() - started_at) * 1000),
        )
    except QueryExecutionError:
        raise
    except sqlite3.Error as exc:
        if time.monotonic() >= deadline or "interrupt" in str(exc).casefold():
            raise QueryExecutionError(
                f"The query exceeded the {timeout_seconds}-second execution limit."
            ) from exc
        raise QueryExecutionError(
            "The query could not run. Check table and column names and try again."
        ) from exc
    finally:
        connection.close()
