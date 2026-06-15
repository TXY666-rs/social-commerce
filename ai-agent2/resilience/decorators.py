"""工具调用装饰器 — 统一的容错 + 可观测层

提供 @resilient_tool 装饰器，将熔断器、指数退避重试、日志记录合并为单层，
避免多层装饰器的顺序依赖问题。

设计要点：
    - 瞬态错误（超时/5xx）→ 指数退避重试（带 jitter）
    - 业务错误（4xx/业务码异常）→ 不重试，直接抛给 ToolNode → LLM 自纠错
    - 熔断器打开 → 抛异常，LLM 看到后建议转人工
    - 异常始终向上传播，由 LangGraph ToolNode + self_correction 处理
    - 与 @tool_result_cache 配合时，缓存层在外（缓存命中则跳过重试逻辑）

工具装饰器栈：
    @register_tool()               ← 自动注册到全局工具列表
    @tool                         ← LangChain StructuredTool
    @tool_result_cache(ttl=60)    ← 内存 TTL 缓存（可选）
    @resilient_tool               ← 熔断 + 重试 + 日志（本模块）
    def get_my_orders(...): ...
"""

import functools
import random
import time
import structlog
import httpx

from resilience.circuit_breaker import (
    get_circuit_breaker,
    CircuitBreakerOpenError,
)

logger = structlog.get_logger(__name__)


# ============================================================
# 配置
# ============================================================

MAX_RETRIES = 3
RETRY_DELAY = 1.0
RETRY_BACKOFF = 2.0

# 认证/客户端错误：不重试（重试也没用）
NON_RETRYABLE_STATUS = {400, 401, 403, 404, 422}

# 熔断器配置
CIRCUIT_FAILURE_THRESHOLD = 5
CIRCUIT_COOLDOWN_SECONDS = 30.0


# ============================================================
# resilient_tool — 统一装饰器
# ============================================================

def resilient_tool(
    max_retries: int = MAX_RETRIES,
    delay: float = RETRY_DELAY,
    backoff: float = RETRY_BACKOFF,
    circuit_threshold: int = CIRCUIT_FAILURE_THRESHOLD,
    circuit_cooldown: float = CIRCUIT_COOLDOWN_SECONDS,
):
    """统一的容错装饰器：熔断器 + 指数退避重试 + 日志。

    执行流程：
        1. 熔断器检查 → 熔断中直接抛 CircuitBreakerOpenError
        2. 执行工具调用
        3. 成功 → 记录耗时日志 + 熔断器 success
        4. 瞬态失败（超时/5xx）→ 指数退避 + jitter 后重试
        5. 业务失败（4xx）→ 不重试，直接抛给 ToolNode
        6. 重试耗尽 → 抛出最后一次的原始异常

    异常始终向上传播，由 LangGraph ToolNode 捕获后转给 LLM 自纠错。
    """
    def decorator(func):
        tool_name = func.__name__
        breaker = get_circuit_breaker(tool_name, circuit_threshold, circuit_cooldown)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # ── 熔断器检查 ──
            breaker.allow_request_or_raise()

            # ── 重试逻辑 ──
            current_delay = delay
            last_error = None

            for attempt in range(1, max_retries + 2):
                start = time.monotonic()
                try:
                    result = func(*args, **kwargs)
                    duration = time.monotonic() - start
                    breaker.record_success()
                    logger.info("tool_call", tool=tool_name, status="success",
                                attempt=attempt, duration_ms=round(duration * 1000, 2))
                    return result

                except Exception as e:
                    duration = time.monotonic() - start
                    last_error = e

                    # 认证/客户端错误 → 不重试，直接抛（记录一次失败）
                    if isinstance(e, httpx.HTTPStatusError) and e.response.status_code in NON_RETRYABLE_STATUS:
                        status = e.response.status_code
                        logger.warning("tool_non_retryable_error", tool=tool_name,
                                       status=status, duration_ms=round(duration * 1000, 2))
                        breaker.record_failure()
                        raise

                    # 瞬态失败 → 判断是否重试
                    if attempt <= max_retries:
                        # 重试阶段：不记录到熔断器（避免单次故障多次计数）
                        jitter = current_delay * (0.75 + random.random() * 0.5)
                        logger.warning("tool_retry", tool=tool_name, attempt=attempt,
                                       max_retries=max_retries, error=str(e)[:200],
                                       retry_in_ms=round(jitter * 1000))
                        time.sleep(jitter)
                        current_delay *= backoff
                    else:
                        # 所有重试耗尽：只在最终失败时记录一次到熔断器
                        breaker.record_failure()
                        logger.error("tool_all_retries_exhausted", tool=tool_name,
                                     attempts=attempt, error=str(e)[:200])

            # 全部重试失败 → 抛出原始异常（不吞掉）
            raise last_error

        return wrapper
    return decorator
