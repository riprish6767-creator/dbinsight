import sqlite3
from pathlib import Path

import pytest

from insightsql.config import Settings
from insightsql.errors import ConfigurationError, GenerationError
from insightsql.llm import generate_sql

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sample_database(tmp_path):
    database = tmp_path / "employee_management.db"
    connection = sqlite3.connect(database)
    try:
        connection.executescript(
            (ROOT / "sql" / "sqlite_schema.sql").read_text(encoding="utf-8")
        )
        connection.executescript(
            (ROOT / "sql" / "sqlite_seed.sql").read_text(encoding="utf-8")
        )
        connection.commit()
    finally:
        connection.close()
    return database


def _settings(database, *, mode="offline", api_key=""):
    return Settings(
        database_path=database,
        history_path=database.parent / "history.db",
        log_path=database.parent / "insightsql.log",
        llm_mode=mode,
        llm_base_url="https://api.example.test/v1",
        llm_api_key=api_key,
        llm_model="test-model",
        llm_timeout_seconds=1,
        query_timeout_seconds=1,
        max_result_rows=20,
        history_limit=20,
    )


@pytest.mark.parametrize(
    ("question", "expected_sql"),
    [
        (
            "How many employees are in each department?",
            "GROUP BY d.department_id, d.department_name",
        ),
        (
            "How many employees are in Engineering?",
            "lower('Engineering')",
        ),
        (
            "Show employees in Human Resources",
            "lower('Human Resources')",
        ),
        (
            "List active projects",
            "project_status = 'Active'",
        ),
        (
            "Show employee project assignments",
            "JOIN projects AS p",
        ),
        (
            "How many active employees?",
            "employment_status = 'Active'",
        ),
        (
            "List departments",
            "FROM departments ORDER BY department_name",
        ),
    ],
)
def test_generates_common_sql_locally_without_api_key(
    sample_database, question, expected_sql
):
    sql = generate_sql(question, _settings(sample_database))

    assert expected_sql in sql
    assert sql.startswith("SELECT")


def test_offline_mode_does_not_call_provider_even_if_key_is_present(
    sample_database, monkeypatch
):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Offline mode must not contact the SQL API.")

    monkeypatch.setattr("insightsql.llm.urllib.request.build_opener", fail_if_called)

    sql = generate_sql(
        "How many employees are there?",
        _settings(sample_database, api_key="configured-but-unused"),
    )

    assert sql == "SELECT COUNT(*) AS employee_count FROM employees"


def test_unsupported_offline_question_has_helpful_message(sample_database):
    with pytest.raises(GenerationError, match="not predictions"):
        generate_sql(
            "Predict which employee may resign next year",
            _settings(sample_database),
        )


def test_api_mode_requires_api_key(sample_database):
    with pytest.raises(ConfigurationError, match="API generation is enabled"):
        generate_sql(
            "List employees",
            _settings(sample_database, mode="api"),
        )


def test_offline_generated_sql_still_rejects_unexpected_write(sample_database, monkeypatch):
    monkeypatch.setattr(
        "insightsql.llm.generate_local_sql",
        lambda question, database: "DELETE FROM employees",
    )

    from insightsql.errors import SQLValidationError

    with pytest.raises(SQLValidationError):
        generate_sql("Show employees", _settings(sample_database))
