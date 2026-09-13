import pandas as pd
from app.tools.dataframe_tools import summary_statistics, groupby_aggregate
from app.tools.chart_tool import _resolve_axes


def test_summary_statistics_multiple_columns():
    df = pd.DataFrame({"sales": [10, 20, 30], "profit": [1, 5, 9], "region": ["E", "W", "E"]})
    result = summary_statistics(df, columns=["sales", "profit"])
    assert set(result["statistics"]) == {"sales", "profit"}
    assert result["statistics"]["sales"]["mean"] == 20.0
    assert result["statistics"]["profit"]["median"] == 5.0


def test_groupby_returns_real_value_field():
    df = pd.DataFrame({"region": ["E", "W", "E"], "sales": [10, 20, 30]})
    result = groupby_aggregate(df, "region", "sales", "sum")
    assert result["value_field"] == "sum_sales"
    assert result["records"][0]["sum_sales"] == 40


def test_chart_axis_auto_resolution_does_not_require_total_sales():
    df = pd.DataFrame([{"region": "E", "sum_sales": 40}, {"region": "W", "sum_sales": 20}])
    x, y = _resolve_axes(df, "region", "total_sales")
    assert x == "region"
    assert y == "sum_sales"
