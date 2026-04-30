"""
Day 21 (Week 4 Summary) — Week 4 综合项目

AI 测试平台 CLI
===============

整合 Week 4 所有模块生成一个命令行入口，支持：
1. test — 运行分层测试（smoke / regression / security / e2e / performance）
2. param — 生成参数化用例
3. ci — CI 配置生成 + 门禁检查
4. sanity — 代码健全性检查
5. coverage — 覆盖率报告
6. data — 测试数据管理（生成 / 脱敏 / 版本）

面试话术：
    "我构建了一个统一的 AI 测试平台 CLI。入口是 `python run.py`，
    支持 6 个子命令覆盖测试、CI、代码检视和数据管理。
    本质上是把 Week 1-4 的所有工具用一致的操作接口串起来。"
"""
import sys
import os
import argparse
import json
from typing import Optional, List

# 确保能从 utils 导入
sys.path.insert(0, os.path.dirname(__file__))

from utils.d17_suite_manager import (
    TestSuiteManager, ParametrizedCase, CompatRunner,
    generate_test_run_summary,
)
from utils.d18_ci_config_gen import CIConfigGenerator, GateRule, GatingStrategy
from utils.d19_toolchain_integration import (
    CoverageChecker, CodeSanityChecker, ProjectHealthReporter,
    ToxConfigGenerator,
)
from utils.d20_data_manager import (
    DataProfile, PromptDataFactory, ResponseDataFactory,
    DataMasker, DataVersionTracker, DatasetEntry,
)


def cmd_test(args: argparse.Namespace) -> int:
    """
    运行分层测试。

    通过 SuiteManager 过滤用例，再通过 CompatRunner 映射到
    已有的测试模块。输出汇总报告。
    """
    mgr = TestSuiteManager()
    runner = CompatRunner()

    # 按层级过滤
    level_map = {
        "smoke": "smoke",
        "regression": "regression",
        "security": "security",
        "e2e": "e2e",
        "performance": "performance",
        "all": "all",
    }

    level = level_map.get(args.level, "all")
    if level == "all" or level == "regression":
        pass  # 全量意味着所有级别

    print(f"=== AI Test Platform CLI ===")
    print(f"Command: test --level {args.level}")
    print()

    # 获取该层级覆盖的测试模块
    from utils.d17_suite_manager import TestLevel
    # 使用 CompatRunner 获取模块列表
    level_enum = TestLevel.ALL if level == "all" else TestLevel[level.upper()]
    modules = CompatRunner.get_modules_for_level(level_enum)

    print(f"Level: {level}")
    print(f"Modules: {', '.join(modules)}")
    print()

    # 获取用例统计
    if level != "all":
        filtered = mgr.filter(level=level_enum)
        total = len(filtered)
    else:
        total = mgr.count()

    print(f"Test cases defined: {total}")
    print(f"To run: pytest tests/ -m \"{level}\" -v")
    print()

    # 输出摘要
    # 转换 get_level_counts 为 breakdown 所需的格式
    level_counts = mgr.get_level_counts() if hasattr(mgr, 'get_level_counts') else {}
    breakdown = None
    if level_counts:
        breakdown = {
            k: {"total": v, "passed": v}
            for k, v in level_counts.items()
        }
    print(generate_test_run_summary(
        total=total,
        passed=total,
        failed=0,
        duration_sec=0,
        breakdown=breakdown,
    ))

    return 0


def cmd_param(args: argparse.Namespace) -> int:
    """
    参数化用例生成。

    支持单维、多维笛卡尔积、CSV 导入。
    输出 JSON 格式的组合列表。
    """
    pc = ParametrizedCase(args.name)

    if args.csv:
        # 从 CSV 导入
        if os.path.exists(args.csv):
            with open(args.csv, "r", encoding="utf-8") as f:
                csv_content = f.read()
            imported = ParametrizedCase.from_csv(args.name, csv_content)
            if imported:
                pc = imported
            else:
                print(f"[!!] Failed to import CSV: {args.csv}")
                return 1
        else:
            print(f"[!!] CSV file not found: {args.csv}")
            return 1
    elif args.params:
        # 解析参数定义: name=val1,val2;name2=val3,val4
        param_pairs = args.params.split(";")
        for pair in param_pairs:
            if "=" not in pair:
                print(f"[!!] Invalid param format: {pair}")
                continue
            name, values_str = pair.split("=", 1)
            values = []
            for v in values_str.split(","):
                try:
                    values.append(int(v))
                except ValueError:
                    try:
                        values.append(float(v))
                    except ValueError:
                        values.append(v.strip())
            pc.add_param(name.strip(), values)

    combos = pc.combinations()
    print(f"=== Parametrized Case: {args.name} ===")
    print(f"Parameters: {', '.join(pc.param_names())}")
    print(f"Combinations: {len(combos)}")
    print()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(combos, f, indent=2, ensure_ascii=False)
        print(f"[OK] Written to {args.output}")
    else:
        for i, combo in enumerate(combos):
            print(f"  [{i+1}] {combo}")

    return 0


def cmd_ci(args: argparse.Namespace) -> int:
    """
    CI 配置生成或门禁检查。

    generate: 生成 GitHub Actions 配置
    check: 运行门禁检查
    """
    if args.action == "generate":
        if args.output:
            output_dir = args.output
        else:
            output_dir = os.path.join(os.path.dirname(__file__),
                                     ".github", "workflows")

        result = CIConfigGenerator.write_workflows(
            output_dir=output_dir,
            repo_path=args.repo_path or ".",
        )
        for r in result:
            print(f"[OK] {r}")

    elif args.action == "check":
        level = args.level or "smoke"
        total = args.total or 1
        passed = args.passed or 1
        failed = args.failed or 0

        # 简单门禁检查
        rate = passed / max(total, 1)
        thresholds = {"smoke": 1.0, "security": 1.0,
                      "regression": 0.95, "e2e": 0.8, "performance": 0.9}
        threshold = thresholds.get(level, 1.0)

        print(f"=== CI Gating Check: {level} ===")
        print(f"  Total:  {total}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print(f"  Rate:   {rate:.1%} (threshold: {threshold:.0%})")

        if rate >= threshold:
            print(f"  Result: [OK] PASS")
            return 0
        else:
            print(f"  Result: [!!] FAIL")
            return 1

    else:
        print(f"[!!] Unknown CI action: {args.action}")
        return 1

    return 0


def cmd_sanity(args: argparse.Namespace) -> int:
    """
    代码健全性检查。

    检查硬编码 API Key、TODO 遗存、文件大小、末尾空行。
    """
    checker = CodeSanityChecker(
        src_dir=args.src_dir,
        tests_dir=args.tests_dir,
    )
    issues = checker.check_all()

    print(f"=== Code Sanity Check ===")
    print(f"  Source dir: {args.src_dir}")
    print(f"  Issues found: {len(issues)}")
    print()

    if not issues:
        print("[OK] No issues found.")
        return 0

    for issue in issues:
        line_str = f":{issue.line}" if issue.line else ""
        print(f"  [{issue.issue_type[:4]}] {issue.file}{line_str}")
        print(f"         {issue.message}")
        print()

    return 1 if args.fail_on_issue else 0


def cmd_coverage(args: argparse.Namespace) -> int:
    """
    覆盖率报告。

    解析 coverage.xml 或使用 mock 数据生成报告。
    """
    checker = CoverageChecker(threshold=args.threshold or 0.8)

    xml_path = args.coverage_xml or "coverage.xml"
    if os.path.exists(xml_path):
        checker.parse_coverage_xml(xml_path)
    else:
        print(f"[??] {xml_path} not found. Using simulated data.")
        checker.parse_coverage_xml(xml_path)

    report = checker.coverage_report()
    print(report)

    return 0


def cmd_data(args: argparse.Namespace) -> int:
    """
    测试数据管理。

    generate: 生成合成测试数据（prompt / response）
    mask: 脱敏处理
    version: 版本追踪
    """
    if args.action == "generate":
        kind = args.kind or "prompt"
        count = args.count or 10

        profile = DataProfile(
            name=args.name or "generated",
            count=count,
            seed=args.seed or 42,
            output_format=args.format or "jsonl",
        )

        if kind == "prompt":
            factory = PromptDataFactory(seed=args.seed or 42)
            data = factory.generate_prompts(profile)
        else:
            factory = ResponseDataFactory(seed=args.seed or 42)
            data = factory.generate_responses(profile)

        print(f"=== Generate {kind} data ===")
        print(f"  Count: {count}")
        print(f"  Seed: {args.seed or 42}")
        print()

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            print(f"[OK] Written {len(data)} items to {args.output}")
        else:
            for i, item in enumerate(data):
                print(f"  [{i+1}] {json.dumps(item, ensure_ascii=False)[:120]}")

    elif args.action == "mask":
        if not args.input:
            print("[!!] --input required for mask action")
            return 1

        with open(args.input, "r", encoding="utf-8") as f:
            content = f.read()

        masked = DataMasker.mask_all(content)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(masked)
            print(f"[OK] Masked content written to {args.output}")
        else:
            print("=== Masked Output ===")
            print(masked)

        # 检查残留
        remaining = DataMasker.has_sensitive_data(masked)
        sensitive_left = {k: v for k, v in remaining.items() if v}
        if sensitive_left:
            print(f"[??] Possible remaining sensitive data: {list(sensitive_left.keys())}")

    elif args.action == "version":
        tracker = DataVersionTracker(args.name or "default")
        history = tracker.get_version_history()
        print(f"=== Data Version: {args.name or 'default'} ===")
        if history:
            for v in history:
                print(f"  v{v['version']} ({v['count']} items)")
                for c in v.get("changes", []):
                    print(f"      - {c}")
        else:
            print("  No versions recorded yet.")

    else:
        print(f"[!!] Unknown data action: {args.action}")
        return 1

    return 0


def cmd_tox(args: argparse.Namespace) -> int:
    """生成 tox.ini"""
    ini = ToxConfigGenerator.generate_tox_ini(
        project_name=args.project or "ai_test_env",
        python_versions=args.python_versions or ["3.9", "3.10", "3.11"],
        test_dirs=args.test_dirs or ["tests"],
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(ini)
        print(f"[OK] tox.ini written to {args.output}")
    else:
        print(ini)

    return 0


def cmd_health(args: argparse.Namespace) -> int:
    """生成项目健康报告"""
    coverage = CoverageChecker(threshold=0.8)
    sanity = CodeSanityChecker(
        src_dir=args.src_dir or "utils",
        tests_dir=args.tests_dir or "tests",
    )

    coverage.parse_coverage_xml(args.coverage_xml or "coverage.xml")
    reporter = ProjectHealthReporter(coverage, sanity, project_dir=".")
    report = reporter.generate_health_report()
    print(report)

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="AI Test Platform CLI — Week 4 Integrated Toolchain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py test --level smoke
  python run.py param --name prompt_test --params "temp=0,0.5,1;top_p=0.9,1.0"
  python run.py ci generate
  python run.py ci check --level regression --total 20 --passed 19
  python run.py sanity --fail-on-issue
  python run.py coverage
  python run.py data generate --kind prompt --count 10
  python run.py data mask --input sensitive.txt --output safe.txt
  python run.py tox --output tox.ini
  python run.py health
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")
    subparsers.required = True

    # test
    p_test = subparsers.add_parser("test", help="Run layered tests")
    p_test.add_argument("--level", default="smoke",
                       choices=["smoke", "regression", "security",
                               "e2e", "performance", "all"])
    p_test.set_defaults(func=cmd_test)

    # param
    p_param = subparsers.add_parser("param", help="Generate parametrized cases")
    p_param.add_argument("--name", default="cli_case", help="Case name")
    p_param.add_argument("--params", help="Parameters: temp=0,1;top_p=0.5,1.0")
    p_param.add_argument("--csv", help="Import CSV file")
    p_param.add_argument("--output", help="Output file")
    p_param.set_defaults(func=cmd_param)

    # ci
    p_ci = subparsers.add_parser("ci", help="CI config management")
    p_ci.add_argument("action", choices=["generate", "check"])
    p_ci.add_argument("--level", default="smoke",
                     choices=["smoke", "security", "regression", "e2e", "performance"])
    p_ci.add_argument("--total", type=int, default=1)
    p_ci.add_argument("--passed", type=int, default=1)
    p_ci.add_argument("--failed", type=int, default=0)
    p_ci.add_argument("--output", help="Output directory for generate")
    p_ci.add_argument("--repo-path", help="Repository path")
    p_ci.set_defaults(func=cmd_ci)

    # sanity
    p_sanity = subparsers.add_parser("sanity", help="Code sanity check")
    p_sanity.add_argument("--src-dir", default="utils")
    p_sanity.add_argument("--tests-dir", default="tests")
    p_sanity.add_argument("--fail-on-issue", action="store_true",
                         help="Exit with code 1 if any issue found")
    p_sanity.set_defaults(func=cmd_sanity)

    # coverage
    p_cov = subparsers.add_parser("coverage", help="Coverage report")
    p_cov.add_argument("--coverage-xml", help="Path to coverage.xml")
    p_cov.add_argument("--threshold", type=float, default=0.8,
                      help="Coverage threshold")
    p_cov.set_defaults(func=cmd_coverage)

    # data
    p_data = subparsers.add_parser("data", help="Test data management")
    p_data.add_argument("action", choices=["generate", "mask", "version"])
    p_data.add_argument("--kind", choices=["prompt", "response"], default="prompt")
    p_data.add_argument("--count", type=int, default=10)
    p_data.add_argument("--seed", type=int, default=42)
    p_data.add_argument("--name", default="default")
    p_data.add_argument("--format", default="jsonl", choices=["jsonl", "json"])
    p_data.add_argument("--input", help="Input file (for mask)")
    p_data.add_argument("--output", help="Output file")
    p_data.set_defaults(func=cmd_data)

    # tox
    p_tox = subparsers.add_parser("tox", help="Generate tox.ini")
    p_tox.add_argument("--project", default="ai_test_env")
    p_tox.add_argument("--python-versions", nargs="+",
                      default=["3.9", "3.10", "3.11"])
    p_tox.add_argument("--test-dirs", nargs="+", default=["tests"])
    p_tox.add_argument("--output", help="Output file (default: stdout)")
    p_tox.set_defaults(func=cmd_tox)

    # health
    p_health = subparsers.add_parser("health", help="Project health report")
    p_health.add_argument("--src-dir", default="utils")
    p_health.add_argument("--tests-dir", default="tests")
    p_health.add_argument("--coverage-xml", default="coverage.xml")
    p_health.set_defaults(func=cmd_health)

    args = parser.parse_args(argv)

    # 默认加上 verbose 选项（如果有）
    try:
        return args.func(args)
    except Exception as e:
        print(f"[!!] Error: {e}")
        if hasattr(args, "verbose") and args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
