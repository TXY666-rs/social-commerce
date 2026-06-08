"""健康检查端点"""
from fastapi import APIRouter, Depends
from memory import SessionManager
from api.dependencies import get_session_manager

router = APIRouter()


@router.get("/health")
async def health_check(session_manager: SessionManager = Depends(get_session_manager)):
    redis_status = session_manager.health_check()
    return {
        "status": "ok",
        "service": "ai-agent",
        "redis_available": redis_status.get("redis_available", False),
    }
