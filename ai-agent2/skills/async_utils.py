"""Skill 异步工具 — 将同步 HTTP 调用包装为异步

解决问题：
    Skill 的 execute() 方法是 async def，但内部调用的是同步 HTTP 函数。
    直接调用会阻塞事件循环。用 asyncio.to_thread() 包装后不阻塞。

使用方式：
    from skills.async_utils import async_http_call
    result = await async_http_call(sync_http_function, arg1, arg2)
"""

import asyncio
from typing import Any, Callable
import structlog

logger = structlog.get_logger(__name__)


async def async_http_call(func: Callable, *args, **kwargs) -> Any:
    """在线程池中执行同步 HTTP 调用，避免阻塞事件循环

    Args:
        func: 同步函数（如 _submit_refund_api, _fetch_orders 等）
        *args, **kwargs: 传递给函数的参数

    Returns:
        函数的返回值
    """
    return await asyncio.to_thread(func, *args, **kwargs)
