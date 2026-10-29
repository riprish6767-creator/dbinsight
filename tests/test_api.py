import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from insightsql.main import app


def _create_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE employees (employee_id INTEGER PRIMARY KEY, name TEXT)"
        )
        connection.execute(
            "INSERT INTO employees (employee_id, name) VALUES (1, 'Ava')"
        )


def _set_test_settings(monkeypatch, tmp_path, database):
    monkeypatch.setenv("INSIGHTSQL_DATABASE_PATH", str(database))
    monkeypatch.setenv(
        "INSIGHTSQL_HISTORY_PATH", str(tmp_path / "history.db")
    )
    monkeypatch.setenv("INSIGHTSQL_LOG_PATH", str(tmp_path / "insightsql.log"))
    monkeypatch.setenv("INSIGHTSQL_HISTORY_LIMIT", "10")


def test_ask_generates_sql_without_executing_or_recording_it(
    monkeypatch, tmp_path
):
    database = tmp_path / "employees.db"
    _create_database(database)
    _set_test_settings(monkeypatch, tmp_path, database)
    monkeypatch.setattr(
        "insightsql.main.generate_sql",
        lambda question, settings: "SELECT name FROM employees",
    )

    with TestClient(
        app,
        client=("127.0.0.1", 50000),
        headers={"host": "127.0.0.1"},
    ) as client:
        response = client.post(
            "/api/ask", json={"question": "Who works here?"}
        )
        history = client.get("/api/history")

    assert response.status_code == 200
    assert response.json() == {"sql": "SELECT name FROM employees"}
    assert history.json() == {"items": []}


def test_query_runs_validated_sql_and_records_history(monkeypatch, tmp_path):
    database = tmp_path / "employees.db"
    _create_database(database)
    _set_test_settings(monkeypatch, tmp_path, database)

    with TestClient(
        app,
        client=("127.0.0.1", 50000),
        headers={"host": "127.0.0.1"},
    ) as client:
        response = client.post(
            "/api/query",
            json={
                "sql": "SELECT name FROM employees",
                "question": "List employees",
            },
        )
        history = client.get("/api/history")

    assert response.status_code == 200
    assert response.json()["rows"] == [["Ava"]]
    assert history.json()["items"][0]["question"] == "List employees"


def test_query_endpoint_rejects_writes_without_changing_database(
    monkeypatch, tmp_path
):
    database = tmp_path / "employees.db"
    _create_database(database)
    _set_test_settings(monkeypatch, tmp_path, database)

    with TestClient(
        app,
        client=("127.0.0.1", 50000),
        headers={"host": "127.0.0.1"},
    ) as client:
        response = client.post(
            "/api/query",
            json={"sql": "DELETE FROM employees"},
        )

    assert response.status_code == 400
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 1


def test_api_rejects_non_local_clients(tmp_path, monkeypatch):
    database = tmp_path / "employees.db"
    _create_database(database)
    _set_test_settings(monkeypatch, tmp_path, database)

    with TestClient(
        app,
        client=("192.0.2.10", 50000),
        headers={"host": "127.0.0.1"},
    ) as client:
        response = client.get(
            "/api/health", headers={"host": "127.0.0.1"}
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "InsightSQL only accepts local connections."


def test_local_responses_include_security_headers(tmp_path, monkeypatch):
    database = tmp_path / "employees.db"
    _create_database(database)
    _set_test_settings(monkeypatch, tmp_path, database)

    with TestClient(
        app,
        client=("127.0.0.1", 50000),
        headers={"host": "127.0.0.1"},
    ) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in response.headers["content-security-policy"]


def test_health_reports_offline_sql_mode_without_api_key(tmp_path, monkeypatch):
    database = tmp_path / "employees.db"
    _create_database(database)
    _set_test_settings(monkeypatch, tmp_path, database)
    monkeypatch.setenv("INSIGHTSQL_LLM_MODE", "offline")
    monkeypatch.setenv("INSIGHTSQL_LLM_API_KEY", "")

    with TestClient(
        app,
        client=("127.0.0.1", 50000),
        headers={"host": "127.0.0.1"},
    ) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["sql_generation_mode"] == "offline"
    assert response.json()["sql_generation_configured"] is True
