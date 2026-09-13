from dataclasses import dataclass
from typing import Any, Callable
import pandas as pd
from .dataframe_tools import get_dataset_schema, summary_statistics, groupby_aggregate, filter_data, correlation_analysis, time_series_analysis, detect_outliers
from .sql_tool import query_database
from .python_tool import run_python

@dataclass
class ToolContext:
    df: pd.DataFrame
    table_name: str
    dataset_path: str

PANDAS_TOOLS: dict[str, Callable[..., dict]] = {
    "get_dataset_schema": get_dataset_schema, "summary_statistics": summary_statistics,
    "groupby_aggregate": groupby_aggregate, "filter_data": filter_data,
    "correlation_analysis": correlation_analysis, "time_series_analysis": time_series_analysis,
    "detect_outliers": detect_outliers,
}
TOOL_DESCRIPTIONS = {
    "get_dataset_schema": "查看字段名称、类型和行数。args={}",
    "summary_statistics": "一次统计一个或多个数值字段。args={columns:[字段1,字段2]}",
    "groupby_aggregate": "按分类字段聚合指标。args={group_by,metric,aggregation,sort?,limit?}",
    "filter_data": "按条件筛选。args={column,operator,value,columns?,limit?}",
    "correlation_analysis": "相关性分析。args={columns:[...],method?}",
    "time_series_analysis": "时间序列聚合。args={date_column,metric,aggregation,freq}",
    "detect_outliers": "异常检测。args={column,method}",
    "query_database": "只读 PostgreSQL 查询。args={sql}；只能访问当前 table_name",
    "run_python": "隔离 Python Sandbox，高级分析时使用；预置 DataFrame 变量 df。args={code}",
}

def execute_tool(name: str, args: dict[str, Any], ctx: ToolContext) -> dict:
    if name in PANDAS_TOOLS: return PANDAS_TOOLS[name](ctx.df, **args)
    if name == "query_database": return query_database(ctx.table_name, **args)
    if name == "run_python": return run_python(ctx.dataset_path, **args)
    raise ValueError(f"未知工具: {name}")
