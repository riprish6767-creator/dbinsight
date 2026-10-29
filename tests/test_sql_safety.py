import pytest

from insightsql.errors import SQLValidationError
from insightsql.sql_safety import validate_read_only_select


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT first_name FROM employees",
        "SELECT department_id, COUNT(*) FROM employees GROUP BY department_id",
        "WITH active AS (SELECT employee_id FROM employees) "
        "SELECT employee_id FROM active",
        "SELECT employee_id FROM employees UNION "
        "SELECT employee_id FROM employees",
        "SELECT * FROM main.employees",
    ],
)
def test_accepts_select_queries_on_application_tables(sql):
    assert validate_read_only_select(sql).sql.startswith(("SELECT", "WITH"))


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM employees",
        "UPDATE employees SET first_name = 'x'",
        "INSERT INTO employees (first_name) VALUES ('x')",
        "DROP TABLE employees",
        "TRUNCATE employees",
        "ALTER TABLE employees ADD COLUMN x TEXT",
        "PRAGMA table_info(employees)",
        "ATTACH DATABASE 'other.db' AS other",
        "SELECT 1; DELETE FROM employees",
        "WITH removed AS (DELETE FROM employees RETURNING employee_id) "
        "SELECT employee_id FROM removed",
        "SELECT * FROM sqlite_master",
        "SELECT * FROM other.employees",
        "SELECT * FROM readfile('secret.txt')",
        "",
    ],
)
def test_rejects_non_select_multiple_or_unsafe_queries(sql):
    with pytest.raises(SQLValidationError):
        validate_read_only_select(sql)


def test_rejects_oversized_sql():
    with pytest.raises(SQLValidationError, match="too long"):
        validate_read_only_select("SELECT " + (" " * 10_000))


def test_normalizes_one_trailing_semicolon():
    assert validate_read_only_select("SELECT employee_id FROM employees;").sql == (
        "SELECT employee_id FROM employees"
    )
