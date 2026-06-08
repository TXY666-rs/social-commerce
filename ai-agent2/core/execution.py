"""图执行模块 — 流式输出 + 重试 + Token Budget 记录

负责执行 LangGraph 图并处理流式输出。
执行完成后将 Token 消耗记录到 Budget 管理器。
"""

import asyncio
import time
from langchain_core.messages import AIMessageChunk, ToolMessage
import structlog

from graph.graph import build_react_graph
from resilience.llm_factory import get_llm, LLMFallbackException
from agents.tools.constants import ERROR_KEYWORDS

logger = structlog.get_logger(__name__)


# 单 Agent 图（延迟初始化）
_graph = None


def _get_graph():
    """获取或初始化图实例"""
    global _graph
    if _graph is None:
        _graph = build_react_graph(get_llm())
    return _graph


def rebuild_graph():
    """LLM 降级后重建图（清除旧的 LLM 绑定）"""
    global _graph
    _graph = build_react_graph(get_llm())
    logger.info("graph_rebuilt_after_llm_fallback")


async def execute_graph_with_retry(context: dict, session_id: str, user_id: str):
    """执行图并流式输出结果

    Args:
        context: 上下文字典，包含 input_messages, summary,
                 working_memory_context, budget_context, token_budget 等
        session_id: 会话 ID
        user_id: 用户 ID

    Yields:
        流式输出的文本片段，或特殊标记 "_FAQ_" 和 "[[TRANSFER_TO_HUMAN]]"
    """
    graph = _get_graph()
    transfer_triggered = False
    tool_calls_made: set[str] = set()
    tool_errors_made: set[str] = set()
    total_input_tokens = 0
    total_output_tokens = 0
    t_start = time.monotonic()

    # 从 context 中取出 Token Budget（用于记录消耗）
    token_budget = context.get("token_budget")

    try:
        async for mode, chunk in graph.astream(
            {"messages": context["input_messages"], "faq_reply": "",
             "session_id": session_id,
             "summary": context["summary"],
             "sentiment_context": context["sentiment_context"],
             "dialog_context": context["dialog_context"],
             "working_memory_context": context.get("working_memory_context", ""),
             "budget_context": context.get("budget_context", "")},
            stream_mode=["messages", "values"],
            config={"recursion_limit": 16},
        ):
            if mode == "values":
                faq_reply = chunk.get("faq_reply", "")
                if faq_reply:
                    try:
                        from monitoring.dashboard import record_chat as _record
                        asyncio.create_task(_record(session_id, is_faq=True, agent_type="faq"))
                    except Exception:
                        pass
                    yield ("_FAQ_", faq_reply)
                    return
            elif mode == "messages":
                msg, _ = chunk
                if isinstance(msg, AIMessageChunk) and msg.content:
                    yield msg.content
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_calls_made.add(tc.get("name", ""))
                        if tc.get("name") == "transfer_to_human":
                            transfer_triggered = True
                # 累加 token 消耗
                usage = getattr(msg, "usage_metadata", None) or {}
                total_input_tokens += int(usage.get("input_tokens", 0))
                total_output_tokens += int(usage.get("output_tokens", 0))
                # 检测工具错误返回
                if isinstance(msg, ToolMessage):
                    content = str(msg.content or "")
                    if any(kw in content for kw in ERROR_KEYWORDS):
                        tool_errors_made.add(getattr(msg, "name", "unknown"))
    except Exception as e:
        logger.error("graph_execution_failed", error=str(e), session_id=session_id)
        yield "抱歉，处理您的请求时出现了问题，请稍后重试。"
        return

    # ── 记录 Token Budget ──
    if token_budget and (total_input_tokens > 0 or total_output_tokens > 0):
        token_budget.record(total_input_tokens, total_output_tokens)

    # ── 记录运营统计 ──
    duration_ms = (time.monotonic() - t_start) * 1000
    try:
        from monitoring.dashboard import record_chat as _record, record_conversation_detail as _detail
        asyncio.create_task(_record(
            session_id,
            is_faq=False,
            agent_type="agent",
            tool_calls=list(tool_calls_made) if tool_calls_made else None,
            tool_errors=list(tool_errors_made) if tool_errors_made else None,
            sentiment=context["sentiment_level"],
            transfer=transfer_triggered,
        ))
        asyncio.create_task(_detail(
            user_id or "anonymous",
            total_input_tokens,
            total_output_tokens,
            duration_ms,
            "agent",
        ))
    except Exception:
        pass

    # ── 将元数据存入 context 供上层读取 ──
    context["_tools_called"] = list(tool_calls_made)
    context["_tool_errors"] = list(tool_errors_made)
    context["_duration_ms"] = duration_ms
    context["_input_tokens"] = total_input_tokens
    context["_output_tokens"] = total_output_tokens
    context["_transfer"] = transfer_triggered

    if transfer_triggered:
        yield "[[TRANSFER_TO_HUMAN]]"
