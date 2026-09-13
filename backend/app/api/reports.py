from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import Report
from app.models.schemas import ReportRequest
from app.services.report_service import generate_html_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("")
def create_report(body: ReportRequest, db: Session = Depends(get_db)):
    report = generate_html_report(db, body.session_id)
    return {"report_id": report.id, "url": f"/api/reports/{report.id}"}


@router.get("/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if not report or not Path(report.path).exists():
        raise HTTPException(404, "报告不存在")
    return FileResponse(report.path, media_type="text/html", filename=f"datapilot-report-{report_id}.html")
