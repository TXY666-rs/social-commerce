"""基础设施服务层 — Nacos客户端、Redis连接、HTTP客户端

LLM 相关功能已迁移到 resilience 模块。
"""

from services.nacos_client import nacos_client, NacosClient
from services.http_client import get_client, close_client
from services.redis_client import get_redis

__all__ = [
    "nacos_client", "NacosClient",
    "get_client", "close_client",
    "get_redis",
]
