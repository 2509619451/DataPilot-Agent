from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import Chart

router = APIRouter(prefix="/charts", tags=["charts"])


@router.get("/{chart_id}")
def get_chart(chart_id: str, db: Session = Depends(get_db)):
    chart = db.get(Chart, chart_id)
    if not chart or not Path(chart.path).exists():
        raise HTTPException(404, "图表不存在")
    return FileResponse(chart.path, media_type="image/png", filename=f"{chart_id}.png")
