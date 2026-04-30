"""
Day 23 — 指数退避重试引擎

功能说明：
    实现三种重试策略：固定间隔、指数退避、Decorrelated Jitter。
    支持最大重试次数控制、成功即停、重试日志记录。

面试话术：
    "我实现了一个可配置的重试引擎，支持固定间隔、指数退避和 Decorrelated Jitter 三种策略。
    指数退避是 2^attempt × base_delay，加 jitter 防止 thundering herd。
    Decorrelated Jitter 用在网络请求上效果最好，方差小但能避免同步峰值。"
"""
import time
import random
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, List


class RetryStrategy(Enum):
    """重试策略"""
    FIXED = "fixed"                  # 固定间隔
    EXPONENTIAL = "exponential"      # 指数退避
    DECORRELATED = "decorrelated"    # Decorrelated Jitter


@dataclass
class RetryStats:
    """重试统计"""
    attempts: int = 0                # 总尝试次数
    total_delay: float = 0.0         # 总等待时间 (s)
    first_success_at: int = 0        # 第几次成功（0=从未成功）
    delays: List[float] = field(default_factory=list)  # 每次等待时间
    errors: List[str] = field(default_factory=list)    # 每次错误信息


class RetryEngine:
    """重试引擎

    Args:
        strategy: 重试策略
        max_retries: 最大重试次数（不含首次）
        base_delay: 基础延迟 (s)
        max_delay: 最大延迟上限 (s)
        jitter: 是否加随机抖动
    """

    def __init__(self,
                 strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 jitter: bool = True):
        self.strategy = strategy
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def _calc_delay(self, attempt: int) -> float:
        """计算第 attempt 次重试的等待时间

        Args:
            attempt: 重试次数（1-based）

        Returns:
            等待时间 (s)
        """
        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay

        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (2 ** attempt)

        elif self.strategy == RetryStrategy.DECORRELATED:
            # Decorrelated Jitter: delay = min(max_delay, base + jitter * previous_delay)
            # 首次使用 base_delay
            if attempt <= 1:
                delay = self.base_delay
            else:
                prev = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
                delay = min(self.max_delay, self.base_delay + random.random() * prev)
        else:
            delay = self.base_delay

        delay = min(delay, self.max_delay)

        if self.jitter:
            # 加 [-50%, +50%] 抖动
            jitter_factor = 1 + random.uniform(-0.5, 0.5)
            delay *= jitter_factor

        return max(0.001, delay)

    def execute(self, fn: Callable[..., Any],
                args: Optional[tuple] = None,
                kwargs: Optional[dict] = None,
                retryable_exceptions: Optional[tuple] = None) -> tuple:
        """执行函数并重试

        Args:
            fn: 目标函数
            args: 位置参数
            kwargs: 关键字参数
            retryable_exceptions: 可重试的异常类型元组

        Returns:
            (结果, RetryStats) 元组

        Raises:
            最后一次异常（如果所有重试都失败）
        """
        args = args or ()
        kwargs = kwargs or {}
        retryable_exceptions = retryable_exceptions or (Exception,)

        stats = RetryStats()
        last_error = None

        # 首次尝试（总是执行）
        try:
            result = fn(*args, **kwargs)
            stats.attempts = 1
            stats.first_success_at = 1
            return result, stats
        except retryable_exceptions as e:
            last_error = e
            stats.errors.append(f"{type(e).__name__}: {e}")

        # 重试循环
        for retry_num in range(1, self.max_retries + 1):
            delay = self._calc_delay(retry_num)
            time.sleep(delay)
            stats.delays.append(delay)
            stats.total_delay += delay

            try:
                result = fn(*args, **kwargs)
                stats.attempts = 1 + retry_num
                stats.first_success_at = 1 + retry_num
                return result, stats
            except retryable_exceptions as e:
                last_error = e
                stats.errors.append(f"{type(e).__name__}: {e}")

        stats.attempts = 1 + self.max_retries
        raise last_error  # type: ignore[misc]


def retry(strategy=RetryStrategy.EXPONENTIAL, max_retries=3,
          base_delay=1.0, max_delay=60.0, jitter=True):
    """重试装饰器

    用法:
        @retry(max_retries=5)
        def call_api():
            ...
    """
    engine = RetryEngine(
        strategy=strategy, max_retries=max_retries,
        base_delay=base_delay, max_delay=max_delay, jitter=jitter,
    )

    def decorator(fn):
        def wrapper(*args, **kwargs):
            result, _ = engine.execute(fn, args, kwargs)
            return result
        return wrapper

    return decorator
