from app.agent.verifier import verifier_node


def test_recovered_error_does_not_pollute_limitations_source():
    state = {
        "current_step": 0,
        "plan": [{"description": "x", "tool": "summary_statistics", "args": {"columns": ["sales"]}}],
        "tool_results": [{"step": 0, "tool": "summary_statistics", "ok": True, "data": {"statistics": {}}}],
        "active_error": {"step": 0, "error": "KeyError: total_sales"},
        "retry_count": 1,
        "errors": [],
        "resolved_errors": [],
        "trace": [],
    }
    out = verifier_node(state)
    assert out["active_error"] is None
    assert out["resolved_errors"][0]["error"] == "KeyError: total_sales"
    assert state["errors"] == []
