from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
from config import settings
from config.logging_config import setup_logging
from middleware.trace import trace_and_metrics_middleware
from services.nacos_client import nacos_client
from memory import SessionManager
from api.dependencies import set_session_manager, get_async_redis
from api.chat import router as chat_router
from api.feedback import router as feedback_router
from api.health import router as health_router
from api.admin import router as admin_router
from api.mock_api import router as mock_api_router

setup_logging()

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：初始化 + Mock 数据 seed + （可选）Nacos 注册 + 优雅关闭"""
    # 初始化 SessionManager
    session_manager = SessionManager()
    set_session_manager(session_manager)

    # 预热 async redis 连接（供 SSE Pub/Sub 使用）
    # 避免首次 SSE 请求时建立连接 + 握手多花 1s
    try:
        ar = get_async_redis()
        await ar.ping()
        logger.info("async_redis_ready", host=settings.REDIS_HOST, port=settings.REDIS_PORT)
    except Exception as e:
        logger.warning("async_redis_ping_failed", error=str(e))

    # ── Mock 数据初始化（幂等，替代 Java 后端的业务数据）──
    try:
        from mock_data import ensure_seeded
        ensure_seeded()
    except Exception as e:
        logger.warning("mock_data_seed_failed", error=str(e))

    # ── 清理旧的转人工工单（重启后 session 已清，旧工单引用断裂不可用）──
    try:
        from services.redis_client import get_redis as _get_sync_redis
        r = _get_sync_redis()
        for prefix in ("chat::transfer::queue", "chat::transfer::ticket::*", "chat::transfer::user_*"):
            keys = [prefix] if "*" not in prefix else r.keys(prefix)
            if keys:
                r.delete(*keys)
        logger.info("transfer_tickets_cleared_on_startup")
    except Exception as e:
        logger.warning("transfer_cleanup_skipped", error=str(e))

    # ── Nacos 注册（可选，连不上不影响启动）──
    if settings.NACOS_SERVER and settings.NACOS_SERVER != "127.0.0.1:8848":
        try:
            await nacos_client.start()
            logger.info("ai_agent_started", nacos_registered=True)
        except Exception as e:
            logger.warning("nacos_register_failed_skipped", error=str(e))
    else:
        logger.info("ai_agent_started", nacos="disabled (standalone mode)")

    yield

    # 服务关闭
    try:
        ar = get_async_redis()
        await ar.close()
    except Exception:
        pass
    try:
        await nacos_client.stop()
    except Exception:
        pass
    logger.info("ai_agent_stopped")


app = FastAPI(title="AI智能客服", version="1.0.0", lifespan=lifespan)

# ── CORS（允许前端跨端口/跨域访问）──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 中间件 ──
app.middleware("http")(trace_and_metrics_middleware)

# ── 路由注册 ──
app.include_router(mock_api_router)       # 业务 mock API（/api/* 电商接口）
app.include_router(chat_router)
app.include_router(feedback_router)
app.include_router(health_router)
app.include_router(admin_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.AGENT_HOST,
        port=settings.AGENT_PORT,
        reload=True,
    )
