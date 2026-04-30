"""
Day 27 — 全量测试运行器

功能：
    一键运行所有测试模块（按层级/按模块/全量），
    记录每次运行的结果日志和时间戳，
    输出汇总报告和失败明细。

面试话术：
    "我把所有 26 个测试模块组织成全量运行器，
    支持 smoke / regression / security / full 四种模式。
    每次运行结果记录到 JSON 日志，方便回查历史。
    PR 前的全量跑通验证从此不需要手动逐个执行。"
"""

import sys
import os
import subprocess
import json
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from enum import Enum


class RunLevel(Enum):
    """运行层级"""
    SMOKE = "smoke"           # 快速验证（d1-d4, d16-d17）
    REGRESSION = "regression" # 功能回归（d6-d10, d18-d20, d26）
    SECURITY = "security"     # 安全测试（d12-d13）
    E2E = "e2e"              # 端到端（d11, d14-d15）
    FULL = "full"             # 全部


@dataclass
class ModuleResult:
    """单模块测试结果"""
    module: str
    passed: int
    failed: int
    skipped: int
    total: int
    duration: float
    output: str = ""

    @property
    def success_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 1.0

    @property
    def passed_str(self) -> str:
        return "[OK]" if self.failed == 0 else "[!!]"


@dataclass
class RunResult:
    """一次运行的完整结果"""
    timestamp: str
    level: str
    results: List[ModuleResult] = field(default_factory=list)
    total_modules: int = 0

    @property
    def total_passed(self) -> int:
        return sum(r.passed for r in self.results)

    @property
    def total_failed(self) -> int:
        return sum(r.failed for r in self.results)

    @property
    def all_passed(self) -> bool:
        return self.total_failed == 0

    @property
    def total_time(self) -> float:
        return sum(r.duration for r in self.results)


class FullTestRunner:
    """全量测试运行器

    根据层级选择测试文件，调用 pytest 运行并收集结果。
    """

    # 模块→层级映射
    MODULE_MAP: Dict[RunLevel, List[str]] = {
        RunLevel.SMOKE: [
            "tests/d1_test_key_manager.py",
            "tests/d2_test_client.py",
            "tests/d4_test_request_format.py",
            "tests/d16_test_browser_checker.py",
            "tests/d17_test_suite_manager.py",
        ],
        RunLevel.REGRESSION: [
            "tests/d6_test_quality.py",
            "tests/d7_test_consistency.py",
            "tests/d8_test_truncation.py",
            "tests/d8_test_tc.py",
            "tests/d8c_test_format.py",
            "tests/d8d_test_style.py",
            "tests/d9_test_llm_judge.py",
            "tests/d10_test_schema.py",
            "tests/d10_test_pipeline_assessment.py",
            "tests/d18_test_ci_config_gen.py",
            "tests/d19_test_toolchain_integration.py",
            "tests/d20_test_data_manager.py",
            "tests/d22_test_load_tester.py",
            "tests/d23_test_retry_engine.py",
            "tests/d24_test_circuit_breaker.py",
            "tests/d25_test_error_system.py",
            "tests/d26_test_token_auditor.py",
        ],
        RunLevel.SECURITY: [
            "tests/d12_test_prompt_injection.py",
            "tests/d13_test_robustness.py",
        ],
        RunLevel.E2E: [
            "tests/d11_test_conversation.py",
            "tests/d14_test_regression.py",
            "tests/d15_test_e2e.py",
        ],
        RunLevel.FULL: [],
    }

    def __init__(self, log_dir: str = "run_logs"):
        self.log_dir = log_dir
        self._history: List[RunResult] = []
        os.makedirs(log_dir, exist_ok=True)

    def run(self, level: RunLevel = RunLevel.FULL,
            extra_modules: List[str] = None) -> RunResult:
        """运行指定层级的测试

        Args:
            level: 运行层级
            extra_modules: 额外追加的测试文件

        Returns:
            RunResult 运行结果
        """
        timestamp = datetime.now().isoformat()
        modules = list(self.MODULE_MAP.get(level, []))
        if extra_modules:
            modules.extend(extra_modules)
        if level == RunLevel.FULL:
            modules = self._discover_all_modules()

        results: List[ModuleResult] = []

        for module in modules:
            if not os.path.exists(module):
                results.append(ModuleResult(
                    module=module, passed=0, failed=0,
                    skipped=0, total=0, duration=0,
                    output="[SKIP] File not found",
                ))
                continue

            start = time.time()
            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "pytest", module, "-q", "--tb=short"],
                    capture_output=True, text=True, timeout=300,
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                )
                duration = time.time() - start
                stdout = proc.stdout
                stderr = proc.stderr

                # 解析 pytest 输出
                passed = failed = skipped = 0
                for line in stdout.split("\n"):
                    if "passed" in line and "failed" in line:
                        # "3 passed, 1 failed, 2 skipped in 0.05s"
                        parts = line.split()
                        for i, p in enumerate(parts):
                            if p == "passed":
                                passed = int(parts[i-1])
                            elif p == "failed":
                                failed = int(parts[i-1])
                            elif p == "skipped":
                                skipped = int(parts[i-1])
                        break
                    elif "passed" in line:
                        parts = line.split()
                        for i, p in enumerate(parts):
                            if p == "passed":
                                passed = int(parts[i-1])
                        break

                total = passed + failed + skipped
                results.append(ModuleResult(
                    module=module, passed=passed, failed=failed,
                    skipped=skipped, total=total, duration=duration,
                    output=stdout[:500] if failed > 0 else "",
                ))

            except subprocess.TimeoutExpired:
                results.append(ModuleResult(
                    module=module, passed=0, failed=0,
                    skipped=0, total=0, duration=time.time() - start,
                    output="[TIMEOUT] Exceeded 300s",
                ))
            except Exception as e:
                results.append(ModuleResult(
                    module=module, passed=0, failed=0,
                    skipped=0, total=0, duration=time.time() - start,
                    output=f"[ERROR] {e}",
                ))

        run_result = RunResult(
            timestamp=timestamp,
            level=level.value,
            total_modules=len(results),
            results=results,
        )
        self._history.append(run_result)
        self._save_log(run_result)
        return run_result

    def _discover_all_modules(self) -> List[str]:
        """自动发现 tests/ 下所有测试文件"""
        modules = []
        base = os.path.dirname(os.path.abspath(__file__))
        tests_dir = os.path.join(base, "..", "tests")
        if not os.path.exists(tests_dir):
            tests_dir = "tests"
        for f in sorted(os.listdir(tests_dir)):
            if (f.endswith("_test.py") or (f.startswith("d") and f.endswith(".py"))
                    and not f.startswith("_")):
                modules.append(os.path.join(tests_dir, f))
        return modules

    def _save_log(self, result: RunResult):
        """保存运行日志"""
        log_file = os.path.join(self.log_dir,
                                f"run_{result.timestamp[:19].replace(':','-')}.json")
        data = {
            "timestamp": result.timestamp,
            "level": result.level,
            "total_modules": result.total_modules,
            "total_passed": result.total_passed,
            "total_failed": result.total_failed,
            "all_passed": result.all_passed,
            "total_time_s": round(result.total_time, 2),
            "modules": [
                {"module": r.module, "passed": r.passed, "failed": r.failed,
                 "skipped": r.skipped, "duration_s": round(r.duration, 2)}
                for r in result.results
            ],
        }
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def summary(self, result: Optional[RunResult] = None) -> str:
        """生成可读摘要"""
        r = result or self._history[-1] if self._history else None
        if not r:
            return "[!!] No runs recorded"

        lines = [
            f"━━━ 全量测试报告 [{r.level}] ━━━",
            f"时间: {r.timestamp[:19]}",
            f"模块数: {r.total_modules}",
            f"结果: {'[OK] All Passed' if r.all_passed else '[!!] Failures Detected'}",
            f"总计: {r.total_passed} passed, {r.total_failed} failed",
            f"总耗时: {r.total_time:.2f}s",
            "",
            "── 模块明细 ──",
        ]
        for mod in r.results:
            status = "[OK]" if mod.failed == 0 else "[!!]"
            lines.append(
                f"  {status} {os.path.basename(mod.module):30s} "
                f"{mod.passed:4d} pass / {mod.failed:2d} fail "
                f"({mod.duration:.2f}s)"
            )

        if r.total_failed > 0:
            lines.extend(["", "── 失败模块 ──"])
            for mod in r.results:
                if mod.failed > 0:
                    lines.append(f"  {mod.module}: {mod.output[:200]}")

        return "\n".join(lines)

    def history(self, n: int = 5) -> str:
        """最近 N 次运行历史"""
        if not self._history:
            return "[!!] No history"
        lines = ["── 运行历史 ──"]
        for r in self._history[-n:]:
            lines.append(
                f"  [{r.level}] {r.timestamp[:19]}  "
                f"{r.total_passed}p/{r.total_failed}f  "
                f"{r.total_modules} modules, {r.total_time:.1f}s"
            )
        return "\n".join(lines)
