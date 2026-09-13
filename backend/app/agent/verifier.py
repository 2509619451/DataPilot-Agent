from __future__ import annotations
import difflib
import json
from copy import deepcopy
from app.agent.state import AgentState
from app.core.config import get_settings
from app.tools.registry import TOOL_DESCRIPTIONS

settings = get_settings()


def _all_fields(state: AgentState) -> list[str]:
    return [f["name"] for f in state["dataset_schema"].get("fields", [])]


def _closest(value: str, fields: list[str]) -> str:
    m = difflib.get_close_matches(value, fields, n=1, cutoff=0.45)
    return m[0] if m else value


def _repair_args_heuristic(args, fields):
    args = deepcopy(args)
    field_keys = {"column", "metric", "date_column", "group_by"}
    for key, value in list(args.items()):
        if key in field_keys and isinstance(value, str) and value not in fields:
            args[key] = _closest(value, fields)
        elif key in {"columns", "group_by"} and isinstance(value, list):
            args[key] = [_closest(v, fields) if isinstance(v, str) and v not in fields else v for v in value]
    return args


def _repair_step(state: AgentState, step: dict, error: dict) -> dict:
    fields = _all_fields(state)
    system = """你是 DataPilot-Agent 的错误恢复器。根据工具错误修复当前步骤。
只能修改当前步骤的 tool/args，不要编造字段。若是字段错误，只能从真实字段中选择。
只返回 JSON：{"tool":"...","args":{},"reason":"..."}"""
    user = f"当前步骤：{json.dumps(step, ensure_ascii=False)}\n错误：{json.dumps(error, ensure_ascii=False)}\n真实字段：{fields}\n工具：{json.dumps(TOOL_DESCRIPTIONS, ensure_ascii=False)}"
    try:
        from app.agent.llm import ask_json
        repaired = ask_json(system, user)
        if repaired and repaired.get("tool") in TOOL_DESCRIPTIONS:
            return {**step, "tool": repaired["tool"], "args": repaired.get("args", {})}
    except Exception:
        pass
    return {**step, "args": _repair_args_heuristic(step.get("args", {}), fields)}


def verifier_node(state: AgentState) -> dict:
    idx = state.get("current_step", 0)
    plan = list(state.get("plan", []))
    last = state.get("tool_results", [])[-1] if state.get("tool_results") else {"ok": False, "error": "没有执行结果"}
    trace = list(state.get("trace", []))

    if last.get("ok"):
        resolved = list(state.get("resolved_errors", []))
        if state.get("active_error"):
            resolved.append(state["active_error"])
        next_idx = idx + 1
        trace.append({"stage": "verifier", "status": "ok", "detail": f"Step {idx+1} 校验通过"})
        return {
            "current_step": next_idx, "retry_count": 0, "active_error": None,
            "resolved_errors": resolved,
            "next_node": "executor" if next_idx < len(plan) else "chart",
            "trace": trace,
        }

    retry = state.get("retry_count", 0)
    error = state.get("active_error") or {"step": idx, "error": last.get("error", "未知错误")}
    if retry < settings.max_retry:
        plan[idx] = _repair_step(state, plan[idx], error)
        trace.append({"stage": "verifier", "status": "retry", "detail": f"Step {idx+1} 自动修复并重试（{retry+1}/{settings.max_retry}）"})
        return {"plan": plan, "retry_count": retry + 1, "next_node": "executor", "trace": trace}

    # 只有超过重试上限仍失败，才进入 unresolved errors；已恢复错误不会污染最终 limitations。
    errors = list(state.get("errors", [])) + [error]
    next_idx = idx + 1
    trace.append({"stage": "verifier", "status": "failed", "detail": f"Step {idx+1} 达到重试上限，继续后续步骤"})
    return {
        "errors": errors, "current_step": next_idx, "retry_count": 0, "active_error": None,
        "next_node": "executor" if next_idx < len(plan) else "chart", "trace": trace,
    }


def route_after_verifier(state: AgentState) -> str:
    return state.get("next_node", "chart")
