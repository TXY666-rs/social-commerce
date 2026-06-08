"""HTTP 客户端 — 线程安全的连接池管理

使用 threading.local 存储客户端实例，确保每个线程有独立的 httpx.Client。
原因：httpx.Client 不是线程安全的，LangGraph 的 ToolNode 在线程池中执行同步工具。
"""

import threading
import httpx
from config import settings
from config.logging_config import get_trace_id

_local = threading.local()


def get_client() -> httpx.Client:
    """获取线程级持久化 HTTP 客户端，连接池自动复用 TCP 连接"""
    client = getattr(_local, 'client', None)
    if client is None or client.is_closed:
        _local.client = httpx.Client(
            base_url=settings.SPRING_GATEWAY_URL,
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0),
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30,
            ),
            event_hooks={
                "request": [_inject_trace_id],
            },
        )
    return _local.client


def _inject_trace_id(request: httpx.Request) -> None:
    """自动注入 X-Trace-Id 到每个请求"""
    try:
        tid = get_trace_id()
        if tid:
            request.headers.setdefault("X-Trace-Id", tid)
    except Exception:
        pass


def close_client():
    """关闭连接池，优雅停机时调用"""
    client = getattr(_local, 'client', None)
    if client is not None and not client.is_closed:
        client.close()
        _local.client = None
