from __future__ import annotations
import time
from app.agent.state import AgentState
from app.services.dataset_service import read_dataframe
from app.tools.registry import ToolContext, execute_tool


def executor_node(state: AgentState) -> dict:
    idx = state.get("current_step", 0)
    plan = state.get("plan", [])
    if idx >= len(plan):
        return {"next_node": "chart"}
    step = plan[idx]
    call = {"step": idx, "description": step.get("description", ""), "tool": step.get("tool"), "args": step.get("args", {})}
    tool_calls = list(state.get("tool_calls", [])) + [call]
    started = time.perf_counter()
    try:
        df = read_dataframe(state["dataset_path"])
        df.columns = [str(c).strip() for c in df.columns]
        ctx = ToolContext(df=df, table_name=state["table_name"], dataset_path=state["dataset_path"])
        data = execute_tool(call["tool"], call["args"], ctx)
        result = {"step": idx, "tool": call["tool"], "ok": True, "data": data, "elapsed_ms": int((time.perf_counter()-started)*1000)}
        active_error = state.get("active_error") if state.get("retry_count", 0) > 0 else None
    except Exception as e:
        result = {"step": idx, "tool": call["tool"], "ok": False, "error": f"{type(e).__name__}: {e}", "elapsed_ms": int((time.perf_counter()-started)*1000)}
        active_error = {"step": idx, "tool": call["tool"], "args": call["args"], "error": result["error"]}

    tool_results = list(state.get("tool_results", [])) + [result]
    trace = list(state.get("trace", [])) + [{"stage": "executor", "status": "ok" if result["ok"] else "error", "detail": f"Step {idx+1}: {call['tool']}"}]
    return {"tool_calls": tool_calls, "tool_results": tool_results, "active_error": active_error, "trace": trace}
