"""工具结果缓存 — 基于内存的 TTL 缓存

对查询类工具（get_my_orders, track_logistics 等）添加短 TTL 缓存，
避免用户连续提问时重复调用后端 API。

使用方式：
    @tool_result_cache(ttl=60)
    @tool
    def get_my_orders(...) -> str:
        ...

缓存策略：
    - TTL 默认 60 秒（适合查询类工具）
    - 写操作（cancel_order, request_refund 等）不缓存
    - 缓存 key = 函数名 + 参数 hash
    - 自动淘汰过期条目
"""

import hashlib
import json
import time
from functools import wraps
from typing import Callable

import structlog

logger = structlog.get_logger(__name__)

# 内存缓存：cache_key → (expire_at, result)
_cache: dict[str, tuple[float, str]] = {}
_CACHE_MAX_SIZE = 10000  # 最大缓存条目数
import threading
_cache_lock = threading.Lock()

# 缓存统计
_stats = {"hits": 0, "misses": 0}
_stats_lock = threading.Lock()


def tool_result_cache(ttl: int = 60):
    """装饰器：为工具函数添加结果缓存。

    Args:
        ttl: 缓存过期时间（秒），默认 60 秒
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> str:
            # 构建缓存 key：函数名 + 排序后的参数
            key_parts = [func.__name__]
            for a in args:
                key_parts.append(json.dumps(a, sort_keys=True, default=str, ensure_ascii=False))
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={json.dumps(v, sort_keys=True, default=str, ensure_ascii=False)}")
            cache_key = hashlib.md5(
                "|".join(key_parts).encode()
            ).hexdigest()

            # 检查缓存
            now = time.time()
            if cache_key in _cache:
                expire_at, result = _cache[cache_key]
                if now < expire_at:
                    with _cache_lock:
                        _stats["hits"] += 1
                    logger.debug("tool_cache_hit", func=func.__name__, key=cache_key[:8])
                    return result
                else:
                    del _cache[cache_key]

            # 缓存未命中，执行函数
            with _cache_lock:
                _stats["misses"] += 1
            result = func(*args, **kwargs)

            # 只缓存成功的非空结果
            if result and not result.startswith("用户未登录") and "失败" not in result[:20]:
                with _cache_lock:
                    # 超限时清理过期条目
                    if len(_cache) >= _CACHE_MAX_SIZE:
                        _cleanup_expired(now)
                    _cache[cache_key] = (now + ttl, result)
                logger.debug("tool_cache_set", func=func.__name__, ttl=ttl)

            # 定期清理过期条目（每次 miss 时有 5% 概率触发）
            misses_count = _stats["misses"]
            if misses_count % 20 == 0:
                with _cache_lock:
                    _cleanup_expired(now)

            return result
        return wrapper
    return decorator


def _cleanup_expired(now: float):
    """清理过期的缓存条目"""
    expired_keys = [k for k, (exp, _) in _cache.items() if now >= exp]
    for k in expired_keys:
        del _cache[k]
    if expired_keys:
        logger.debug("tool_cache_cleanup", expired_count=len(expired_keys))


def get_cache_stats() -> dict:
    """获取缓存统计信息"""
    total = _stats["hits"] + _stats["misses"]
    hit_rate = _stats["hits"] / total if total > 0 else 0
    return {
        "hits": _stats["hits"],
        "misses": _stats["misses"],
        "hit_rate": f"{hit_rate:.1%}",
        "current_size": len(_cache),
    }


def clear_cache():
    """清空所有缓存"""
    _cache.clear()
    logger.info("tool_cache_cleared")
