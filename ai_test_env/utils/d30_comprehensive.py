"""
Day 30 — 综合端到端测试

功能：
    一键运行：
    1. 全量测试（d1-d29 所有模块）
    2. 结果聚合 + 报告生成
    3. 仪表盘展示
    4. 整体状态汇总

    相当于"系统的系统测试"——验证所有模块能正常联动。

面试话术：
    "d30 是整个平台的最终验证：
    从 API 客户端→质量评估→安全测试→性能压测→
    全量运行器→报告聚合→仪表盘，完整闭环。
    每次运行后输出一份健康状态报告。"
"""

import sys
import os
import time
from datetime import datetime

# 确保项目根路径在 sys.path
_project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _project_root)


def check_imports() -> dict:
    """检查所有模块能否正常导入"""
    status = {}
    modules = [
        ("d1", "utils.d1_api_client", "AIClient"),
        ("d3", "utils.d3_error_classifier", "ErrorClassifier"),
        ("d4", "utils.d4_response_validator", "ResponseValidator"),
        ("d5", "utils.d5_key_manager", "KeyManager"),
        ("d6", "utils.d6_quality_checker", "QualityChecker"),
        ("d7", "utils.d7_consistency_checker", "ConsistencyChecker"),
        ("d8", "utils.d8_truncation_analyzer", "TruncationAnalyzer"),
        ("d8b", "utils.d8_tc_tester", "TestCoverageTester"),
        ("d8c", "utils.d8c_format_validator", "FormatValidator"),
        ("d8d", "utils.d8d_style_checker", "StyleChecker"),
        ("d8e", "utils.d8e_multilingual_tester", "MultilingualTester"),
        ("d8f", "utils.d8f_timeliness_tester", "TimelinessTester"),
        ("d9", "utils.d9_llm_judge", "LLMJudge"),
        ("d10", "utils.d10_schema_validator", "SchemaValidator"),
        ("d10b", "utils.d10_pipeline_assessment", "PipelineAssessor"),
        ("d11", "utils.d11_conversation_tester", "ConversationTester"),
        ("d12", "utils.d12_injection_detector", "InjectionDetector"),
        ("d12b", "utils.d12_prompt_injection_tester", "PromptInjectionTester"),
        ("d13", "utils.d13_robustness_tester", "RobustnessTester"),
        ("d14", "utils.d14_regression_tester", "RegressionTester"),
        ("d15", "utils.d15_e2e_tester", "E2ETester"),
        ("d16", "utils.d16_browser_checker", "BrowserChecker"),
        ("d17", "utils.d17_suite_manager", "TestSuiteManager"),
        ("d18", "utils.d18_ci_config_gen", "CIConfigGenerator"),
        ("d19", "utils.d19_toolchain_integration", "ToolchainIntegrator"),
        ("d20", "utils.d20_data_manager", "DataManager"),
        ("d21", "run", "main"),
        ("d22", "utils.d22_load_tester", "LoadTester"),
        ("d23", "utils.d23_retry_engine", "RetryEngine"),
        ("d24", "utils.d24_circuit_breaker", "CircuitBreaker"),
        ("d25", "utils.d25_error_system", "ErrorClassifier"),
        ("d26", "utils.d26_token_auditor", "TokenAuditor"),
        ("d27", "utils.d27_full_runner", "FullTestRunner"),
        ("d28", "utils.d28_report_aggregator", "ReportAggregator"),
        ("d29", "utils.d29_dashboard", "DashboardBuilder"),
    ]
    for day, mod_path, attr in modules:
        try:
            mod = __import__(mod_path, fromlist=[attr])
            if hasattr(mod, attr):
                status[day] = {"ok": True, "msg": attr}
            else:
                status[day] = {"ok": False, "msg": f"{attr} not found in {mod_path}"}
        except Exception as e:
            status[day] = {"ok": False, "msg": str(e)}
    return status


def run_all_tests() -> dict:
    """调用 pytest 运行所有测试模块"""
    import subprocess

    test_dir = os.path.join(_project_root, "tests")
    test_files = sorted(f for f in os.listdir(test_dir)
                        if f.endswith((".py")) and not f.startswith("_"))

    results = {}
    total_pass = total_fail = 0
    total_modules = len(test_files)

    print(f"发现 {total_modules} 个测试文件，开始运行...\n")

    for tf in test_files:
        fpath = os.path.join(test_dir, tf)
        start = time.time()
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", fpath, "-q", "--tb=line"],
            capture_output=True, text=True, timeout=300,
            cwd=_project_root,
        )
        duration = time.time() - start
        stdout = proc.stdout

        # 解析结果行
        passed = failed = skipped = 0
        for line in stdout.split("\n"):
            if "passed" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "passed":
                        passed = int(parts[i-1])
                    elif p == "failed":
                        failed = int(parts[i-1])
                    elif p == "skipped":
                        skipped = int(parts[i-1])

        total_pass += passed
        total_fail += failed

        results[tf] = {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration": round(duration, 2),
            "ok": failed == 0,
        }

        emoji = "[OK]" if failed == 0 else "[!!]"
        print(f"  {emoji} {tf:35s} {passed:4d}p {failed:2d}f "
              f"{skipped:2d}s ({duration:.2f}s)")

    summary = {
        "total_modules": total_modules,
        "total_passed": total_pass,
        "total_failed": total_fail,
        "all_passed": total_fail == 0,
        "total_time": round(sum(r["duration"] for r in results.values()), 2),
        "results": results,
    }
    return summary


def main():
    print("=" * 60)
    print("  AI 测试平台 — 综合端到端验证")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # === 第 1 步：导入检查 ===
    print("\n[1/3] 模块导入检查")
    print("-" * 40)
    import_status = check_imports()
    import_ok = sum(1 for v in import_status.values() if v["ok"])
    import_fail = sum(1 for v in import_status.values() if not v["ok"])

    for day, s in sorted(import_status.items()):
        emoji = "[OK]" if s["ok"] else "[!!]"
        print(f"  {emoji} d{day}: {s['msg']}")

    print(f"\n  导入: {import_ok}/{len(import_status)} OK, "
          f"{import_fail} failed")

    # === 第 2 步：运行全部测试 ===
    print(f"\n[2/3] 全量测试 ({datetime.now().strftime('%H:%M:%S')})")
    print("-" * 40)
    test_summary = run_all_tests()

    print(f"\n  全部: {test_summary['total_passed']} passed, "
          f"{test_summary['total_failed']} failed, "
          f"{test_summary['total_modules']} modules, "
          f"{test_summary['total_time']:.2f}s")

    # === 第 3 步：仪表盘 ===
    print(f"\n[3/3] 系统健康仪表盘 ({datetime.now().strftime('%H:%M:%S')})")
    print("-" * 40)

    from utils.d29_dashboard import DashboardBuilder

    builder = DashboardBuilder()
    pass_rate = (test_summary["total_passed"] /
                 max(test_summary["total_passed"] + test_summary["total_failed"], 1))
    builder.add_pass_rate(pass_rate)
    builder.add_module_stability(
        total=test_summary["total_modules"],
        unstable=sum(1 for r in test_summary["results"].values() if not r["ok"]),
    )
    builder.add_pass_rate_check(pass_rate)
    builder.add_runs_count(1)
    builder.add_total_time(test_summary["total_time"])

    # 导入检查是一个自定义检查
    builder.add_custom_check(
        "模块导入完整",
        passed=(import_fail == 0),
        pass_message=f"全部 {import_ok}/{len(import_status)} 模块导入成功",
        fail_message=f"{import_fail} 个模块导入失败 (OK={import_ok}/{len(import_status)})",
    )

    report = builder.build()
    print(report.display())

    # === 最终裁定 ===
    print("=" * 60)
    if test_summary["all_passed"] and import_fail == 0:
        print("  最终状态: ✅ ALL PASS — Week 6 实战项目通过")
    else:
        print("  最终状态: ❌ FAILURES — 请查看上方失败详情")
    print("=" * 60)

    return 0 if test_summary["all_passed"] and import_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
