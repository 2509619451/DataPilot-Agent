from __future__ import annotations
from html import escape
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.core.config import get_settings
from app.models.entities import AnalysisRun, Report

settings = get_settings()


def generate_html_report(db: Session, session_id: str) -> Report:
    run = db.scalars(
        select(AnalysisRun).where(
            AnalysisRun.session_id == session_id, AnalysisRun.status == "completed"
        ).order_by(AnalysisRun.created_at.desc()).limit(1)
    ).first()
    if not run or not run.final_answer:
        raise HTTPException(404, "当前会话还没有可生成报告的分析结果")
    a = run.final_answer
    def lis(items):
        return "".join(f"<li>{escape(str(x))}</li>" for x in items)
    metrics = "".join(
        f"<tr><td>{escape(str(m.get('name','')))}</td><td>{escape(str(m.get('value','')))}</td></tr>"
        for m in a.get("metrics", [])
    )
    html = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>DataPilot 分析报告</title>
<style>body{{font-family:Arial,'Microsoft YaHei',sans-serif;max-width:980px;margin:40px auto;line-height:1.7;color:#222}}h1,h2{{color:#172554}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px}}.muted{{color:#666}}</style></head><body>
<h1>DataPilot-Agent 数据分析报告</h1><p class="muted">Run ID: {escape(run.id)}</p>
<h2>问题</h2><p>{escape(run.question)}</p><h2>核心结论</h2><p>{escape(a.get('summary',''))}</p>
<h2>关键发现</h2><ol>{lis(a.get('findings',[]))}</ol><h2>关键指标</h2><table><tr><th>指标</th><th>数值</th></tr>{metrics}</table>
<h2>建议</h2><ul>{lis(a.get('recommendations',[]))}</ul><h2>限制</h2><ul>{lis(a.get('limitations',[]))}</ul></body></html>'''
    rid = str(uuid4())
    path = Path(settings.report_dir) / f"report_{rid}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    report = Report(id=rid, session_id=session_id, path=str(path))
    db.add(report); db.commit(); db.refresh(report)
    return report
