"""TraceId 中间件

每个请求：注入 TraceId + 记录请求日志
"""
import time
import uuid
from fastapi import Request
from config.logging_config import set_trace_id
import structlog

logger = structlog.get_logger(__name__)


async def trace_and_metrics_middleware(request: Request, call_next):
    """每个请求：注入 TraceId + 记录请求日志"""
    # 1. TraceId：优先从 Gateway 传入的 header 读取，否则生成
    trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex[:16]
    set_trace_id(trace_id)

    # 2. 记录请求开始时间
    start = time.monotonic()

    # 3. 注入 trace_id 到响应 header，方便前端/下游排查
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id

    duration = time.monotonic() - start
    path = request.url.path
    method = request.method
    status_code = response.status_code

    logger.info(
        "http_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration * 1000, 2),
        trace_id=trace_id,
    )

    return response
