# Day 21 — Week 5 综合项目：AI 测试平台 CLI

## 学习目标

1. **理解 CLI 架构**：掌握 8 个子命令设计和顶层入口设计
2. **掌握 argparse 子命令**：熟练使用 `add_subparsers()` 实现命令分发
3. **理解返回值约定**：掌握 exit code 与 CI 集成的兼容设计
4. **整合核心模块**：学会用统一 CLI 调用 d17-d20 的核心模块
5. **构建工程化工具链**：理解从"散落模块"到"工程化工具链"的完整路径

---

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

---

## 面试题

### 面试题 1：如何设计一个工程化的 CLI 工具？

**答案：**

设计工程化的 CLI 工具需要考虑架构分层、命令设计和错误处理：

**1. 分层架构**
```
CLI 入口 (run.py)
├── 命令解析层 (argparse)
├── 命令分发层 (func pattern)
└── 业务逻辑层 (各模块调用)
```

**2. 子命令设计**
- 按功能模块划分（如 test/ci/sanity/coverage/data）
- 使用 `add_subparsers()` 实现嵌套子命令
- 统一参数风格（如 `--level`, `--output`）

**3. 返回值约定**
- 0 = 成功
- 非 0 = 失败（1=参数错误，2=文件不存在，3=门禁失败）
- 兼容 GitHub Actions exit code

**4. 错误处理**
```python
try:
    args.func(args)
except FileNotFoundError:
    print("Error: File not found", file=sys.stderr)
    sys.exit(2)
except ValueError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
```

### 面试题 2：如何保证 CLI 工具的可测试性？

**答案：**

CLI 工具的可测试性设计：

**1. func pattern 分离**
```python
def cmd_test(args):
    # 业务逻辑
    return 0

# 测试时可以单独调用
assert cmd_test(parse_args(["--level", "smoke"])) == 0
```

**2. 参数解析与执行分离**
```python
parser = argparse.ArgumentParser()
# 配置解析器

# 测试时可以直接调用 business logic
result = do_something(param)
assert result == expected
```

**3. Mock 外部依赖**
```python
def cmd_test(args):
    if args.mock:
        # 使用 mock 数据
        return mock_handler()
    # 真实执行
    return real_handler()
```

**4. 集成测试覆盖**
- Happy path：正常参数
- Sad path：无效参数、文件不存在、权限错误
- 边界条件：空参数、超长参数

---

## 代码示例

### AI 测试平台 CLI 实现

```python
import argparse
import sys
from typing import Callable, Dict, Any

class AICLIRunner:
    """AI 测试平台 CLI 运行器"""
    
    def __init__(self):
        self.commands: Dict[str, Callable] = {}
        self.parser = self._build_parser()
    
    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="ai-test-runner",
            description="AI Testing Platform CLI"
        )
        
        sub = parser.add_subparsers(dest="command", help="Available commands")
        
        # test 子命令
        self._add_test_command(sub)
        
        # ci 子命令
        self._add_ci_command(sub)
        
        # sanity 子命令
        self._add_sanity_command(sub)
        
        # coverage 子命令
        self._add_coverage_command(sub)
        
        # data 子命令
        self._add_data_command(sub)
        
        return parser
    
    def _add_test_command(self, sub):
        p_test = sub.add_parser("test", help="Run tests by level")
        p_test.add_argument(
            "--level",
            choices=["smoke", "regression", "security", "e2e", "performance", "all"],
            default="smoke",
            help="Test level to run"
        )
        p_test.add_argument("--verbose", "-v", action="store_true")
    
    def _add_ci_command(self, sub):
        p_ci = sub.add_parser("ci", help="CI configuration and gating")
        ci_sub = p_ci.add_subparsers(dest="ci_action")
        
        p_gen = ci_sub.add_parser("generate", help="Generate CI config")
        p_gen.add_argument("--output", default=".", help="Output directory")
        
        p_check = ci_sub.add_parser("check", help="Run CI gate check")
        p_check.add_argument("--level", required=True)
        p_check.add_argument("--total", type=int, required=True)
        p_check.add_argument("--passed", type=int, required=True)
    
    def _add_sanity_command(self, sub):
        p_sanity = sub.add_parser("sanity", help="Run code sanity checks")
        p_sanity.add_argument("--src-dir", default="utils")
        p_sanity.add_argument("--tests-dir", default="tests")
    
    def _add_coverage_command(self, sub):
        p_cov = sub.add_parser("coverage", help="Coverage reporting")
        p_cov.add_argument("--threshold", type=float, default=0.85)
    
    def _add_data_command(self, sub):
        p_data = sub.add_parser("data", help="Test data management")
        data_sub = p_data.add_subparsers(dest="data_action")
        
        p_gen = data_sub.add_parser("generate", help="Generate test data")
        p_gen.add_argument("--kind", default="prompt")
        p_gen.add_argument("--count", type=int, default=50)
        p_gen.add_argument("--output", default="data.jsonl")
        
        p_mask = data_sub.add_parser("mask", help="Mask sensitive data")
        p_mask.add_argument("--input", required=True)
        p_mask.add_argument("--output", default="safe.txt")
        
        p_ver = data_sub.add_parser("version", help="Show data version")
        p_ver.add_argument("--name", required=True)
    
    def run(self, args=None) -> int:
        args = self.parser.parse_args(args)
        
        if not args.command:
            self.parser.print_help()
            return 0
        
        try:
            return self._dispatch(args)
        except FileNotFoundError as e:
            print(f"Error: File not found - {e}", file=sys.stderr)
            return 2
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    
    def _dispatch(self, args) -> int:
        if args.command == "test":
            return self._cmd_test(args)
        elif args.command == "ci":
            return self._cmd_ci(args)
        elif args.command == "sanity":
            return self._cmd_sanity(args)
        elif args.command == "coverage":
            return self._cmd_coverage(args)
        elif args.command == "data":
            return self._cmd_data(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1
    
    def _cmd_test(self, args) -> int:
        levels = {
            "smoke": "冒烟测试",
            "regression": "回归测试",
            "security": "安全测试",
            "e2e": "端到端测试",
            "performance": "性能测试",
            "all": "全量测试"
        }
        print(f"Running {levels.get(args.level, args.level)}...")
        return 0
    
    def _cmd_ci(self, args) -> int:
        if args.ci_action == "generate":
            print(f"Generating CI config to {args.output}...")
            return 0
        elif args.ci_action == "check":
            total = args.total
            passed = args.passed
            rate = passed / total if total > 0 else 0
            print(f"Gate check: {passed}/{total} ({rate:.0%})")
            return 0 if rate >= 0.85 else 1
        return 0
    
    def _cmd_sanity(self, args) -> int:
        print(f"Running sanity check on {args.src_dir}...")
        return 0
    
    def _cmd_coverage(self, args) -> int:
        print(f"Coverage threshold: {args.threshold:.0%}")
        return 0
    
    def _cmd_data(self, args) -> int:
        if args.data_action == "generate":
            print(f"Generating {args.count} {args.kind} records...")
            return 0
        elif args.data_action == "mask":
            print(f"Masking {args.input} -> {args.output}...")
            return 0
        elif args.data_action == "version":
            print(f"Version info for {args.name}")
            return 0
        return 0

def main():
    runner = AICLIRunner()
    sys.exit(runner.run())

if __name__ == "__main__":
    main()
```

---

## 练习题

### 练习题 1：实现 CLI 帮助信息彩色化

**要求：**
扩展 CLIRunner，实现帮助信息的彩色输出。

**步骤：**
1. 定义颜色常量（ERROR=red, WARN=yellow, INFO=blue）
2. 实现彩色打印函数
3. 在错误消息中使用彩色输出
4. 添加 `--color/--no-color` 选项

### 练习题 2：实现 CLI 命令历史记录

**要求：**
实现命令执行历史记录和回放功能。

**步骤：**
1. 设计历史记录存储结构
2. 记录每次命令执行的时间和结果
3. 实现 `history` 子命令查看历史
4. 实现 `rerun` 子命令回放历史命令

### 练习题 3：实现 CLI 配置管理

**要求：**
实现多环境配置文件支持。

**步骤：**
1. 设计配置结构（dev/staging/prod）
2. 实现配置加载和切换
3. 支持 `config show` 和 `config set` 命令
4. 实现配置验证

---
