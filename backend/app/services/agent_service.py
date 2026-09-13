from __future__ import annotations
import json
import time
from decimal import Decimal
from datetime import date, datetime
from collections.abc import Iterator
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.agent.graph import AGENT_GRAPH
from app.core.config import get_settings
from app.models.entities import AnalysisRun, Chart
from app.models.schemas import ChatRequest
from app.services.dataset_service import get_dataset_or_404
from app.services.session_service import add_message, create_session, get_history, get_session_or_404

settings = get_settings()


def _json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            pass
    return str(value)


def _recursion_limit() -> int:
    return max(60, settings.max_agent_steps * (settings.max_retry + 2) * 2 + 10)


def _prepare(db: Session, req: ChatRequest):
    dataset = get_dataset_or_404(db, req.dataset_id)
    if req.session_id:
        chat_session = get_session_or_404(db, req.session_id)
        if chat_session.dataset_id != req.dataset_id:
            raise HTTPException(400, "session_id 与 dataset_id 不匹配")
    else:
        chat_session = create_session(db, req.dataset_id)
    add_message(db, chat_session.id, "user", req.message)
    history = get_history(db, chat_session.id, limit=12)
    run = AnalysisRun(session_id=chat_session.id, question=req.message, status="running")
    db.add(run); db.commit(); db.refresh(run)
    initial = {
        "session_id": chat_session.id,
        "dataset_id": dataset.id,
        "dataset_path": dataset.stored_path,
        "table_name": dataset.table_name,
        "question": req.message,
        "dataset_schema": dataset.profile,
        "history": history,
        "trace": [{"stage": "start", "status": "ok", "detail": "开始分析"}],
    }
    return dataset, chat_session, run, initial


def _persist(db: Session, dataset, chat_session, run: AnalysisRun, state: dict, started: float) -> dict:
    answer = state.get("final_answer") or {
        "summary": "分析未能生成最终结论。", "findings": [], "metrics": [],
        "charts": [], "recommendations": [], "limitations": ["Agent 未正常完成 Reporter 阶段。"],
    }
    public_charts = []
    for c in state.get("charts", []):
        chart = Chart(
            id=c["id"], session_id=chat_session.id, dataset_id=dataset.id,
            title=c.get("title", "数据分析图表"), chart_type=c.get("chart_type", "bar"),
            path=c["path"], meta={"x": c.get("x"), "y": c.get("y")},
        )
        db.merge(chart)
        public_charts.append({
            "id": c["id"], "title": c.get("title"), "chart_type": c.get("chart_type"),
            "x": c.get("x"), "y": c.get("y"), "url": f"/api/charts/{c['id']}",
        })
    answer["charts"] = public_charts
    answer = _json_safe(answer)
    run.status = "completed"
    run.plan = _json_safe(state.get("plan", []))
    run.tool_calls = _json_safe(state.get("tool_calls", []))
    run.tool_results = _json_safe(state.get("tool_results", []))
    run.charts = _json_safe(public_charts)
    run.errors = _json_safe(state.get("errors", []))
    run.resolved_errors = _json_safe(state.get("resolved_errors", []))
    run.final_answer = answer
    run.execution_ms = int((time.perf_counter() - started) * 1000)
    db.add(run)
    add_message(db, chat_session.id, "assistant", answer.get("summary", ""), payload=answer)
    db.commit()
    return answer


def run_agent(db: Session, req: ChatRequest) -> dict:
    dataset, chat_session, run, initial = _prepare(db, req)
    started = time.perf_counter()
    try:
        state = AGENT_GRAPH.invoke(initial, config={"recursion_limit": _recursion_limit()})
        answer = _persist(db, dataset, chat_session, run, state, started)
        return {"session_id": chat_session.id, "run_id": run.id, "answer": answer, "trace": state.get("trace", [])}
    except Exception as e:
        run.status = "failed"; run.errors = [{"error": f"{type(e).__name__}: {e}"}]
        run.execution_ms = int((time.perf_counter() - started) * 1000); db.add(run); db.commit()
        raise


def stream_agent(db: Session, req: ChatRequest) -> Iterator[str]:
    dataset, chat_session, run, initial = _prepare(db, req)
    started = time.perf_counter(); final_state = initial; sent = 0
    yield f"data: {json.dumps({'type':'session','session_id':chat_session.id,'run_id':run.id}, ensure_ascii=False)}\n\n"
    try:
        for state in AGENT_GRAPH.stream(initial, config={"recursion_limit": _recursion_limit()}, stream_mode="values"):
            final_state = state
            trace = state.get("trace", [])
            while sent < len(trace):
                yield f"data: {json.dumps({'type':'trace','data':trace[sent]}, ensure_ascii=False, default=str)}\n\n"
                sent += 1
        answer = _persist(db, dataset, chat_session, run, final_state, started)
        payload = {"type": "done", "session_id": chat_session.id, "run_id": run.id, "answer": answer}
        yield f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
    except Exception as e:
        run.status = "failed"; run.errors = [{"error": f"{type(e).__name__}: {e}"}]
        run.execution_ms = int((time.perf_counter() - started) * 1000); db.add(run); db.commit()
        yield f"data: {json.dumps({'type':'error','message':str(e)}, ensure_ascii=False)}\n\n"
