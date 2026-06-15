"""Redis 连接管理 — 全局共享连接（sync + async 双客户端）

sync 客户端：供 LangGraph 同步节点、工具函数使用
async 客户端：供 FastAPI async 路由、监控模块使用

连接池配置：
    max_connections=50     防止耗尽文件描述符
    socket_timeout=5       读超时（区别于连接超时）
    retry_on_timeout=True  超时自动重试
    health_check_interval=30  每30秒探测连接健康
"""
import asyncio
import redis as redis_lib
import redis.asyncio as aioredis
from config.settings import settings
import structlog

logger = structlog.get_logger(__name__)

# ── 同步客户端 ──
_redis: redis_lib.Redis | None = None

# ── 异步客户端 ──
_async_redis: aioredis.Redis | None = None


def _build_redis_kwargs() -> dict:
    """共享的连接参数"""
    return dict(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD or None,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=5,
        retry_on_timeout=True,
        max_connections=50,
        health_check_interval=30,
    )


def get_redis() -> redis_lib.Redis:
    """获取全局共享同步 Redis 连接（惰性初始化）

    用途：LangGraph 同步节点、工具函数、装饰器
    """
    global _redis
    if _redis is None:
        kwargs = _build_redis_kwargs()
        _redis = redis_lib.Redis(**kwargs)
    return _redis


def get_async_redis() -> aioredis.Redis:
    """获取全局共享异步 Redis 连接（惰性初始化）

    用途：FastAPI async 路由、监控模块、sentiment 等 async 上下文
    """
    global _async_redis
    if _async_redis is None:
        kwargs = _build_redis_kwargs()
        _async_redis = aioredis.Redis(**kwargs)
    return _async_redis


async def async_redis_safe(coro_func, *args, default=None, **kwargs):
    """安全执行异步 Redis 操作，失败时返回默认值而非抛异常

    用于监控/统计等非关键路径，避免 Redis 故障影响主流程。
    """
    try:
        r = get_async_redis()
        return await coro_func(r, *args, **kwargs)
    except Exception as e:
        logger.debug("async_redis_safe_failed", error=str(e))
        return default


def reset_connections():
    """重置所有连接（服务关闭时调用）"""
    global _redis, _async_redis
    if _redis is not None:
        try:
            _redis.close()
        except Exception:
            pass
        _redis = None
    if _async_redis is not None:
        try:
            # 注意：异步 close 需要 await，这里用 fire-and-forget
            asyncio.get_event_loop().create_task(_async_redis.close())
        except Exception:
            pass
        _async_redis = None
