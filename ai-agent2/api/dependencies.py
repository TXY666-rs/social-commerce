"""API 依赖注入 — 全局单例的 getter/setter"""
from memory import SessionManager

_session_manager: SessionManager | None = None
_async_redis = None  # redis.asyncio.Redis 单例，给 SSE Pub/Sub 用


def get_session_manager() -> SessionManager:
    assert _session_manager is not None, "SessionManager 未初始化，请先调用 set_session_manager()"
    return _session_manager


def set_session_manager(sm: SessionManager):
    global _session_manager
    _session_manager = sm


def get_async_redis():
    """获取全局 async redis 客户端（懒加载单例），用于 SSE Pub/Sub 订阅。
    复用 settings 中的连接信息，与 sync 客户端同源。
    """
    global _async_redis
    if _async_redis is None:
        import redis.asyncio as aioredis
        from config import settings
        _async_redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
            socket_connect_timeout=3,
        )
    return _async_redis
