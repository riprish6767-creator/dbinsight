from insightsql.history import get_history, initialize_history, record_query


def test_records_query_metadata_without_result_values_and_applies_limit(tmp_path):
    path = tmp_path / "data" / "history.db"
    initialize_history(path, history_limit=2)

    for index in range(3):
        record_query(
            path,
            2,
            question=f"Question {index}",
            sql="SELECT employee_id FROM employees",
            columns=["employee_id"],
            row_count=index,
            truncated=False,
            elapsed_ms=1,
        )

    items = get_history(path, limit=10)

    assert len(items) == 2
    assert items[0]["question"] == "Question 2"
    assert "rows" not in items[0]
