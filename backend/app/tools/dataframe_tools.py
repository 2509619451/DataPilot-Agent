from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd


def _check_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise KeyError(f"字段不存在: {missing}; 可用字段: {list(df.columns)}")


def get_dataset_schema(df: pd.DataFrame, **_: Any) -> dict:
    return {"columns": [{"name": str(c), "type": str(df[c].dtype)} for c in df.columns], "rows": int(len(df))}


def summary_statistics(df: pd.DataFrame, columns: str | list[str] | None = None, **_: Any) -> dict:
    """V4 修复：支持一次统计多列。"""
    if columns is None:
        cols = list(df.select_dtypes(include="number").columns)
    elif isinstance(columns, str):
        cols = [columns]
    else:
        cols = list(columns)
    if not cols:
        raise ValueError("没有可统计的数值字段")
    _check_columns(df, cols)
    result = {}
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce").dropna()
        if s.empty:
            result[c] = {"count": 0}; continue
        result[c] = {
            "count": int(s.count()), "mean": float(s.mean()), "median": float(s.median()),
            "std": float(s.std(ddof=1)) if len(s) > 1 else 0.0, "min": float(s.min()),
            "max": float(s.max()), "q1": float(s.quantile(0.25)), "q3": float(s.quantile(0.75)),
        }
    return {"statistics": result}


def groupby_aggregate(df: pd.DataFrame, group_by: str | list[str], metric: str, aggregation: str = "sum", sort: str = "desc", limit: int = 50, **_: Any) -> dict:
    groups = [group_by] if isinstance(group_by, str) else list(group_by)
    _check_columns(df, groups + [metric])
    allowed = {"sum", "mean", "median", "min", "max", "count", "nunique"}
    if aggregation not in allowed:
        raise ValueError(f"aggregation 仅支持 {sorted(allowed)}")
    output_col = f"{aggregation}_{metric}"
    grouped = df.groupby(groups, dropna=False)[metric].agg(aggregation).reset_index(name=output_col)
    grouped = grouped.sort_values(output_col, ascending=(sort == "asc")).head(max(1, min(limit, 500)))
    return {"records": grouped.replace({np.nan: None}).to_dict("records"), "value_field": output_col, "group_fields": groups}


def filter_data(df: pd.DataFrame, column: str, operator: str, value: Any, columns: list[str] | None = None, limit: int = 100, **_: Any) -> dict:
    _check_columns(df, [column]); s = df[column]
    ops = {
        "==": lambda: s == value, "!=": lambda: s != value,
        ">": lambda: pd.to_numeric(s, errors="coerce") > float(value),
        ">=": lambda: pd.to_numeric(s, errors="coerce") >= float(value),
        "<": lambda: pd.to_numeric(s, errors="coerce") < float(value),
        "<=": lambda: pd.to_numeric(s, errors="coerce") <= float(value),
        "contains": lambda: s.astype(str).str.contains(str(value), case=False, na=False),
    }
    if operator not in ops:
        raise ValueError(f"不支持的 operator: {operator}")
    out = df.loc[ops[operator]()] 
    if columns:
        _check_columns(out, columns); out = out[columns]
    return {"count": int(len(out)), "records": out.head(limit).replace({np.nan: None}).to_dict("records")}


def correlation_analysis(df: pd.DataFrame, columns: list[str], method: str = "pearson", **_: Any) -> dict:
    _check_columns(df, columns)
    if len(columns) < 2: raise ValueError("相关性分析至少需要两个字段")
    corr = df[columns].apply(pd.to_numeric, errors="coerce").corr(method=method)
    return {"matrix": corr.round(6).replace({np.nan: None}).to_dict()}


def time_series_analysis(df: pd.DataFrame, date_column: str, metric: str, aggregation: str = "sum", freq: str = "M", **_: Any) -> dict:
    _check_columns(df, [date_column, metric])
    allowed = {"sum", "mean", "median", "min", "max", "count"}
    if aggregation not in allowed: raise ValueError(f"aggregation 仅支持 {sorted(allowed)}")
    temp = df[[date_column, metric]].copy(); temp[date_column] = pd.to_datetime(temp[date_column], errors="coerce")
    temp = temp.dropna(subset=[date_column])
    if temp.empty: raise ValueError(f"字段 {date_column} 无法解析为日期")
    value_field = f"{aggregation}_{metric}"
    out = temp.set_index(date_column).resample(freq)[metric].agg(aggregation).reset_index(name=value_field)
    out[date_column] = out[date_column].dt.strftime("%Y-%m-%d")
    return {"records": out.replace({np.nan: None}).to_dict("records"), "date_field": date_column, "value_field": value_field}


def detect_outliers(df: pd.DataFrame, column: str, method: str = "iqr", z_threshold: float = 3.0, limit: int = 100, **_: Any) -> dict:
    _check_columns(df, [column]); s = pd.to_numeric(df[column], errors="coerce")
    if method == "iqr":
        q1, q3 = s.quantile(0.25), s.quantile(0.75); iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr; mask = (s < low) | (s > high)
        bounds = {"low": float(low), "high": float(high)}
    elif method == "zscore":
        std = s.std(ddof=0); z = (s - s.mean()) / (std if std else 1); mask = z.abs() > z_threshold
        bounds = {"z_threshold": float(z_threshold)}
    else: raise ValueError("method 仅支持 iqr / zscore")
    out = df.loc[mask]
    return {"count": int(mask.sum()), "bounds": bounds, "records": out.head(limit).replace({np.nan: None}).to_dict("records")}
