"""
Day 24 — 熔断器测试

覆盖：
1. CircuitState 三态枚举
2. CLOSED 状态正常通过
3. 连续失败触发 OPEN
4. OPEN 状态快速失败 + fallback
5. OPEN → HALF_OPEN 超时恢复
6. HALF_OPEN → CLOSED 成功足够多
7. HALF_OPEN → OPEN 失败过多
8. CircuitStats 统计
9. 手动 reset
10. 边界情况（threshold=1, timeout=0）
"""
import sys
import os
import time
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d24_circuit_breaker import (
    CircuitBreaker, CircuitState, CircuitBreakerOpenError
)


class TestCircuitState(unittest.TestCase):
    """状态枚举"""

    def test_three_states(self):
        self.assertEqual(CircuitState.CLOSED.value, "closed")
        self.assertEqual(CircuitState.OPEN.value, "open")
        self.assertEqual(CircuitState.HALF_OPEN.value, "half_open")


class TestClosedState(unittest.TestCase):
    """CLOSED 状态"""

    def test_success_stays_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
        cb.call(lambda: "ok")
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_some_failures_below_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
        call_n = {"n": 0}

        def _fail_twice_then_ok():
            call_n["n"] += 1
            if call_n["n"] <= 2:
                raise ValueError("fail")

        # 失败2次 + 成功1次，未达到3次阈值
        for _ in range(3):
            try:
                cb.call(_fail_twice_then_ok)
            except ValueError:
                pass
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_stats_recorded_in_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.call(lambda: "ok")
        cb.call(lambda: "ok2")
        self.assertEqual(cb.stats.total_calls, 2)
        self.assertEqual(cb.stats.success_count, 2)


class TestOpenState(unittest.TestCase):
    """OPEN 状态"""

    def test_threshold_triggers_open(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10)
        fail_fn = lambda: (_ for _ in ()).throw(ValueError("fail"))

        for _ in range(2):
            try:
                cb.call(fail_fn)
            except (ValueError, CircuitBreakerOpenError):
                pass

        self.assertEqual(cb.state, CircuitState.OPEN)

    def test_open_raises_error(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10)
        fail_fn = lambda: (_ for _ in ()).throw(ValueError("fail"))

        try:
            cb.call(fail_fn)
        except ValueError:
            pass

        with self.assertRaises(CircuitBreakerOpenError):
            cb.call(lambda: "should not reach")

    def test_open_calls_fallback(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10)
        fail_fn = lambda: (_ for _ in ()).throw(ValueError("fail"))

        try:
            cb.call(fail_fn)
        except (ValueError, CircuitBreakerOpenError):
            pass

        result = cb.call(fail_fn, fallback=lambda: "fallback ok")
        self.assertEqual(result, "fallback ok")


class TestHalfOpenTransition(unittest.TestCase):
    """HALF_OPEN 状态转换"""

    def test_open_to_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
        fail_fn = lambda: (_ for _ in ()).throw(ValueError("fail"))

        try:
            cb.call(fail_fn)
        except (ValueError, CircuitBreakerOpenError):
            pass

        self.assertEqual(cb.state, CircuitState.OPEN)
        time.sleep(0.06)

        # 在 HALF_OPEN 状态下调用触发状态检查
        cb._try_transition()
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

    def test_half_open_to_closed_success_ratio(self):
        cb = CircuitBreaker(
            failure_threshold=1, recovery_timeout=0.05,
            half_open_max_requests=2, half_open_success_ratio=0.5
        )
        fail_fn = lambda: (_ for _ in ()).throw(ValueError("fail"))

        try:
            cb.call(fail_fn)
        except (ValueError, CircuitBreakerOpenError):
            pass

        time.sleep(0.06)

        # HALF_OPEN 后全部成功
        cb.call(lambda: "ok1")
        cb.call(lambda: "ok2")
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_half_open_to_open_fail_ratio(self):
        cb = CircuitBreaker(
            failure_threshold=1, recovery_timeout=0.05,
            half_open_max_requests=2, half_open_success_ratio=0.5
        )
        fail_fn = lambda: (_ for _ in ()).throw(ValueError("fail"))

        try:
            cb.call(fail_fn)
        except (ValueError, CircuitBreakerOpenError):
            pass

        time.sleep(0.06)

        # HALF_OPEN 后全部失败
        for _ in range(2):
            try:
                cb.call(fail_fn)
            except (ValueError, CircuitBreakerOpenError):
                pass

        self.assertEqual(cb.state, CircuitState.OPEN)

    def test_half_open_full_recovery_cycle(self):
        """完整周期：CLOSED→OPEN→HALF_OPEN→CLOSED"""
        cb = CircuitBreaker(
            failure_threshold=1, recovery_timeout=0.05,
            half_open_max_requests=2, half_open_success_ratio=0.5
        )
        fail_fn = lambda: (_ for _ in ()).throw(ValueError("fail"))

        # CLOSED → OPEN
        try:
            cb.call(fail_fn)
        except (ValueError, CircuitBreakerOpenError):
            pass
        self.assertEqual(cb.state, CircuitState.OPEN)

        # OPEN → HALF_OPEN
        time.sleep(0.06)
        cb.call(lambda: "recovery")
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

        # HALF_OPEN → CLOSED
        cb.call(lambda: "ok2")
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_half_open_reopens_on_failure(self):
        """HALF_OPEN 条件下失败→OPEN"""
        cb = CircuitBreaker(
            failure_threshold=1, recovery_timeout=0.05,
            half_open_max_requests=2, half_open_success_ratio=0.5
        )
        fail_fn = lambda: (_ for _ in ()).throw(ValueError("fail"))

        try:
            cb.call(fail_fn)
        except (ValueError, CircuitBreakerOpenError):
            pass

        time.sleep(0.06)
        # _try_transition 会把 OPEN → HALF_OPEN
        cb._try_transition()
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

        # 连续 2 次失败（half_open_max_requests=2, success_ratio=0）→ 回到 OPEN
        try:
            cb.call(fail_fn)
        except (ValueError, CircuitBreakerOpenError):
            pass

        try:
            cb.call(fail_fn)
        except (ValueError, CircuitBreakerOpenError):
            pass

        self.assertEqual(cb.state, CircuitState.OPEN)


class TestReset(unittest.TestCase):
    """手动重置"""

    def test_reset_returns_to_closed(self):
        cb = CircuitBreaker(failure_threshold=1)
        fail_fn = lambda: (_ for _ in ()).throw(ValueError("fail"))

        try:
            cb.call(fail_fn)
        except (ValueError, CircuitBreakerOpenError):
            pass

        self.assertEqual(cb.state, CircuitState.OPEN)
        cb.reset()
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_reset_clears_failures(self):
        cb = CircuitBreaker(failure_threshold=1)
        fail_fn = lambda: (_ for _ in ()).throw(ValueError("fail"))

        try:
            cb.call(fail_fn)
        except (ValueError, CircuitBreakerOpenError):
            pass

        cb.reset()
        result = cb.call(lambda: "ok")
        self.assertEqual(result, "ok")
        self.assertEqual(cb.state, CircuitState.CLOSED)


class TestStats(unittest.TestCase):
    """熔断统计"""

    def test_stats_after_success(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.call(lambda: "ok")
        self.assertEqual(cb.stats.success_count, 1)
        self.assertEqual(cb.stats.fail_count, 0)

    def test_stats_after_failure(self):
        cb = CircuitBreaker(failure_threshold=3)
        fail_fn = lambda: (_ for _ in ()).throw(ValueError("fail"))
        try:
            cb.call(fail_fn)
        except (ValueError, CircuitBreakerOpenError):
            pass
        self.assertEqual(cb.stats.fail_count, 1)

    def test_state_changes_counted(self):
        cb = CircuitBreaker(failure_threshold=1)
        fail_fn = lambda: (_ for _ in ()).throw(ValueError("fail"))

        try:
            cb.call(fail_fn)
        except (ValueError, CircuitBreakerOpenError):
            pass

        self.assertGreaterEqual(cb.stats.state_changes, 1)


class TestEdgeCases(unittest.TestCase):
    """边界情况"""

    def test_threshold_one(self):
        """threshold=1 一次失败即熔断"""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10)
        fail_fn = lambda: (_ for _ in ()).throw(ValueError("fail"))

        try:
            cb.call(fail_fn)
        except (ValueError, CircuitBreakerOpenError):
            pass

        self.assertEqual(cb.state, CircuitState.OPEN)

    def test_zero_timeout(self):
        """timeout=0 立即恢复"""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        fail_fn = lambda: (_ for _ in ()).throw(ValueError("fail"))

        try:
            cb.call(fail_fn)
        except (ValueError, CircuitBreakerOpenError):
            pass

        # timeout=0 → _try_transition 立即进入 HALF_OPEN
        cb._try_transition()
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)


if __name__ == "__main__":
    unittest.main(verbosity=2)
