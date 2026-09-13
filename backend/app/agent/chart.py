from __future__ import annotations
from app.agent.state import AgentState
from app.tools.chart_tool import create_chart_from_records


def _records_for_step(state: AgentState, step_index: int | None):
    candidates = [r for r in state.get("tool_results", []) if r.get("ok") and isinstance(r.get("data"), dict) and r["data"].get("records")]
    if step_index is not None:
        exact = [r for r in candidates if r.get("step") == step_index]
        if exact: return exact[-1]["data"]["records"]
    return candidates[-1]["data"]["records"] if candidates else []


def chart_node(state: AgentState) -> dict:
    charts = []
    errors = list(state.get("errors", []))
    trace = list(state.get("trace", []))
    for request in state.get("chart_requests", [])[:4]:
        try:
            records = _records_for_step(state, request.get("source_step"))
            if not records: continue
            chart = create_chart_from_records(
                records=records, chart_type=request.get("chart_type", "bar"),
                x=request.get("x"), y=request.get("y"), title=request.get("title", "数据分析图表"),
            )
            charts.append(chart)
        except Exception as e:
            errors.append({"stage": "chart", "error": f"{type(e).__name__}: {e}"})
            trace.append({"stage": "chart", "status": "error", "detail": str(e)})
    if charts:
        trace.append({"stage": "chart", "status": "ok", "detail": f"生成 {len(charts)} 张图表"})
    else:
        trace.append({"stage": "chart", "status": "skip", "detail": "本次无需或没有足够数据生成图表"})
    return {"charts": charts, "errors": errors, "trace": trace}
