"""
Day 19 (Week 4 Day 4) — 开源工具整合

功能：
1. Tox 配置生成器 — 生成 tox.ini，支持多 Python 版本和多环境
2. Coverage 检查器 — 读取 coverage.xml，评估行/分支/函数覆盖率
3. Code sanity 检查 — 硬编码泄露检测、import 死引用、TODO 遗存
4. Project 健康报告 — 整合以上三项的综合报告

面试话术：
    "我负责的工具链整合包括 Tox 多环境测试、Coverage 覆盖率门禁和
    Code sanity 静态检查。覆盖率目标：核心模块 >= 90%，工具模块 >= 70%。
    CI 中每个 PR 都会触发 sanity 检查，防止硬编码 API Key 泄露。"
"""
import re
import os
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------------------------
# Tox 配置生成器
# ---------------------------------------------------------------------------

class ToxConfigGenerator:
    """Tox 配置生成器"""

    @staticmethod
    def generate_tox_ini(project_name: str = "ai_test_env",
                         python_versions: List[str] = None,
                         test_dirs: List[str] = None) -> str:
        """生成 tox.ini"""
        versions = python_versions or ["3.9", "3.10", "3.11"]
        dirs = test_dirs or ["tests"]

        env_list = []
        for v in versions:
            short = v.replace(".", "")
            env_list.append(f"py{short}")

        deps = [
            "pytest",
            "pytest-cov",
            "pytest-html",
            "openai",
            "python-dotenv",
        ]

        commands = []
        for d in dirs:
            commands.append(
                f"    pytest {d} -v --cov=utils --cov-report=xml "
                f"--cov-report=term --html=report.html --self-contained-html"
            )

        return f"""[tox]
envlist = {", ".join(env_list)}
isolated_build = True
skip_missing_interpreters = True

[testenv]
deps =
    {chr(10) + '    '.join(deps)}

commands =
{chr(10).join(commands)}

[pytest]
addopts = --tb=short -p no:warnings
testpaths = {" ".join(dirs)}

[coverage:run]
source = {project_name}
omit =
    */tests/*
    */__pycache__/*
    */.tox/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if __name__ == "__main__":
"""

    @staticmethod
    def generate_ci_tox_workflow(repo_path: str = "ai_test_env") -> str:
        """生成使用 Tox 的 CI workflow"""
        return f"""name: Tox CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  tox:
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
      fail-fast: false

    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{{{ matrix.python-version }}}}
      - name: Install tox
        run: pip install tox
      - name: Run tox
        working-directory: {repo_path}
        run: tox
        env:
          DEEPSEEK_API_KEY: ${{{{ secrets.DEEPSEEK_API_KEY }}}}
"""


# ---------------------------------------------------------------------------
# Coverage 检查器
# ---------------------------------------------------------------------------

@dataclass
class CoverageResult:
    """覆盖率结果"""
    line_rate: float = 0.0
    branch_rate: float = 0.0
    function_rate: float = 0.0
    total_lines: int = 0
    covered_lines: int = 0
    files_analyzed: int = 0
    module_rates: Dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> Dict:
        return {
            "line_rate": self.line_rate,
            "branch_rate": self.branch_rate,
            "function_rate": self.function_rate,
            "total_lines": self.total_lines,
            "covered_lines": self.covered_lines,
            "files_analyzed": self.files_analyzed,
            "module_rates": self.module_rates,
        }


class CoverageChecker:
    """
    覆盖率检查器

    解析 coverage.xml (Cobertura 格式) 或通过 pytest-cov 直接获取结果。
    支持模块级别的覆盖率阈值检查。
    """

    # 模块覆盖率阈值
    MODULE_THRESHOLDS = {
        "api_client": 0.90,
        "response_validator": 0.90,
        "quality_checker": 0.85,
        "prompt_injection_tester": 0.85,
        "robustness_tester": 0.85,
        "regression_tester": 0.80,
        "e2e_tester": 0.75,
        "conversation_tester": 0.80,
        "llm_judge": 0.80,
        "key_manager": 0.90,
        "error_classifier": 0.80,
        "consistency_checker": 0.80,
        "truncation_analyzer": 0.80,
        "pipeline_assessment": 0.80,
        "browser_checker": 0.75,
        "suite_manager": 0.80,
        "ci_config_gen": 0.80,
    }

    def __init__(self, threshold: float = 0.80):
        self.threshold = threshold
        self.result = CoverageResult()

    def parse_coverage_xml(self, xml_path: str) -> CoverageResult:
        """
        解析 Cobertura XML 格式的覆盖率报告。

        模拟实现，实际项目中应解析 coverage.xml 的 <class> 和 <line> 标签。
        """
        if not os.path.exists(xml_path):
            print(f"[??] Coverage XML not found: {xml_path}. Using mock.")
            self.result = self._mock_result()
            return self.result

        self.result = self._parse_xml(xml_path)
        return self.result

    def _parse_xml(self, xml_path: str) -> CoverageResult:
        """解析 XML（简化实现）"""
        import xml.etree.ElementTree as ET

        tree = ET.parse(xml_path)
        root = tree.getroot()

        result = CoverageResult()
        packages = root.findall(".//package")

        for pkg in packages:
            pkg_name = pkg.get("name", "unknown")
            classes = pkg.findall("classes/class")

            for cls in classes:
                filename = cls.get("filename", "")
                result.files_analyzed += 1
                lines_el = cls.find("lines")
                if lines_el is not None:
                    total = int(lines_el.get("valid", 0))
                    covered = int(lines_el.get("covered", 0))
                    result.total_lines += total
                    result.covered_lines += covered

                    # 按模块统计
                    module_name = Path(filename).stem
                    rate = covered / max(total, 1)
                    result.module_rates[module_name] = rate

        result.line_rate = result.covered_lines / max(result.total_lines, 1)
        return result

    def _mock_result(self) -> CoverageResult:
        """模拟覆盖率结果"""
        return CoverageResult(
            line_rate=0.87,
            branch_rate=0.82,
            function_rate=0.91,
            total_lines=1250,
            covered_lines=1087,
            files_analyzed=12,
            module_rates={
                "api_client": 0.94,
                "response_validator": 0.92,
                "quality_checker": 0.88,
                "prompt_injection_tester": 0.86,
                "robustness_tester": 0.85,
                "regression_tester": 0.82,
                "e2e_tester": 0.78,
                "conversation_tester": 0.83,
                "llm_judge": 0.81,
                "key_manager": 0.95,
                "error_classifier": 0.79,
                "browser_checker": 0.76,
            }
        )

    def check_module_rates(self) -> Dict[str, Dict]:
        """
        检查每个模块的覆盖率是否达标。

        Returns:
            {module: {"rate": float, "threshold": float, "passed": bool}}
        """
        results = {}
        for mod, threshold in self.MODULE_THRESHOLDS.items():
            rate = self.result.module_rates.get(mod, 0)
            results[mod] = {
                "rate": rate,
                "threshold": threshold,
                "passed": rate >= threshold,
            }
        return results

    def coverage_report(self) -> str:
        """
        生成覆盖率报告。

        Returns:
            格式化的报告字符串
        """
        report = []
        r = self.result
        report.append("=== Coverage Report ===")
        report.append(f"  Lines:     {r.covered_lines}/{r.total_lines} ({r.line_rate:.1%})")
        report.append(f"  Branches:  {r.branch_rate:.1%}")
        report.append(f"  Functions: {r.function_rate:.1%}")
        report.append(f"  Files:     {r.files_analyzed}")
        report.append("")

        thresholds = self.check_module_rates()
        report.append("--- Module Breakdown ---")
        for mod, info in sorted(thresholds.items()):
            status = "[OK]" if info["passed"] else "[!!]"
            report.append(
                f"  {status} {mod}: {info['rate']:.1%} "
                f"(threshold: {info['threshold']:.0%})"
            )

        failed = [m for m, i in thresholds.items() if not i["passed"]]
        if failed:
            report.append("")
            report.append(f"[!!] {len(failed)} module(s) below threshold:")
            for m in failed:
                report.append(f"       - {m}")

        return "\n".join(report)


# ---------------------------------------------------------------------------
# Code Sanity 检查器
# ---------------------------------------------------------------------------

@dataclass
class SanityIssue:
    """代码检查问题"""
    file: str
    line: int
    issue_type: str  # "HARDCODED_KEY" / "DEAD_IMPORT" / "TODO_REMAINING"
    message: str

    def as_dict(self) -> Dict:
        return {
            "file": self.file,
            "line": self.line,
            "type": self.issue_type,
            "message": self.message,
        }


class CodeSanityChecker:
    """
    代码健全性检查器

    检查项：
    1. 硬编码泄露（API Key / Token / Secret）
    2. TODO/FIXME 遗存
    3. 过大的单文件（>500 行）
    4. 文件末尾缺少空行
    """

    # 可疑模式（匹配硬编码 API Key、Token 等）
    SUSPICIOUS_PATTERNS = {
        "api_key_in_code": re.compile(
            r'(?i)(api[_-]?key|secret|token|password)'
            r'\s*[=:]\s*["\'](sk-|ghp_|gho_|ghu_|ghs_|ghr_)[a-zA-Z0-9]+',
            re.IGNORECASE,
        ),
        "sk_key_literal": re.compile(
            r'sk-[a-zA-Z0-9]{20,}',
            re.IGNORECASE,
        ),
        "env_file_key": re.compile(
            r'(?i)DEEPSEEK_API_KEY\s*=\s*sk-',
        ),
    }

    def __init__(self, src_dir: str = "utils", tests_dir: str = "tests"):
        self.src_dir = src_dir
        self.tests_dir = tests_dir
        self.issues: List[SanityIssue] = []

    def check_all(self) -> List[SanityIssue]:
        """运行全部检查"""
        self.issues.clear()
        self.check_hardcoded_keys()
        self.check_todo_remaining()
        self.check_file_size()
        self.check_trailing_newline()
        return self.issues

    def check_hardcoded_keys(self) -> List[SanityIssue]:
        """检查硬编码密钥"""
        for root, dirs, files in os.walk(self.src_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                self._scan_file(fpath, self.SUSPICIOUS_PATTERNS)
        return self.issues

    def check_todo_remaining(self) -> List[SanityIssue]:
        """检查 TODO/FIXME 遗存"""
        for root, dirs, files in os.walk(self.src_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                self._scan_text_pattern(fpath, "TODO", "TODO_REMAINING")
                self._scan_text_pattern(fpath, "FIXME", "TODO_REMAINING")
        return self.issues

    def _scan_file(self, fpath: str, patterns: Dict) -> None:
        """扫描文件匹配正则模式"""
        rel_path = os.path.relpath(fpath)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    for pname, pattern in patterns.items():
                        if pattern.search(line):
                            self.issues.append(SanityIssue(
                                file=rel_path,
                                line=i,
                                issue_type="HARDCODED_KEY",
                                message=f"Possible {pname}: {line.strip()[:80]}",
                            ))
        except (UnicodeDecodeError, IOError) as e:
            self.issues.append(SanityIssue(
                file=rel_path,
                line=0,
                issue_type="TODO_REMAINING",
                message=f"Read error: {e}",
            ))

    def _scan_text_pattern(self, fpath: str, text: str,
                           issue_type: str) -> None:
        """扫描文件中是否包含指定文本"""
        rel_path = os.path.relpath(fpath)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if text in line.upper() and text not in line:
                        # 避免把含 TODO 的注释当成问题通知
                        continue
                    if text in line:
                        self.issues.append(SanityIssue(
                            file=rel_path,
                            line=i,
                            issue_type=issue_type,
                            message=f"{text} found: {line.strip()[:80]}",
                        ))
        except (UnicodeDecodeError, IOError):
            pass

    def check_file_size(self, max_lines: int = 500) -> List[SanityIssue]:
        """检查文件大小"""
        for root, dirs, files in os.walk(self.src_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        line_count = sum(1 for _ in f)
                    if line_count > max_lines:
                        self.issues.append(SanityIssue(
                            file=rel_path,
                            line=0,
                            issue_type="TODO_REMAINING",
                            message=f"File too large: {line_count} lines (max {max_lines})",
                        ))
                except (UnicodeDecodeError, IOError):
                    pass
        return self.issues

    def check_trailing_newline(self) -> List[SanityIssue]:
        """检查文件末尾是否有空行"""
        for root, dirs, files in os.walk(self.src_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath)
                try:
                    with open(fpath, "rb") as f:
                        content = f.read()
                    if content and not content.endswith(b"\n"):
                        self.issues.append(SanityIssue(
                            file=rel_path,
                            line=0,
                            issue_type="TODO_REMAINING",
                            message="File missing trailing newline",
                        ))
                except IOError:
                    pass
        return self.issues


# ---------------------------------------------------------------------------
# 健康报告
# ---------------------------------------------------------------------------

class ProjectHealthReporter:
    """
    项目健康报告生成器

    整合 Tox 配置、Coverage、Code Sanity 的综合报告。
    """

    def __init__(self, coverage: CoverageChecker,
                 sanity: CodeSanityChecker,
                 project_dir: str = "."):
        self.coverage = coverage
        self.sanity = sanity
        self.project_dir = project_dir

    def generate_health_report(self) -> str:
        """
        生成完整健康报告。
        """
        lines = []
        lines.append("=" * 60)
        lines.append("  Project Health Report")
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 60)
        lines.append("")

        # 1. Coverage
        lines.append("--- 1. Test Coverage ---")
        lines.append(self.coverage.coverage_report())
        lines.append("")

        # 2. Sanity
        lines.append("--- 2. Code Sanity ---")
        sanity_issues = self.sanity.check_all()
        if not sanity_issues:
            lines.append("  [OK] No issues found.")
        else:
            for issue in sanity_issues:
                lines.append(f"  [{issue.issue_type[:4]}] "
                           f"{issue.file}:{issue.line} - {issue.message}")
        lines.append("")

        # 3. Tox config
        lines.append("--- 3. Tox Config ---")
        tox_exists = os.path.exists(os.path.join(self.project_dir, "tox.ini"))
        lines.append(f"  tox.ini: {'[OK] exists' if tox_exists else '[??] not found'}")

        ci_dir = os.path.join(self.project_dir, ".github", "workflows")
        ci_files = []
        if os.path.isdir(ci_dir):
            ci_files = [f for f in os.listdir(ci_dir) if f.endswith(".yml")]
        lines.append(f"  CI workflows: {len(ci_files)} file(s)")
        for cf in sorted(ci_files):
            lines.append(f"    - {cf}")

        lines.append("")
        lines.append("=" * 60)
        lines.append(f"  Score: {self._calculate_score():.0f}/100")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _calculate_score(self) -> float:
        """计算健康评分"""
        score = 0.0

        # Coverage (0-50)
        score += min(self.coverage.result.line_rate * 50, 50)

        # Sanity (0-30)
        issues = self.sanity.issues
        score += max(30 - len(issues) * 3, 0)

        # Tox + CI (0-20)
        for check_dir in [self.project_dir,
                          os.path.join(self.project_dir, ".github")]:
            if os.path.exists(check_dir):
                score += 5

        return min(score, 100)
