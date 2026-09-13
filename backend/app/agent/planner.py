from __future__ import annotations
import json
from app.agent.llm import ask_json
from app.agent.state import AgentState
from app.tools.registry import TOOL_DESCRIPTIONS


def _fallback_plan(state: AgentState) -> dict:
    q = state["question"].lower()
    fields = [f["name"] for f in state["dataset_schema"].get("fields", [])]
    numeric = [f["name"] for f in state["dataset_schema"].get("fields", []) if any(x in f.get("dtype", "").lower() for x in ("int", "float", "double"))]
    categorical = [c for c in fields if c not in numeric]
    steps = []
    charts = []

    # 无 LLM 时仍提供可运行的最低限度启发式。
    if any(k in q for k in ("平均", "均值", "中位", "标准差", "描述", "统计")) and numeric:
        steps.append({"description": "计算数值字段描述性统计", "tool": "summary_statistics", "args": {"columns": numeric[:8]}})
    elif any(k in q for k in ("异常", "离群")) and numeric:
        steps.append({"description": "检测异常值", "tool": "detect_outliers", "args": {"column": numeric[0], "method": "iqr"}})
    elif any(k in q for k in ("相关", "关系")) and len(numeric) >= 2:
        steps.append({"description": "计算相关系数", "tool": "correlation_analysis", "args": {"columns": numeric[:5]}})
    elif categorical and numeric:
        steps.append({"description": "按分类字段汇总数值指标", "tool": "groupby_aggregate", "args": {"group_by": categorical[0], "metric": numeric[0], "aggregation": "sum", "limit": 20}})
        charts.append({"source_step": 0, "chart_type": "bar", "title": f"{categorical[0]} - {numeric[0]} 汇总"})
    else:
        steps.append({"description": "查看数据结构", "tool": "get_dataset_schema", "args": {}})

    return {"goal": state["question"], "steps": steps, "charts": charts}


def planner_node(state: AgentState) -> dict:
    schema = state["dataset_schema"]
    tool_text = "\n".join(f"- {k}: {v}" for k, v in TOOL_DESCRIPTIONS.items())
    system = """你是 DataPilot-Agent 的 Planner。你的职责是把用户问题拆成少量、可验证的数据分析步骤。
规则：
1. 所有数值必须由工具计算，不允许猜。
2. 只能使用提供的真实字段；字段不确定时先 get_dataset_schema。
3. 优先用 Pandas 工具；复杂多步运算再用只读 SQL 或 Python Sandbox。
4. summary_statistics 的 columns 可以一次传多个字段。
5. 最多 8 个步骤。
6. charts 仅在比较、趋势、分布等确实有帮助时生成；source_step 指向会返回 records 的步骤序号。
7. 只返回 JSON，不要 Markdown。
JSON 结构：{"goal":"...","steps":[{"description":"...","tool":"...","args":{}}],"charts":[{"source_step":0,"chart_type":"bar|line|pie|scatter","x":null,"y":null,"title":"..."}]}"""
    user = f"""用户问题：{state['question']}
当前 PostgreSQL 表名：{state['table_name']}
数据集 Profile：{json.dumps(schema, ensure_ascii=False, default=str)}
最近对话：{json.dumps(state.get('history', [])[-8:], ensure_ascii=False, default=str)}
可用工具：\n{tool_text}"""
    try:
        result = ask_json(system, user) or _fallback_plan(state)
    except Exception:
        result = _fallback_plan(state)

    steps = [s for s in result.get("steps", []) if s.get("tool") in TOOL_DESCRIPTIONS][:8]
    if not steps:
        steps = _fallback_plan(state)["steps"]
    trace = list(state.get("trace", [])) + [{"stage": "planner", "status": "ok", "detail": f"生成 {len(steps)} 个分析步骤"}]
    return {
        "goal": result.get("goal", state["question"]),
        "plan": steps,
        "chart_requests": result.get("charts", [])[:4],
        "current_step": 0,
        "retry_count": 0,
        "active_error": None,
        "tool_calls": [],
        "tool_results": [],
        "errors": [],
        "resolved_errors": [],
        "charts": [],
        "trace": trace,
    }
