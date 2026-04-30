"""
Day 22 — 并发压测模块测试

覆盖：
1. LatencyReport 数据结构和 summary 格式
2. LoadTester 基本执行（单线程/多线程）
3. 百分位计算准确性
4. 预热轮次排除
5. 失败请求统计
6. 边界情况：0请求、1请求、异常函数
"""
import sys
import os
import time
import unittest
import pytest
pytestmark = pytest.mark.filterwarnings("ignore::pytest.PytestReturnNotNoneWarning")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d22_load_tester import LoadTester, LatencyReport


def _noop(*args, **kwargs):
    """无操作函数，用于基础测试"""
    pass


def _slow_fn(delay_ms=10, *args, **kwargs):
    """模拟延迟函数"""
    time.sleep(delay_ms / 1000)
    return "ok"


def _err_fn(*args, **kwargs):
    """总是抛出异常"""
    raise ValueError("mock error")


class TestLatencyReport(unittest.TestCase):
    """LatencyReport 数据结构"""

    def test_default_values(self):
        """默认值均为 0"""
        r = LatencyReport()
        self.assertEqual(r.p50, 0.0)
        self.assertEqual(r.p95, 0.0)
        self.assertEqual(r.rps, 0.0)

    def test_success_rate_zero(self):
        """无请求时成功率为 0"""
        r = LatencyReport()
        self.assertEqual(r.success_rate(), 0.0)

    def test_success_rate_half(self):
        """半成功"""
        r = LatencyReport(total_requests=10, success_count=5, fail_count=5)
        self.assertEqual(r.success_rate(), 0.5)

    def test_success_rate_full(self):
        """全成功"""
        r = LatencyReport(total_requests=10, success_count=10, fail_count=0)
        self.assertEqual(r.success_rate(), 1.0)

    def test_summary_contains_keys(self):
        """摘要包含关键字段"""
        r = LatencyReport(total_requests=10, success_count=10,
                          p50=100, p95=200, rps=50, total_time=0.2)
        s = r.summary()
        self.assertIn("P50", s)
        self.assertIn("P95", s)
        self.assertIn("RPS", s)


class TestLoadTesterBasic(unittest.TestCase):
    """基本执行"""

    def test_run_zero_requests(self):
        """0 请求"""
        tester = LoadTester(_noop, concurrency=1)
        report = tester.run(0)
        self.assertEqual(report.total_requests, 0)
        self.assertEqual(report.p50, 0.0)

    def test_run_one_request(self):
        """1 请求"""
        tester = LoadTester(_noop, concurrency=1)
        report = tester.run(1)
        self.assertEqual(report.total_requests, 1)
        self.assertEqual(report.success_count, 1)

    def test_run_multiple_requests(self):
        """多个请求"""
        tester = LoadTester(_noop, concurrency=3)
        report = tester.run(10)
        self.assertEqual(report.total_requests, 10)
        self.assertEqual(report.success_count, 10)

    def test_run_with_args(self):
        """传递参数"""
        tester = LoadTester(_slow_fn, concurrency=2)
        report = tester.run(4, fn_args=(5,))  # 5ms delay each
        self.assertEqual(report.total_requests, 4)
        self.assertEqual(report.success_count, 4)
        self.assertGreater(report.total_time, 0)


class TestPercentileAccuracy(unittest.TestCase):
    """百分位计算准确性"""

    def setUp(self):
        self.tester = LoadTester(_noop, concurrency=1)

    def test_p50_median(self):
        """P50 是中位数"""
        data = [10, 20, 30, 40, 50]
        self.assertEqual(self.tester._percentile(data, 50), 30)

    def test_p95_small_set(self):
        """小数据集的 P95"""
        data = [10, 20, 30, 40, 50]
        # 5 * 0.95 = 4.75 → int=4, sorted[4]=50
        self.assertEqual(self.tester._percentile(data, 95), 50)

    def test_p99_large_set(self):
        """大数据集的 P99 接近最大值"""
        data = list(range(1, 101))  # 1..100
        self.assertAlmostEqual(self.tester._percentile(data, 99), 99, delta=1)

    def test_empty_data(self):
        """空数据返回 0"""
        self.assertEqual(self.tester._percentile([], 50), 0.0)

    def test_single_element(self):
        """单元素"""
        self.assertEqual(self.tester._percentile([42], 95), 42.0)

    def test_p50_even(self):
        """偶数个元素时 P50 取中间偏右"""
        data = [1, 2, 3, 4]
        # sorted[1] = 2 (4*0.5=2, min(2,3)=2, value=3)
        # Actually idx = int(4*0.5)=2, min(2,3)=2, data[2]=3
        self.assertEqual(self.tester._percentile(data, 50), 3)


class TestWarmup(unittest.TestCase):
    """预热轮次"""

    def test_warmup_counted_correctly(self):
        """预热轮次不干扰统计"""
        call_count = {"total": 0}

        def track_fn(*a, **kw):
            call_count["total"] += 1
            return "ok"

        tester = LoadTester(track_fn, concurrency=1, warmup=3)
        report = tester.run(5)
        # 预热 3 + 正式 5 = 8 次调用
        self.assertEqual(call_count["total"], 8)
        self.assertEqual(report.total_requests, 5)


class TestErrorHandling(unittest.TestCase):
    """错误处理"""

    def test_all_fail(self):
        """全部失败"""
        tester = LoadTester(_err_fn, concurrency=2)
        report = tester.run(5)
        self.assertEqual(report.fail_count, 5)
        self.assertEqual(report.success_count, 0)
        self.assertGreater(report.total_time, 0)

    def test_partial_fail(self):
        """部分失败"""
        call_idx = {"n": 0}

        def _alternate(*a, **kw):
            call_idx["n"] += 1
            if call_idx["n"] % 2 == 0:
                raise ValueError("mock err")
            return "ok"

        tester = LoadTester(_alternate, concurrency=1)
        report = tester.run(4)
        self.assertGreater(report.success_count, 0)
        self.assertGreater(report.fail_count, 0)
        self.assertEqual(report.success_count + report.fail_count, 4)


class TestThroughput(unittest.TestCase):
    """吞吐量"""

    def test_rps_increases_with_concurrency(self):
        """并发度越高 RPS 越高（对于有限延迟）"""

        def _fixed_delay(*a, **kw):
            time.sleep(0.05)
            return "ok"

        # 串行
        serial = LoadTester(_fixed_delay, concurrency=1)
        r1 = serial.run(5)

        # 并发
        parallel = LoadTester(_fixed_delay, concurrency=5)
        r2 = parallel.run(5)

        self.assertGreater(r2.rps, r1.rps)

    def test_total_time_recorded(self):
        """总耗时 > 0（用慢函数确保 timer 可测量）"""
        tester = LoadTester(_slow_fn, concurrency=1)
        report = tester.run(1, fn_args=(5,))
        self.assertGreater(report.total_time, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
