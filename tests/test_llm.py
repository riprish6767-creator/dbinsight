import urllib.error
from pathlib import Path
import re

import pytest

from insightsql.config import Settings
from insightsql.errors import GenerationError
from insightsql.llm import generate_sql


def _settings():
    return Settings(
        database_path=Path("employee_management.db"),
        history_path=Path("history.db"),
        log_path=Path("insightsql.log"),
        llm_mode="api",
        llm_base_url="https://api.example.test/v1",
        llm_api_key="test-key-never-log-this",
        llm_model="test-model",
        llm_timeout_seconds=1,
        query_timeout_seconds=1,
        max_result_rows=10,
        history_limit=10,
    )


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, "provider rejected the API key (HTTP 401)"),
        (403, "provider rejected the API key (HTTP 403)"),
        (404, "endpoint or model was not found (HTTP 404)"),
        (429, "rate-limiting requests (HTTP 429)"),
        (500, "rejected the request (HTTP 500)"),
    ],
)
def test_provider_http_errors_are_actionable_and_do_not_leak_key(
    monkeypatch, status, expected
):
    class FailingOpener:
        def open(self, request, timeout):
            raise urllib.error.HTTPError(
                request.full_url, status, "test", {}, None
            )

    monkeypatch.setattr(
        "insightsql.llm.get_schema", lambda database: [{"name": "employees"}]
    )
    monkeypatch.setattr(
        "insightsql.llm.urllib.request.build_opener",
        lambda *args: FailingOpener(),
    )

    with pytest.raises(GenerationError, match=re.escape(expected)) as error:
        generate_sql("List employees", _settings())

    assert _settings().llm_api_key not in str(error.value)
