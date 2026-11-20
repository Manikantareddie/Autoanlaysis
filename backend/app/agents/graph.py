from typing_extensions import TypedDict
from langgraph.graph import START, END, StateGraph
from app.agents.planner import create_plan, create_sql

class AnalysisState(TypedDict, total=False):
    question: str
    profile: dict
    context: dict | None
    plan: object
    proposal: object

def plan_node(state: AnalysisState) -> dict:
    return {"plan": create_plan(state["question"], state["profile"], state.get("context"))}

def sql_node(state: AnalysisState) -> dict:
    return {"proposal": create_sql(state["question"], state["plan"], state["profile"], state.get("context"))}

analysis_graph = StateGraph(AnalysisState).add_node("plan", plan_node).add_node("generate_sql", sql_node).add_edge(START, "plan").add_edge("plan", "generate_sql").add_edge("generate_sql", END).compile()

