"""
Day 26 — Token 审计 + 费用监控测试

覆盖：
1. TokenRecord 数据结构和计算
2. DailyReport 数据结构和汇总
3. TokenAuditor 记录调用
4. daily_report 报告生成
5. 异常检测（SPIKE / DROP / STEADY_INCREASE）
6. 空报告
7. 模型细分
8. to_json 导出
"""
import sys
import os
import json
import time
import unittest
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d26_token_auditor import (
    TokenAuditor, TokenRecord, DailyReport,
    AnomalyType, AnomalyAlert,
)


def _make_timestamp(days_ago: int = 0, base: float = None):
    """生成几天前的时间戳"""
    base = base or time.time()
    return base - days_ago * 86400


class TestTokenRecord(unittest.TestCase):
    """TokenRecord"""

    def test_total_property(self):
        r = TokenRecord(timestamp=100, prompt_tokens=10, completion_tokens=20)
        self.assertEqual(r.total_tokens, 30)

    def test_to_dict(self):
        r = TokenRecord(timestamp=100, prompt_tokens=10, completion_tokens=20,
                        model="deepseek-chat", call_id="abc")
        d = r.to_dict()
        self.assertEqual(d["model"], "deepseek-chat")
        self.assertEqual(d["call_id"], "abc")


class TestDailyReport(unittest.TestCase):
    """DailyReport"""

    def test_total_tokens(self):
        r = DailyReport(date="2026-04-30",
                        total_prompt_tokens=100, total_completion_tokens=200)
        self.assertEqual(r.total_tokens, 300)

    def test_estimated_cost(self):
        r = DailyReport(date="2026-04-30",
                        total_prompt_tokens=1_000_000,
                        total_completion_tokens=500_000)
        # input: 1 * 1, output: 0.5 * 2 = 1 + 1 = 2
        self.assertAlmostEqual(r.estimated_cost, 2.0, places=4)

    def test_summary_format(self):
        r = DailyReport(date="2026-04-30", total_calls=10,
                        total_prompt_tokens=100, total_completion_tokens=200)
        s = r.summary()
        self.assertIn("2026-04-30", s)
        self.assertIn("Calls: 10", s)
        self.assertIn("Total: 300", s)

    def test_summary_with_anomalies(self):
        r = DailyReport(date="2026-04-30", anomalies=[
            {"type": "spike", "message": "Token usage high"}
        ])
        s = r.summary()
        self.assertIn("Anomalies: 1", s)
        self.assertIn("spike", s)


class TestTokenAuditorRecord(unittest.TestCase):
    """记录调用"""

    def setUp(self):
        self.auditor = TokenAuditor()

    def test_record_call(self):
        r = self.auditor.record_call(prompt_tokens=50, completion_tokens=150)
        self.assertEqual(r.prompt_tokens, 50)
        self.assertEqual(r.completion_tokens, 150)
        self.assertEqual(self.auditor.total_records, 1)

    def test_record_multiple(self):
        for i in range(10):
            self.auditor.record_call(i * 10, i * 20)
        self.assertEqual(self.auditor.total_records, 10)


class TestDailyReportGeneration(unittest.TestCase):
    """报告生成"""

    def test_empty_report(self):
        """无数据"""
        auditor = TokenAuditor()
        report = auditor.daily_report("2026-04-30")
        self.assertEqual(report.total_calls, 0)
        self.assertEqual(report.total_tokens, 0)

    def test_report_with_data(self):
        """有数据"""
        auditor = TokenAuditor()
        now = time.time()
        # 篡改时间戳确保落在当天
        auditor.record_call(100, 200)
        report = auditor.daily_report(datetime.now().strftime("%Y-%m-%d"))
        self.assertGreater(report.total_calls, 0)
        self.assertGreater(report.total_tokens, 0)

    def test_model_breakdown(self):
        """模型细分"""
        auditor = TokenAuditor()
        # 当前时间戳
        auditor.record_call(100, 200, model="deepseek-chat")
        auditor.record_call(50, 100, model="deepseek-reasoner")
        today = datetime.now().strftime("%Y-%m-%d")
        report = auditor.daily_report(today)
        self.assertIn("deepseek-chat", report.model_breakdown)
        self.assertIn("deepseek-reasoner", report.model_breakdown)
        self.assertEqual(report.model_breakdown["deepseek-chat"]["prompt_tokens"], 100)


class TestAnomalyDetection(unittest.TestCase):
    """异常检测"""

    def test_no_anomaly_with_one_record(self):
        """单天无异常"""
        auditor = TokenAuditor()
        auditor.record_call(100, 200)
        alerts = auditor.detect_anomalies()
        self.assertEqual(len(alerts), 0)

    def test_spike_detection(self):
        """突增检测"""
        auditor = TokenAuditor(spike_threshold=1.5, baseline_window=3)
        base = time.time()

        # 6 天基线数据（每天 100 tokens）
        for day in range(6, 0, -1):
            r = TokenRecord(
                timestamp=_make_timestamp(day, base),
                prompt_tokens=50, completion_tokens=50,
            )
            auditor._records.append(r)

        # 今天突增到 10 倍
        r = TokenRecord(
            timestamp=base,
            prompt_tokens=500, completion_tokens=500,
        )
        auditor._records.append(r)

        alerts = auditor.detect_anomalies()
        self.assertTrue(any(a.anomaly_type == AnomalyType.SPIKE for a in alerts))

    def test_drop_detection(self):
        """突降检测"""
        auditor = TokenAuditor(spike_threshold=1.5, baseline_window=3)
        base = time.time()

        for day in range(6, 0, -1):
            r = TokenRecord(
                timestamp=_make_timestamp(day, base),
                prompt_tokens=500, completion_tokens=500,
            )
            auditor._records.append(r)

        # 今天降到 10
        r = TokenRecord(
            timestamp=base,
            prompt_tokens=5, completion_tokens=5,
        )
        auditor._records.append(r)

        alerts = auditor.detect_anomalies()
        self.assertTrue(any(a.anomaly_type == AnomalyType.DROP for a in alerts))

    def test_steady_increase(self):
        """持续增长检测"""
        auditor = TokenAuditor(steady_increase_days=3, baseline_window=5)
        base = time.time() - 5 * 86400

        # 前 2 天稳定值
        for day in [5, 4, 3]:
            r = TokenRecord(
                timestamp=_make_timestamp(day, base + 5*86400),
                prompt_tokens=100, completion_tokens=100,
            )
            auditor._records.append(r)

        # 后 3 天递增
        for day, mult in [(2, 1.2), (1, 1.5), (0, 2.0)]:
            r = TokenRecord(
                timestamp=_make_timestamp(day, base + 5*86400),
                prompt_tokens=int(100 * mult), completion_tokens=int(100 * mult),
            )
            auditor._records.append(r)

        alerts = auditor.detect_anomalies()
        steady = [a for a in alerts if a.anomaly_type == AnomalyType.STEADY_INCREASE]
        self.assertGreaterEqual(len(steady), 1)


class TestExport(unittest.TestCase):
    """导出"""

    def test_to_json(self):
        auditor = TokenAuditor()
        auditor.record_call(100, 200)
        out_path = "_test_token_audit.json"
        try:
            auditor.to_json(out_path)
            with open(out_path, "r") as f:
                data = json.load(f)
            self.assertIn("records", data)
            self.assertIn("reports", data)
        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)


class TestEdgeCases(unittest.TestCase):
    """边界情况"""

    def test_zero_token_record(self):
        r = TokenRecord(timestamp=100, prompt_tokens=0, completion_tokens=0)
        self.assertEqual(r.total_tokens, 0)

    def test_large_token_values(self):
        auditor = TokenAuditor()
        auditor.record_call(10_000_000, 5_000_000)
        today = datetime.now().strftime("%Y-%m-%d")
        report = auditor.daily_report(today)
        self.assertEqual(report.total_calls, 1)
        self.assertEqual(report.total_prompt_tokens, 10_000_000)
        self.assertEqual(report.total_completion_tokens, 5_000_000)
        # cost: 10 * 1 + 5 * 2 = 20
        self.assertAlmostEqual(report.estimated_cost, 20.0, places=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
