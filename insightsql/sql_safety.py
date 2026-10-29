from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from insightsql.errors import SQLValidationError

MAX_SQL_LENGTH = 10_000
ALLOWED_TABLES = frozenset(
    {"departments", "employees", "projects", "employee_projects"}
)
_FORBIDDEN_NODE_NAMES = frozenset(
    {
        "alter",
        "attach",
        "command",
        "copy",
        "create",
        "delete",
        "detach",
        "drop",
        "grant",
        "insert",
        "into",
        "lock",
        "merge",
        "pragma",
        "revoke",
        "transaction",
        "truncate",
        "update",
        "use",
    }
)


@dataclass(frozen=True)
class ValidatedSQL:
    sql: str
    expression: exp.Expression


def validate_read_only_select(sql: str) -> ValidatedSQL:
    if not isinstance(sql, str) or not sql.strip():
        raise SQLValidationError("Enter a SQL query to continue.")
    if len(sql) > MAX_SQL_LENGTH:
        raise SQLValidationError(
            f"SQL is too long. Keep it under {MAX_SQL_LENGTH:,} characters."
        )

    try:
        statements = [statement for statement in sqlglot.parse(sql, read="sqlite") if statement]
    except ParseError as exc:
        raise SQLValidationError(
            "The SQL could not be parsed. Check the syntax and try again."
        ) from exc

    if len(statements) != 1:
        raise SQLValidationError("Run one SELECT statement at a time.")

    expression = statements[0]
    if not isinstance(
        expression, (exp.Select, exp.Union, exp.Intersect, exp.Except)
    ):
        raise SQLValidationError("Only read-only SELECT queries are allowed.")

    if any(
        node.__class__.__name__.casefold() in _FORBIDDEN_NODE_NAMES
        for node in expression.walk()
    ):
        raise SQLValidationError(
            "This query contains a command that is not allowed. "
            "Only read-only SELECT queries are permitted."
        )

    cte_names = {
        cte.alias_or_name.casefold()
        for cte in expression.find_all(exp.CTE)
        if cte.alias_or_name
    }
    for table in expression.find_all(exp.Table):
        table_name = table.name.casefold()
        database_name = table.db.casefold()
        catalog_name = table.catalog.casefold()
        if table_name in cte_names:
            continue
        if (
            table_name not in ALLOWED_TABLES
            or database_name not in {"", "main"}
            or catalog_name
        ):
            raise SQLValidationError(
                "Queries can only read the employee management tables: "
                "departments, employees, projects, and employee_projects."
            )

    return ValidatedSQL(sql=sql.strip().rstrip(";"), expression=expression)
