"""转人工工具 — Human-in-the-Loop 机制

设计思路：
    当 Agent 无法解决用户问题时，触发转人工。转人工后：
    ① 写入 Redis 转接队列（供管理端拉取）
    ② 写入 Redis 转接标记（供用户侧轮询）
    ③ 返回等待提示给用户

    人工坐席通过管理端接口拉取队列、回复用户。
    人工回复通过 SessionManager 写入 Agent 会话历史（chat::ai::session::），
    用户下次发消息时 Agent 会读到人工回复，实现无缝切换。

Redis 数据结构：
    - 转接队列: Redis List "chat::transfer::queue"
      每个元素: JSON {id, user_id, reason, summary, created_at, status}
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

# 转接队列 TTL（30 分钟）
TRANSFER_TTL = 1800
# 转接标记 TTL（1 小时）
TRANSFER_MARK_TTL = 3600


def do_transfer_to_human(user_id: str, reason: str) -> tuple[bool, str, str]:
    """转人工核心逻辑 — 供 Tool 层和 Skill 层共用

    Args:
        user_id: 用户 ID
        reason: 转人工原因

    Returns:
        (success, transfer_id, error_message)
    """
    r = get_redis()

    # 生成转接工单 ID
    transfer_id = str(uuid.uuid4())[:8]

    # 获取会话摘要
    summary = _extract_recent_summary(r, user_id)

    # 构建转接工单
    ticket = {
        "id": transfer_id,
        "user_id": user_id,
        "reason": reason,
        "summary": summary,
        "created_at": time.time(),
        "status": "pending",
    }

    # ① 写入转接队列（供管理端拉取）
    r.lpush("chat::transfer::queue", json.dumps(ticket, ensure_ascii=False))
    r.ltrim("chat::transfer::queue", 0, 99)  # 最多保留 100 条

    # ② 写入转接标记（供用户侧轮询）
    session_id = f"user_{user_id}"
    r.setex(f"chat::transfer::{session_id}", TRANSFER_MARK_TTL, "pending")

    # ③ 保存工单详情（供管理端查看）
    r.setex(f"chat::transfer::ticket::{transfer_id}",
            TRANSFER_TTL, json.dumps(ticket, ensure_ascii=False))

    logger.info("transfer_to_human",
                 transfer_id=transfer_id,
                 user_id=user_id,
                 reason=reason)

    return True, transfer_id, ""


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
        return "转接人工客服时出现异常，请稍后重试。您也可以拨打客服热线 400-xxx-xxxx。"


def _extract_recent_summary(r, user_id: str) -> str:
    """从最近的 Agent 会话历史中提取摘要"""
    try:
        from memory.session_memory import KEY_PREFIX
        session_id = f"user_{user_id}"
        data = r.get(f"{KEY_PREFIX}{session_id}")
        if data:
            history = json.loads(data)
            recent = history[-4:]  # 最近 4 条
            lines = []
            for msg in recent:
                role = msg.get("role", "user")
                content = str(msg.get("content", ""))[:50]
                prefix = "用户" if role == "user" else "客服"
                lines.append(f"{prefix}: {content}")
            return "\n".join(lines)
    except Exception:
        pass
    return "（无法获取对话摘要）"
