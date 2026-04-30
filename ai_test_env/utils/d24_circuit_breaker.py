"""
Day 24 — 熔断器（Circuit Breaker）

功能说明：
    三态熔断器：CLOSED(正常) → OPEN(熔断) → HALF_OPEN(半开) → CLOSED(恢复)。
    失败计数超过阈值后熔断，超时后进入半开状态探测恢复。

面试话术：
    "我实现了三态熔断器保护 API 调用链。连续 5 次失败自动 OPEN，
    30 秒后进入 HALF_OPEN 试探性放行 3 个请求，成功超过 50% 就恢复 CLOSED。
    核心设计是快速失败，避免下游因为上游不可用而连带崩溃。"
"""
import time
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, List


class CircuitState(Enum):
    """熔断器三态"""
    CLOSED = "closed"          # 正常，请求通过
    OPEN = "open"              # 熔断，请求快速失败
    HALF_OPEN = "half_open"    # 半开，探测性放行


@dataclass
class CircuitStats:
    """熔断统计"""
    total_calls: int = 0
    success_count: int = 0
    fail_count: int = 0
    state_changes: int = 0
    recent_failures: List[float] = field(default_factory=list)


class CircuitBreaker:
    """熔断器

    Args:
        failure_threshold: 连续失败次数阈值
        recovery_timeout: 从 OPEN 到 HALF_OPEN 的超时 (s)
        half_open_max_requests: HALF_OPEN 状态最大探测请求数
        half_open_success_ratio: HALF_OPEN 恢复成功率
    """

    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: float = 30.0,
                 half_open_max_requests: int = 3,
                 half_open_success_ratio: float = 0.5):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests
        self.half_open_success_ratio = half_open_success_ratio

        self._state = CircuitState.CLOSED
        self._last_failure_time: float = 0.0
        self._consecutive_failures = 0
        self._lock = threading.Lock()
        self.stats = CircuitStats()
        self._half_open_successes = 0
        self._half_open_attempts = 0

    @property
    def state(self) -> CircuitState:
        return self._state

    def _should_open(self) -> bool:
        """检查是否需要从 HALF_OPEN 回到 OPEN"""
        if self._state != CircuitState.HALF_OPEN:
            return False
        if self._half_open_attempts >= self.half_open_max_requests:
            ratio = self._half_open_successes / max(self._half_open_attempts, 1)
            return ratio < self.half_open_success_ratio
        return False

    def _should_close(self) -> bool:
        """检查是否需要从 HALF_OPEN 进入 CLOSED"""
        if self._state != CircuitState.HALF_OPEN:
            return False
        if self._half_open_attempts >= self.half_open_max_requests:
            ratio = self._half_open_successes / max(self._half_open_attempts, 1)
            return ratio >= self.half_open_success_ratio
        return False

    def _try_transition(self) -> None:
        """检查状态转换"""
        now = time.time()

        if self._state == CircuitState.CLOSED:
            if self._consecutive_failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._last_failure_time = now
                self.stats.state_changes += 1

        elif self._state == CircuitState.OPEN:
            if now - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_successes = 0
                self._half_open_attempts = 0
                self._consecutive_failures = 0
                self.stats.state_changes += 1

    def call(self, fn: Callable[..., Any],
             fallback: Optional[Callable[..., Any]] = None,
             args: Optional[tuple] = None,
             kwargs: Optional[dict] = None) -> Any:
        """执行调用，受熔断器保护

        Args:
            fn: 目标函数
            fallback: 降级函数（熔断时调用）
            args: 位置参数
            kwargs: 关键字参数

        Returns:
            fn 或 fallback 的返回值

        Raises:
            Exception: 若函数失败且无 fallback
        """
        args = args or ()
        kwargs = kwargs or {}

        with self._lock:
            self._try_transition()
            current_state = self._state

            if current_state == CircuitState.OPEN:
                if fallback:
                    return fallback(*args, **kwargs)
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")

            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_attempts >= self.half_open_max_requests:
                    if fallback:
                        return fallback(*args, **kwargs)
                    raise CircuitBreakerOpenError("Half-open max requests exceeded")
                self._half_open_attempts += 1

        # 执行调用
        try:
            result = fn(*args, **kwargs)
        except Exception as e:
            with self._lock:
                self.stats.total_calls += 1
                self.stats.fail_count += 1
                self._consecutive_failures += 1
                self.stats.recent_failures.append(time.time())

                if self._state == CircuitState.HALF_OPEN:
                    if self._should_open():
                        self._state = CircuitState.OPEN
                        self._last_failure_time = time.time()
                        self.stats.state_changes += 1

                self._try_transition()

            if fallback:
                return fallback(*args, **kwargs)
            raise

        # 成功
        with self._lock:
            self.stats.total_calls += 1
            self.stats.success_count += 1
            self._consecutive_failures = 0

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._should_close():
                    self._state = CircuitState.CLOSED
                    self.stats.state_changes += 1

        return result

    def reset(self) -> None:
        """手动重置为 CLOSED"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._consecutive_failures = 0
            self._half_open_successes = 0
            self._half_open_attempts = 0
            self.stats.state_changes += 1


class CircuitBreakerOpenError(Exception):
    """熔断器处于 OPEN 状态时抛出的异常"""
    pass
