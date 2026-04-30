"""
Day 19 (Week 4 Day 4) — 开源工具整合 单元测试

覆盖：
1. ToxConfigGenerator tox.ini / CI workflow 生成
2. CoverageChecker 覆盖率解析 + 模块阈值检查
3. CodeSanityChecker 硬编码/TODO/文件大小/末尾空行
4. ProjectHealthReporter 综合报告 + 评分
"""
import sys
import os
import unittest
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d19_toolchain_integration import (
    ToxConfigGenerator, CoverageChecker, CoverageResult,
    CodeSanityChecker, SanityIssue,
    ProjectHealthReporter,
)


class TestToxConfigGenerator(unittest.TestCase):
    """Tox 配置生成"""

    def test_generate_tox_ini(self):
        """生成 tox.ini"""
        ini = ToxConfigGenerator.generate_tox_ini()
        self.assertIn("[tox]", ini)
        self.assertIn("[testenv]", ini)
        self.assertIn("pytest", ini)
        self.assertIn("pytest-cov", ini)
        self.assertIn("[coverage:run]", ini)
        self.assertIn("py39", ini)
        self.assertIn("py310", ini)
        self.assertIn("py311", ini)

    def test_generate_tox_ini_custom_versions(self):
        """自定义 Python 版本"""
        ini = ToxConfigGenerator.generate_tox_ini(
            python_versions=["3.12"]
        )
        self.assertIn("py312", ini)
        self.assertNotIn("py39", ini)

    def test_generate_tox_ini_custom_dirs(self):
        """自定义测试目录"""
        ini = ToxConfigGenerator.generate_tox_ini(
            test_dirs=["tests/unit", "tests/integration"]
        )
        self.assertIn("tests/unit", ini)
        self.assertIn("tests/integration", ini)

    def test_tox_ini_contains_openai_dep(self):
        """tox.ini 包含 openai 依赖"""
        ini = ToxConfigGenerator.generate_tox_ini()
        self.assertIn("openai", ini)
        self.assertIn("python-dotenv", ini)

    def test_ci_tox_workflow_contains_strategy_matrix(self):
        """CI tox workflow 含矩阵策略"""
        wf = ToxConfigGenerator.generate_ci_tox_workflow()
        self.assertIn("Tox CI", wf)
        self.assertIn("matrix", wf)
        self.assertIn("tox", wf)
        self.assertIn("actions/checkout", wf)

    def test_ci_tox_workflow_multi_version(self):
        """多 Python 版本"""
        wf = ToxConfigGenerator.generate_ci_tox_workflow()
        self.assertIn("3.9", wf)
        self.assertIn("3.10", wf)
        self.assertIn("3.11", wf)

    def test_tox_ini_custom_project_name(self):
        """自定义项目名"""
        ini = ToxConfigGenerator.generate_tox_ini(project_name="my_app")
        self.assertIn("my_app", ini)


class TestCoverageChecker(unittest.TestCase):
    """覆盖率检查"""

    def setUp(self):
        self.checker = CoverageChecker(threshold=0.80)

    def test_mock_result_when_xml_missing(self):
        """XML 不存在时返回 mock"""
        result = self.checker.parse_coverage_xml("nonexistent.xml")
        self.assertGreater(result.line_rate, 0)
        self.assertGreater(len(result.module_rates), 0)

    def test_mock_result_keys(self):
        """mock 结果关键字段存在"""
        self.checker.parse_coverage_xml("nonexistent.xml")
        r = self.checker.result
        self.assertTrue(hasattr(r, "line_rate"))
        self.assertTrue(hasattr(r, "total_lines"))
        self.assertTrue(hasattr(r, "covered_lines"))

    def test_check_module_rates_returns_dict(self):
        """模块检查返回 dict"""
        self.checker.parse_coverage_xml("nonexistent.xml")
        rates = self.checker.check_module_rates()
        self.assertIsInstance(rates, dict)
        self.assertIn("api_client", rates)
        self.assertIn("response_validator", rates)

    def test_check_module_rates_structure(self):
        """模块检查结构正确"""
        self.checker.parse_coverage_xml("nonexistent.xml")
        rates = self.checker.check_module_rates()
        for mod, info in rates.items():
            self.assertIn("rate", info)
            self.assertIn("threshold", info)
            self.assertIn("passed", info)

    def test_check_module_rates_high_coverage_pass(self):
        """高覆盖率模块通过"""
        self.checker.parse_coverage_xml("nonexistent.xml")
        rates = self.checker.check_module_rates()
        self.assertTrue(rates["api_client"]["passed"])
        self.assertTrue(rates["key_manager"]["passed"])

    def test_check_module_rates_edge_cases(self):
        """边缘模块检查"""
        self.checker.parse_coverage_xml("nonexistent.xml")
        rates = self.checker.check_module_rates()
        # 覆盖率偏低的应标记
        for mod, info in rates.items():
            if not info["passed"]:
                self.assertLess(info["rate"], info["threshold"])

    def test_coverage_report_contains_sections(self):
        """覆盖率报告包含关键章节"""
        self.checker.parse_coverage_xml("nonexistent.xml")
        report = self.checker.coverage_report()
        self.assertIn("Coverage Report", report)
        self.assertIn("Module Breakdown", report)
        self.assertIn("Lines:", report)

    def test_coverage_report_shows_failed(self):
        """覆盖率报告显示失败模块"""
        self.checker.parse_coverage_xml("nonexistent.xml")
        report = self.checker.coverage_report()
        if "[!!]" in report:
            self.assertIn("below threshold", report)

    def test_as_dict(self):
        """CoverageResult 转 dict"""
        r = CoverageResult(line_rate=0.85, total_lines=100, covered_lines=85)
        d = r.as_dict()
        self.assertEqual(d["line_rate"], 0.85)
        self.assertEqual(d["total_lines"], 100)

    def test_parse_real_xml(self):
        """解析真实 XML（如果存在）"""
        xml_path = os.path.join(os.path.dirname(__file__), "..", "coverage.xml")
        if os.path.exists(xml_path):
            result = self.checker.parse_coverage_xml(xml_path)
            self.assertGreater(result.files_analyzed, 0)

    def test_check_module_threshold_zero_passed(self):
        """模块全部通过的场景"""
        self.checker.parse_coverage_xml("nonexistent.xml")
        self.checker.MODULE_THRESHOLDS = {"api_client": 0.0}
        rates = self.checker.check_module_rates()
        self.assertTrue(rates["api_client"]["passed"])


class TestCodeSanityChecker(unittest.TestCase):
    """代码健全性检查"""

    def setUp(self):
        self.sanity = CodeSanityChecker()

    def test_check_all_returns_list(self):
        """检查全部返回 list"""
        issues = self.sanity.check_all()
        self.assertIsInstance(issues, list)

    def test_check_hardcoded_keys(self):
        """硬编码检查"""
        issues = self.sanity.check_hardcoded_keys()
        # utils 目录中的 .env 文件不应包含硬编码 key
        for issue in issues:
            self.assertEqual(issue.issue_type, "HARDCODED_KEY")

    def test_check_todo_returns_list(self):
        """TODO 检查"""
        issues = self.sanity.check_todo_remaining()
        self.assertIsInstance(issues, list)

    def test_check_file_size_returns_list(self):
        """文件大小检查"""
        issues = self.sanity.check_file_size(max_lines=500)
        self.assertIsInstance(issues, list)

    def test_check_trailing_newline_returns_list(self):
        """末尾空行检查"""
        issues = self.sanity.check_trailing_newline()
        self.assertIsInstance(issues, list)

    def test_sanity_issue_as_dict(self):
        """SanityIssue 转 dict"""
        issue = SanityIssue("test.py", 10, "HARDCODED_KEY", "Found key")
        d = issue.as_dict()
        self.assertEqual(d["file"], "test.py")
        self.assertEqual(d["line"], 10)
        self.assertEqual(d["type"], "HARDCODED_KEY")

    def test_pattern_matches_sk_key(self):
        """匹配 sk- 模式的 key"""
        pattern = self.sanity.SUSPICIOUS_PATTERNS["sk_key_literal"]
        self.assertIsNotNone(pattern.search("sk-12345678901234567890"))
        self.assertIsNone(pattern.search("api_key = 'hello'"))


class TestProjectHealthReporter(unittest.TestCase):
    """健康报告"""

    def setUp(self):
        self.coverage = CoverageChecker(threshold=0.80)
        self.sanity = CodeSanityChecker()
        self.reporter = ProjectHealthReporter(
            self.coverage, self.sanity, project_dir="."
        )

    def test_generate_health_report_contains_sections(self):
        """健康报告包含所有章节"""
        self.coverage.parse_coverage_xml("nonexistent.xml")
        report = self.reporter.generate_health_report()
        self.assertIn("Project Health Report", report)
        self.assertIn("Test Coverage", report)
        self.assertIn("Code Sanity", report)
        self.assertIn("Tox Config", report)

    def test_health_report_has_score(self):
        """健康报告有评分"""
        self.coverage.parse_coverage_xml("nonexistent.xml")
        report = self.reporter.generate_health_report()
        self.assertIn("Score:", report)

    def test_score_range(self):
        """评分在 0-100"""
        score = self.reporter._calculate_score()
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_score_no_issues_gives_higher_score(self):
        """无问题得分更高"""
        base_score = self.reporter._calculate_score()
        # 清理 issues
        self.sanity.issues = []
        clean_score = self.reporter._calculate_score()
        self.assertGreaterEqual(clean_score, base_score)


if __name__ == "__main__":
    unittest.main(verbosity=2)
