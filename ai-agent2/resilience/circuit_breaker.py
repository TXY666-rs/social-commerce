"""熔断器（Circuit Breaker）— 工具级故障隔离

设计思路：
    当某个工具连续失败 N 次后，"熔断"该工具，后续调用直接抛异常，
    由 LangGraph ToolNode 捕获并转给 LLM 自纠错。经过冷却期后，
    放行一次"探测请求"试探是否恢复。

状态机：
    CLOSED（正常）→ 连续失败 >= threshold → OPEN（熔断）
    OPEN（熔断）→ 冷却时间到 → HALF_OPEN（半开）
    HALF_OPEN（半开）→ 探测成功 → CLOSED（恢复）
    HALF_OPEN（半开）→ 探测失败 → OPEN（再次熔断）

面试要点：
    - 为什么需要熔断？避免一个下游服务故障拖垮整个调用链
    - 与重试的区别？重试是"同一个请求多次尝试"，熔断是"多个请求共享故障状态"
    - 半开状态的作用？避免服务恢复后被大量请求瞬间打垮
    - 为什么抛异常而非返回兜底？让 LLM 看到错误后自主调整策略（自纠错）
"""

import time
import threading
import structlog

logger = structlog.get_logger(__name__)


class CircuitBreakerOpenError(Exception):
    """熔断器打开时抛出的异常，由 ToolNode 捕获后转给 LLM 自纠错"""
    pass


class CircuitState:
    """熔断器状态枚举"""
    CLOSED = "closed"           # 正常：允许所有请求通过
    OPEN = "open"               # 熔断：拒绝所有请求，直接返回兜底
    HALF_OPEN = "half_open"     # 半开：只放行一个探测请求


class CircuitBreaker:
    """单个工具的熔断器

    Args:
        name:              工具名（用于日志和指标）
        failure_threshold:  连续失败多少次后触发熔断（默认 5）
        cooldown_seconds:  熔断后冷却时间（默认 30 秒）
        half_open_max:     半开状态最多放行几个探测请求（默认 1）
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
        half_open_max: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_max = half_open_max

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
        self._lock = threading.RLock()  # 可重入锁，允许同一线程多次获取

    @property
    def state(self) -> str:
        """获取当前状态（自动检查是否应该从 OPEN 转为 HALF_OPEN）"""
        with self._lock:
            if self._state == CircuitState.OPEN:
                # 冷却时间到了，转为半开
                if time.monotonic() - self._last_failure_time >= self.cooldown_seconds:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info("circuit_half_open", tool=self.name)
            return self._state

    def allow_request(self) -> bool:
        """判断是否允许本次请求通过

        Returns:
            True = 允许（正常或半开的探测请求）
            False = 拒绝（熔断中，应返回兜底结果）
        """
        with self._lock:
            current = self.state  # 触发自动状态转换

            if current == CircuitState.CLOSED:
                return True

            if current == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.half_open_max:
                    self._half_open_calls += 1
                    logger.info("circuit_probe_allowed", tool=self.name,
                                probe_num=self._half_open_calls)
                    return True
                return False

            # OPEN 状态
            return False

    def allow_request_or_raise(self):
        """判断是否允许本次请求通过，熔断时抛出异常而非返回 False

        异常会被 ToolNode 捕获，转为错误消息返回给 LLM，触发自纠错。
        """
        if not self.allow_request():
            raise CircuitBreakerOpenError(
                f"工具 {self.name} 暂时不可用（连续失败 {self._failure_count} 次，"
                f"冷却 {self.cooldown_seconds} 秒后自动恢复）"
            )

    def record_success(self):
        """记录一次成功调用"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # 半开状态的成功 → 恢复正常
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count += 1
                logger.info("circuit_recovered", tool=self.name,
                            total_success=self._success_count)
            elif self._state == CircuitState.CLOSED:
                # 正常状态的成功 → 重置连续失败计数
                self._failure_count = 0
                self._success_count += 1

    def record_failure(self):
        """记录一次失败调用"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                # 半开状态的失败 → 再次熔断
                self._state = CircuitState.OPEN
                logger.warning("circuit_reopened_after_probe", tool=self.name)
                return

            if self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    # 连续失败达到阈值 → 熔断
                    self._state = CircuitState.OPEN
                    logger.error("circuit_opened", tool=self.name,
                                 failures=self._failure_count,
                                 cooldown=self.cooldown_seconds)

    def get_status(self) -> dict:
        """获取熔断器状态信息（供监控和调试）"""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "cooldown_seconds": self.cooldown_seconds,
        }


# ============================================================
# 全局熔断器注册表
# ============================================================

_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    cooldown_seconds: float = 30.0,
) -> CircuitBreaker:
    """获取或创建指定工具的熔断器（单例模式）"""
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            cooldown_seconds=cooldown_seconds,
        )
    return _breakers[name]


def get_all_breakers() -> dict[str, dict]:
    """获取所有熔断器的状态（供管理 API 使用）"""
    return {name: cb.get_status() for name, cb in _breakers.items()}
