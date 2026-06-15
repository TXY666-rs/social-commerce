"""基础设施服务层 — Redis 连接（核心）+ Nacos 客户端（可选）

重构后：
  - Redis 是核心依赖（记忆/Skill/mock 数据都依赖它）
  - HTTP 客户端已删除（不再调 Java 后端）
  - Nacos 改为可选（连不上只 warning，不影响启动）
"""

from services.redis_client import get_redis
from services.nacos_client import nacos_client, NacosClient

__all__ = [
    "get_redis",
    "nacos_client", "NacosClient",
]
