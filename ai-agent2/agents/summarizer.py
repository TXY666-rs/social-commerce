"""对话总结 — 后台异步 LLM 总结 + Redis 持久化，支持跨会话上下文延续"""
import json
import asyncio
from datetime import datetime, timezone
import structlog
from config.settings import settings
from resilience.llm_factory import get_llm, LLMFallbackException
from services.redis_client import get_redis

logger = structlog.get_logger(__name__)

SUMMARY_TTL = 7 * 86400  # 7 天

SUMMARY_PROMPT = """你是一个信息提取助手。请用一句话总结以下客服对话的要点。

总结要求：
1. 用户的核心问题是什么（如"想退货"、"查询物流"）
2. 问题是否已解决
3. 有什么需要跟进的（如"已提交投诉，等待处理"）

对话：
{conversation}

请直接输出总结，不要任何前缀。"""


def get_session_summary(session_id: str) -> str:
    """从 Redis 读取上次对话总结"""
    if not session_id:
        return ""
    try:
        r = get_redis()
        key = f"chat::ai::summary::{session_id}"
        raw = r.get(key)
        if raw:
            data = json.loads(raw)
            return data.get("summary", "")
    except Exception:
        pass
    return ""


def _save_session_summary(session_id: str, summary: str) -> None:
    """保存对话总结到 Redis"""
    if not session_id or not summary:
        return
    try:
        r = get_redis()
        key = f"chat::ai::summary::{session_id}"
        data = json.dumps({
            "summary": summary,
            "updated": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)
        r.setex(key, SUMMARY_TTL, data)
    except Exception as e:
        logger.warning("save_summary_failed", error=str(e), session_id=session_id)


async def summarize_conversation(session_id: str, messages: list, force: bool = False) -> None:
    """异步总结对话并持久化。不阻塞主流程，启动后台任务执行。

    Args:
        session_id: 会话ID
        messages: 对话消息列表
        force: 强制总结（即使是 FAQ 命中，A5 优化跳过后使用）
    """
    if not session_id or len(messages) < 2:
        return

    try:
        conversation_lines = []
        for msg in messages[-8:]:
            role = msg.get("role", "user") if isinstance(msg, dict) else "user"
            content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            conversation_lines.append(f"[{role}]: {content}")
        conversation_text = "\n".join(conversation_lines)

        if len(conversation_text) < 20:
            return

        prompt = SUMMARY_PROMPT.format(conversation=conversation_text)
        llm = get_llm()
        response = await llm.ainvoke(prompt)
        summary = response.content.strip()

        if summary and len(summary) > 5:
            _save_session_summary(session_id, summary)
            logger.info("conversation_summarized", session_id=session_id, summary_length=len(summary))

    except LLMFallbackException:
        logger.warning("summarize_skipped_llm_unavailable", session_id=session_id)
    except Exception as e:
        logger.warning("summarize_failed", error=str(e), session_id=session_id)
