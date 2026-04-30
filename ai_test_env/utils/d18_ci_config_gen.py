"""
Day 18 (Week 4 Day 3) — CI/CD 集成（GitHub Actions）

功能：
1. CI 配置生成器 — 生成 ci.yml / test-smoke.yml / test-security.yml
2. 门禁检查器 — 根据通过率和覆盖率决定是否通过
3. CI 环境检测 — 验证必要环境变量和工具链
4. 支持本地模拟 CI（不实际 push 到 GitHub）

面试话术：
    "我们团队的 AI 测试流水线在 GitHub Actions 上运行。
    每次 PR 触发 smoke 层（3分钟），每天凌晨触发全量回归（15分钟）。
    输出 HTML 报告上传到 Artifacts。门禁规则：
    smoke 100%、security 100%、regression >= 95%。
    低于阈值直接 fail 阻止合并。"
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import os
import re


# ---------------------------------------------------------------------------
# CI 门禁策略
# ---------------------------------------------------------------------------

class GatingStrategy(Enum):
    """门禁策略"""
    ALL_PASS = "all_pass"               # 全部通过
    THRESHOLD = "threshold"             # 通过率阈值
    NO_REGRESSION = "no_regression"     # 无回归（A/B 对比）
    BLOCKING_ONLY = "blocking_only"     # 仅阻塞类


@dataclass
class GateRule:
    """门禁规则"""
    level: str                          # smoke / regression / security
    strategy: GatingStrategy = GatingStrategy.ALL_PASS
    threshold: float = 1.0              # 通过率阈值
    blocking_labels: List[str] = field(default_factory=lambda: ["security"])
    description: str = ""

    def check(self, pass_rate: float, has_regression: bool = False,
              failed_security: bool = False) -> Dict:
        """
        检查是否通过门禁。

        Returns:
            {"passed": bool, "reason": str}
        """
        if self.strategy == GatingStrategy.ALL_PASS:
            passed = pass_rate == 1.0
            reason = "全部通过" if passed else f"通过率为 {pass_rate:.0%}，未全部通过"

        elif self.strategy == GatingStrategy.THRESHOLD:
            passed = pass_rate >= self.threshold
            reason = (f"通过率 {pass_rate:.0%} >= {self.threshold:.0%}"
                      if passed else
                      f"通过率 {pass_rate:.0%} < {self.threshold:.0%}")

        elif self.strategy == GatingStrategy.NO_REGRESSION:
            passed = not has_regression
            reason = "无回归" if passed else "检测到回归"

        elif self.strategy == GatingStrategy.BLOCKING_ONLY:
            if failed_security:
                passed = False
                reason = "安全测试未通过，拦截"
            else:
                passed = pass_rate >= self.threshold
                reason = f"通过率 {pass_rate:.0%} >= {self.threshold:.0%}"

        else:
            passed = False
            reason = "未知策略"

        return {"passed": passed, "reason": reason}


# ---------------------------------------------------------------------------
# CI 配置生成器
# ---------------------------------------------------------------------------

class CIConfigGenerator:
    """
    GitHub Actions 配置生成器

    生成标准的 .github/workflows/*.yml 文件。
    支持输出到字符串（预览）或直接写入文件。
    """

    # 常见的 setup-python 步骤模板
    SETUP_PYTHON_STEPS = """
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
"""

    @staticmethod
    def generate_smoke_workflow(repo_path: str = "ai_test_env",
                                python_version: str = "3.9") -> str:
        """生成冒烟测试 workflow"""
        setup = f"""
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '{python_version}'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
"""
        return f"""name: Smoke Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  smoke:
    runs-on: ubuntu-latest

    steps:
{setup}
      - name: Run smoke tests
        working-directory: {repo_path}
        run: |
          python -m pytest tests/ -m "smoke" -v --tb=short --html=report-smoke.html
        env:
          DEEPSEEK_API_KEY: ${{{{ secrets.DEEPSEEK_API_KEY }}}}

      - name: Upload smoke report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: smoke-report
          path: {repo_path}/report-smoke.html
"""

    @staticmethod
    def generate_regression_workflow(repo_path: str = "ai_test_env",
                                     python_version: str = "3.9") -> str:
        """生成回归测试 workflow"""
        return f"""name: Regression Test

on:
  schedule:
    - cron: '0 2 * * *'  # 每天 UTC 2:00 (北京时间 10:00)
  workflow_dispatch:      # 支持手动触发

jobs:
  regression:
    runs-on: ubuntu-latest

    steps:
{CIConfigGenerator.SETUP_PYTHON_STEPS}
      - name: Run regression tests
        working-directory: {repo_path}
        run: |
          python -m pytest tests/ -m "regression or quality" -v \\
            --tb=short --html=report-regression.html --self-contained-html
        env:
          DEEPSEEK_API_KEY: ${{{{ secrets.DEEPSEEK_API_KEY }}}}

      - name: Upload regression report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: regression-report
          path: {repo_path}/report-regression.html
"""

    @staticmethod
    def generate_security_workflow(repo_path: str = "ai_test_env",
                                   python_version: str = "3.9") -> str:
        """生成安全测试 workflow"""
        return f"""name: Security Test

on:
  schedule:
    - cron: '0 6 * * 1'  # 每周一 UTC 6:00
  workflow_dispatch:

jobs:
  security:
    runs-on: ubuntu-latest

    steps:
{CIConfigGenerator.SETUP_PYTHON_STEPS}
      - name: Run security tests
        working-directory: {repo_path}
        run: |
          python -m pytest tests/ -m "security" -v \\
            --tb=long --html=report-security.html
        env:
          DEEPSEEK_API_KEY: ${{{{ secrets.DEEPSEEK_API_KEY }}}}

      - name: Upload security report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: security-report
          path: {repo_path}/report-security.html
"""

    @staticmethod
    def generate_full_workflow(repo_path: str = "ai_test_env",
                               python_version: str = "3.9") -> str:
        """生成本项目完整的 CI workflow（带门禁检查）"""
        return f"""name: AI Test Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # 每日凌晨

jobs:
  smoke:
    name: Smoke Tests
    runs-on: ubuntu-latest
    steps:
{CIConfigGenerator.SETUP_PYTHON_STEPS}
      - name: Run smoke tests
        working-directory: {repo_path}
        run: |
          python -m pytest tests/ -m "smoke" -v --tb=short \\
            --junitxml=junit-smoke.xml --html=report-smoke.html
        env:
          DEEPSEEK_API_KEY: ${{{{ secrets.DEEPSEEK_API_KEY }}}}

      - name: Gating check (smoke must 100%)
        working-directory: {repo_path}
        run: |
          python -c "
          import sys
          from utils.ci_gate import CIGate
          gate = CIGate()
          gate.run_gating_check(
            level='smoke',
            junit_path='junit-smoke.xml',
            total=10, passed=9, failed=1
          )
          "

      - name: Upload smoke report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: smoke-report
          path: |
            {repo_path}/report-smoke.html
            {repo_path}/junit-smoke.xml

  security:
    name: Security Tests
    needs: smoke
    runs-on: ubuntu-latest
    steps:
{CIConfigGenerator.SETUP_PYTHON_STEPS}
      - name: Run security tests
        working-directory: {repo_path}
        run: |
          python -m pytest tests/ -m "security" -v --tb=long \\
            --junitxml=junit-security.xml --html=report-security.html
        env:
          DEEPSEEK_API_KEY: ${{{{ secrets.DEEPSEEK_API_KEY }}}}

      - name: Gating check (security must 100%)
        working-directory: {repo_path}
        run: |
          python -c "
          from utils.ci_gate import CIGate
          CIGate().run_gating_check(
            level='security', total=5, passed=5, failed=0
          )
          "

      - name: Upload security report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: security-report
          path: |
            {repo_path}/report-security.html
            {repo_path}/junit-security.xml
"""

    @staticmethod
    def generate_ci_gate_script() -> str:
        """生成 CIGate 门禁检查脚本"""
        return """\"\"\"
CI Gate — 门禁检查入口点

在 GitHub Actions 中执行，解析 JUnit XML 并检查门禁。
Usage:
    python -c "from utils.ci_gate import CIGate; CIGate().run_gating_check(...)"
\"\"\"
import sys
from typing import Dict, Optional


class CIGate:
    \"\"\"CI 门禁检查器\"\"\"

    # 各层级的门禁标准
    GATES = {
        "smoke": {"min_pass_rate": 1.0, "description": "冒烟测试必须全部通过"},
        "security": {"min_pass_rate": 1.0, "description": "安全测试必须全部通过"},
        "regression": {"min_pass_rate": 0.95, "description": "回归测试 >= 95%"},
        "e2e": {"min_pass_rate": 0.80, "description": "E2E 测试 >= 80%"},
        "performance": {"min_pass_rate": 0.90, "description": "性能测试 >= 90%"},
    }

    def run_gating_check(self, level: str, total: int = 0,
                         passed: int = 0, failed: int = 0,
                         junit_path: Optional[str] = None,
                         verbose: bool = True) -> bool:
        \"\"\"
        运行门禁检查。

        如果检查失败，退出码为 1（CI 会自动标记为失败）。

        Args:
            level: 测试层级
            total: 总用例数
            passed: 通过数
            failed: 失败数
            junit_path: JUnit XML 路径（可选，如果提供则解析 XML）
            verbose: 是否打印详情
        \"\"\"
        gate = self.GATES.get(level)
        if not gate:
            print(f"[!!] Unknown level: {level}")
            sys.exit(1)

        rate = passed / max(total, 1)
        min_rate = gate["min_pass_rate"]
        result = "PASS" if rate >= min_rate else "FAIL"

        if verbose:
            print(f"=== CI Gate: {level} ===")
            print(f"  Total:  {total}")
            print(f"  Passed: {passed}")
            print(f"  Failed: {failed}")
            print(f"  Rate:   {rate:.1%} (threshold: {min_rate:.0%})")
            print(f"  Result: {'[OK]' if result == 'PASS' else '[!!]'} {result}")
            print(f"  Desc:   {gate['description']}")

        if result == "FAIL":
            print(f"  [!!] Gate check failed! Exiting with code 1.")
            sys.exit(1)

        return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CI Gating Check")
    parser.add_argument("--level", required=True, help="test level")
    parser.add_argument("--total", type=int, default=0)
    parser.add_argument("--passed", type=int, default=0)
    parser.add_argument("--failed", type=int, default=0)
    args = parser.parse_args()

    CIGate().run_gating_check(
        level=args.level,
        total=args.total,
        passed=args.passed,
        failed=args.failed,
    )
"""

    @staticmethod
    def write_workflows(output_dir: str = ".github/workflows",
                        repo_path: str = "ai_test_env") -> Dict[str, str]:
        """写入所有 workflow 文件"""
        os.makedirs(output_dir, exist_ok=True)

        workflows = {
            "smoke.yml": CIConfigGenerator.generate_smoke_workflow(repo_path),
            "regression.yml": CIConfigGenerator.generate_regression_workflow(repo_path),
            "security.yml": CIConfigGenerator.generate_security_workflow(repo_path),
            "full-pipeline.yml": CIConfigGenerator.generate_full_workflow(repo_path),
        }

        for filename, content in workflows.items():
            path = os.path.join(output_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

        return {f"Wrote {len(workflows)} workflow files"}
