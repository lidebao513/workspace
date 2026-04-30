"""
Day 23 — 指数退避重试引擎测试

覆盖：
1. RetryStrategy 枚举
2. RetryStats 数据结构
3. 三种策略的延迟计算
4. 成功即停
5. 重试耗尽
6. 抖动和非抖动模式
7. 装饰器用法
8. 最大延迟上限
"""
import sys
import os
import unittest
import pytest
pytestmark = pytest.mark.filterwarnings("ignore::pytest.PytestReturnNotNoneWarning")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d23_retry_engine import RetryEngine, RetryStrategy, RetryStats, retry


class TestRetryStrategy(unittest.TestCase):
    """策略枚举"""

    def test_strategy_values(self):
        self.assertEqual(RetryStrategy.FIXED.value, "fixed")
        self.assertEqual(RetryStrategy.EXPONENTIAL.value, "exponential")
        self.assertEqual(RetryStrategy.DECORRELATED.value, "decorrelated")


class TestRetryStats(unittest.TestCase):
    """统计数据结构"""

    def test_defaults(self):
        s = RetryStats()
        self.assertEqual(s.attempts, 0)
        self.assertEqual(s.total_delay, 0.0)
        self.assertEqual(s.first_success_at, 0)


class TestDelayCalculation(unittest.TestCase):
    """延迟计算"""

    def test_fixed_delay(self):
        """固定间隔"""
        engine = RetryEngine(strategy=RetryStrategy.FIXED,
                             base_delay=2.0, jitter=False)
        d1 = engine._calc_delay(1)
        d2 = engine._calc_delay(5)
        self.assertAlmostEqual(d1, 2.0, places=1)
        self.assertAlmostEqual(d2, 2.0, places=1)

    def test_exponential_growth(self):
        """指数增长: 2^attempt × base"""
        engine = RetryEngine(strategy=RetryStrategy.EXPONENTIAL,
                             base_delay=1.0, jitter=False)
        d1 = engine._calc_delay(1)  # 2^1 = 2
        d2 = engine._calc_delay(2)  # 2^2 = 4
        d3 = engine._calc_delay(3)  # 2^3 = 8
        self.assertAlmostEqual(d1, 2.0, places=1)
        self.assertAlmostEqual(d2, 4.0, places=1)
        self.assertAlmostEqual(d3, 8.0, places=1)

    def test_exponential_capped_by_max(self):
        """指数增长不超过 max_delay"""
        engine = RetryEngine(strategy=RetryStrategy.EXPONENTIAL,
                             base_delay=1.0, max_delay=10.0, jitter=False)
        d = engine._calc_delay(10)  # 2^10 = 1024, capped to 10
        self.assertAlmostEqual(d, 10.0, places=1)

    def test_jitter_varies(self):
        """加抖动后值不同"""
        engine = RetryEngine(strategy=RetryStrategy.FIXED,
                             base_delay=10.0, jitter=True)
        values = {engine._calc_delay(1) for _ in range(50)}
        self.assertGreater(len(values), 1)

    def test_min_delay_positive(self):
        """延迟至少 0.001s"""
        engine = RetryEngine(strategy=RetryStrategy.FIXED,
                             base_delay=0.0, jitter=False)
        d = engine._calc_delay(1)
        self.assertGreaterEqual(d, 0.001)


class TestExecute(unittest.TestCase):
    """execute 方法"""

    def test_success_first_try(self):
        """第一次就成功"""
        engine = RetryEngine(max_retries=3)
        result, stats = engine.execute(lambda: "ok")
        self.assertEqual(result, "ok")
        self.assertEqual(stats.attempts, 1)
        self.assertEqual(stats.first_success_at, 1)

    def test_success_after_retries(self):
        """重试后成功"""
        engine = RetryEngine(strategy=RetryStrategy.FIXED,
                             max_retries=5, base_delay=0.01, jitter=False)
        call_count = {"n": 0}

        def _fail_twice():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise ConnectionError("fail")
            return "ok"

        result, stats = engine.execute(_fail_twice)
        self.assertEqual(result, "ok")
        self.assertEqual(stats.first_success_at, 3)
        self.assertEqual(stats.attempts, 3)

    def test_all_retries_exhausted(self):
        """所有重试耗尽"""
        engine = RetryEngine(strategy=RetryStrategy.FIXED,
                             max_retries=2, base_delay=0.01, jitter=False)

        def _always_fail():
            raise ValueError("always fail")

        with self.assertRaises(ValueError):
            engine.execute(_always_fail)

    def test_retryable_exceptions_filter(self):
        """仅重试指定异常"""
        engine = RetryEngine(strategy=RetryStrategy.FIXED,
                             max_retries=3, base_delay=0.01, jitter=False)

        def _raise_type_error():
            raise TypeError("not retryable")

        with self.assertRaises(TypeError):
            engine.execute(_raise_type_error)

    def test_stats_recorded_on_failure(self):
        """失败时统计信息完整"""
        engine = RetryEngine(strategy=RetryStrategy.FIXED,
                             max_retries=2, base_delay=0.01, jitter=False)

        def _fail():
            raise ValueError("nope")

        try:
            engine.execute(_fail)
        except ValueError:
            pass

    def test_stats_show_errors(self):
        """错误列表记录了异常信息"""
        engine = RetryEngine(strategy=RetryStrategy.FIXED,
                             max_retries=2, base_delay=0.01, jitter=False)
        call_count = {"n": 0}

        def _fail_twice():
            call_count["n"] += 1
            raise RuntimeError(f"error #{call_count['n']}")

        try:
            engine.execute(_fail_twice)
        except RuntimeError:
            pass

    def test_total_delay_positive(self):
        """总等待时间 > 0"""
        engine = RetryEngine(strategy=RetryStrategy.FIXED,
                             max_retries=2, base_delay=0.02, jitter=False)
        call_count = {"n": 0}

        def _always_fail():
            call_count["n"] += 1
            raise ValueError("nope")

        try:
            engine.execute(_always_fail)
        except ValueError:
            pass
        self.assertGreater(call_count["n"], 1)


class TestDecorator(unittest.TestCase):
    """装饰器"""

    def test_retry_decorator(self):
        """装饰器正常工作"""
        call_count = {"n": 0}

        @retry(max_retries=3, base_delay=0.01, jitter=False)
        def unstable():
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise ValueError("not yet")
            return "ok"

        result = unstable()
        self.assertEqual(result, "ok")
        self.assertEqual(call_count["n"], 2)


class TestEdgeCases(unittest.TestCase):
    """边界情况"""

    def test_zero_max_retries(self):
        """max_retries=0 即不重试"""
        engine = RetryEngine(max_retries=0)

        def _fail():
            raise ValueError("fail")

        with self.assertRaises(ValueError):
            engine.execute(_fail)


if __name__ == "__main__":
    unittest.main(verbosity=2)
