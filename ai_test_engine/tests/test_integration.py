"""
Week 7 Day 33 — 集成测试 + 全模块报告生成
"""
import sys, os, time, json, unittest
from dataclasses import dataclass, field
from typing import List, Dict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 直接导入同级包中的测试类（作为 ModuleFinder）
from tests.quality.test_quality import (
    TestQualityScore, TestLLMJudge, TestAssessmentPipeline,
    QualityScore, LLMJudge, AssessmentPipeline,
)
from tests.security.test_security import (
    TestInjectionTester, TestRobustnessTester, TestRegressionTester,
    InjectionTester, RobustnessTester, RegressionTester,
)
from tests.performance.test_performance import (
    TestLoadTester, TestCircuitBreaker, TestTokenAuditor,
    LoadTester, CircuitBreaker, TokenAuditor, LoadReport,
)


@dataclass
class IntegrationReport:
    """全模块集成报告"""
    module: str = ""
    total: int = 0
    passed: int = 0
    failed: int = 0
    details: List[str] = field(default_factory=list)
    duration: float = 0.0

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0


class TestIntegration(unittest.TestCase):
    """集成测试：按模块分组执行并收集报告"""

    def _run_group(self, module_name: str, test_cases: list) -> IntegrationReport:
        report = IntegrationReport(module=module_name)
        t0 = time.time()
        suites = []
        for tc in test_cases:
            suites.append(unittest.TestLoader().loadTestsFromTestCase(tc))
        suite = unittest.TestSuite(suites)
        runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=0)
        result = runner.run(suite)
        report.total = result.testsRun
        report.passed = result.testsRun - len(result.failures) - len(result.errors)
        report.failed = len(result.failures) + len(result.errors)
        for cls_name, tb in result.failures + result.errors:
            report.details.append(f"[!!] {cls_name}: {tb.split(chr(10))[-2] if chr(10) in tb else tb[:80]}")
        report.duration = time.time() - t0
        return report

    def test_quality_module(self):
        report = self._run_group("Quality", [TestQualityScore, TestLLMJudge, TestAssessmentPipeline])
        self.assertGreater(report.total, 0, f"Quality: no tests found")
        self.assertEqual(report.failed, 0, f"Quality failures: {len(report.details)}")

    def test_security_module(self):
        report = self._run_group("Security", [TestInjectionTester, TestRobustnessTester, TestRegressionTester])
        self.assertGreater(report.total, 0, f"Security: no tests found")
        self.assertEqual(report.failed, 0, f"Security failures: {len(report.details)}")

    def test_performance_module(self):
        report = self._run_group("Performance", [TestLoadTester, TestCircuitBreaker, TestTokenAuditor])
        self.assertGreater(report.total, 0, f"Performance: no tests found")
        self.assertEqual(report.failed, 0, f"Performance failures: {len(report.details)}")

    def test_integration_summary(self):
        """生成全模块汇总报告"""
        modules = [
            ("Smoke Connectivity", [
                unittest.TestLoader().loadTestsFromModule(
                    __import__("tests.smoke.test_connectivity", fromlist=[""]))
            ]),
        ]
        total_tests = 0
        total_passed = 0
        for name, suites in modules:
            suite = unittest.TestSuite(suites)
            t0 = time.time()
            runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=0)
            r = runner.run(suite)
            total_tests += r.testsRun
            total_passed += r.testsRun - len(r.failures) - len(r.errors)

        self.assertGreater(total_tests, 0, "No tests in integration summary")
        self.assertGreaterEqual(total_passed, 0)

    def test_standalone_module_functions(self):
        """验证各模块可独立使用"""
        # Quality
        self.assertAlmostEqual(QualityScore.overall({"a": 1.0, "b": 1.0}), 1.0)
        score = LLMJudge.parse_score('{"score":0.9}')
        self.assertAlmostEqual(score, 0.9)
        r = AssessmentPipeline.assess("good response")
        self.assertEqual(r["verdict"], "pass")
        # Security
        self.assertEqual(len(InjectionTester.attack_cases()), 9)
        r = RobustnessTester.test_all("hello")
        self.assertEqual(len(r), 6)
        d = RegressionTester.compare(0.5, 0.8)
        self.assertAlmostEqual(d["delta"], 0.3)
        # Performance
        lt = LoadTester(concurrency=2)
        lr = lt.run(3)
        self.assertEqual(lr.successes, 3)
        cb = CircuitBreaker(failure_threshold=2)
        cb.on_failure()
        cb.on_failure()
        self.assertEqual(cb.state, "OPEN")
        ta = TokenAuditor()
        ta.record_call(100, 50)
        self.assertGreater(ta.total_cost(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
