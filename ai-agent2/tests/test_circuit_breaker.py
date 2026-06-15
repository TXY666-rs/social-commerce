"""resilience/circuit_breaker.py 单元测试

覆盖类与函数：
    - CircuitBreaker: 熔断器完整生命周期
    - CircuitBreakerOpenError: 熔断异常
    - CircuitState: 状态枚举
    - get_circuit_breaker(): 全局注册表
    - get_all_breakers(): 状态查询

状态机：
    CLOSED → (连续失败 >= threshold) → OPEN
    OPEN   → (冷却时间到)             → HALF_OPEN
    HALF_OPEN → (探测成功)            → CLOSED（恢复）
    HALF_OPEN → (探测失败)            → OPEN（再次熔断）
"""

import time
import threading
from unittest.mock import patch

import pytest

from resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    get_circuit_breaker,
    get_all_breakers,
    _breakers,
)


# ============================================================
# 辅助 fixtures
# ============================================================

@pytest.fixture
def cb():
    """创建一个测试用熔断器：阈值=3，冷却=10秒，半开最多1个探测"""
    return CircuitBreaker(
        name="test_tool",
        failure_threshold=3,
        cooldown_seconds=10.0,
        half_open_max=1,
    )


@pytest.fixture(autouse=True)
def clean_global_registry():
    """每个测试前后清理全局熔断器注册表，避免测试间互相影响"""
    _breakers.clear()
    yield
    _breakers.clear()


# ============================================================
# 1. 初始状态
# ============================================================

class TestCircuitBreakerInitialState:
    """测试熔断器初始状态"""

    def test_initial_state_is_closed(self, cb):
        """初始状态应为 CLOSED"""
        assert cb.state == CircuitState.CLOSED

    def test_initial_failure_count_is_zero(self, cb):
        """初始失败计数为 0"""
        assert cb._failure_count == 0

    def test_initial_success_count_is_zero(self, cb):
        """初始成功计数为 0"""
        assert cb._success_count == 0

    def test_initial_allow_request(self, cb):
        """初始状态允许请求通过"""
        assert cb.allow_request() is True


# ============================================================
# 2. CLOSED 状态行为
# ============================================================

class TestCircuitBreakerClosedState:
    """测试 CLOSED 状态下的行为"""

    def test_single_failure_keeps_closed(self, cb):
        """单次失败不触发熔断，仍为 CLOSED"""
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 1

    def test_two_failures_keep_closed(self, cb):
        """两次失败（阈值=3）仍为 CLOSED"""
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 2

    def test_failures_below_threshold_stay_closed(self, cb):
        """失败次数低于阈值，保持 CLOSED"""
        for _ in range(cb.failure_threshold - 1):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_record_success_resets_failure_count(self, cb):
        """CLOSED 状态下 record_success 重置失败计数"""
        cb.record_failure()
        cb.record_failure()
        assert cb._failure_count == 2
        cb.record_success()
        assert cb._failure_count == 0
        assert cb._success_count == 1

    def test_record_success_increments_success_count(self, cb):
        """CLOSED 状态下 record_success 增加成功计数"""
        cb.record_success()
        cb.record_success()
        assert cb._success_count == 2


# ============================================================
# 3. CLOSED → OPEN 转换
# ============================================================

class TestCircuitBreakerOpenTransition:
    """测试 CLOSED → OPEN 的熔断触发"""

    def test_consecutive_failures_open_circuit(self, cb):
        """连续失败达到阈值，触发熔断（CLOSED → OPEN）"""
        for _ in range(cb.failure_threshold):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_open_state_rejects_requests(self, cb):
        """OPEN 状态拒绝所有请求"""
        for _ in range(cb.failure_threshold):
            cb.record_failure()
        assert cb.allow_request() is False

    def test_allow_request_or_raises_when_open(self, cb):
        """OPEN 状态下 allow_request_or_raise 抛出 CircuitBreakerOpenError"""
        for _ in range(cb.failure_threshold):
            cb.record_failure()
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            cb.allow_request_or_raise()
        assert "test_tool" in str(exc_info.value)

    def test_open_error_message_contains_cooldown(self, cb):
        """熔断异常消息中包含冷却时间"""
        for _ in range(cb.failure_threshold):
            cb.record_failure()
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            cb.allow_request_or_raise()
        assert "10" in str(exc_info.value)  # cooldown_seconds = 10

    def test_allow_request_or_raise_passes_when_closed(self, cb):
        """CLOSED 状态下 allow_request_or_raise 正常通过（不抛异常）"""
        cb.allow_request_or_raise()  # 不应抛出


# ============================================================
# 4. OPEN → HALF_OPEN 转换（冷却期后）
# ============================================================

class TestCircuitBreakerHalfOpenTransition:
    """测试 OPEN → HALF_OPEN 的冷却期转换"""

    def test_cooldown_triggers_half_open(self, cb):
        """冷却时间到达后，OPEN → HALF_OPEN"""
        # 触发熔断
        for _ in range(cb.failure_threshold):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # 模拟冷却时间过去
        with patch("resilience.circuit_breaker.time.monotonic",
                   return_value=time.monotonic() + 11.0):
            assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_not_triggered_before_cooldown(self, cb):
        """冷却时间未到时，仍为 OPEN"""
        for _ in range(cb.failure_threshold):
            cb.record_failure()

        # 仅过了 5 秒（冷却期 10 秒）
        with patch("resilience.circuit_breaker.time.monotonic",
                   return_value=time.monotonic() + 5.0):
            assert cb.state == CircuitState.OPEN

    def test_half_open_allows_probe_request(self, cb):
        """HALF_OPEN 状态允许探测请求通过"""
        for _ in range(cb.failure_threshold):
            cb.record_failure()

        with patch("resilience.circuit_breaker.time.monotonic",
                   return_value=time.monotonic() + 11.0):
            assert cb.allow_request() is True

    def test_half_open_limits_probe_count(self):
        """HALF_OPEN 状态只允许 half_open_max 个探测请求"""
        cb = CircuitBreaker(
            name="test_limited",
            failure_threshold=2,
            cooldown_seconds=5.0,
            half_open_max=2,  # 最多 2 个探测
        )
        # 触发熔断
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # 冷却后进入 HALF_OPEN
        with patch("resilience.circuit_breaker.time.monotonic",
                   return_value=time.monotonic() + 6.0):
            # 第 1 个探测：允许
            assert cb.allow_request() is True
            # 第 2 个探测：允许
            assert cb.allow_request() is True
            # 第 3 个探测：拒绝（超出 half_open_max=2）
            assert cb.allow_request() is False


# ============================================================
# 5. HALF_OPEN → CLOSED（探测成功，恢复）
# ============================================================

class TestCircuitBreakerRecovery:
    """测试 HALF_OPEN → CLOSED 的恢复路径"""

    def test_probe_success_recovers_to_closed(self, cb):
        """HALF_OPEN 探测成功 → CLOSED（恢复）"""
        # 触发熔断
        for _ in range(cb.failure_threshold):
            cb.record_failure()

        future_time = time.monotonic() + 11.0
        with patch("resilience.circuit_breaker.time.monotonic",
                   return_value=future_time):
            # 进入 HALF_OPEN 并允许探测
            assert cb.state == CircuitState.HALF_OPEN
            cb.allow_request()  # 探测请求通过

            # 探测成功 → 恢复
            cb.record_success()
            assert cb.state == CircuitState.CLOSED
            assert cb._failure_count == 0

    def test_recovery_increments_success_count(self, cb):
        """恢复后成功计数增加"""
        for _ in range(cb.failure_threshold):
            cb.record_failure()

        future_time = time.monotonic() + 11.0
        with patch("resilience.circuit_breaker.time.monotonic",
                   return_value=future_time):
            cb.allow_request()
            cb.record_success()
            assert cb._success_count == 1


# ============================================================
# 6. HALF_OPEN → OPEN（探测失败，再次熔断）
# ============================================================

class TestCircuitBreakerReopen:
    """测试 HALF_OPEN → OPEN 的再次熔断"""

    def test_probe_failure_reopens_circuit(self, cb):
        """HALF_OPEN 探测失败 → OPEN（再次熔断）"""
        # 触发熔断
        for _ in range(cb.failure_threshold):
            cb.record_failure()

        future_time = time.monotonic() + 11.0
        with patch("resilience.circuit_breaker.time.monotonic",
                   return_value=future_time):
            assert cb.state == CircuitState.HALF_OPEN
            cb.allow_request()  # 探测请求通过

            # 探测失败 → 再次熔断
            cb.record_failure()
            # 注意：record_failure 内部直接设 _state = OPEN，不经过 state property
            assert cb._state == CircuitState.OPEN

    def test_reopen_updates_last_failure_time(self, cb):
        """再次熔断时更新 last_failure_time"""
        for _ in range(cb.failure_threshold):
            cb.record_failure()
        first_failure_time = cb._last_failure_time

        future_time = first_failure_time + 11.0
        with patch("resilience.circuit_breaker.time.monotonic",
                   return_value=future_time):
            cb.state  # 触发 HALF_OPEN
            cb.allow_request()
            cb.record_failure()  # 探测失败
            assert cb._last_failure_time == future_time


# ============================================================
# 7. get_status() — 状态查询
# ============================================================

class TestCircuitBreakerGetStatus:
    """测试 get_status() 返回的状态信息"""

    def test_status_keys(self, cb):
        """get_status 返回包含所有必要字段的字典"""
        status = cb.get_status()
        expected_keys = {"name", "state", "failure_count", "success_count",
                         "failure_threshold", "cooldown_seconds"}
        assert set(status.keys()) == expected_keys

    def test_status_initial_values(self, cb):
        """初始状态值正确"""
        status = cb.get_status()
        assert status["name"] == "test_tool"
        assert status["state"] == CircuitState.CLOSED
        assert status["failure_count"] == 0
        assert status["success_count"] == 0
        assert status["failure_threshold"] == 3
        assert status["cooldown_seconds"] == 10.0

    def test_status_after_failures(self, cb):
        """失败后的状态值"""
        cb.record_failure()
        cb.record_failure()
        status = cb.get_status()
        assert status["failure_count"] == 2
        assert status["state"] == CircuitState.CLOSED

    def test_status_after_opening(self, cb):
        """熔断后的状态值"""
        for _ in range(cb.failure_threshold):
            cb.record_failure()
        status = cb.get_status()
        assert status["state"] == CircuitState.OPEN
        assert status["failure_count"] == 3


# ============================================================
# 8. 全局注册表
# ============================================================

class TestGlobalRegistry:
    """测试全局熔断器注册表"""

    def test_get_circuit_breaker_creates_new(self):
        """get_circuit_breaker 创建新的熔断器"""
        cb = get_circuit_breaker("api_call", failure_threshold=5, cooldown_seconds=60)
        assert cb.name == "api_call"
        assert cb.failure_threshold == 5
        assert cb.cooldown_seconds == 60

    def test_get_circuit_breaker_returns_singleton(self):
        """get_circuit_breaker 对同一名称返回同一实例（单例）"""
        cb1 = get_circuit_breaker("singleton_test")
        cb2 = get_circuit_breaker("singleton_test")
        assert cb1 is cb2

    def test_get_all_breakers_empty_initially(self):
        """初始时 get_all_breakers 返回空字典"""
        assert get_all_breakers() == {}

    def test_get_all_breakers_after_creation(self):
        """创建熔断器后 get_all_breakers 返回对应状态"""
        get_circuit_breaker("tool_a")
        get_circuit_breaker("tool_b")
        all_status = get_all_breakers()
        assert "tool_a" in all_status
        assert "tool_b" in all_status
        assert all_status["tool_a"]["state"] == CircuitState.CLOSED


# ============================================================
# 9. CircuitBreakerOpenError 异常
# ============================================================

class TestCircuitBreakerOpenError:
    """测试熔断异常类"""

    def test_error_is_exception(self):
        """CircuitBreakerOpenError 继承自 Exception"""
        assert issubclass(CircuitBreakerOpenError, Exception)

    def test_error_can_be_raised_and_caught(self):
        """CircuitBreakerOpenError 可以被正常抛出和捕获"""
        with pytest.raises(CircuitBreakerOpenError):
            raise CircuitBreakerOpenError("测试异常")

    def test_error_message_preserved(self):
        """异常消息被完整保留"""
        msg = "工具 xyz 暂时不可用"
        try:
            raise CircuitBreakerOpenError(msg)
        except CircuitBreakerOpenError as e:
            assert str(e) == msg


# ============================================================
# 10. 线程安全（加分测试）
# ============================================================

class TestCircuitBreakerThreadSafety:
    """测试熔断器的线程安全性"""

    def test_concurrent_failures_do_not_crash(self):
        """多线程并发 record_failure 不会崩溃"""
        cb = CircuitBreaker(name="concurrent_test", failure_threshold=100)
        errors = []

        def fail_many_times():
            try:
                for _ in range(50):
                    cb.record_failure()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=fail_many_times) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0  # 无异常
        # 所有 200 次失败都被记录（阈值=100，会触发熔断）
        assert cb._failure_count >= 100

    def test_concurrent_allow_and_record(self):
        """多线程同时进行 allow_request 和 record 操作不会崩溃"""
        cb = CircuitBreaker(name="mixed_test", failure_threshold=50, cooldown_seconds=0.01)
        errors = []

        def worker():
            try:
                for _ in range(20):
                    cb.allow_request()
                    cb.record_failure()
                    cb.record_success()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# ============================================================
# 11. 完整生命周期集成测试
# ============================================================

class TestCircuitBreakerLifecycle:
    """测试熔断器完整生命周期：CLOSED → OPEN → HALF_OPEN → CLOSED"""

    def test_full_lifecycle_recovery(self):
        """完整生命周期：正常 → 熔断 → 冷却 → 半开探测 → 恢复"""
        cb = CircuitBreaker(
            name="lifecycle_test",
            failure_threshold=3,
            cooldown_seconds=10.0,
            half_open_max=1,
        )

        # 阶段1：正常状态
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

        # 阶段2：连续失败触发熔断
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

        # 阶段3：冷却期过后进入半开
        future = time.monotonic() + 11.0
        with patch("resilience.circuit_breaker.time.monotonic", return_value=future):
            assert cb.state == CircuitState.HALF_OPEN

            # 阶段4：探测请求通过
            assert cb.allow_request() is True

            # 阶段5：探测成功，恢复正常
            cb.record_success()
            assert cb.state == CircuitState.CLOSED
            assert cb._failure_count == 0

    def test_full_lifecycle_reopen(self):
        """完整生命周期：正常 → 熔断 → 冷却 → 半开探测 → 再次熔断"""
        cb = CircuitBreaker(
            name="reopen_test",
            failure_threshold=2,
            cooldown_seconds=5.0,
            half_open_max=1,
        )

        # 触发熔断
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # 冷却后进入 HALF_OPEN
        future = time.monotonic() + 6.0
        with patch("resilience.circuit_breaker.time.monotonic", return_value=future):
            assert cb.state == CircuitState.HALF_OPEN
            cb.allow_request()

            # 探测失败 → 再次熔断
            cb.record_failure()
            assert cb._state == CircuitState.OPEN
