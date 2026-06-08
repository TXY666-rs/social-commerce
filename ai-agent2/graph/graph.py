"""LangGraph 图结构定义 — 只负责边和节点的连接

节点函数在 graph/nodes.py 中定义，本文件只做图的组装。

图结构（单 Agent + 全量工具）：
    START → check_faq → agent → tools → guard → agent
                           ↓
                      mark_failed → agent
                           ↓
                      error_handler → END
"""

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from graph.state import AgentState
from graph.nodes import (
    check_faq_node, guard_node, mark_failed_node, error_handler_node,
    route_after_faq, route_after_agent, make_call_model,
)
from agents.tools import ALL_TOOLS
from resilience.llm_factory import get_llm


def build_react_graph(llm=None):
    """构建单 Agent React 图

    Args:
        llm: LLM 实例，为 None 时使用 get_llm()

    Returns:
        编译后的 LangGraph 图
    """
    if llm is None:
        llm = get_llm()

    call_model = make_call_model(llm)

    builder = StateGraph(AgentState)

    # ── 节点 ──
    builder.add_node("check_faq", check_faq_node)
    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(ALL_TOOLS, handle_tool_errors=True))
    builder.add_node("guard", guard_node)
    builder.add_node("mark_failed", mark_failed_node)
    builder.add_node("error_handler", error_handler_node)

    # ── 边 ──
    builder.add_edge(START, "check_faq")
    builder.add_conditional_edges("check_faq", route_after_faq, {END: END, "agent": "agent"})
    builder.add_conditional_edges("agent", route_after_agent, {
        "tools": "tools",
        "mark_failed": "mark_failed",
        "error_handler": "error_handler",
        END: END,
    })
    builder.add_edge("tools", "guard")
    builder.add_edge("guard", "agent")
    builder.add_edge("mark_failed", "agent")
    builder.add_edge("error_handler", END)

    return builder.compile()
