# Day 21 — Week 5 综合项目：AI 测试平台 CLI

## 一、今日目标

> 将 Week 4（d16-d20）所有模块整合为一个统一的命令行工具。这是从"散落模块"到"工程化工具链"的最后一步。

- 理解 CLI 入口 `run.py` 的 8 个子命令设计
- 掌握各子命令的参数定义和输出格式
- 学会用统一 CLI 调用 5 个核心模块（d17-d20）
- 理解返回值约定（0=成功，非0=失败）与 CI exit code 兼容

---

## 二、CLI 架构

```
run.py (顶层入口)
├── test        — 运行分层测试（smoke / regression / security / e2e / performance / all）
├── param       — 参数化用例生成（单维度 / 多维度 / CSV）
├── ci          — CI 配置生成 + 门禁检查（generate / check）
├── sanity      — 代码健全性检查（硬编码密钥 / TODO 遗存）
├── coverage    — 覆盖率报告与门禁
├── data        — 测试数据管理（generate / mask / version）
├── tox         — 生成 tox.ini 配置文件
└── health      — 项目健康综合报告
```

使用示例：

```bash
python run.py test --level smoke
python run.py param --name demo --params "temp=0,0.5,1;top_p=0.9,1.0" --output cases.json
python run.py ci generate --output .github/workflows/
python run.py ci check --level smoke --total 10 --passed 10
python run.py sanity --src-dir utils --tests-dir tests
python run.py coverage --threshold 0.85
python run.py data generate --kind prompt --count 50 --output data.jsonl
python run.py data mask --input secrets.txt --output safe.txt
python run.py data version --name injection_dataset
python run.py tox --output tox.ini
python run.py health
```

---

## 三、实现细节

### 3.1 argparse 子命令分发

每个子命令使用 `argparse.ArgumentParser.add_subparsers()` 注册：

```python
import argparse

def build_parser():
    parser = argparse.ArgumentParser(prog="ai-test-runner")
    sub = parser.add_subparsers(dest="command")

    # test 子命令
    p_test = sub.add_parser("test")
    p_test.add_argument("--level", choices=["smoke","regression","security",
                                             "e2e","performance","all"],
                        default="smoke")
    p_test.set_defaults(func=cmd_test)

    # ci 子命令
    p_ci = sub.add_parser("ci")
    p_ci_sub = p_ci.add_subparsers(dest="ci_action")
    p_ci_gen = p_ci_sub.add_parser("generate")
    p_ci_gen.add_argument("--output", default=".")
    p_ci_check = p_ci_sub.add_parser("check")
    p_ci_check.add_argument("--level", required=True)
    p_ci_check.add_argument("--total", type=int, required=True)
    p_ci_check.add_argument("--passed", type=int, required=True)

    return parser
```

### 3.2 分发逻辑（func pattern）

```python
def main(argv: list = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        return args.func(args)
    parser.print_help()
    return 0
```

每个 `cmd_xxx` 函数接收 `args` 命名空间，返回 int：

```python
def cmd_test(args):
    from utils.d17_suite_manager import TestSuiteManager, TestLevel
    mgr = TestSuiteManager()
    cases = mgr.filter(level=TestLevel(args.level))
    print(f"[test] Running {len(cases)} test cases at level {args.level}")
    # 此处调用 pytest 执行
    return 0

def cmd_ci_check(args):
    from utils.d18_ci_config_gen import CIGate, GatingPolicy
    gate = CIGate(policy=GatingPolicy())
    result = gate.check_case(args.level, args.passed, args.total - args.passed, args.total)
    if result.passed:
        print(f"[ci:check] Gate PASSED for {args.level}")
        return 0
    print(f"[ci:check] Gate FAILED for {args.level}")
    return 1
```

### 3.3 返回值约定

| 返回值 | 含义 | CI 效果 |
|--------|------|--------|
| 0 | 成功 | CI step green |
| 1 | 检查失败（门禁、覆盖率等） | CI step red |
| 2+ | 系统/参数错误 | CI step red |

```python
def cmd_sanity(args):
    from utils.d19_toolchain_integration import CodeSanityChecker
    issues = CodeSanityChecker.check_project()
    if issues:
        for i in issues:
            print(f"[!!] {i.type}: {i.message}")
        if args.fail_on_issue:
            return 1
    return 0
```

---

## 四、模块依赖关系

```
run.py
  ├── test      → d17_suite_manager (TestSuiteManager)
  ├── param     → d17_suite_manager (ParametrizedCase)
  ├── ci        → d18_ci_config_gen (CIConfigGenerator, CIGate)
  ├── sanity    → d19_toolchain_integration (CodeSanityChecker)
  ├── coverage  → d19_toolchain_integration (CoverageThresholdChecker)
  ├── data      → d20_data_manager (PromptDataFactory, DataMasker, DataVersionTracker)
  ├── tox       → d19_toolchain_integration (ToxManager)
  └── health    → d19_toolchain_integration (HealthReport)
```

不依赖 d16（browser_checker）因为它需要 Playwright 浏览器环境，不适合在纯 CLI 中使用。

---

## 五、Week 5 完整产出汇总

| 天 | 主题 | 核心文件 | 测试 |
|---|------|---------|------|
| d16 | Playwright 浏览器自动化 | `browser_checker.py` | 28/28 PASS |
| d17 | pytest 参数化 + 分层管理 | `suite_manager.py` | 37/37 PASS |
| d18 | CI/CD 集成 | `ci_config_gen.py` | 22/22 PASS |
| d19 | 开源工具整合 | `toolchain_integration.py` | 29/29 PASS |
| d20 | 测试数据管理 | `data_manager.py` | 42/42 PASS |
| d21 | 综合项目 CLI | `run.py` | 28/28 PASS |

### 汇总统计

```
项目根目录
├── utils/       → 15 个工具模块
├── tests/       → 21 个测试文件 (557 测试用例)
├── docs/        → day1~day21 学习文档
├── run.py       → CLI 入口 (16304 字节)
├── requirements.txt
├── pytest.ini
└── tox.ini
```

---

## 六、测试要点

### 6.1 test 子命令

```
test --level smoke       → 返回 0
test --level regression  → 返回 0
test --level security    → 返回 0
test --level all         → 返回 0
test --level invalid     → argpase raise SystemExit
```

### 6.2 param 子命令

```
param --name demo --params "temp=0,1"                → 4 组合 (笛卡尔积)
param --name demo --params "temp=0,1;top_p=0.5,1.0"  → 4 组合 (多维)
param --name demo --csv nonexistent.csv               → 返回 1
param --name demo --output out.json                   → 写入 JSON
```

### 6.3 ci 子命令

```
ci generate --output dir    → 写入 YAML 文件
ci check --level smoke ...  → ALL_PASS: 10/10=0, 9/10=1
ci check --level regression → THRESHOLD: 19/20=0, 16/20=1
```

### 6.4 data 子命令

```
data generate --kind prompt    → 打印 prompt
data generate --kind response  → 打印 response
data mask --input file.txt     → 打印脱敏结果
data mask --input f.txt --output f.masked → 写入文件
data mask (no input)            → 返回 1
data version --name xxx         → 返回 0
```

---

## 七、面试话术

> "我设计了一个分层式的 AI 测试平台。底层是 15 个工具模块，每个专注于一个测试维度——从 Prompt Injection 检测到并发压测、从数据脱敏到 CI 门禁。上层是统一的 CLI 入口 run.py，8 个子命令覆盖了所有测试需求。这种架构的好处是：底层模块可以独立演进和单元测试，上层不关心内部实现细节。每个命令返回 int（0=成功，非0=失败），原生兼容 GitHub Actions exit code 判断。"

> "d21 测试了所有子命令的参数解析和异常处理——无效参数返回 1、文件不存在返回 1、门禁不通过返回 1。28 个测试覆盖了各个命令的 happy path 和 sad path，确保 CLI 层不会掩盖失败。"

---

## 八、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `run.py` | CLI 入口 | [OK] |
| `tests/d21_test_run.py` | 28 个 CLI 测试 | [OK] 28/28 PASS |
| `day21_study.md` | 本文档 | [OK] 已升级 |
