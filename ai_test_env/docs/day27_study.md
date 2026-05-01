# Day 27 — 全量测试运行器

## 学习目标

1. 理解全量运行器的层级设计和模块映射
2. 掌握 pytest 结果解析和汇总方法
3. 学会运行日志的 JSON 持久化
4. 理解历史追踪和失败模块突出显示机制

---

## 一、今日目标

> 把 26 个测试模块组织成"一键运行"的 FullTestRunner——支持 smoke / regression / security / e2e / full 五种模式，记录每次运行结果，输出摘要报告。Day 21 的 CLI 提供了命令行入口，Day 27 提供了批量运行的引擎。

- 理解全量运行器的层级设计和模块映射
- 掌握 pytest 结果解析和汇总
- 学会运行日志的 JSON 持久化
- 理解历史追踪和失败模块突出显示

---

## 二、为什么需要全量运行器？

手动执行 `python -m pytest tests/d6_test_quality.py` 跑 26 个模块太慢。需要一个工具：

- **一键跑通**：`runner.run(RunLevel.FULL)` 执行所有测试文件
- **分层跑**：PR 提交前只跑 `smoke` 层（<30s），每天定时跑 `full`
- **结果记录**：每次运行保存到 `run_logs/`，可回查历史
- **失败高亮**：只看哪些模块failed，不用人工翻 pytest 输出

---

## 三、层级设计

### 3.1 层级映射

| 层级 | 包含模块数 | 预估耗时 | 使用场景 |
|------|-----------|---------|---------|
| **SMOKE** | 5 | ~15s | 每次 commit |
| **REGRESSION** | 16 | ~30s | 每日回归 |
| **SECURITY** | 2 | ~10s | 每日安全 |
| **E2E** | 3 | ~15s | 每周端到端 |
| **FULL** | 全部 | ~60s | 全量验证 |

### 3.2 模块映射定义

```python
MODULE_MAP = {
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
        # ... 16 个回归模块
        "tests/d26_test_token_auditor.py",
    ],
    # ...
}
```

---

## 四、运行流程

```
run(level=FULL)
  │
  ├── 选择模块列表（按层级映射或自动发现）
  │
  ├── 逐个运行：
  │     ├── subprocess.run(["pytest", module, "-q"])
  │     ├── 解析 stdout 提取 passed/failed/skipped 数
  │     └── 记录 ModuleResult（模块名、通过数、用时）
  │
  ├── 汇总 RunResult
  │     ├── total_passed / total_failed
  │     ├── all_passed 布尔值
  │     └── summary() 可读报告
  │
  └── _save_log() 写入 run_logs/run_YYYY-MM-DDTHH-mm-ss.json
```

---

## 五、结果解析

pytest 的 `-q` 模式输出格式：

```
                                                     ← 点号表示进度
3 passed in 0.05s                                    ← 纯通过
3 passed, 1 failed in 0.05s                          ← 有失败
3 passed, 1 failed, 2 skipped in 0.05s               ← 有跳过
```

解析逻辑：

```python
for line in stdout.split("\n"):
    if "passed" in line and "failed" in line:
        parts = line.split()
        for i, p in enumerate(parts):
            if p == "passed":
                passed = int(parts[i-1])
            elif p == "failed":
                failed = int(parts[i-1])
```

---

## 六、运行日志

每次运行自动写入 JSON：

```json
{
  "timestamp": "2026-04-30T19:00:00",
  "level": "full",
  "total_modules": 26,
  "total_passed": 535,
  "total_failed": 0,
  "all_passed": true,
  "total_time_s": 42.5,
  "modules": [
    {"module": "tests/d1_test_key_manager.py", "passed": 8, "failed": 0, "skipped": 0, "duration_s": 0.3},
    ...
  ]
}
```

---

## 七、使用示例

```python
from utils.d27_full_runner import FullTestRunner, RunLevel

runner = FullTestRunner()

# 冒烟测试（快速）
result = runner.run(RunLevel.SMOKE)
print(runner.summary(result))

# 安全测试
result = runner.run(RunLevel.SECURITY)
print(runner.summary(result))

# 全量测试
result = runner.run(RunLevel.FULL)
print(runner.summary(result))
print(runner.history())
```

输出示例：
```
━━━ 全量测试报告 [full] ━━━
时间: 2026-04-30T19:00:00
模块数: 32
结果: [OK] All Passed
总计: 535 passed, 0 failed
总耗时: 42.50s
```

---

## 八、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| ModuleResult | 有失败 | success_rate < 1, passed_str == "[!!]" |
| RunResult 汇总 | 求和 | total_passed = sum(all模块) |
| RunResult 空 | 无模块 | all_passed=True |
| 层级映射 | 所有层级 | 都有模块 |
| 自动发现 | _discover_all | 26+ 模块 |
| 摘要 | 有通过/失败 | 包含对应关键词 |
| 历史 | 多次运行 | 仅显示最近 N 次 |
| 日志 | _save_log | 写入 JSON 文件 |

---

## 面试题

### 题目 1：如何设计一个支持分层执行的测试运行框架？

**参考答案：**

**分层设计思想：**

不同的测试运行场景需要不同的测试范围：
- **SMOKE 测试**：核心功能验证，<30 秒，适合每次 commit
- **REGRESSION 测试**：完整回归，<5 分钟，适合每日定时
- **E2E 测试**：端到端验证，<15 分钟，适合每周
- **FULL 测试**：全部测试，<60 秒，适合版本发布前

**核心架构：**

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Callable
import subprocess
import json
from datetime import datetime

class RunLevel(Enum):
    SMOKE = "smoke"
    REGRESSION = "regression"
    SECURITY = "security"
    E2E = "e2e"
    FULL = "full"

@dataclass
class ModuleResult:
    module: str
    passed: int
    failed: int
    skipped: int
    duration_s: float

    @property
    def success_rate(self) -> float:
        total = self.passed + self.failed
        return self.passed / total if total > 0 else 1.0

    @property
    def passed_str(self) -> str:
        if self.failed > 0:
            return "[!!]"
        return "[OK]"

@dataclass
class RunResult:
    timestamp: str
    level: str
    total_modules: int
    total_passed: int
    total_failed: int
    total_skipped: int
    total_time_s: float
    all_passed: bool
    modules: List[ModuleResult] = field(default_factory=list)

class FullTestRunner:
    """全量测试运行器"""

    MODULE_MAP = {
        RunLevel.SMOKE: [
            "tests/d1_test_key_manager.py",
            "tests/d2_test_client.py",
            "tests/d4_test_request_format.py",
            "tests/d16_test_browser_checker.py",
            "tests/d17_test_suite_manager.py",
        ],
        RunLevel.FULL: [],  # 自动发现
    }

    def __init__(self, log_dir: str = "run_logs"):
        self.log_dir = log_dir

    def run(self, level: RunLevel, discover: bool = False) -> RunResult:
        """执行测试运行"""
        modules = self._discover_all() if discover else self.MODULE_MAP.get(level, [])

        results = []
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        start_time = datetime.now()

        for module in modules:
            result = self._run_module(module)
            results.append(result)
            total_passed += result.passed
            total_failed += result.failed
            total_skipped += result.skipped

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        run_result = RunResult(
            timestamp=start_time.isoformat(),
            level=level.value,
            total_modules=len(results),
            total_passed=total_passed,
            total_failed=total_failed,
            total_skipped=total_skipped,
            total_time_s=total_time,
            all_passed=total_failed == 0,
            modules=results
        )

        self._save_log(run_result)
        return run_result

    def _run_module(self, module: str) -> ModuleResult:
        """运行单个测试模块"""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", module, "-q"],
                capture_output=True,
                text=True,
                timeout=60
            )

            passed, failed, skipped = self._parse_output(result.stdout)
            return ModuleResult(
                module=module,
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration_s=0.0
            )
        except Exception as e:
            return ModuleResult(
                module=module,
                passed=0,
                failed=1,
                skipped=0,
                duration_s=0.0
            )

    def _parse_output(self, output: str) -> tuple:
        """解析 pytest 输出"""
        passed = failed = skipped = 0

        for line in output.split("\n"):
            if "passed" in line and "failed" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "passed":
                        passed = int(parts[i - 1])
                    elif p == "failed":
                        failed = int(parts[i - 1])
            elif "passed" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "passed":
                        passed = int(parts[i - 1])

        return passed, failed, skipped

    def _discover_all(self) -> List[str]:
        """自动发现所有测试模块"""
        import glob
        return sorted(glob.glob("tests/d*_test_*.py"))

    def _save_log(self, result: RunResult):
        """保存运行日志"""
        import os
        os.makedirs(self.log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        log_file = os.path.join(self.log_dir, f"run_{timestamp}.json")

        with open(log_file, "w") as f:
            json.dump({
                "timestamp": result.timestamp,
                "level": result.level,
                "total_modules": result.total_modules,
                "total_passed": result.total_passed,
                "total_failed": result.total_failed,
                "all_passed": result.all_passed,
                "modules": [
                    {"module": m.module, "passed": m.passed, "failed": m.failed}
                    for m in result.modules
                ]
            }, f, indent=2)
```

---

### 题目 2：如何实现测试报告的聚合和分析？

**参考答案：**

**测试报告聚合的核心需求：**

1. **模块稳定性评分**：按失败率对模块排序
2. **趋势分析**：对比历史运行数据，发现退化
3. **失败根因追踪**：定位持续失败的模块

**聚合器实现：**

```python
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime
import json
import os

@dataclass
class ModuleStability:
    module: str
    runs: int
    failures: int
    total_passed: int
    total_failed: int
    last_failed: str

    @property
    def pass_rate(self) -> float:
        return 1.0 - (self.failures / max(self.runs, 1))

    @property
    def grade(self) -> str:
        if self.pass_rate >= 0.95:
            return "A"
        elif self.pass_rate >= 0.8:
            return "B"
        return "C"

@dataclass
class AggregatedReport:
    total_runs: int
    date_range: str
    overall_pass_rate: float
    module_stabilities: List[ModuleStability]
    summary: str

class ReportAggregator:
    """测试报告聚合器"""

    def __init__(self, log_dir: str = "run_logs"):
        self.log_dir = log_dir

    def aggregate(self, days: int = 30) -> AggregatedReport:
        """聚合历史报告"""
        entries = self._load_all(days)

        if not entries:
            return AggregatedReport(
                total_runs=0,
                date_range="N/A",
                overall_pass_rate=1.0,
                module_stabilities=[],
                summary="No data"
            )

        module_stats = self._calculate_module_stats(entries)

        dates = sorted(set(e["timestamp"][:10] for e in entries))
        date_range = f"{dates[0]} ~ {dates[-1]}" if dates else "N/A"

        total_passed = sum(m.total_passed for m in module_stats)
        total_failed = sum(m.total_failed for m in module_stats)
        overall_rate = total_passed / (total_passed + total_failed) if (total_passed + total_failed) > 0 else 1.0

        return AggregatedReport(
            total_runs=len(entries),
            date_range=date_range,
            overall_pass_rate=overall_rate,
            module_stabilities=module_stats,
            summary=self._generate_summary(module_stats, overall_rate)
        )

    def _load_all(self, days: int) -> List[Dict]:
        """加载历史日志"""
        entries = []
        if not os.path.exists(self.log_dir):
            return entries

        cutoff = datetime.now().timestamp() - (days * 86400)

        for filename in os.listdir(self.log_dir):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(self.log_dir, filename)
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    timestamp = datetime.fromisoformat(data["timestamp"]).timestamp()
                    if timestamp >= cutoff:
                        entries.append(data)
            except Exception:
                continue

        return entries

    def _calculate_module_stats(self, entries: List[Dict]) -> List[ModuleStability]:
        """计算模块稳定性"""
        stats = defaultdict(lambda: {"runs": 0, "failures": 0, "passed": 0, "failed": 0, "last_failed": ""})

        for entry in entries:
            for module_data in entry.get("modules", []):
                module = module_data["module"]
                stats[module]["runs"] += 1
                stats[module]["passed"] += module_data.get("passed", 0)
                stats[module]["failed"] += module_data.get("failed", 0)
                if module_data.get("failed", 0) > 0:
                    stats[module]["failures"] += 1
                    stats[module]["last_failed"] = entry["timestamp"]

        result = [
            ModuleStability(
                module=module,
                runs=data["runs"],
                failures=data["failures"],
                total_passed=data["passed"],
                total_failed=data["failed"],
                last_failed=data["last_failed"]
            )
            for module, data in stats.items()
        ]

        return sorted(result, key=lambda x: x.pass_rate)

    def _generate_summary(self, stabilities: List[ModuleStability], overall_rate: float) -> str:
        """生成摘要"""
        unstable = [s for s in stabilities if s.grade == "C"]
        if unstable:
            return f"Overall: {overall_rate:.1%} | Unstable modules: {len(unstable)}"
        return f"Overall: {overall_rate:.1%} | All stable"
```

---

## 代码示例

```python
"""
Day 27 代码示例：全量测试运行器完整实现
演示分层测试执行和结果汇总
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict
import subprocess
import json
from datetime import datetime


class RunLevel(Enum):
    SMOKE = "smoke"
    REGRESSION = "regression"
    SECURITY = "security"
    E2E = "e2e"
    FULL = "full"


@dataclass
class ModuleResult:
    module: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_s: float = 0.0

    @property
    def success_rate(self) -> float:
        total = self.passed + self.failed
        return self.passed / total if total > 0 else 1.0

    @property
    def passed_str(self) -> str:
        return "[!!]" if self.failed > 0 else "[OK]"


@dataclass
class RunResult:
    timestamp: str
    level: str
    total_modules: int
    total_passed: int
    total_failed: int
    total_skipped: int
    total_time_s: float
    all_passed: bool
    modules: List[ModuleResult] = field(default_factory=list)


class FullTestRunner:
    """全量测试运行器"""

    MODULE_MAP = {
        RunLevel.SMOKE: [
            "tests/d1_test_key_manager.py",
            "tests/d2_test_client.py",
        ],
        RunLevel.FULL: [],
    }

    def __init__(self, log_dir: str = "run_logs"):
        self.log_dir = log_dir

    def run(self, level: RunLevel, discover: bool = False) -> RunResult:
        modules = self._discover_all() if discover else self.MODULE_MAP.get(level, [])

        results = []
        total_passed = total_failed = total_skipped = 0
        start_time = datetime.now()

        for module in modules:
            result = self._run_module(module)
            results.append(result)
            total_passed += result.passed
            total_failed += result.failed
            total_skipped += result.skipped

        total_time = (datetime.now() - start_time).total_seconds()

        run_result = RunResult(
            timestamp=start_time.isoformat(),
            level=level.value,
            total_modules=len(results),
            total_passed=total_passed,
            total_failed=total_failed,
            total_skipped=total_skipped,
            total_time_s=total_time,
            all_passed=total_failed == 0,
            modules=results
        )

        self._save_log(run_result)
        return run_result

    def _run_module(self, module: str) -> ModuleResult:
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", module, "-q"],
                capture_output=True,
                text=True,
                timeout=60
            )
            passed, failed, skipped = self._parse_output(result.stdout)
            return ModuleResult(module=module, passed=passed, failed=failed, skipped=skipped)
        except Exception:
            return ModuleResult(module=module, passed=0, failed=1, skipped=0)

    def _parse_output(self, output: str) -> tuple:
        passed = failed = skipped = 0
        for line in output.split("\n"):
            if "passed" in line and "failed" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "passed":
                        passed = int(parts[i - 1])
                    elif p == "failed":
                        failed = int(parts[i - 1])
            elif "passed" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "passed":
                        passed = int(parts[i - 1])
        return passed, failed, skipped

    def _discover_all(self) -> List[str]:
        import glob
        return sorted(glob.glob("tests/d*_test_*.py"))

    def _save_log(self, result: RunResult):
        import os
        os.makedirs(self.log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        log_file = os.path.join(self.log_dir, f"run_{timestamp}.json")

        with open(log_file, "w") as f:
            json.dump({
                "timestamp": result.timestamp,
                "level": result.level,
                "total_modules": result.total_modules,
                "total_passed": result.total_passed,
                "total_failed": result.total_failed,
                "all_passed": result.all_passed,
                "modules": [
                    {"module": m.module, "passed": m.passed, "failed": m.failed}
                    for m in result.modules
                ]
            }, f, indent=2)

    def summary(self, result: RunResult) -> str:
        status = "[OK] All Passed" if result.all_passed else "[!!] Failures"
        return f"""━━━ 测试报告 [{result.level}] ━━━
时间: {result.timestamp}
模块数: {result.total_modules}
结果: {status}
总计: {result.total_passed} passed, {result.total_failed} failed
总耗时: {result.total_time_s:.2f}s"""


def demo():
    print("=" * 60)
    print("Day 27 代码示例：全量测试运行器演示")
    print("=" * 60)

    runner = FullTestRunner()

    print("\n[1] 测试分层设计")
    print("-" * 40)
    for level in RunLevel:
        count = len(runner.MODULE_MAP.get(level, []))
        print(f"{level.value:12}: {count} modules")

    print("\n[2] 模拟测试结果汇总")
    print("-" * 40)
    mock_result = RunResult(
        timestamp=datetime.now().isoformat(),
        level="full",
        total_modules=5,
        total_passed=100,
        total_failed=2,
        total_skipped=0,
        total_time_s=42.5,
        all_passed=False,
        modules=[
            ModuleResult("d1_test.py", passed=20, failed=0),
            ModuleResult("d2_test.py", passed=25, failed=0),
            ModuleResult("d3_test.py", passed=30, failed=1),
            ModuleResult("d4_test.py", passed=25, failed=1),
            ModuleResult("d5_test.py", passed=0, failed=0, skipped=5),
        ]
    )
    print(runner.summary(mock_result))

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
```

---

## 练习题

### 练习 1：实现测试失败自动重试机制

**要求：**
在 FullTestRunner 中添加失败重试功能，对失败的测试模块自动重试一次。

**提示：**
```python
def run_with_retry(
    self,
    level: RunLevel,
    max_retries: int = 1
) -> RunResult:
    """执行测试，失败的模块自动重试"""
    pass
```

**验收标准：**
- 首次运行失败的模块自动重试
- 统计重试次数
- 重试后仍然失败才标记为失败

---

### 练习 2：实现并行测试执行

**要求：**
使用 concurrent.futures 实现测试的并行执行，加快测试速度。

**提示：**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_parallel(
    self,
    level: RunLevel,
    max_workers: int = 4
) -> RunResult:
    """并行执行测试"""
    pass
```

**验收标准：**
- 多线程并行执行测试模块
- 统计并行执行的加速比
- 正确汇总所有模块结果

---

### 练习 3：实现测试运行历史对比

**要求：**
实现测试运行历史的对比功能，显示两次运行之间的差异（新增失败、新增通过等）。

**提示：**
```python
class RunDiff:
    """运行结果对比"""
    new_failures: List[str]
    new_passes: List[str]
    improved_modules: List[str]
    degraded_modules: List[str]

def compare(runs: List[RunResult]) -> List[RunDiff]:
    """对比历史运行结果"""
    pass
```

**验收标准：**
- 对比相邻两次运行的结果
- 识别新增失败和新增通过的模块
- 生成对比报告

---

## 九、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d27_full_runner.py` | 全量测试运行器 | [OK] |
| `tests/d27_test_full_runner.py` | 17 个测试 | [OK] 17/17 PASS |
| `day27_study.md` | 本文档 | [OK] 已创建 |
