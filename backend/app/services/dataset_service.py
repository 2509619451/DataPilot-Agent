from __future__ import annotations
import math
import re
from pathlib import Path
from uuid import uuid4
import numpy as np
import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import engine
from app.models.entities import Dataset

settings = get_settings()
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def _safe_filename(name: str) -> str:
    name = Path(name or "dataset.csv").name
    return re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]", "_", name)


def read_dataframe(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin1"):
            try:
                return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"不支持的文件类型: {suffix}")


def _json_value(v):
    if pd.isna(v):
        return None
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        x = float(v)
        return None if math.isnan(x) or math.isinf(x) else x
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    return v.item() if hasattr(v, "item") else v


def build_profile(df: pd.DataFrame, filename: str) -> dict:
    columns = []
    for col in df.columns:
        s = df[col]
        info = {
            "name": str(col), "dtype": str(s.dtype),
            "missing": int(s.isna().sum()), "unique": int(s.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(s):
            desc = s.describe(percentiles=[0.25, 0.5, 0.75])
            info["statistics"] = {k: _json_value(v) for k, v in desc.items()}
        else:
            top = s.dropna().astype(str).value_counts().head(5)
            info["top_values"] = [{"value": str(k), "count": int(v)} for k, v in top.items()]
        columns.append(info)
    return {
        "filename": filename, "rows": int(len(df)), "columns": int(len(df.columns)),
        "fields": columns, "duplicate_rows": int(df.duplicated().sum()),
    }


def save_upload(db: Session, upload: UploadFile) -> Dataset:
    filename = _safe_filename(upload.filename or "dataset.csv")
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "仅支持 CSV / XLSX / XLS 文件")
    raw = upload.file.read()
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"文件不能超过 {settings.max_upload_mb} MB")

    dataset_id = str(uuid4())
    stored_name = f"{dataset_id}_{filename}"
    path = Path(settings.upload_dir) / stored_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    try:
        df = read_dataframe(path)
    except Exception as e:
        path.unlink(missing_ok=True)
        raise HTTPException(400, f"读取数据失败: {e}") from e
    if df.empty:
        path.unlink(missing_ok=True)
        raise HTTPException(400, "数据集为空")

    df.columns = [str(c).strip() for c in df.columns]
    table_name = f"dataset_{dataset_id.replace('-', '')[:16]}"
    profile = build_profile(df, filename)
    df.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=2000, method="multi")

    entity = Dataset(
        id=dataset_id, filename=filename, stored_path=str(path), table_name=table_name,
        row_count=len(df), column_count=len(df.columns), profile=profile,
    )
    db.add(entity); db.commit(); db.refresh(entity)
    return entity


def get_dataset_or_404(db: Session, dataset_id: str) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "数据集不存在")
    return dataset
