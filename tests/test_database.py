import sqlite3

import pytest

from insightsql.database import execute_select, get_schema
from insightsql.errors import QueryExecutionError


def test_executes_select_read_only_and_limits_results(tmp_path):
    database = tmp_path / "test.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE employees (employee_id INTEGER)")
        connection.executemany(
            "INSERT INTO employees VALUES (?)", [(1,), (2,), (3,)]
        )

    result = execute_select(
        database,
        "SELECT employee_id FROM employees ORDER BY employee_id",
        timeout_seconds=3,
        max_rows=2,
    )

    assert result.columns == ["employee_id"]
    assert result.rows == [[1], [2]]
    assert result.row_count == 2
    assert result.truncated is True
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 3


def test_rejects_write_even_if_called_without_validator(tmp_path):
    database = tmp_path / "test.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE employees (employee_id INTEGER)")
        connection.execute("INSERT INTO employees VALUES (1)")

    with pytest.raises(QueryExecutionError):
        execute_select(
            database,
            "DELETE FROM employees",
            timeout_seconds=3,
            max_rows=10,
        )
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 1


def test_schema_only_returns_expected_application_tables(tmp_path):
    database = tmp_path / "test.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE employees (employee_id INTEGER)")
        connection.execute("CREATE TABLE other_data (secret TEXT)")

    schema = get_schema(database)

    assert [table["name"] for table in schema] == ["employees"]
    assert schema[0]["columns"][0]["name"] == "employee_id"


def test_caps_total_result_payload_size(tmp_path):
    database = tmp_path / "test.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE employees (name TEXT)")
        connection.executemany(
            "INSERT INTO employees (name) VALUES (?)",
            [("x" * 750_000,), ("y" * 750_000,), ("z" * 750_000,)],
        )

    result = execute_select(
        database,
        "SELECT name FROM employees",
        timeout_seconds=3,
        max_rows=10,
    )

    assert result.row_count == 2
    assert result.truncated is True


def test_missing_database_has_friendly_error(tmp_path):
    with pytest.raises(QueryExecutionError, match="database was not found"):
        get_schema(tmp_path / "missing.db")
