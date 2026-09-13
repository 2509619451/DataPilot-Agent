from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    session_id: str
    dataset_id: str
    dataset_path: str
    table_name: str
    question: str
    dataset_schema: dict[str, Any]
    history: list[dict[str, Any]]

    goal: str
    plan: list[dict[str, Any]]
    chart_requests: list[dict[str, Any]]
    current_step: int
    retry_count: int
    active_error: dict[str, Any] | None
    next_node: str

    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    resolved_errors: list[dict[str, Any]]
    charts: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    final_answer: dict[str, Any]
