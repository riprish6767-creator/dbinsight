from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from insightsql.database import _open_read_only
from insightsql.errors import GenerationError

_VALUE_QUERIES = {
    ("departments", "department_name"):
        "SELECT department_name FROM departments ORDER BY department_name",
    ("employees", "employment_status"):
        "SELECT DISTINCT employment_status FROM employees ORDER BY employment_status",
    ("projects", "project_status"):
        "SELECT DISTINCT project_status FROM projects ORDER BY project_status",
}


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _contains_phrase(question: str, phrase: str) -> bool:
    normalized_phrase = _normalize(phrase)
    if not normalized_phrase:
        return False
    return f" {normalized_phrase} " in f" {question} "


def _find_database_value(
    database_path: Path, table: str, column: str, question: str
) -> str | None:
    statement = _VALUE_QUERIES.get((table, column))
    if statement is None:
        raise GenerationError("That question is not supported in local mode.")
    try:
        with _open_read_only(database_path, timeout_seconds=1) as connection:
            values = [row[0] for row in connection.execute(statement)]
    except sqlite3.Error as exc:
        raise GenerationError(
            "Could not read the database values needed to answer that question."
        ) from exc
    return next(
        (value for value in values if _contains_phrase(question, value)), None
    )


def generate_local_sql(question: str, database_path: Path) -> str:
    normalized = _normalize(question)
    if not normalized:
        raise GenerationError("Enter a question about employees, departments, or projects.")
    if {"predict", "forecast", "recommend", "explain"}.intersection(
        normalized.split()
    ):
        raise GenerationError(
            "Offline mode supports factual lookups and counts, not predictions or "
            "explanations. Rephrase as a question about existing employees, "
            "departments, projects, or assignments."
        )

    department = _find_database_value(
        database_path, "departments", "department_name", normalized
    )
    employee_status = _find_database_value(
        database_path, "employees", "employment_status", normalized
    )
    project_status = _find_database_value(
        database_path, "projects", "project_status", normalized
    )

    employee_terms = {"employee", "employees", "staff", "person", "people"}
    project_terms = {"project", "projects"}
    assignment_terms = {"assigned", "assignment", "assignments", "working"}
    count_terms = {"count", "many", "number", "total"}
    has_employee = bool(employee_terms.intersection(normalized.split()))
    has_project = bool(project_terms.intersection(normalized.split()))
    has_assignment = bool(assignment_terms.intersection(normalized.split()))
    wants_count = bool(count_terms.intersection(normalized.split()))

    if has_assignment and has_project and not has_employee:
        raise GenerationError(
            "To see project assignments, ask for project assignments by employee "
            "or employee assignments by project."
        )

    if has_assignment and has_project and has_employee:
        sql = (
            "SELECT e.employee_number, e.first_name, e.last_name, "
            "p.project_code, p.project_name, ep.project_role, "
            "ep.allocation_percent "
            "FROM employee_projects AS ep "
            "JOIN employees AS e ON e.employee_id = ep.employee_id "
            "JOIN projects AS p ON p.project_id = ep.project_id"
        )
        if department:
            sql += (
                " JOIN departments AS d ON d.department_id = e.department_id "
                f"WHERE lower(d.department_name) = lower({_sql_literal(department)})"
            )
        return sql + " ORDER BY e.last_name, e.first_name, p.project_name"

    if has_project:
        if wants_count:
            if project_status:
                status_filter = (
                    f" WHERE project_status = {_sql_literal(project_status)}"
                )
            else:
                status_filter = ""
            return f"SELECT COUNT(*) AS project_count FROM projects{status_filter}"
        if project_status:
            status_filter = f" WHERE project_status = {_sql_literal(project_status)}"
        else:
            status_filter = ""
        return (
            "SELECT project_code, project_name, project_status, start_date, end_date "
            f"FROM projects{status_filter} ORDER BY project_name"
        )

    if department and has_employee:
        if wants_count:
            return (
                "SELECT COUNT(*) AS employee_count "
                "FROM employees AS e "
                "JOIN departments AS d ON d.department_id = e.department_id "
                f"WHERE lower(d.department_name) = lower({_sql_literal(department)})"
            )
        return (
            "SELECT e.employee_number, e.first_name, e.last_name, e.job_title, "
            "e.email, e.hire_date "
            "FROM employees AS e "
            "JOIN departments AS d ON d.department_id = e.department_id "
            f"WHERE lower(d.department_name) = lower({_sql_literal(department)}) "
            "ORDER BY e.last_name, e.first_name"
        )

    if has_employee and wants_count and (
        "department" in normalized.split()
        or "departments" in normalized.split()
        or "each" in normalized.split()
        or "per" in normalized.split()
        or "by" in normalized.split()
    ):
        return (
            "SELECT d.department_name, COUNT(e.employee_id) AS employee_count "
            "FROM departments AS d "
            "LEFT JOIN employees AS e ON e.department_id = d.department_id "
            "GROUP BY d.department_id, d.department_name "
            "ORDER BY d.department_name"
        )

    if has_employee and wants_count:
        if employee_status:
            return (
                "SELECT COUNT(*) AS employee_count FROM employees "
                f"WHERE employment_status = {_sql_literal(employee_status)}"
            )
        return "SELECT COUNT(*) AS employee_count FROM employees"

    if department and not has_employee:
        return (
            "SELECT department_code, department_name, location "
            "FROM departments "
            f"WHERE lower(department_name) = lower({_sql_literal(department)})"
        )

    if "department" in normalized.split() or "departments" in normalized.split():
        return (
            "SELECT department_code, department_name, location "
            "FROM departments ORDER BY department_name"
        )

    if has_employee:
        if employee_status:
            status_filter = (
                f" WHERE employment_status = {_sql_literal(employee_status)}"
            )
        else:
            status_filter = ""
        return (
            "SELECT employee_number, first_name, last_name, job_title, "
            "email, employment_status FROM employees"
            f"{status_filter} ORDER BY last_name, first_name"
        )

    raise GenerationError(
        "I can answer common questions about employees, departments, projects, "
        "employee counts, and project assignments in offline mode. Try asking "
        "“How many employees are in each department?” or “List active projects.” "
        "For other questions, configure an optional compatible SQL-generation API."
    )
