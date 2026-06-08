"""Agent 状态定义 — LangGraph 图共享此状态结构"""
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """Agent 状态：消息列表，add_messages 保证自动追加而非覆盖

    字段分组：
        核心:     messages, faq_reply, session_id
        上下文:   summary, sentiment_context, dialog_context
        记忆:     working_memory_context, budget_context
        容错:     last_error, is_fatal_error, retry_count
    """
    # ── 核心 ──
    messages: Annotated[list[BaseMessage], add_messages]
    faq_reply: str
    session_id: str

    # ── 上下文 ──
    summary: str
    sentiment_context: str
    dialog_context: str

    # ── 记忆 ──
    working_memory_context: str     # Working Memory 任务状态
    budget_context: str             # Token Budget 预算状态

    # ── 容错 ──
    last_error: str
    is_fatal_error: bool
    retry_count: int
