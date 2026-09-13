from langgraph.graph import StateGraph, START, END
from app.agent.state import AgentState
from app.agent.planner import planner_node
from app.agent.executor import executor_node
from app.agent.verifier import verifier_node, route_after_verifier
from app.agent.chart import chart_node
from app.agent.reporter import reporter_node


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("chart", chart_node)
    graph.add_node("reporter", reporter_node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "verifier")
    graph.add_conditional_edges("verifier", route_after_verifier, {"executor": "executor", "chart": "chart"})
    graph.add_edge("chart", "reporter")
    graph.add_edge("reporter", END)
    return graph.compile()


AGENT_GRAPH = build_graph()
