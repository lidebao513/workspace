"""
Day 18 (Week 4 Day 3) — CI/CD 集成 单元测试

覆盖：
1. GateRule 门禁策略（ALL_PASS / THRESHOLD / NO_REGRESSION / BLOCKING_ONLY）
2. CIConfigGenerator 各种 workflow 模板生成
3. CIGate 门禁检查（正常通过 + 失败退出）
"""
import sys
import os
import unittest
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d18_ci_config_gen import (
    GatingStrategy, GateRule, CIConfigGenerator,
)


class TestGateRule(unittest.TestCase):
    """门禁规则"""

    def test_all_pass_success(self):
        """ALL_PASS 全部通过"""
        rule = GateRule("smoke", GatingStrategy.ALL_PASS)
        result = rule.check(pass_rate=1.0)
        self.assertTrue(result["passed"])

    def test_all_pass_fail(self):
        """ALL_PASS 未全部通过"""
        rule = GateRule("smoke", GatingStrategy.ALL_PASS)
        result = rule.check(pass_rate=0.95)
        self.assertFalse(result["passed"])

    def test_threshold_pass(self):
        """THRESHOLD 阈值通过"""
        rule = GateRule("regression", GatingStrategy.THRESHOLD, threshold=0.95)
        result = rule.check(pass_rate=0.97)
        self.assertTrue(result["passed"])

    def test_threshold_fail(self):
        """THRESHOLD 阈值未通过"""
        rule = GateRule("regression", GatingStrategy.THRESHOLD, threshold=0.95)
        result = rule.check(pass_rate=0.90)
        self.assertFalse(result["passed"])

    def test_no_regression_pass(self):
        """NO_REGRESSION 无回归"""
        rule = GateRule("regression", GatingStrategy.NO_REGRESSION)
        result = rule.check(pass_rate=1.0, has_regression=False)
        self.assertTrue(result["passed"])

    def test_no_regression_fail(self):
        """NO_REGRESSION 有回归"""
        rule = GateRule("regression", GatingStrategy.NO_REGRESSION)
        result = rule.check(pass_rate=0.5, has_regression=True)
        self.assertFalse(result["passed"])

    def test_blocking_only_pass(self):
        """BLOCKING_ONLY 通过"""
        rule = GateRule("security", GatingStrategy.BLOCKING_ONLY, threshold=0.9)
        result = rule.check(pass_rate=0.95, failed_security=False)
        self.assertTrue(result["passed"])

    def test_blocking_only_fail_security(self):
        """BLOCKING_ONLY 安全失败"""
        rule = GateRule("security", GatingStrategy.BLOCKING_ONLY)
        result = rule.check(pass_rate=0.95, failed_security=True)
        self.assertFalse(result["passed"])

    def test_blocking_only_low_rate(self):
        """BLOCKING_ONLY 通过率低"""
        rule = GateRule("performance", GatingStrategy.BLOCKING_ONLY,
                       threshold=0.9)
        result = rule.check(pass_rate=0.5, failed_security=False)
        self.assertFalse(result["passed"])

    def test_unknown_strategy(self):
        """未知策略"""
        rule = GateRule("unknown", "not_a_real_strategy")
        result = rule.check(pass_rate=0.5)
        self.assertFalse(result["passed"])

    def test_default_strategy(self):
        """默认策略为 ALL_PASS"""
        rule = GateRule("smoke")
        self.assertEqual(rule.strategy, GatingStrategy.ALL_PASS)

    def test_default_blocking_labels(self):
        """默认阻塞标签"""
        rule = GateRule("smoke")
        self.assertIn("security", rule.blocking_labels)


class TestCIConfigGenerator(unittest.TestCase):
    """CI 配置生成器"""

    def test_smoke_workflow_contains_keywords(self):
        """冒烟 workflow 包含关键内容"""
        yml = CIConfigGenerator.generate_smoke_workflow()
        self.assertIn("Smoke Test", yml)
        self.assertIn("pytest", yml)
        self.assertIn("actions/checkout", yml)
        self.assertIn("actions/setup-python", yml)
        self.assertIn("smoke", yml.lower())
        self.assertIn("DEEPSEEK_API_KEY", yml)

    def test_regression_workflow_default(self):
        """回归 workflow"""
        yml = CIConfigGenerator.generate_regression_workflow()
        self.assertIn("Regression Test", yml)
        self.assertIn("cron", yml)
        self.assertIn("regression", yml.lower())

    def test_security_workflow_weekly(self):
        """安全 workflow 每周触发"""
        yml = CIConfigGenerator.generate_security_workflow()
        self.assertIn("Security Test", yml)
        self.assertIn("security", yml.lower())

    def test_full_workflow_multi_job(self):
        """完整 workflow 多 job"""
        yml = CIConfigGenerator.generate_full_workflow()
        self.assertIn("AI Test Pipeline", yml)
        self.assertIn("Smoke Tests", yml)
        self.assertIn("Security Tests", yml)
        self.assertIn("needs: smoke", yml)

    def test_full_gating_check(self):
        """完整 workflow 含门禁检查"""
        yml = CIConfigGenerator.generate_full_workflow()
        self.assertIn("run_gating_check", yml)

    def test_ci_gate_script_generation(self):
        """门禁脚本生成"""
        script = CIConfigGenerator.generate_ci_gate_script()
        self.assertIn("class CIGate", script)
        self.assertIn("run_gating_check", script)
        self.assertIn("sys.exit(1)", script)

    def test_ci_gate_has_gates_dict(self):
        """门禁配置字典"""
        script = CIConfigGenerator.generate_ci_gate_script()
        self.assertIn("GATES", script)

    def test_write_workflows(self):
        """写入 workflow 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = CIConfigGenerator.write_workflows(
                output_dir=tmpdir, repo_path="ai_test_env"
            )
            # 检查文件是否创建
            files = os.listdir(tmpdir)
            self.assertIn("smoke.yml", files)
            self.assertIn("regression.yml", files)
            self.assertIn("security.yml", files)
            self.assertIn("full-pipeline.yml", files)

    def test_repo_path_customization(self):
        """自定义 repo 路径"""
        yml = CIConfigGenerator.generate_smoke_workflow(repo_path="custom_path")
        self.assertIn("custom_path", yml)

    def test_python_version_customization(self):
        """自定义 Python 版本"""
        yml = CIConfigGenerator.generate_smoke_workflow(python_version="3.12")
        self.assertIn("3.12", yml)


if __name__ == "__main__":
    unittest.main(verbosity=2)
