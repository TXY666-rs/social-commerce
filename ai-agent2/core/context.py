"""上下文构建模块 — 会话历史 + 情感 + 对话进度 + Working Memory + Token Budget

负责构建 LLM 调用所需的完整上下文。

上下文组成：
    1. 会话摘要（历史对话要点）
    2. 情感上下文（用户情绪状态）
    3. 对话进度（最近几轮的关键信息）
    4. Working Memory（当前任务状态）
    5. Token Budget（预算状态）
    6. 消息裁剪（根据预算动态调整保留轮数）
"""

from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
import structlog

from agents.summarizer import get_session_summary
from core.sentiment import detect_sentiment, get_escalation, build_sentiment_context, get_sentiment_count, save_sentiment_count
from core.dialog_tracker import build_dialog_context
from memory.working_memory import get_working_memory
from cost.token_budget import get_token_budget
from agents.tools.constants import MAX_CONTEXT_MESSAGES, MIN_RECENT_PAIRS

logger = structlog.get_logger(__name__)


def _trim_messages(messages: list, keep_turns: int | None = None) -> list:
    """上下文窗口截断：根据 Token Budget 动态调整保留轮数。

    策略：
    1. 如果指定了 keep_turns，按轮数截断（Budget 驱动）
    2. 否则使用默认的 MAX_CONTEXT_MESSAGES
    3. 始终保留至少 MIN_RECENT_PAIRS 轮对话
    """
    if keep_turns is not None:
        max_messages = keep_turns * 2  # 每轮 = user + assistant
    else:
        max_messages = MAX_CONTEXT_MESSAGES

    if len(messages) <= max_messages:
        return messages

    trim_count = min(
        len(messages) - max_messages,
        len(messages) - MIN_RECENT_PAIRS * 2
    )
    if trim_count <= 0:
        return messages

    kept = messages[trim_count:]
    logger.info("context_trimmed",
                original=len(messages),
                trimmed=trim_count,
                kept=len(kept),
                budget_driven=keep_turns is not None)
    return kept


def build_context(messages: list, session_id: str, user_id: str, last_user_msg: str) -> dict:
    """构建执行上下文

    Returns:
        包含以下字段的字典：
        - input_messages: 处理后的消息列表
        - summary: 对话摘要
        - sentiment_context: 情感上下文
        - sentiment_level: 情感等级
        - dialog_context: 对话进度上下文
        - working_memory_context: 任务状态上下文
        - budget_context: Token 预算上下文
        - token_budget: TokenBudget 实例（供执行模块记录消耗）
    """
    # ── 1. 对话摘要（历史要点 + 日期 + 登录态） ──
    summary = get_session_summary(session_id)
    date_info = f"今天是 {datetime.now().strftime('%Y年%m月%d日')}（系统时间，所有时间计算以此为准）。"
    if user_id:
        date_info += "\n当前用户已登录，可以直接查询订单和商品信息。"
    else:
        date_info += "\n当前用户未登录，无法查询订单。请提示用户先登录。"

    effective_summary = summary
    if date_info.strip():
        effective_summary = (summary + "\n" + date_info) if summary else date_info

    # ── 2. 情感检测 + 累计升级 ──
    sentiment_level = detect_sentiment(last_user_msg) if last_user_msg else "neutral"
    prev_count = get_sentiment_count(session_id)
    level, new_count, _ = get_escalation(sentiment_level, prev_count)
    sentiment_context = build_sentiment_context(level, new_count)
    save_sentiment_count(session_id, new_count)
    if level != "neutral":
        logger.info("sentiment_detected", level=level, cumulative=new_count, session_id=session_id)

    # ── 3. 对话进度 ──
    dialog_context = build_dialog_context(messages, max_turns=3)

    # ── 4. Working Memory（任务状态追踪） ──
    wm = get_working_memory(session_id)
    wm.increment_turn()
    working_memory_context = wm.build_context()

    # ── 5. Token Budget（预算管理） ──
    token_budget = get_token_budget(session_id)
    budget_context = token_budget.build_budget_context()

    # ── 6. 构建输入消息（根据 Budget 决定裁剪策略） ──
    keep_turns = token_budget.get_keep_turns()
    input_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                input_messages.append(HumanMessage(content=content))
            else:
                input_messages.append(AIMessage(content=content))
        else:
            input_messages.append(msg)

    input_messages = _trim_messages(input_messages, keep_turns if token_budget.should_compress() else None)

    msg_types = [type(m).__name__ for m in input_messages]
    logger.info("graph_input_messages", count=len(input_messages), types=msg_types,
                user_id=user_id,
                budget_level=token_budget.level,
                wm_task=wm.get_state().task_type)

    return {
        "input_messages": input_messages,
        "summary": effective_summary,
        "sentiment_context": sentiment_context,
        "sentiment_level": sentiment_level,
        "dialog_context": dialog_context,
        "working_memory_context": working_memory_context,
        "budget_context": budget_context,
        "token_budget": token_budget,
    }
