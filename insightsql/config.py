from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def _path_from_env(name: str, default: str) -> Path:
    path = Path(os.getenv(name, default)).expanduser()
    return (ROOT_DIR / path).resolve() if not path.is_absolute() else path.resolve()


def _positive_int(name: str, default: int, maximum: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a whole number.") from exc
    if not 1 <= value <= maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}.")
    return value


@dataclass(frozen=True)
class Settings:
    database_path: Path
    history_path: Path
    log_path: Path
    llm_mode: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_timeout_seconds: int
    query_timeout_seconds: int
    max_result_rows: int
    history_limit: int

    @classmethod
    def from_env(cls) -> Settings:
        llm_mode = os.getenv("INSIGHTSQL_LLM_MODE", "offline").strip().casefold()
        if llm_mode not in {"offline", "api"}:
            raise ValueError("INSIGHTSQL_LLM_MODE must be 'offline' or 'api'.")

        base_url = os.getenv(
            "INSIGHTSQL_LLM_BASE_URL", "https://api.openai.com/v1"
        ).strip().rstrip("/")
        parsed_url = urlparse(base_url)
        if (
            parsed_url.scheme not in {"https", "http"}
            or not parsed_url.netloc
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ValueError(
                "INSIGHTSQL_LLM_BASE_URL must be an HTTP(S) base URL without "
                "credentials, a query, or a fragment."
            )
        if parsed_url.scheme != "https" and parsed_url.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError(
                "The SQL generation API must use HTTPS unless it runs locally."
            )

        model = os.getenv("INSIGHTSQL_LLM_MODEL", "gpt-4o-mini").strip()
        if not model or len(model) > 200:
            raise ValueError("INSIGHTSQL_LLM_MODEL must be 1–200 characters.")

        return cls(
            database_path=_path_from_env(
                "INSIGHTSQL_DATABASE_PATH", "employee_management.db"
            ),
            history_path=_path_from_env(
                "INSIGHTSQL_HISTORY_PATH", "data/query_history.db"
            ),
            log_path=_path_from_env(
                "INSIGHTSQL_LOG_PATH", "logs/insightsql.log"
            ),
            llm_mode=llm_mode,
            llm_base_url=base_url,
            llm_api_key=os.getenv("INSIGHTSQL_LLM_API_KEY", "").strip(),
            llm_model=model,
            llm_timeout_seconds=_positive_int(
                "INSIGHTSQL_LLM_TIMEOUT_SECONDS", 30, 120
            ),
            query_timeout_seconds=_positive_int(
                "INSIGHTSQL_QUERY_TIMEOUT_SECONDS", 3, 30
            ),
            max_result_rows=_positive_int(
                "INSIGHTSQL_MAX_RESULT_ROWS", 500, 5000
            ),
            history_limit=_positive_int(
                "INSIGHTSQL_HISTORY_LIMIT", 500, 10000
            ),
        )
