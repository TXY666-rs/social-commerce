import json
import time
import asyncio
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Depends
from fastapi.responses import StreamingResponse
import structlog

from config.schemas import ChatRequest, ChatResponse, EvalInfo
from config.logging_config import get_trace_id
from middleware.auth import resolve_user
from agents.executor import stream_react_agent
from agents.summarizer import summarize_conversation
from memory import SessionManager
from api.dependencies import get_session_manager
from middleware.context import set_request_context, clear_request_context
from monitoring.realtime import record_eval_data
from core.security import validate_input, sanitize_output, record_security_event, detect_pii, mask_pii

logger = structlog.get_logger(__name__)

router = APIRouter()


def _build_messages(history: list, recent: int = 10) -> tuple[list, list]:
    """从会话历史构建消息列表（裁剪到最近 N 条）"""
    recent_history = history[-recent:] if len(history) > recent else history
    messages = []
    for msg in recent_history:
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})
    return messages, recent_history


async def _setup_session(
    request: ChatRequest,
    session_manager: SessionManager,
    x_user_id: Optional[str] = None,
    x_user_role: Optional[str] = None,
    authorization: Optional[str] = None,
) -> tuple[str, str, list, list]:
    """设置会话：安全检查 + 验证用户 + 记录消息 + 返回 (user_id, session_id, messages, recent_history)"""
    # ── 安全检查 ──
    is_valid, error_msg = validate_input(request.message)
    if not is_valid:
        record_security_event("injection", request.message[:100])
        raise HTTPException(status_code=400, detail=error_msg)

    # PII 检测（用户输入中的手机号/身份证/邮箱 → 脱敏后存入历史）
    pii_found = detect_pii(request.message)
    if pii_found:
        record_security_event("pii_input", str(list(pii_found.keys())))
        request.message = mask_pii(request.message)

    user_info = await resolve_user(x_user_id, x_user_role, authorization, request.token)
    if not user_info or not user_info.id:
        raise HTTPException(status_code=401, detail="请先登录后再使用客服")
    user_id = str(user_info.id)

    # 允许请求方指定 session_id（评估框架每条用例用不同 session 避免状态串扰）
    session_id = request.session_id or f"user_{user_id}"
    set_request_context(session_id, request.token or "", user_id)

    history = session_manager.add_message(session_id, "user", request.message)
    messages, recent_history = _build_messages(history)
    return user_id, session_id, messages, recent_history


def _post_process_reply(
    session_manager: SessionManager,
    session_id: str,
    reply: str,
    is_faq: bool,
    recent_history: list,
) -> str:
    """统一的回复后处理：输出过滤 + 存入历史 + 触发摘要

    Returns:
        过滤后的最终回复文本
    """
    reply = sanitize_output(reply)
    session_manager.add_message(session_id, "assistant", reply)

    if not is_faq:
        asyncio.create_task(summarize_conversation(session_id, recent_history))
    else:
        logger.info("faq_hit_skip_summarize", session_id=session_id)

    return reply


async def _consume_agent_stream(
    agent_stream,
) -> tuple[list, str, str, list, dict, bool, str]:
    """消费 stream_react_agent 异步流，分离文本块和元数据

    Returns:
        (text_chunks, agent_type, route_source, tools_called, eval_data, is_faq, skill_name)
    """
    text_chunks = []
    agent_type = "unknown"
    route_source = "unknown"
    tools_called = []
    eval_data = {}
    is_faq = False
    skill_name = ""

    async for chunk in agent_stream:
        if isinstance(chunk, dict) and chunk.get("_metadata_"):
            agent_type = chunk.get("agent_type", "unknown")
            tools_called = chunk.get("tools_called", [])
            route_source = chunk.get("route_source", "unknown")
            eval_data = chunk.get("eval", {})
            skill_name = chunk.get("skill_name", "")
        elif isinstance(chunk, tuple) and chunk[0] == "_FAQ_":
            is_faq = True
            route_source = "faq"
            text_chunks.append(chunk[1])
        else:
            text_chunks.append(chunk)

    return text_chunks, agent_type, route_source, tools_called, eval_data, is_faq, skill_name


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    x_user_id: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    user_id, session_id, messages, recent_history = await _setup_session(
        request, session_manager, x_user_id, x_user_role, authorization
    )

    logger.info("chat_request", user_id=user_id, session_id=session_id, trace_id=get_trace_id())

    t0 = time.monotonic()
    try:
        agent_stream = stream_react_agent(messages, request.token or "", user_id, session_id)
        result = await _consume_agent_stream(agent_stream)
        text_chunks, agent_type, route_source, tools_called, eval_data, is_faq, skill_name = result
    finally:
        clear_request_context(session_id)

    reply = _post_process_reply(session_manager, session_id, "".join(text_chunks), is_faq, recent_history)

    total_ms = (time.monotonic() - t0) * 1000

    # 组装 eval 信息
    eval_info = EvalInfo(
        route_confidence=eval_data.get("route_confidence", ""),
        route_reason=eval_data.get("route_reason", ""),
        safety=eval_data.get("safety", {}),
        latency=eval_data.get("latency", {"total_ms": round(total_ms)}),
        token=eval_data.get("token", {}),
    )

    # 实时采集 eval 数据到 Redis（供质量监控面板使用）
    asyncio.create_task(record_eval_data(
        user_id=user_id,
        agent_type=agent_type,
        route_source=route_source,
        latency=eval_info.latency,
        token=eval_info.token,
        safety=eval_info.safety,
        tools_called=tools_called,
        is_faq=is_faq,
        skill_name=skill_name,
    ))

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        agent_type=agent_type,
        tools_called=tools_called,
        route_source=route_source,
        skill_name=skill_name,
        eval=eval_info,
    )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    x_user_id: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    user_id, session_id, messages, recent_history = await _setup_session(
        request, session_manager, x_user_id, x_user_role, authorization
    )

    logger.info("chat_stream_request", user_id=user_id, session_id=session_id, trace_id=get_trace_id())

    async def event_generator():
        t0 = time.monotonic()
        full_reply = []
        agent_type = "unknown"
        route_source = "unknown"
        tools_called = []
        eval_data = {}
        is_faq = False
        skill_name = ""
        try:
            async for chunk in stream_react_agent(messages, request.token or "", user_id, session_id):
                if isinstance(chunk, dict) and chunk.get("_metadata_"):
                    agent_type = chunk.get("agent_type", "unknown")
                    tools_called = chunk.get("tools_called", [])
                    route_source = chunk.get("route_source", "unknown")
                    eval_data = chunk.get("eval", {})
                    skill_name = chunk.get("skill_name", "")
                elif isinstance(chunk, tuple) and chunk[0] == "_FAQ_":
                    is_faq = True
                    route_source = "faq"
                    content = chunk[1]
                    full_reply.append(content)
                    yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                else:
                    full_reply.append(chunk)
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            _post_process_reply(session_manager, session_id, "".join(full_reply), is_faq, recent_history)

            total_ms = (time.monotonic() - t0) * 1000

            # 实时采集 eval 数据到 Redis
            asyncio.create_task(record_eval_data(
                user_id=user_id,
                agent_type=agent_type,
                route_source=route_source,
                latency=eval_data.get("latency", {"total_ms": round(total_ms)}),
                token=eval_data.get("token", {}),
                safety=eval_data.get("safety", {}),
                tools_called=tools_called,
                is_faq=is_faq,
                skill_name=skill_name,
            ))

            yield f"data: {json.dumps({'done': True, 'session_id': session_id}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error("sse_stream_error", error=str(e), user_id=user_id, trace_id=get_trace_id())
        finally:
            clear_request_context(session_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str, session_manager: SessionManager = Depends(get_session_manager)):
    history = session_manager.get_history(session_id)
    return {"session_id": session_id, "messages": history}


@router.delete("/chat/clear/{session_id}")
async def clear_chat(session_id: str, session_manager: SessionManager = Depends(get_session_manager)):
    session_manager.clear_session(session_id)
    return {"session_id": session_id, "message": "会话已清除"}
