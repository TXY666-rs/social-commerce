from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog
from config import settings
from config.logging_config import setup_logging
from middleware.trace import trace_and_metrics_middleware
from services.nacos_client import nacos_client
from services.http_client import close_client
from memory import SessionManager
from api.dependencies import set_session_manager
from api.chat import router as chat_router
from api.feedback import router as feedback_router
from api.health import router as health_router
from api.admin import router as admin_router

setup_logging()

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：初始化 + 注册到 Nacos + 优雅关闭"""
    # 初始化 SessionManager
    session_manager = SessionManager()
    set_session_manager(session_manager)

    # 注册到 Nacos
    try:
        await nacos_client.start()
        logger.info("ai_agent_started", nacos_registered=True)
    except Exception as e:
        logger.error("nacos_register_failed", error=str(e))

    yield

    # 服务关闭
    await nacos_client.stop()
    close_client()
    logger.info("ai_agent_stopped", nacos_deregistered=True)


app = FastAPI(title="AI智能客服", version="1.0.0", lifespan=lifespan)

# ── 中间件 ──
app.middleware("http")(trace_and_metrics_middleware)

# ── 路由注册 ──
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
