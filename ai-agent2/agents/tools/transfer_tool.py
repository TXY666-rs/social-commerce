"""转人工工具 — Human-in-the-Loop 机制

设计思路：
    当 Agent 无法解决用户问题时，触发转人工。转人工后：
    ① 写入 Redis 转接队列（供管理端拉取，含优先级排序）
    ② 写入 Redis 转接标记（供用户侧下次发消息时检查）
    ③ 返回等待提示给用户

    人工坐席通过管理端接口拉取队列、回复用户。
    人工回复通过 SessionManager 写入 Agent 会话历史（chat::ai::session::），
    用户下次发消息时 Agent 会读到人工回复，实现无缝切换。

Redis 数据结构：
    - 转接队列: Redis List "chat::transfer::queue"
      每个元素: JSON {id, user_id, reason, context, priority, sentiment,
                       queue_position, created_at, status}
    - 转接标记: Redis String "chat::transfer::{session_id}"
      值: "pending" / "accepted" / "completed"
    - 工单详情: Redis String "chat::transfer::ticket::{transfer_id}"
    - 人工回复: 写入 Agent 会话历史 chat::ai::session::{session_id}
"""

import json
import uuid
import time
import structlog
from langchain_core.tools import tool
from agents.tools.registry import register_tool
from services.redis_client import get_redis
from middleware.context import _get_user_id

logger = structlog.get_logger(__name__)

# 工单详情 TTL（24 小时）
TRANSFER_TTL = 86400
# 转接标记 TTL（24 小时）
TRANSFER_MARK_TTL = 86400


def do_transfer_to_human(user_id: str, reason: str) -> tuple[bool, str, str]:
    """转人工核心逻辑 — 供 Tool 层和 Skill 层共用

    Args:
        user_id: 用户 ID
        reason: 转人工原因

    Returns:
        (success, transfer_id, error_message)
    """
    r = get_redis()
    session_id = f"user_{user_id}"

    # 生成转接工单 ID
    transfer_id = str(uuid.uuid4())[:8]

    # 获取情感状态 → 决定优先级
    sentiment = _get_current_sentiment(r, session_id)
    priority = _sentiment_to_priority(sentiment)

    # 提取富上下文（完整对话 + 已调工具 + 情感历史）
    context = _extract_rich_context(r, session_id)

    # 计算当前排队位置
    queue_position = _get_queue_position(r, priority)

    # 构建转接工单
    ticket = {
        "id": transfer_id,
        "user_id": user_id,
        "reason": reason,
        "context": context,
        "priority": priority,
        "sentiment": sentiment,
        "queue_position": queue_position,
        "created_at": time.time(),
        "status": "pending",
    }

    # ① 写入转接队列（供管理端拉取）
    r.lpush("chat::transfer::queue", json.dumps(ticket, ensure_ascii=False))
    r.ltrim("chat::transfer::queue", 0, 199)  # 最多保留 200 条

    # ② 写入转接标记（供用户侧下次发消息时检查）
    r.setex(f"chat::transfer::{session_id}", TRANSFER_MARK_TTL, "pending")

    # ③ 保存工单详情（供管理端查看，TTL 24h）
    r.setex(f"chat::transfer::ticket::{transfer_id}",
            TRANSFER_TTL, json.dumps(ticket, ensure_ascii=False))

    # ④ 写入系统消息到用户会话（用户侧 loadHistory 时可见）
    try:
        from memory.session_memory import SessionManager
        mgr = SessionManager()
        mgr.add_message(session_id, "assistant",
                       "正在等待人工介入，请稍候...",
                       source="system")
    except Exception:
        pass

    logger.info("transfer_to_human",
                transfer_id=transfer_id,
                user_id=user_id,
                reason=reason,
                priority=priority,
                sentiment=sentiment)

    return True, transfer_id, ""


def get_transfer_status(user_id: str) -> dict | None:
    """获取用户当前的转人工状态（供 chat.py 在下次发消息时检查）

    Returns:
        {"status": "accepted"|"completed"|"pending", ...} 或 None
    """
    try:
        r = get_redis()
        session_id = f"user_{user_id}"
        status = r.get(f"chat::transfer::{session_id}")
        if status:
            return {"status": status.decode() if isinstance(status, bytes) else status}
    except Exception:
        pass
    return None


@register_tool()
@tool
def transfer_to_human(reason: str = "用户主动要求转人工") -> str:
    """当用户明确要求转人工，或多次尝试无法解决时调用此工具。

    Args:
        reason: 转人工原因（如"用户主动要求"、"多次尝试未解决"等）

    Returns:
        转接确认提示
    """
    user_id = _get_user_id() or "anonymous"

    try:
        success, transfer_id, _ = do_transfer_to_human(user_id, reason)
        return (
            f"正在为您转接人工客服，转接单号: {transfer_id}\n"
            f"当前排队中，请稍候...人工客服接入后会主动联系您。\n"
            f"（您也可以继续向我提问，我会尽力帮助您）"
        )

    except Exception as e:
        logger.error("transfer_failed", error=str(e))
        return "转接人工客服时出现异常，请稍后重试。"


# ============================================================
# 内部辅助函数
# ============================================================

def _get_current_sentiment(r, session_id: str) -> str:
    """从 Redis 读取当前会话的情感状态"""
    try:
        from core.sentiment import get_sentiment_count
        count = get_sentiment_count(session_id)
        if count >= 3:
            return "angry"
        elif count >= 1:
            return "negative"
        return "neutral"
    except Exception:
        return "neutral"


def _sentiment_to_priority(sentiment: str) -> str:
    """情感 → 优先级映射：愤怒用户优先处理"""
    return {"angry": "high", "negative": "medium"}.get(sentiment, "low")


def _get_queue_position(r, priority: str) -> int:
    """计算当前排队位置（前面有多少个同级或更高优先级的工单）"""
    try:
        queue = r.lrange("chat::transfer::queue", 0, -1)
        pending_count = 0
        for raw in queue:
            ticket = json.loads(raw)
            if ticket.get("status") != "pending":
                continue
            ticket_priority = ticket.get("priority", "low")
            # 统计同级或更高优先级的排队数
            if _priority_rank(ticket_priority) <= _priority_rank(priority):
                pending_count += 1
        return pending_count + 1
    except Exception:
        return 1


def _priority_rank(priority: str) -> int:
    """优先级数值排名（越小越优先）"""
    return {"high": 1, "medium": 2, "low": 3}.get(priority, 3)


def _extract_rich_context(r, session_id: str) -> dict:
    """从会话历史中提取富上下文，供人工客服快速了解情况

    包含：完整对话历史（最近 10 条，过滤系统消息）、情感状态、已使用的工具
    """
    context = {
        "messages": [],
        "sentiment": "neutral",
        "tools_used": [],
        "message_count": 0,
    }

    # 系统消息关键词（转人工流程自动注入的，不属于真实对话）
    _SYSTEM_PATTERNS = ("人工客服已接入", "人工客服已结束")

    try:
        from memory.session_memory import KEY_PREFIX
        data = r.get(f"{KEY_PREFIX}{session_id}")
        if data:
            history = json.loads(data)
            context["message_count"] = len(history)

            # 过滤系统消息后，取最近 10 条真实对话
            real_messages = [
                msg for msg in history
                if not (
                    msg.get("role") == "assistant"
                    and any(p in str(msg.get("content", "")) for p in _SYSTEM_PATTERNS)
                )
            ]
            for msg in real_messages[-10:]:
                context["messages"].append({
                    "role": msg.get("role", "user"),
                    "content": str(msg.get("content", "")),
                })

            # 从消息中提取工具调用信息
            for msg in history:
                content = str(msg.get("content", ""))
                if msg.get("role") == "assistant" and "转接单号" in content:
                    context["tools_used"].append("transfer_to_human")

    except Exception as e:
        logger.warning("extract_context_failed", error=str(e))

    # 情感状态
    try:
        count = _get_current_sentiment(r, session_id)
        context["sentiment"] = count
    except Exception:
        pass

    return context
