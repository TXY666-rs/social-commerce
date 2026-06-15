import json
import time
from typing import Optional
import redis
import structlog
from config import settings

logger = structlog.get_logger(__name__)

# 与 Spring 体系统一的 key 前缀规范:
# Spring 使用: chat::memory::{userId}
# ai-agent 使用: chat::ai::session::{session_id}
KEY_PREFIX = "chat::ai::session::"
NOTIFY_CHANNEL_PREFIX = "chat::ai::notify::"  # Pub/Sub channel, 一对一 session_id
TTL_SECONDS = 86400  # 24 小时


class SessionManager:

    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._redis_available = False
        self._connect()

    def _connect(self) -> bool:
        """建立 Redis 连接，返回是否成功"""
        try:
            self._redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD or None,
                decode_responses=True,
                socket_connect_timeout=3,
            )
            self._redis_client.ping()
            self._redis_available = True
            logger.info("redis_connected",
                        host=settings.REDIS_HOST,
                        port=settings.REDIS_PORT)
            return True
        except Exception as e:
            self._redis_client = None
            self._redis_available = False
            logger.error("redis_connect_failed",
                         host=settings.REDIS_HOST,
                         port=settings.REDIS_PORT,
                         error=str(e))
            return False

    def _ensure_redis(self) -> bool:
        """保证 Redis 连接可用：已连接则 ping 验证，断开则自动重连"""
        if self._redis_client is None:
            return self._connect()

        try:
            self._redis_client.ping()
            self._redis_available = True
            return True
        except Exception:
            logger.warning("redis_ping_failed_reconnecting")
            return self._connect()

    def health_check(self) -> dict:
        """外部 health check 接口，返回 Redis 连接状态"""
        ok = self._ensure_redis()
        return {
            "redis_available": ok,
        }

    def _key(self, session_id: str) -> str:
        return f"{KEY_PREFIX}{session_id}"

    def get_history(self, session_id: str) -> list:
        if not self._ensure_redis():
            raise RuntimeError("Redis 不可用，无法读取会话历史")
        try:
            key = self._key(session_id)
            data = self._redis_client.get(key)
            if data:
                # 每次读取时刷新 TTL，避免活跃用户会话过期
                self._redis_client.expire(key, TTL_SECONDS)
                return json.loads(data)
        except Exception as e:
            logger.error("redis_get_history_failed",
                         session_id=session_id,
                         error=str(e))
            raise RuntimeError(f"读取会话历史失败: {e}")
        return []

    def add_message(self, session_id: str, role: str, content: str) -> list:
        history = self.get_history(session_id)
        history.append({
            "role": role,
            "content": content,
            "timestamp": str(int(time.time())),
        })
        if not self._ensure_redis():
            raise RuntimeError("Redis 不可用，无法保存会话消息")
        try:
            self._redis_client.setex(
                self._key(session_id),
                TTL_SECONDS,
                json.dumps(history, ensure_ascii=False),
            )
        except Exception as e:
            logger.error("redis_add_message_failed",
                         session_id=session_id,
                         error=str(e))
            raise RuntimeError(f"保存会话消息失败: {e}")

        # ── 广播通知 SSE 订阅者（失败不影响主流程） ──
        # 写者 pub，读者 sub；读者收到通知后会重新拉 history 算 diff
        try:
            self._redis_client.publish(
                f"{NOTIFY_CHANNEL_PREFIX}{session_id}",
                json.dumps(
                    {"role": role, "ts": int(time.time())},
                    ensure_ascii=False,
                ),
            )
        except Exception as e:
            logger.warning("redis_publish_failed",
                           session_id=session_id,
                           error=str(e))

        return history

    def clear_session(self, session_id: str):
        if not self._ensure_redis():
            raise RuntimeError("Redis 不可用，无法清除会话")
        try:
            self._redis_client.delete(self._key(session_id))
        except Exception as e:
            logger.error("redis_clear_session_failed",
                         session_id=session_id,
                         error=str(e))
            raise RuntimeError(f"清除会话失败: {e}")
