from __future__ import annotations
import re
from sqlalchemy import text
from app.core.config import get_settings
settings = get_settings()
FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|call|execute|vacuum|analyze)\b", re.I)


def query_database(table_name: str, sql: str, **_) -> dict:
    cleaned = sql.strip().rstrip(";")
    if ";" in cleaned: raise ValueError("只允许单条 SQL")
    if not re.match(r"^(select|with)\b", cleaned, re.I): raise ValueError("SQL Tool 只允许 SELECT / WITH 查询")
    if FORBIDDEN.search(cleaned): raise ValueError("检测到禁止的 SQL 关键字")
    refs = re.findall(r"\b(?:from|join)\s+\"?([A-Za-z_][A-Za-z0-9_]*)\"?", cleaned, re.I)
    ctes = set(re.findall(r"(?:\bwith|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s+as\s*\(", cleaned, re.I))
    if refs and any(r != table_name and r not in ctes for r in refs):
        raise ValueError(f"SQL 只能查询当前数据表 {table_name}")
    from app.core.database import engine
    with engine.begin() as conn:
        conn.execute(text(f"SET LOCAL statement_timeout = {int(settings.sql_timeout_ms)}"))
        rows = conn.execute(text(cleaned)).mappings().fetchmany(500)
    return {"records": [dict(r) for r in rows], "row_count": len(rows)}
