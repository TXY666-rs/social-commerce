"""Agent 执行器 — 活跃Skill → FAQ → Skill触发 → 单 React Agent

这是整个 Agent 的核心入口，负责：
1. 提取用户消息
2. 活跃 Skill 检查（会话连续性，最高优先级）
3. FAQ 快路径（精确匹配，零延迟）
4. Skill 触发检测（新 Skill 激活）
5. 单 React Agent（Skill/FAQ 均未命中时的兜底）
6. 构建上下文（摘要/情感/对话进度/WM/Budget）
7. 执行图并流式输出
"""

import asyncio
import time
import structlog
from agents.faq import match_greeting, match_feature_query
from core.context import build_context
from core.execution import execute_graph_with_retry
from skills.trigger import check_active_skill, trigger_skill
from reasoning.self_correction import check_safety

logger = structlog.get_logger(__name__)


# ── 辅助函数 ──

def _build_eval_metadata(
    route_reason: str,
    total_ms: float,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> dict:
    """构建统一的 eval 元数据块"""
    return {
        "route_confidence": "high",
        "route_reason": route_reason,
        "latency": {"routing_ms": 0, "total_ms": round(total_ms)},
        "token": {"input": input_tokens, "output": output_tokens},
        "safety": {"injection": False, "pii": False, "leak": False},
    }


def _extract_last_user_message(messages: list) -> str:
    """从消息列表中提取最后一条用户消息"""
    for msg in reversed(messages):
        if isinstance(msg, dict):
            if msg.get("role") == "user":
                return msg.get("content", "")
        elif hasattr(msg, "type") and msg.type == "human":
            return msg.content
    return ""


async def stream_react_agent(messages: list, token: str = "", user_id: str = "", session_id: str = ""):
    """流式执行 Agent

    Args:
        messages: 对话消息列表
        token: 用户 token
        user_id: 用户 ID
        session_id: 会话 ID

    Yields:
        流式输出的文本片段。
        最后一个 yield 是一个 dict（带 _metadata_=True 标记），包含：
            tools_called, route_source, skill_name
    """
    last_user_msg = _extract_last_user_message(messages)

    # 元数据容器，各路径填充后在最后 yield 给调用方
    metadata = {
        "_metadata_": True,
        "agent_type": "",
        "tools_called": [],
        "route_source": "",
        "skill_name": "",
        "eval": {
            "route_confidence": "",
            "route_reason": "",
            "latency": {"routing_ms": 0, "total_ms": 0},
            "token": {"input": 0, "output": 0},
            "safety": {},
        },
    }
    t_start = time.monotonic()

    # 1. 活跃 Skill 检查（会话连续性，最高优先级）
    active_skill_reply, active_skill_name = await check_active_skill(last_user_msg, session_id)
    if active_skill_reply:
        logger.info("active_skill_handled", session_id=session_id, skill=active_skill_name, reply_preview=active_skill_reply[:50])
        is_safe, safe_content = check_safety(active_skill_reply)
        yield safe_content if not is_safe else active_skill_reply
        total_ms = round((time.monotonic() - t_start) * 1000)
        metadata.update({
            "agent_type": "skill",
            "route_source": "active_skill",
            "skill_name": active_skill_name or "",
            "eval": _build_eval_metadata(f"活跃Skill({active_skill_name})连续对话", total_ms),
        })
        yield metadata
        return

    # 2. FAQ 快路径（精确匹配，零延迟）
    faq_reply = match_greeting(last_user_msg) or match_feature_query(last_user_msg)
    if faq_reply:
        logger.info("faq_matched", session_id=session_id, reply_preview=faq_reply[:50])
        try:
            from monitoring.dashboard import record_chat as _record
            asyncio.create_task(_record(session_id, is_faq=True, agent_type="faq"))
        except Exception:
            logger.debug("faq_stats_record_failed")
        yield faq_reply
        total_ms = round((time.monotonic() - t_start) * 1000)
        metadata.update({
            "agent_type": "faq",
            "route_source": "faq",
            "eval": _build_eval_metadata("FAQ精确匹配", total_ms),
        })
        yield metadata
        return

    # 3. Skill 触发检测（新 Skill 激活）
    skill_reply, triggered_skill_name = await trigger_skill(last_user_msg, session_id)
    if skill_reply:
        logger.info("skill_triggered_and_handled", session_id=session_id, skill=triggered_skill_name, reply_preview=skill_reply[:50])
        is_safe, safe_content = check_safety(skill_reply)
        yield safe_content if not is_safe else skill_reply
        total_ms = round((time.monotonic() - t_start) * 1000)
        metadata.update({
            "agent_type": "skill",
            "route_source": "skill",
            "skill_name": triggered_skill_name or "",
            "eval": _build_eval_metadata(f"Skill触发匹配({triggered_skill_name})", total_ms),
        })
        yield metadata
        return

    # 4. 单 React Agent（Skill/FAQ 均未命中，全量工具 + 统一 Prompt）
    logger.info("react_agent_fallback", message_preview=last_user_msg[:80] if last_user_msg else "(empty)")

    # 5. 构建上下文（不再依赖 agent_type）
    context = build_context(messages, session_id, user_id, last_user_msg)
    context["route_source"] = "react_agent"

    # 6. 执行图并流式输出
    async for chunk in execute_graph_with_retry(context, session_id, user_id):
        yield chunk

    # 7. 从 context 中读取元数据，yield 给调用方
    metadata.update({
        "agent_type": "agent",
        "tools_called": context.get("_tools_called", []),
        "route_source": "react_agent",
        "eval": {
            "route_confidence": "high",
            "route_reason": "React Agent 全量工具处理",
            "latency": {
                "routing_ms": 0,
                "total_ms": round(context.get("_duration_ms", 0)),
            },
            "token": {
                "input": context.get("_input_tokens", 0),
                "output": context.get("_output_tokens", 0),
            },
        },
    })
    yield metadata
