"""pytest 全局配置与公共 fixtures

运行方式（在项目根目录执行）：
    pytest
    pytest tests/test_security.py -v
    pytest tests/ -k "injection" --tb=short
"""

import sys
import os
import json
from unittest.mock import MagicMock, patch

import pytest

# ============================================================
# 路径配置 — 确保项目根目录在 sys.path 中，使模块可以被导入
# ============================================================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# MockRedis — 内存实现的 Redis 替身，用于不依赖真实 Redis 的测试
# ============================================================

class MockRedis:
    """简易内存 Redis 替身，仅实现测试所需的接口（get / setex / delete）"""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._ttls: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = value
        self._ttls[key] = ttl

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._ttls.pop(key, None)

    def exists(self, key: str) -> bool:
        return key in self._store

    def keys(self, pattern: str = "*") -> list[str]:
        # 简单实现，不支持通配符
        return list(self._store.keys())

    def flushdb(self) -> None:
        self._store.clear()
        self._ttls.clear()


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_redis():
    """提供一个 MockRedis 实例，并 patch services.redis_client.get_redis()

    使用方式：
        def test_something(mock_redis):
            # 此时 services.redis_client.get_redis() 返回 mock_redis
            mock_redis.setex("key", 60, "value")
            assert mock_redis.get("key") == "value"
    """
    redis_instance = MockRedis()
    with patch("services.redis_client.get_redis", return_value=redis_instance):
        yield redis_instance


@pytest.fixture
def mock_redis_magic():
    """提供 unittest.mock.MagicMock 版的 Redis，适合只需要断言调用而不需要真实存取的测试"""
    mock = MagicMock()
    mock.get.return_value = None
    mock.setex.return_value = None
    mock.delete.return_value = None
    with patch("services.redis_client.get_redis", return_value=mock):
        yield mock


@pytest.fixture
def clean_env(monkeypatch):
    """清理可能影响测试的环境变量"""
    # 可在子测试中通过 monkeypatch 设置临时环境变量
    yield monkeypatch


# ============================================================
# 辅助工具函数
# ============================================================

def build_json_payload(data: dict) -> str:
    """将 dict 序列化为 JSON 字符串（用于模拟 Redis 存储格式）"""
    return json.dumps(data)


def repeat(func, times: int):
    """重复调用某函数 N 次（用于熔断器连续失败场景）"""
    return [func() for _ in range(times)]
