import pytest
from app.tools.sql_tool import query_database


def test_reject_write_sql_before_database_execution():
    with pytest.raises(ValueError):
        query_database("dataset_abc", "DELETE FROM dataset_abc")


def test_reject_other_table_before_database_execution():
    with pytest.raises(ValueError):
        query_database("dataset_abc", "SELECT * FROM users")
