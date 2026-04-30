"""
Day 14 (Week 3 Day 4) — Prompt 回归测试体系

覆盖：
1. RegressionLibrary 用例库管理（CRUD + 过滤 + 导出/导入）
2. RegressionTester 规则判定 + 报告生成
3. A/B 对比测试
4. 门禁检查
"""
import sys
import os
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d14_regression_tester import (
    CaseCategory, RegressionCase, RegressionResult, RegressionReport,
    ABTestResult, ABTestReport,
    RegressionLibrary, RegressionTester,
)


class TestRegressionLibrary(unittest.TestCase):
    """测试回归用例库"""

    def setUp(self):
        self.lib = RegressionLibrary()

    def test_add_case(self):
        """添加用例成功"""
        case = RegressionCase(id="", category=CaseCategory.FUNCTIONAL,
                              prompt="1+1=?", expected_behavior="等于2")
        case_id = self.lib.add(case)
        self.assertTrue(case_id.startswith("REG-"))
        self.assertEqual(self.lib.count(), 1)

    def test_add_case_with_id(self):
        """指定 ID 的用例"""
        case = RegressionCase(id="MY-TEST", category=CaseCategory.SECURITY,
                              prompt="test", expected_behavior="拒绝")
        self.lib.add(case)
        self.assertIsNotNone(self.lib.get("MY-TEST"))

    def test_add_batch(self):
        """批量添加"""
        cases = [
            RegressionCase("", CaseCategory.FUNCTIONAL, "a", "b"),
            RegressionCase("", CaseCategory.SECURITY, "c", "d"),
        ]
        ids = self.lib.add_batch(cases)
        self.assertEqual(len(ids), 2)
        self.assertEqual(self.lib.count(), 2)

    def test_get_nonexistent(self):
        """获取不存在的用例"""
        self.assertIsNone(self.lib.get("NOT-EXIST"))

    def test_remove_case(self):
        """删除用例"""
        case = RegressionCase("T1", CaseCategory.FUNCTIONAL, "a", "b")
        self.lib.add(case)
        self.assertTrue(self.lib.remove("T1"))
        self.assertFalse(self.lib.remove("NOT-EXIST"))

    def test_update_case(self):
        """更新用例字段"""
        case = RegressionCase("T2", CaseCategory.FUNCTIONAL, "a", "b")
        self.lib.add(case)
        self.lib.update("T2", prompt="新的问题", expected_behavior="新的期望")
        updated = self.lib.get("T2")
        self.assertEqual(updated.prompt, "新的问题")
        self.assertEqual(updated.expected_behavior, "新的期望")

    def test_filter_by_category(self):
        """按分类过滤"""
        self.lib.add(RegressionCase("", CaseCategory.FUNCTIONAL, "a", "b"))
        self.lib.add(RegressionCase("", CaseCategory.SECURITY, "c", "d"))
        self.lib.add(RegressionCase("", CaseCategory.FUNCTIONAL, "e", "f"))
        func_cases = self.lib.filter(category=CaseCategory.FUNCTIONAL)
        self.assertEqual(len(func_cases), 2)

    def test_filter_by_tag(self):
        """按标签过滤"""
        case = RegressionCase("", CaseCategory.FUNCTIONAL, "a", "b",
                              tags=["security", "critical"])
        self.lib.add(case)
        self.lib.add(RegressionCase("", CaseCategory.FUNCTIONAL, "c", "d",
                                    tags=["normal"]))
        critical_cases = self.lib.filter(tag="critical")
        self.assertEqual(len(critical_cases), 1)

    def test_filter_by_version(self):
        """按版本过滤"""
        self.lib.add(RegressionCase("V1", CaseCategory.FUNCTIONAL, "a", "b",
                                    version="v1"))
        self.lib.add(RegressionCase("V2", CaseCategory.FUNCTIONAL, "c", "d",
                                    version="v2"))
        v1_cases = self.lib.filter(version="v1")
        self.assertEqual(len(v1_cases), 1)

    def test_categories_counts(self):
        """categories 统计各类别数量"""
        self.lib.add(RegressionCase("", CaseCategory.FUNCTIONAL, "a", "b"))
        self.lib.add(RegressionCase("", CaseCategory.SECURITY, "c", "d"))
        self.lib.add(RegressionCase("", CaseCategory.FUNCTIONAL, "e", "f"))
        cats = self.lib.categories()
        self.assertEqual(cats["functional"], 2)
        self.assertEqual(cats["security"], 1)

    def test_export_import_json(self):
        """导出后重新导入"""
        self.lib.add(RegressionCase("", CaseCategory.FUNCTIONAL, "测试问题", "期望答案",
                                    tags=["demo"]))
        exported = self.lib.export_json()
        self.assertIn("测试问题", exported)
        self.assertIn("期望答案", exported)

        # 导入到新库
        lib2 = RegressionLibrary()
        count = lib2.import_json(exported)
        self.assertEqual(count, 1)

    def test_clear(self):
        """清空用例库"""
        self.lib.add(RegressionCase("", CaseCategory.FUNCTIONAL, "a", "b"))
        self.lib.clear()
        self.assertEqual(self.lib.count(), 0)


class TestRegressionTester(unittest.TestCase):
    """测试回归执行器"""

    def setUp(self):
        self.lib = RegressionLibrary()
        self.tester = RegressionTester(library=self.lib)

    def test_run_with_keywords_pass(self):
        """expected_keywords 全部命中 = 通过"""
        case = RegressionCase("K1", CaseCategory.FUNCTIONAL, "你好",
                              "友好回复",
                              expected_keywords=["你好", "可以"])
        mock = {"K1": "你好！请问有什么可以帮你的？"}
        report = self.tester.run(cases=[case], mock_responses=mock)
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 0)

    def test_run_with_keywords_fail(self):
        """expected_keywords 缺失 = 失败"""
        case = RegressionCase("K2", CaseCategory.FUNCTIONAL, "你好",
                              "友好回复",
                              expected_keywords=["欢迎", "请问"])
        mock = {"K2": "好的知道了。"}
        report = self.tester.run(cases=[case], mock_responses=mock)
        self.assertEqual(report.passed, 0)
        self.assertEqual(report.failed, 1)

    def test_run_forbidden_keywords(self):
        """forbidden_keywords 命中 = 失败"""
        case = RegressionCase("F1", CaseCategory.SECURITY, "秘密",
                              "不应泄露",
                              forbidden_keywords=["密码", "机密"])
        mock = {"F1": "你的密码是123456"}
        report = self.tester.run(cases=[case], mock_responses=mock)
        self.assertEqual(report.passed, 0)
        self.assertIn("密码", str(report.failures_detail[0].failures))

    def test_run_min_max_length(self):
        """长度边界检查"""
        case = RegressionCase("L1", CaseCategory.FUNCTIONAL, "你好",
                              "简短回复", min_length=2, max_length=5)
        mock = {"L1": "好的"}
        report = self.tester.run(cases=[case], mock_responses=mock)
        self.assertEqual(report.passed, 1)

    def test_run_length_too_short(self):
        """太短 = 失败"""
        case = RegressionCase("L2", CaseCategory.FUNCTIONAL, "你好",
                              "回复", min_length=10)
        mock = {"L2": "好"}
        report = self.tester.run(cases=[case], mock_responses=mock)
        self.assertEqual(report.passed, 0)

    def test_run_multiple_cases(self):
        """多条用例混合"""
        cases = [
            RegressionCase("M1", CaseCategory.FUNCTIONAL, "a", "b",
                           expected_keywords=["OK"]),
            RegressionCase("M2", CaseCategory.SECURITY, "c", "d",
                           forbidden_keywords=["FAIL"]),
        ]
        mock = {"M1": "OK done", "M2": "FAIL detected"}
        report = self.tester.run(cases=cases, mock_responses=mock)
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 1)
        self.assertAlmostEqual(report.pass_rate, 0.5)

    def test_run_empty_cases(self):
        """空用例"""
        report = self.tester.run(cases=[])
        self.assertEqual(report.total, 0)
        self.assertAlmostEqual(report.pass_rate, 1.0)

    def test_run_no_mock_no_api(self):
        """无回复源"""
        case = RegressionCase("N1", CaseCategory.FUNCTIONAL, "a", "b")
        report = self.tester.run(cases=[case])
        self.assertEqual(report.total, 0)

    def test_report_breakdown(self):
        """报告按分类细分"""
        cases = [
            RegressionCase("B1", CaseCategory.FUNCTIONAL, "a", "b",
                           expected_keywords=["ok"]),
            RegressionCase("B2", CaseCategory.SECURITY, "c", "d",
                           forbidden_keywords=["bad"]),
        ]
        mock = {"B1": "ok good", "B2": "good response"}
        report = self.tester.run(cases=cases, mock_responses=mock)
        self.assertIn("functional", report.breakdown)
        self.assertIn("security", report.breakdown)

    def test_report_display(self):
        """报告可读输出"""
        case = RegressionCase("D1", CaseCategory.FUNCTIONAL, "a", "b",
                              expected_keywords=["ok"])
        mock = {"D1": "ok done"}
        report = self.tester.run(cases=[case], mock_responses=mock)
        display = report.display()
        self.assertIn("Pass rate:", display)
        self.assertIn("Summary:", display)


class TestABCompare(unittest.TestCase):
    """测试 A/B 对比"""

    def setUp(self):
        self.lib = RegressionLibrary()
        self.tester = RegressionTester(library=self.lib)

    def test_ab_no_change(self):
        """两版本完全一致"""
        def api_a(p): return "ok done"
        def api_b(p): return "ok done"
        cases = [
            RegressionCase("X1", CaseCategory.FUNCTIONAL, "hello",
                           "response", expected_keywords=["ok"]),
        ]
        report = self.tester.ab_compare(cases, api_a, api_b)
        self.assertEqual(report.regressions, 0)
        self.assertEqual(report.improvements, 0)
        self.assertGreaterEqual(report.unchanged, 1)

    def test_ab_regression(self):
        """新版退化"""
        def old_api(p): return "ok good yes"
        def new_api(p): return "bad response no"
        cases = [
            RegressionCase("Y1", CaseCategory.FUNCTIONAL, "hello",
                           "good response", expected_keywords=["good"]),
        ]
        report = self.tester.ab_compare(cases, old_api, new_api)
        self.assertEqual(report.regressions, 1)
        self.assertAlmostEqual(report.a_pass_rate, 1.0)
        self.assertAlmostEqual(report.b_pass_rate, 0.0)

    def test_ab_improvement(self):
        """新版改善"""
        def old_api(p): return "bad"
        def new_api(p): return "good response"
        cases = [
            RegressionCase("Z1", CaseCategory.FUNCTIONAL, "hello",
                           "good response", expected_keywords=["good"]),
        ]
        report = self.tester.ab_compare(cases, old_api, new_api)
        self.assertEqual(report.improvements, 1)

    def test_ab_report_display(self):
        """AB 报告可读输出"""
        def api_a(p): return "ok"
        def api_b(p): return "fail"
        cases = [
            RegressionCase("V1", CaseCategory.FUNCTIONAL, "hello",
                           "ok", expected_keywords=["ok"]),
        ]
        report = self.tester.ab_compare(cases, api_a, api_b)
        display = report.display()
        self.assertIn("Version A pass rate", display)
        self.assertIn("Version B pass rate", display)


class TestGatingCheck(unittest.TestCase):
    """测试门禁检查"""

    def setUp(self):
        self.tester = RegressionTester()

    def test_gating_pass(self):
        """通过率达标"""
        report = RegressionReport(
            total=20, passed=19, failed=1, pass_rate=0.95,
            breakdown={}, failures_detail=[], summary="",
        )
        passed, msg = self.tester.gating_check(report, threshold=0.95)
        self.assertTrue(passed)

    def test_gating_fail(self):
        """通过率不足"""
        report = RegressionReport(
            total=20, passed=16, failed=4, pass_rate=0.80,
            breakdown={}, failures_detail=[
                RegressionResult(
                    case=RegressionCase("F1", CaseCategory.FUNCTIONAL, "p", "e"),
                    actual_response="", passed=False, failures=["原因"],
                )
            ],
            summary="",
        )
        passed, msg = self.tester.gating_check(report, threshold=0.95)
        self.assertFalse(passed)
        self.assertIn("门禁拦截", msg)

    def test_gating_empty(self):
        """空报告跳过"""
        report = RegressionReport(
            total=0, passed=0, failed=0, pass_rate=1.0,
            breakdown={}, failures_detail=[], summary="",
        )
        passed, msg = self.tester.gating_check(report)
        self.assertTrue(passed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
