"""Redis 连接管理 — 全局共享连接，避免各模块重复连接"""
import redis as redis_lib
from config.settings import settings

_redis = None


def get_redis() -> redis_lib.Redis:
    """获取全局共享 Redis 连接（惰性初始化）"""
    global _redis
    if _redis is None:
        _redis = redis_lib.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=3,
        )
    return _redis
