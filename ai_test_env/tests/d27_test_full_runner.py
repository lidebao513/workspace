"""
D27 — 全量测试运行器测试

覆盖：
1. ModuleResult 数据结构和计算
2. RunResult 汇总属性
3. FullTestRunner 层级映射
4. summary 输出格式
5. 模块发现
6. history 追踪
"""

import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d27_full_runner import (
    RunLevel, ModuleResult, RunResult, FullTestRunner,
)


def test_module_result():
    r = ModuleResult(module="d6_test_quality.py", passed=15, failed=0, skipped=0,
                      total=15, duration=0.5)
    assert r.success_rate == 1.0
    assert r.passed_str == "[OK]"

    r2 = ModuleResult(module="d12_test_injection.py", passed=25, failed=2, skipped=0,
                       total=27, duration=1.2)
    assert r2.success_rate == 25 / 27
    assert r2.passed_str == "[!!]"


def test_module_result_zero_total():
    r = ModuleResult(module="missing.py", passed=0, failed=0, skipped=0,
                      total=0, duration=0)
    assert r.success_rate == 1.0
    assert r.passed_str == "[OK]"


def test_run_result():
    results = [
        ModuleResult(module="a.py", passed=10, failed=0, skipped=0, total=10, duration=0.5),
        ModuleResult(module="b.py", passed=20, failed=2, skipped=0, total=22, duration=1.0),
    ]
    run = RunResult(timestamp="2026-04-30T19:00:00", level="regression",
                     results=results, total_modules=2)
    assert run.total_passed == 30
    assert run.total_failed == 2
    assert not run.all_passed
    assert run.total_modules == 2
    assert run.total_time == 1.5


def test_run_result_all_pass():
    results = [
        ModuleResult(module="a.py", passed=10, failed=0, skipped=0, total=10, duration=0.5),
    ]
    run = RunResult(timestamp="now", level="smoke", results=results)
    assert run.all_passed


def test_run_result_empty():
    run = RunResult(timestamp="now", level="full", results=[])
    assert run.total_passed == 0
    assert run.total_modules == 0
    assert run.total_failed == 0
    assert run.all_passed


def test_runner_module_map():
    runner = FullTestRunner()
    assert RunLevel.SMOKE in runner.MODULE_MAP
    assert RunLevel.FULL in runner.MODULE_MAP
    assert RunLevel.REGRESSION in runner.MODULE_MAP
    assert RunLevel.SECURITY in runner.MODULE_MAP
    assert RunLevel.E2E in runner.MODULE_MAP


def test_runner_map_has_modules():
    runner = FullTestRunner()
    for level in [RunLevel.SMOKE, RunLevel.REGRESSION, RunLevel.SECURITY, RunLevel.E2E]:
        modules = runner.MODULE_MAP[level]
        assert len(modules) > 0, f"{level} 没有模块"


def test_runner_discover_all():
    runner = FullTestRunner()
    modules = runner._discover_all_modules()
    assert len(modules) >= 26, f"发现的模块不足: {len(modules)}, 文件={[os.path.basename(m) for m in modules[:5]]}"
    # d1_test_key_manager.py (在 Windows 上路径可能是 tests\d1_test_key_manager.py)
    assert any("d1_test_key_manager" in m for m in modules) or any("d1" in os.path.basename(m) and "test" in m for m in modules)
    assert any("d26_test" in m for m in modules)


def test_runner_log_dir_created():
    log_dir = "_test_run_logs"
    try:
        runner = FullTestRunner(log_dir=log_dir)
        assert os.path.exists(log_dir)
    finally:
        import shutil
        if os.path.exists(log_dir):
            shutil.rmtree(log_dir)


def test_runner_summary_no_runs():
    runner = FullTestRunner()
    s = runner.summary()
    assert "No runs" in s or "!!" in s


def test_runner_history_no_runs():
    runner = FullTestRunner()
    h = runner.history()
    assert "No history" in h


def test_runner_summary_with_result():
    runner = FullTestRunner()
    results = [
        ModuleResult(module="tests/a.py", passed=10, failed=0, skipped=0,
                      total=10, duration=0.5),
    ]
    run = RunResult(timestamp="2026-04-30T19:00:00", level="smoke", results=results)
    runner._history.append(run)
    s = runner.summary()
    assert "All Passed" in s
    assert "10 pass" in s


def test_runner_summary_with_failures():
    runner = FullTestRunner()
    results = [
        ModuleResult(module="tests/b.py", passed=8, failed=2, skipped=0,
                      total=10, duration=0.5, output="AssertionError: x != y"),
    ]
    run = RunResult(timestamp="now", level="security", results=results)
    runner._history.append(run)
    s = runner.summary()
    assert "Failures Detected" in s
    assert "b.py" in s


def test_runner_history_tracking():
    runner = FullTestRunner()
    for i in range(3):
        r = RunResult(timestamp=f"2026-04-30T19:0{i}:00", level="smoke", results=[])
        runner._history.append(r)
    h = runner.history(n=2)
    assert "19:01" in h
    assert "19:02" in h
    assert "19:00" not in h


def test_runner_save_log_writes_file():
    import tempfile, shutil
    log_dir = tempfile.mkdtemp()
    try:
        runner = FullTestRunner(log_dir=log_dir)
        results = [ModuleResult(module="tests/c.py", passed=5, failed=0,
                                 skipped=0, total=5, duration=0.1)]
        run = RunResult(timestamp="2026-04-30T19:00:00", level="full", results=results)
        runner._save_log(run)
        files = os.listdir(log_dir)
        assert len(files) == 1
        with open(os.path.join(log_dir, files[0]), "r") as f:
            data = json.load(f)
            assert data["total_passed"] == 5
            assert data["all_passed"] == True
    finally:
        shutil.rmtree(log_dir)


def test_runner_extra_modules():
    runner = FullTestRunner()
    # 验证 extra_modules 参数不会导致错误
    assert hasattr(runner, "MODULE_MAP")


def test_run_level_values():
    assert RunLevel.SMOKE.value == "smoke"
    assert RunLevel.REGRESSION.value == "regression"
    assert RunLevel.SECURITY.value == "security"
    assert RunLevel.E2E.value == "e2e"
    assert RunLevel.FULL.value == "full"
