from __future__ import annotations
import json
from app.agent.llm import ask_json
from app.agent.state import AgentState


def _compact_results(state: AgentState) -> list[dict]:
    out = []
    for r in state.get("tool_results", []):
        if not r.get("ok"): continue
        data = r.get("data", {})
        compact = dict(data)
        if isinstance(compact.get("records"), list): compact["records"] = compact["records"][:30]
        out.append({"step": r.get("step"), "tool": r.get("tool"), "data": compact})
    return out


def _fallback_report(state: AgentState) -> dict:
    results = _compact_results(state)
    findings = []
    metrics = []
    for r in results:
        data = r["data"]
        if data.get("records"):
            findings.append(f"{r['tool']} 返回 {len(data['records'])} 条结果，详见执行结果与图表。")
        if data.get("statistics"):
            for col, stats in data["statistics"].items():
                if "mean" in stats:
                    metrics.append({"name": f"{col} mean", "value": round(stats["mean"], 5)})
    return {
        "summary": "分析已完成；结论严格基于成功执行的工具结果。" if results else "本次没有获得足以支持数值结论的成功工具结果。",
        "findings": findings[:8], "metrics": metrics[:20],
        "charts": [{k: c.get(k) for k in ("id", "title", "chart_type", "x", "y")} for c in state.get("charts", [])],
        "recommendations": ["可继续基于当前会话追问更具体的地区、产品、时间或异常明细。"] if results else [],
        "limitations": [e.get("error", str(e)) for e in state.get("errors", [])],
    }


def reporter_node(state: AgentState) -> dict:
    results = _compact_results(state)
    system = """你是 DataPilot-Agent Reporter。根据真实工具结果输出结构化分析结论。
硬规则：
1. 不得编造任何字段、数值、趋势或因果。
2. 只使用成功工具结果中的数字。
3. errors 只包含最终未恢复的错误；resolved_errors 已成功恢复，不得写入 limitations。
4. 对极小样本、缺失步骤、空结果要明确限制。
5. 只返回 JSON，结构：
{"summary":"","findings":[],"metrics":[{"name":"","value":0}],"recommendations":[],"limitations":[]}"""
    user = f"""问题：{state['question']}
目标：{state.get('goal','')}
成功工具结果：{json.dumps(results, ensure_ascii=False, default=str)}
未恢复错误：{json.dumps(state.get('errors', []), ensure_ascii=False)}
图表：{json.dumps([{k:c.get(k) for k in ('id','title','chart_type','x','y')} for c in state.get('charts', [])], ensure_ascii=False)}"""
    try:
        answer = ask_json(system, user) or _fallback_report(state)
    except Exception:
        answer = _fallback_report(state)
    answer.setdefault("summary", "")
    for key in ("findings", "metrics", "recommendations", "limitations"):
        answer.setdefault(key, [])
    answer["charts"] = [{k: c.get(k) for k in ("id", "title", "chart_type", "x", "y")} for c in state.get("charts", [])]
    trace = list(state.get("trace", [])) + [{"stage": "reporter", "status": "ok", "detail": "生成结构化最终结论"}]
    return {"final_answer": answer, "trace": trace}
