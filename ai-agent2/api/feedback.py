"""用户反馈 API — /chat/feedback, /chat/feedback/stats"""
import json
import uuid
from typing import Optional
from fastapi import APIRouter, Header
from datetime import datetime
import structlog

from config.schemas import FeedbackRequest
from middleware.auth import resolve_user
from services.redis_client import get_redis

logger = structlog.get_logger(__name__)

router = APIRouter()

FEEDBACK_TTL = 72 * 3600  # 72 小时


@router.post("/chat/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    x_user_id: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    """用户对 AI 回复进行 👍/👎 反馈。"""
    user_info = await resolve_user(x_user_id, None, authorization, request.token)
    user_id = str(user_info.id) if user_info and user_info.id else "anonymous"

    message_id = request.message_id or str(uuid.uuid4())
    feedback = {
        "message_id": message_id,
        "session_id": request.session_id,
        "rating": request.rating,
        "comment": request.comment,
        "message_content": (request.message_content or "")[:500],
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        r = get_redis()
        today = datetime.now().strftime("%Y-%m-%d")
        r.setex(f"chat::feedback::{message_id}", FEEDBACK_TTL,
                json.dumps(feedback, ensure_ascii=False))
        r.lpush(f"chat::feedback::list::{today}", json.dumps(feedback, ensure_ascii=False))
        r.ltrim(f"chat::feedback::list::{today}", 0, 499)
        r.expire(f"chat::feedback::list::{today}", FEEDBACK_TTL)
    except Exception as e:
        logger.warning("feedback_store_failed", error=str(e))

    logger.info("user_feedback_received",
                rating=request.rating,
                session_id=request.session_id,
                user_id=user_id,
                comment=(request.comment or "")[:100])

    # 记录反馈统计
    try:
        import asyncio
        from monitoring.dashboard import record_feedback
        asyncio.create_task(record_feedback(request.session_id, request.rating))
    except Exception:
        pass

    return {"status": "ok", "message": "感谢您的反馈！"}


@router.get("/chat/feedback/stats")
async def get_feedback_stats():
    """查询反馈统计（管理用）"""
    try:
        r = get_redis()
        today = datetime.now().strftime("%Y-%m-%d")
        records = r.lrange(f"chat::feedback::list::{today}", 0, -1)
        up_count = 0
        down_count = 0
        for raw in records:
            try:
                fb = json.loads(raw)
                if fb.get("rating") == "up":
                    up_count += 1
                elif fb.get("rating") == "down":
                    down_count += 1
            except Exception:
                pass
        return {"total": len(records), "up": up_count, "down": down_count}
    except Exception:
        return {"total": 0, "up": 0, "down": 0}
