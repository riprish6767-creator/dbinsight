from __future__ import annotations

import logging
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from insightsql.config import ROOT_DIR, Settings
from insightsql.database import execute_select, get_schema
from insightsql.errors import (
    ConfigurationError,
    GenerationError,
    QueryExecutionError,
    SQLValidationError,
)
from insightsql.history import get_history, initialize_history, record_query
from insightsql.llm import generate_sql
from insightsql.logging_config import configure_logging
from insightsql.sql_safety import validate_read_only_select

logger = logging.getLogger("insightsql")
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_MAX_QUESTION_LENGTH = 2_000


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=_MAX_QUESTION_LENGTH)


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sql: str = Field(min_length=1, max_length=10_000)
    question: str = Field(default="", max_length=_MAX_QUESTION_LENGTH)


def _settings() -> Settings:
    try:
        return Settings.from_env()
    except ValueError as exc:
        raise ConfigurationError(
            "InsightSQL configuration is invalid. Check the local .env settings."
        ) from exc


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = _settings()
    settings.history_path.parent.mkdir(parents=True, exist_ok=True)
    configure_logging(settings.log_path)
    initialize_history(settings.history_path, settings.history_limit)
    logger.info("InsightSQL started")
    yield
    logger.info("InsightSQL stopped")


app = FastAPI(
    title="InsightSQL",
    version="1.0.0",
    description="Local-first, read-only natural-language SQLite queries.",
    lifespan=lifespan,
)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)


@app.middleware("http")
async def enforce_local_access(request: Request, call_next):
    client_host = request.client.host if request.client else ""
    requested_host = request.url.hostname or ""
    if client_host not in _LOCAL_HOSTS or requested_host not in _LOCAL_HOSTS:
        return _json_error(403, "InsightSQL only accepts local connections.")
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self' data:; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


def _json_error(status_code: int, message: str):
    return JSONResponse(status_code=status_code, content={"detail": message})


def _handle_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ConfigurationError):
        logger.error("Application configuration error: %s", exc)
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, (GenerationError, SQLValidationError)):
        logger.info("Request rejected: %s", type(exc).__name__)
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, QueryExecutionError):
        logger.info("Query failed: %s", str(exc))
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    logger.error(
        "Unhandled request error method=%s path=%s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Check the local application log."},
    )


def _execute_and_record(
    settings: Settings, sql: str, question: str
) -> dict[str, Any]:
    try:
        validated_sql = validate_read_only_select(sql).sql
        result = execute_select(
            settings.database_path,
            validated_sql,
            timeout_seconds=settings.query_timeout_seconds,
            max_rows=settings.max_result_rows,
        )
        history_id = record_query(
            settings.history_path,
            settings.history_limit,
            question=question,
            sql=validated_sql,
            columns=result.columns,
            row_count=result.row_count,
            truncated=result.truncated,
            elapsed_ms=result.elapsed_ms,
        )
    except (SQLValidationError, QueryExecutionError) as exc:
        raise _handle_error(exc) from exc

    logger.info(
        "Query completed history_id=%s row_count=%s truncated=%s elapsed_ms=%s",
        history_id,
        result.row_count,
        result.truncated,
        result.elapsed_ms,
    )
    return {
        "history_id": history_id,
        "sql": validated_sql,
        "columns": result.columns,
        "rows": result.rows,
        "row_count": result.row_count,
        "truncated": result.truncated,
        "elapsed_ms": result.elapsed_ms,
    }


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(Path(__file__).resolve().parent / "static" / "index.html")


@app.get("/api/health")
def health():
    try:
        settings = _settings()
        schema = get_schema(settings.database_path)
    except (ConfigurationError, QueryExecutionError) as exc:
        raise _handle_error(exc) from exc
    return {
        "status": "ok",
        "database": settings.database_path.name,
        "tables_available": len(schema),
        "sql_generation_configured": (
            settings.llm_mode == "offline" or bool(settings.llm_api_key)
        ),
        "sql_generation_mode": settings.llm_mode,
    }


@app.get("/api/schema")
def schema():
    try:
        return {"tables": get_schema(_settings().database_path)}
    except (ConfigurationError, QueryExecutionError) as exc:
        raise _handle_error(exc) from exc


@app.get("/api/history")
def history():
    try:
        settings = _settings()
        return {"items": get_history(settings.history_path, settings.history_limit)}
    except ConfigurationError as exc:
        raise _handle_error(exc) from exc
    except (sqlite3.Error, OSError, ValueError) as exc:
        logger.exception("Could not read query history")
        raise HTTPException(
            status_code=500, detail="Query history could not be loaded."
        ) from exc


@app.post("/api/ask")
def ask(request: AskRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=422, detail="Enter a natural-language question."
        )
    try:
        settings = _settings()
        sql = generate_sql(question, settings)
        validated_sql = validate_read_only_select(sql).sql
        logger.info("SQL generated for a natural-language question")
        return {"sql": validated_sql}
    except (
        ConfigurationError,
        GenerationError,
        QueryExecutionError,
        SQLValidationError,
    ) as exc:
        raise _handle_error(exc) from exc


@app.post("/api/query")
def query(request: QueryRequest):
    question = request.question.strip() or "Manual SQL query"
    try:
        settings = _settings()
        return _execute_and_record(settings, request.sql, question)
    except (ConfigurationError, SQLValidationError, QueryExecutionError) as exc:
        raise _handle_error(exc) from exc


def run() -> None:
    import uvicorn

    uvicorn.run("insightsql.main:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()
