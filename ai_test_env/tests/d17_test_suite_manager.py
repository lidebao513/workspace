"""
Day 17 (Week 4 Day 2) — pytest 参数化 + 分层管理 单元测试

覆盖：
1. TestSuiteManager 按层级/标签/模块过滤
2. ParametrizedCase 单维度 + 多维度 + CSV 导入
3. PytestMarkerGenerator 标签生成
4. CompatRunner 模块映射
5. generate_test_run_summary 报告摘要
"""
import sys
import os
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d17_suite_manager import (
    TestLevel, TagCategory, TestCaseMeta,
    TestSuiteManager, ParametrizedCase, PytestMarkerGenerator,
    CompatRunner, generate_test_run_summary,
)


class TestTestCaseMeta(unittest.TestCase):
    """测试用例元信息"""

    def test_meta_defaults(self):
        """默认 priority=3"""
        meta = TestCaseMeta("test", TestLevel.SMOKE, [TagCategory.API], "mod")
        self.assertEqual(meta.priority, 3)
        self.assertEqual(meta.estimated_ms, 500)
        self.assertFalse(meta.ci_only)

    def test_meta_to_dict(self):
        """转字典"""
        meta = TestCaseMeta("test", TestLevel.SMOKE, [TagCategory.API], "mod")
        d = meta.to_dict()
        self.assertIn("name", d)
        self.assertIn("level", d)
        self.assertIn("tags", d)


class TestSuiteMgr(unittest.TestCase):
    """测试套件管理器TestSuiteManager"""

    def setUp(self):
        self.mgr = TestSuiteManager()

    def test_has_builtin_cases(self):
        """内置用例"""
        self.assertGreater(self.mgr.count(), 10)

    def test_filter_by_level_smoke(self):
        """冒烟过滤"""
        cases = self.mgr.filter(level=TestLevel.SMOKE)
        self.assertTrue(all(c.level == TestLevel.SMOKE for c in cases))
        self.assertGreater(len(cases), 0)

    def test_filter_by_level_security(self):
        """安全过滤"""
        cases = self.mgr.filter(level=TestLevel.SECURITY)
        self.assertTrue(all(c.level == TestLevel.SECURITY for c in cases))
        self.assertGreater(len(cases), 0)

    def test_filter_by_tag_security(self):
        """安全标签过滤"""
        cases = self.mgr.filter(tag=TagCategory.SECURITY)
        self.assertTrue(all(TagCategory.SECURITY in c.tags for c in cases))
        self.assertGreaterEqual(len(cases), 3)

    def test_filter_by_module(self):
        """模块过滤"""
        cases = self.mgr.filter(module="api_client")
        self.assertTrue(all(c.module == "api_client" for c in cases))

    def test_filter_by_priority(self):
        """优先级过滤"""
        cases = self.mgr.filter(priority=1)
        self.assertTrue(all(c.priority == 1 for c in cases))

    def test_get_level_counts(self):
        """层级统计"""
        counts = self.mgr.get_level_counts()
        self.assertIn("smoke", counts)
        self.assertIn("regression", counts)

    def test_get_tag_counts(self):
        """标签统计"""
        counts = self.mgr.get_tag_counts()
        self.assertIn("api", counts)

    def test_add_custom_case(self):
        """添加自定义用例"""
        meta = TestCaseMeta("my_custom_test", TestLevel.PERFORMANCE,
                           [TagCategory.PERFORMANCE], "custom_mod")
        self.mgr.add(meta)
        self.assertEqual(self.mgr.count(), 21)
        self.assertIsNotNone(self.mgr.get("my_custom_test"))

    def test_export_json(self):
        """导出 JSON"""
        j = self.mgr.export_json()
        self.assertIsInstance(j, str)
        self.assertIn("smoke", j)

    def test_generate_coverage_report(self):
        """覆盖率报告"""
        report = self.mgr.generate_coverage_report()
        self.assertIn("Test Coverage Report", report)
        self.assertIn("Total cases", report)
        self.assertIn("Critical Cases", report)
        self.assertIn("[CRIT]", report)


class TestParametrizedCase(unittest.TestCase):
    """参数化用例ParametrizedCase"""

    def test_single_dimension(self):
        """单维度"""
        pc = ParametrizedCase("temp_test")
        pc.add_param("temperature", [0, 0.5, 1, 2])
        combos = pc.combinations()
        self.assertEqual(len(combos), 4)

    def test_multi_dimension(self):
        """多维度"""
        pc = ParametrizedCase("combo_test")
        pc.add_param("temperature", [0, 1])
        pc.add_param("top_p", [0.5, 1.0])
        combos = pc.combinations()
        self.assertEqual(len(combos), 4)

    def test_multi_dimension_values(self):
        """多维度值正确"""
        pc = ParametrizedCase("combo_test")
        pc.add_param("x", [1, 2])
        pc.add_param("y", ["a", "b"])
        combos = pc.combinations()
        self.assertEqual(combos[0], {"x": 1, "y": "a"})
        self.assertEqual(combos[3], {"x": 2, "y": "b"})

    def test_csv_direct_combinations(self):
        """CSV导入的行数应等于数据行数而非笛卡尔积"""
        pc = ParametrizedCase("csv_test")
        pc.add_param("temperature", [0, 1, 2])
        pc.add_param("top_p", [0.5, 1.0, 1.5])
        combos = pc.combinations()
        self.assertEqual(len(combos), 9)

    def test_empty_params(self):
        """无参数"""
        pc = ParametrizedCase("empty")
        combos = pc.combinations()
        self.assertEqual(combos, [{}])

    def test_param_names(self):
        """参数名列表"""
        pc = ParametrizedCase("test")
        pc.add_param("temp", [1, 2])
        self.assertEqual(pc.param_names(), ["temp"])

    def test_description(self):
        """描述文本"""
        pc = ParametrizedCase("test")
        pc.add_param("temp", [1, 2])
        pc.add_param("p", [0.5, 1.0])
        desc = pc.description()
        self.assertIn("test", desc)
        self.assertIn("combos", desc)

    def test_from_csv(self):
        """CSV 导入"""
        csv = """temperature,top_p
0,0.5
1,1.0
2,1.5"""
        pc = ParametrizedCase.from_csv("csv_test", csv)
        self.assertIsNotNone(pc)
        combos = pc.combinations()
        # from_csv 对每列独立构建参数列表，combinations 做笛卡尔积
        # 3 行数据 × 2 列 → 每列 3 个值 → 3×3=9 组合
        self.assertEqual(len(combos), 9)

    def test_from_csv_invalid(self):
        """CSV 无效（仅一行）"""
        pc = ParametrizedCase.from_csv("bad", "just_header")
        self.assertIsNone(pc)


class TestPytestMarkerGenerator(unittest.TestCase):
    """pytest 标签生成"""

    def test_level_to_mark(self):
        """层级转 mark"""
        self.assertEqual(PytestMarkerGenerator.level_to_mark(TestLevel.SMOKE), "smoke")

    def test_tag_to_mark(self):
        """标签转 mark"""
        self.assertEqual(PytestMarkerGenerator.tag_to_mark(TagCategory.SECURITY), "security")

    def test_marks_from_meta(self):
        """从元数据生成 marks"""
        meta = TestCaseMeta("test", TestLevel.SECURITY, [TagCategory.SECURITY], "mod")
        marks = PytestMarkerGenerator.marks_from_meta(meta)
        self.assertIn("security", marks)

    def test_select_expr_levels(self):
        """层级选择表达式"""
        expr = PytestMarkerGenerator.select_expr(levels=[TestLevel.SMOKE])
        self.assertEqual(expr, "(smoke)")

    def test_select_expr_tags(self):
        """标签选择表达式"""
        expr = PytestMarkerGenerator.select_expr(
            tags=[TagCategory.SECURITY, TagCategory.REGRESSION]
        )
        self.assertIn("security", expr)
        self.assertIn("regression", expr)

    def test_select_expr_both(self):
        """层级+标签"""
        expr = PytestMarkerGenerator.select_expr(
            levels=[TestLevel.SMOKE],
            tags=[TagCategory.API]
        )
        self.assertIn("smoke", expr)
        self.assertIn("api", expr)

    def test_select_expr_empty(self):
        """无过滤"""
        expr = PytestMarkerGenerator.select_expr()
        self.assertEqual(expr, "")


class TestCompatRunner(unittest.TestCase):
    """兼容运行器"""

    def test_get_smoke_modules(self):
        """冒烟级模块"""
        modules = CompatRunner.get_modules_for_level(TestLevel.SMOKE)
        self.assertIn("test_params", modules)
        self.assertIn("test_request_format", modules)

    def test_get_security_modules(self):
        """安全级模块"""
        modules = CompatRunner.get_modules_for_level(TestLevel.SECURITY)
        self.assertIn("test_prompt_injection", modules)
        self.assertIn("test_robustness", modules)

    def test_get_regression_modules(self):
        """回归级模块"""
        modules = CompatRunner.get_modules_for_level(TestLevel.REGRESSION)
        self.assertIn("test_quality", modules)
        self.assertIn("test_consistency", modules)

    def test_get_all_modules(self):
        """全部模块"""
        modules = CompatRunner.get_modules_for_level(TestLevel.ALL)
        self.assertGreater(len(modules), 10)

    def test_module_label(self):
        """模块标签"""
        label = CompatRunner.get_module_label("test_prompt_injection")
        self.assertIn("security", label)


class TestReportSummary(unittest.TestCase):
    """报告摘要"""

    def test_basic_summary(self):
        """基本信息"""
        summary = generate_test_run_summary(10, 9, 1, 3.5)
        self.assertIn("Test Run Summary", summary)
        self.assertRegex(summary, r"90\.?0?%")
        # "90.0%" in the output format
        self.assertIn("3.50s", summary)

    def test_with_breakdown(self):
        """含分层"""
        breakdown = {
            "smoke": {"total": 3, "passed": 3},
            "regression": {"total": 7, "passed": 6},
        }
        summary = generate_test_run_summary(10, 9, 1, 3.5, breakdown)
        self.assertIn("Breakdown", summary)
        self.assertIn("smoke", summary)

    def test_empty(self):
        """0 测试"""
        summary = generate_test_run_summary(0, 0, 0, 0)
        self.assertIn("Test Run Summary", summary)


if __name__ == "__main__":
    unittest.main(verbosity=2)
