from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.cache import cache_get_json, cache_set_json
from app.core.database import get_db
from app.models.entities import Dataset
from app.models.schemas import UploadResponse
from app.services.dataset_service import get_dataset_or_404, save_upload

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/upload", response_model=UploadResponse)
async def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)):
    dataset = save_upload(db, file)
    await cache_set_json(f"dataset:profile:{dataset.id}", dataset.profile, ttl=3600)
    return UploadResponse(dataset_id=dataset.id, filename=dataset.filename, rows=dataset.row_count, columns=dataset.column_count, profile=dataset.profile)


@router.get("")
def list_datasets(db: Session = Depends(get_db)):
    rows = db.scalars(select(Dataset).order_by(Dataset.created_at.desc()).limit(100)).all()
    return [{"dataset_id": d.id, "filename": d.filename, "rows": d.row_count, "columns": d.column_count, "created_at": d.created_at} for d in rows]


@router.get("/{dataset_id}/profile")
async def dataset_profile(dataset_id: str, db: Session = Depends(get_db)):
    cached = await cache_get_json(f"dataset:profile:{dataset_id}")
    if cached is not None:
        return cached
    dataset = get_dataset_or_404(db, dataset_id)
    await cache_set_json(f"dataset:profile:{dataset_id}", dataset.profile, ttl=3600)
    return dataset.profile
