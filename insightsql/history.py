from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

_HISTORY_RETENTION_DAYS = 30
_MAX_QUESTION_LENGTH = 2_000


def initialize_history(history_path: Path, history_limit: int) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(history_path, timeout=5) as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS query_history (
                history_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                question TEXT NOT NULL,
                sql TEXT NOT NULL,
                columns_json TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                truncated INTEGER NOT NULL CHECK (truncated IN (0, 1)),
                elapsed_ms INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS ix_query_history_created_at "
            "ON query_history (created_at DESC)"
        )
        retention_cutoff = (
            datetime.now(UTC) - timedelta(days=_HISTORY_RETENTION_DAYS)
        ).isoformat()
        connection.execute(
            "DELETE FROM query_history WHERE created_at < ?",
            (retention_cutoff,),
        )
        connection.execute(
            """
            DELETE FROM query_history
            WHERE history_id NOT IN (
                SELECT history_id FROM query_history
                ORDER BY created_at DESC LIMIT ?
            )
            """,
            (history_limit,),
        )
        connection.commit()


def record_query(
    history_path: Path,
    history_limit: int,
    *,
    question: str,
    sql: str,
    columns: list[str],
    row_count: int,
    truncated: bool,
    elapsed_ms: int,
) -> str:
    history_id = str(uuid4())
    created_at = datetime.now(UTC).isoformat()
    safe_question = question[:_MAX_QUESTION_LENGTH]
    with sqlite3.connect(history_path, timeout=5) as connection:
        connection.execute(
            """
            INSERT INTO query_history
                (history_id, created_at, question, sql, columns_json,
                 row_count, truncated, elapsed_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                history_id,
                created_at,
                safe_question,
                sql,
                json.dumps(columns),
                row_count,
                int(truncated),
                elapsed_ms,
            ),
        )
        connection.execute(
            """
            DELETE FROM query_history
            WHERE history_id NOT IN (
                SELECT history_id FROM query_history
                ORDER BY created_at DESC LIMIT ?
            )
            """,
            (history_limit,),
        )
        connection.commit()
    return history_id


def get_history(history_path: Path, limit: int) -> list[dict[str, Any]]:
    with sqlite3.connect(history_path, timeout=5) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT history_id, created_at, question, sql, columns_json,
                   row_count, truncated, elapsed_ms
            FROM query_history
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "history_id": row["history_id"],
            "created_at": row["created_at"],
            "question": row["question"],
            "sql": row["sql"],
            "columns": json.loads(row["columns_json"]),
            "row_count": row["row_count"],
            "truncated": bool(row["truncated"]),
            "elapsed_ms": row["elapsed_ms"],
        }
        for row in rows
    ]
