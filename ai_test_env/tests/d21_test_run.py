"""
Day 21 (Week 4 Summary) — 综合项目 CLI 测试

覆盖：
1. run.py 各子命令的调用（test / param / ci / sanity / coverage / data / tox / health）
2. 参数解析和错误处理
3. 输出格式检查
"""
import sys
import os
import unittest
import tempfile
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from run import main


class TestCLITestCommand(unittest.TestCase):
    """test 子命令"""

    def test_test_smoke(self):
        """smoke 层级"""
        rc = main(["test", "--level", "smoke"])
        self.assertEqual(rc, 0)

    def test_test_regression(self):
        """regression 层级"""
        rc = main(["test", "--level", "regression"])
        self.assertEqual(rc, 0)

    def test_test_security(self):
        """security 层级"""
        rc = main(["test", "--level", "security"])
        self.assertEqual(rc, 0)

    def test_test_all(self):
        """all 层级"""
        rc = main(["test", "--level", "all"])
        self.assertEqual(rc, 0)

    def test_test_invalid_level(self):
        """无效层级返回非零"""
        # argparse 对无效 choice 会 sys.exit(2)，测试捕获 SystemExit
        with self.assertRaises(SystemExit):
            main(["test", "--level", "invalid_level"])


class TestCLIParamCommand(unittest.TestCase):
    """param 子命令"""

    def test_param_single(self):
        """单维度"""
        rc = main(["param", "--name", "test", "--params", "temp=0,1,2"])
        self.assertEqual(rc, 0)

    def test_param_multi(self):
        """多维度"""
        rc = main(["param", "--name", "test",
                    "--params", "temp=0,1;top_p=0.5,1.0"])
        self.assertEqual(rc, 0)

    def test_param_with_output(self):
        """输出到文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                        delete=False) as f:
            output = f.name
        try:
            rc = main(["param", "--name", "test",
                        "--params", "x=1,2;y=a,b",
                        "--output", output])
            self.assertEqual(rc, 0)
            with open(output, "r") as f:
                data = json.load(f)
            self.assertEqual(len(data), 4)
        finally:
            os.unlink(output)

    def test_param_csv_not_found(self):
        """CSV 文件不存在"""
        rc = main(["param", "--name", "test", "--csv", "nonexistent.csv"])
        self.assertEqual(rc, 1)

    def test_param_empty_params(self):
        """无参数"""
        rc = main(["param", "--name", "empty"])
        self.assertEqual(rc, 0)


class TestCLICICommand(unittest.TestCase):
    """ci 子命令"""

    def test_ci_generate_to_temp(self):
        """生成到临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            rc = main(["ci", "generate", "--output", tmpdir])
            self.assertEqual(rc, 0)
            files = os.listdir(tmpdir)
            self.assertGreater(len(files), 0)

    def test_ci_check_smoke_pass(self):
        """smoke 门禁通过"""
        rc = main(["ci", "check", "--level", "smoke",
                    "--total", "10", "--passed", "10"])
        self.assertEqual(rc, 0)

    def test_ci_check_smoke_fail(self):
        """smoke 门禁失败"""
        rc = main(["ci", "check", "--level", "smoke",
                    "--total", "10", "--passed", "9"])
        self.assertEqual(rc, 1)

    def test_ci_check_regression_pass(self):
        """regression 门禁通过"""
        rc = main(["ci", "check", "--level", "regression",
                    "--total", "20", "--passed", "19"])
        self.assertEqual(rc, 0)


class TestCLISanityCommand(unittest.TestCase):
    """sanity 子命令"""

    def test_sanity_normal(self):
        """正常扫描"""
        rc = main(["sanity", "--src-dir", "utils"])
        self.assertEqual(rc, 0)

    def test_sanity_no_fail(self):
        """不因问题退出"""
        rc = main(["sanity", "--src-dir", "utils",
                    "--tests-dir", "tests"])
        self.assertEqual(rc, 0)


class TestCLICoverageCommand(unittest.TestCase):
    """coverage 子命令"""

    def test_coverage_no_xml(self):
        """无 coverage.xml"""
        rc = main(["coverage"])
        self.assertEqual(rc, 0)

    def test_coverage_with_threshold(self):
        """自定义阈值"""
        rc = main(["coverage", "--threshold", "0.85"])
        self.assertEqual(rc, 0)


class TestCLIDataCommand(unittest.TestCase):
    """data 子命令"""

    def test_data_generate_prompt(self):
        """生成 prompt"""
        rc = main(["data", "generate", "--kind", "prompt",
                    "--count", "5"])
        self.assertEqual(rc, 0)

    def test_data_generate_response(self):
        """生成 response"""
        rc = main(["data", "generate", "--kind", "response",
                    "--count", "5"])
        self.assertEqual(rc, 0)

    def test_data_generate_to_file(self):
        """生成到文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl",
                                        delete=False) as f:
            output = f.name
        try:
            rc = main(["data", "generate", "--kind", "prompt",
                        "--count", "3", "--output", output])
            self.assertEqual(rc, 0)
            with open(output, "r") as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 3)
        finally:
            os.unlink(output)

    def test_data_mask_with_input_file(self):
        """脱敏输入文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                        delete=False) as f:
            f.write("user@test.com 13812345678")
            input_file = f.name
        try:
            rc = main(["data", "mask", "--input", input_file])
            self.assertEqual(rc, 0)
        finally:
            os.unlink(input_file)

    def test_data_mask_to_output(self):
        """脱敏输出到文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                        delete=False) as fin:
            fin.write("email: foo@bar.com")
            input_file = fin.name
        output_file = input_file + ".masked"
        try:
            rc = main(["data", "mask", "--input", input_file,
                        "--output", output_file])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(output_file))
        finally:
            os.unlink(input_file)
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_data_mask_no_input(self):
        """无输入文件"""
        rc = main(["data", "mask"])
        self.assertEqual(rc, 1)

    def test_data_version(self):
        """版本查询"""
        rc = main(["data", "version", "--name", "test_dataset"])
        self.assertEqual(rc, 0)


class TestCLIToxCommand(unittest.TestCase):
    """tox 子命令"""

    def test_tox_generate(self):
        """生成 tox.ini"""
        rc = main(["tox"])
        self.assertEqual(rc, 0)

    def test_tox_with_output(self):
        """输出到文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini",
                                        delete=False) as f:
            output = f.name
        try:
            rc = main(["tox", "--output", output])
            self.assertEqual(rc, 0)
            with open(output, "r") as f:
                content = f.read()
            self.assertIn("[tox]", content)
        finally:
            os.unlink(output)


class TestCLIHealthCommand(unittest.TestCase):
    """health 子命令"""

    def test_health_report(self):
        """健康报告"""
        rc = main(["health"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
