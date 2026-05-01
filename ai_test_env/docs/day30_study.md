# Day 30 — 综合端到端测试

## 学习目标

1. 理解端到端自检的"三步走"流程（导入检查 → 全量测试 → 仪表盘）
2. 掌握模块导入自动检查方法
3. 理解全量测试 + 聚合 + 仪表盘的完整闭环
4. 学会整体状态裁定（ALL PASS 或 FAILURES）

---

## 一、今日目标

> Week 6 的最后一天，把 AI 测试平台之前 29 个模块（d1-d29）整合为一次端到端验证。运行全量测试（d1-d29）→ 聚合报告 → 输出仪表盘。做完这一步，整个平台就完工了。

- 理解端到端自检的"三步走"流程
- 掌握模块导入自动检查方法
- 理解全量测试 + 聚合 + 仪表盘的完整闭环
- 学会整体状态裁定（ALL PASS 或 FAILURES）

---

## 二、三步走流程

```
[1/3] 模块导入检查
  ├── check_imports()
  └── 验证 34 个模块能否正常 import

[2/3] 全量测试
  ├── run_all_tests()
  ├── 发现 tests/ 下全部测试文件
  ├── 每个文件 subprocess.run(["pytest", ...])
  ├── 解析输出：passed / failed / skipped
  └── 汇总 total_passed / total_failed / total_time

[3/3] 系统健康仪表盘
  ├── DashboardBuilder()
  ├── 添加通过率、稳定性、运行次数等
  └── 输出 display()

最终裁定
  ├── 测试全通过 + 导入全 OK = ✅ ALL PASS
  └── 否则 = ❌ FAILURES
```

---

## 三、导入表格

`check_imports()` 维护了一张 34 个模块的映射表，覆盖 d1-d30 及其子模块（如 d8b 测试覆盖率、d10b 流水线评估）：

```
d1   → utils.d1_api_client.AIClient
d8   → utils.d8_truncation_analyzer.TruncationAnalyzer
d12  → utils.d12_injection_detector.InjectionDetector
d12b → utils.d12_prompt_injection_tester.PromptInjectionTester
d14  → utils.d14_regression_tester.RegressionTester
d18  → utils.d18_ci_config_gen.CIConfigGenerator
d21  → run.main（CLI 入口）
d25  → utils.d25_error_system.ErrorClassifier
d30  → utils.d30_comprehensive.check_imports（自我检查）
```

---

## 四、输出示例

```
============================================================
  AI 测试平台 — 综合端到端验证
  时间: 2026-04-30 19:35:00
============================================================

[1/3] 模块导入检查
----------------------------------------
  [OK] d1: AIClient
  [OK] d3: ErrorClassifier
  ...
  导入: 34/34 OK, 0 failed

[2/3] 全量测试 (19:35:12)
----------------------------------------
  [OK] d1_test_api_client.py         8p  0f  0s (0.32s)
  [!!] d12_test_injection.py       25p  2f  0s (0.50s)
  ...
  全部: 535 passed, 2 failed, 31 modules, 42.50s

[3/3] 系统健康仪表盘
----------------------------------------
━━━ AI 测试平台仪表盘 ━━━
  🟢 测试通过率: 99.6%
  🟢 模块稳定率: 93.8%
  ...

最终状态: ❌ FAILURES — 请查看上方失败详情
============================================================
```

---

## 五、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| 返回类型 | check_imports() | dict |
| 模块数量 | import 检查 | >= 30 |
| Week 6 导入 | d26-d30 | 全部 OK |
| Week 5 导入 | d21-d25 | 全部 OK |
| 字段存在 | check_imports 每条 | 含 "ok" + "msg" |

---

## 六、Week 6 全局统计

| Day | 模块 | util | test | study | tests 通过 | 状态 |
|:----|:-----|:-----|:-----|:------|:-----------|:-----|
| 26 | Token 审计 | 9.1KB | 8.2KB | 5.1KB | 18/18 ✅ | ✅ |
| 27 | 全量运行器 | 10.5KB | 5.9KB | 4.9KB | 17/17 ✅ | ✅ |
| 28 | 报告聚合器 | 9.1KB | 5.8KB | 4.5KB | 15/15 ✅ | ✅ |
| 29 | 仪表盘 | 7.6KB | 3.6KB | 2.9KB | 12/12 ✅ | ✅ |
| 30 | 综合项目 | 7.3KB | 1.1KB | — | 4/4 ✅ | ✅ |

---

## 面试题

### 题目 1：如何设计一个端到端测试框架的完整闭环？

**参考答案：**

**端到端测试的核心价值：**

端到端测试验证整个系统的集成度，确保各个模块在组合使用时能够正常工作。这不同于单元测试只验证单个模块，E2E 测试验证模块间的协作。

**完整闭环设计：**

```python
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from enum import Enum
import subprocess
import importlib


class E2EPhase(Enum):
    IMPORT_CHECK = "import_check"
    UNIT_TESTS = "unit_tests"
    INTEGRATION_TESTS = "integration_tests"
    DASHBOARD = "dashboard"


@dataclass
class ImportResult:
    """导入检查结果"""
    module: str
    success: bool
    error: Optional[str] = None


@dataclass
class TestResult:
    """测试执行结果"""
    module: str
    passed: int
    failed: int
    skipped: int
    duration_s: float


@dataclass
class E2EReport:
    """端到端测试报告"""
    timestamp: str
    import_results: List[ImportResult] = field(default_factory=list)
    test_results: List[TestResult] = field(default_factory=list)
    overall_pass: bool = True
    summary: str = ""


class ImportChecker:
    """模块导入检查器"""

    MODULE_MAP = {
        "d1": "utils.d1_api_client.AIClient",
        "d2": "utils.d2_response_parser.ResponseParser",
        "d8": "utils.d8_truncation_analyzer.TruncationAnalyzer",
        "d12": "utils.d12_injection_detector.InjectionDetector",
        "d18": "utils.d18_ci_config_gen.CIConfigGenerator",
        "d21": "utils.d21_cli.CLI",
        "d22": "utils.d22_load_tester.LoadTester",
        "d23": "utils.d23_retry_logic.ExponentialBackoff",
        "d24": "utils.d24_circuit_breaker.CircuitBreaker",
        "d25": "utils.d25_error_handler.ErrorClassifier",
        "d26": "utils.d26_token_auditor.TokenAuditor",
        "d27": "utils.d27_full_runner.FullTestRunner",
        "d28": "utils.d28_report_aggregator.ReportAggregator",
        "d29": "utils.d29_dashboard.DashboardBuilder",
    }

    def check_all(self) -> List[ImportResult]:
        """检查所有模块导入"""
        results = []
        for name, path in self.MODULE_MAP.items():
            result = self._check_module(name, path)
            results.append(result)
        return results

    def _check_module(self, name: str, path: str) -> ImportResult:
        """检查单个模块"""
        try:
            module_path = ".".join(path.split(".")[:-1])
            class_name = path.split(".")[-1]
            importlib.import_module(module_path)
            return ImportResult(module=name, success=True)
        except Exception as e:
            return ImportResult(module=name, success=False, error=str(e))


class E2ETestRunner:
    """端到端测试运行器"""

    def __init__(self):
        self.import_checker = ImportChecker()
        self._test_cache: Dict[str, TestResult] = {}

    def run_full_e2e(self) -> E2EReport:
        """运行完整 E2E 测试"""
        timestamp = datetime.now().isoformat()

        print("━━━ Phase 1: 导入检查 ━━━")
        import_results = self.import_checker.check_all()
        for result in import_results:
            status = "✓" if result.success else "✗"
            print(f"  {status} {result.module}")

        print("\n━━━ Phase 2: 测试执行 ━━━")
        test_results = self._discover_and_run_tests()

        print("\n━━━ Phase 3: 汇总裁定 ━━━")
        overall_pass = all(r.success for r in import_results) and \
                       all(r.failed == 0 for r in test_results)

        failed_imports = [r for r in import_results if not r.success]
        failed_tests = [r for r in test_results if r.failed > 0]

        summary_parts = []
        if failed_imports:
            summary_parts.append(f"导入失败: {len(failed_imports)}")
        if failed_tests:
            summary_parts.append(f"测试失败: {len(failed_tests)}")
        if overall_pass:
            summary_parts.append("ALL PASS ✅")

        return E2EReport(
            timestamp=timestamp,
            import_results=import_results,
            test_results=test_results,
            overall_pass=overall_pass,
            summary=" | ".join(summary_parts) if summary_parts else "No issues found"
        )

    def _discover_and_run_tests(self) -> List[TestResult]:
        """发现并运行所有测试"""
        import glob
        test_files = sorted(glob.glob("tests/d*_test_*.py"))

        results = []
        for test_file in test_files:
            result = self._run_test_file(test_file)
            results.append(result)
            status = "✓" if result.failed == 0 else "✗"
            print(f"  {status} {test_file}: {result.passed}/{result.passed + result.failed}")

        return results

    def _run_test_file(self, test_file: str) -> TestResult:
        """运行单个测试文件"""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", test_file, "-q"],
                capture_output=True,
                text=True,
                timeout=120
            )
            passed, failed, skipped = self._parse_pytest_output(result.stdout)
            return TestResult(
                module=test_file,
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration_s=0.0
            )
        except Exception:
            return TestResult(module=test_file, passed=0, failed=1, skipped=0, duration_s=0.0)

    def _parse_pytest_output(self, output: str) -> Tuple[int, int, int]:
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


class DashboardIntegrator:
    """仪表盘集成器"""

    def __init__(self, e2e_report: E2EReport):
        self.report = e2e_report

    def generate(self) -> str:
        """生成仪表盘"""
        lines = ["━━━ AI 测试平台 E2E 仪表盘 ━━━", f"时间: {self.report.timestamp}", ""]

        import_ok = all(r.success for r in self.report.import_results)
        tests_ok = all(r.failed == 0 for r in self.report.test_results)

        overall = "✅ ALL PASS" if self.report.overall_pass else "❌ FAILURES"
        lines.append(f"整体状态: {overall}")
        lines.append("")

        lines.append("── 导入检查 ──")
        for r in self.report.import_results:
            status = "✓" if r.success else "✗"
            lines.append(f"  {status} {r.module}")
        lines.append("")

        total_passed = sum(r.passed for r in self.report.test_results)
        total_failed = sum(r.failed for r in self.report.test_results)
        lines.append(f"── 测试汇总 ──")
        lines.append(f"  通过: {total_passed}")
        lines.append(f"  失败: {total_failed}")

        return "\n".join(lines)
```

---

### 题目 2：如何在大型测试平台中确保质量的持续改进？

**参考答案：**

**持续改进的质量保障体系：**

```python
from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime, timedelta


@dataclass
class QualityTrend:
    """质量趋势"""
    metric: str
    current: float
    previous: float
    delta: float
    trend: str


class QualityTracker:
    """质量追踪器"""

    def __init__(self):
        self._history: List[Dict] = []

    def record(self, metrics: Dict[str, float]) -> None:
        """记录质量指标"""
        self._history.append({
            "timestamp": datetime.now().isoformat(),
            **metrics
        })

    def analyze_trends(self, metric: str, window: int = 7) -> QualityTrend:
        """分析趋势"""
        if len(self._history) < 2:
            return QualityTrend(metric, 0.0, 0.0, 0.0, "insufficient_data")

        recent = self._history[-window:]
        current = recent[-1].get(metric, 0.0)
        previous = recent[0].get(metric, 0.0)
        delta = current - previous

        if delta > 0.05:
            trend = "improving"
        elif delta < -0.05:
            trend = "degrading"
        else:
            trend = "stable"

        return QualityTrend(
            metric=metric,
            current=current,
            previous=previous,
            delta=delta,
            trend=trend
        )

    def generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []

        for metric in ["pass_rate", "stability", "coverage"]:
            trend = self.analyze_trends(metric)
            if trend.trend == "degrading":
                recommendations.append(
                    f"{metric}: 质量下降，需要关注 (当前 {trend.current:.1%})"
                )

        return recommendations


class CIQualityGate:
    """CI 质量门禁"""

    THRESHOLDS = {
        "pass_rate": 0.95,
        "stability": 0.90,
        "coverage": 0.80
    }

    @classmethod
    def evaluate(cls, metrics: Dict[str, float]) -> Tuple[bool, List[str]]:
        """评估是否通过门禁"""
        failures = []
        for metric, threshold in cls.THRESHOLDS.items():
            value = metrics.get(metric, 0.0)
            if value < threshold:
                failures.append(f"{metric}: {value:.1%} < {threshold:.1%}")

        passed = len(failures) == 0
        return passed, failures
```

---

## 代码示例

```python
"""
Day 30 代码示例：综合端到端测试完整实现
演示三步走流程和完整闭环
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import subprocess
import importlib


@dataclass
class ImportResult:
    module: str
    success: bool
    error: Optional[str] = None


@dataclass
class TestResult:
    module: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0


@dataclass
class E2EReport:
    timestamp: str
    import_results: List[ImportResult] = field(default_factory=list)
    test_results: List[TestResult] = field(default_factory=list)
    overall_pass: bool = True
    summary: str = ""


class ImportChecker:
    MODULE_MAP = {
        "d1": "utils.d1_api_client.AIClient",
        "d21": "utils.d21_cli.CLI",
        "d22": "utils.d22_load_tester.LoadTester",
        "d23": "utils.d23_retry_logic.ExponentialBackoff",
        "d24": "utils.d24_circuit_breaker.CircuitBreaker",
        "d27": "utils.d27_full_runner.FullTestRunner",
        "d28": "utils.d28_report_aggregator.ReportAggregator",
        "d29": "utils.d29_dashboard.DashboardBuilder",
    }

    def check_all(self) -> List[ImportResult]:
        return [self._check_module(name, path) for name, path in self.MODULE_MAP.items()]

    def _check_module(self, name: str, path: str) -> ImportResult:
        try:
            module_path = ".".join(path.split(".")[:-1])
            importlib.import_module(module_path)
            return ImportResult(module=name, success=True)
        except Exception as e:
            return ImportResult(module=name, success=False, error=str(e))


class E2ETestRunner:
    def __init__(self):
        self.import_checker = ImportChecker()

    def run_full_e2e(self) -> E2EReport:
        timestamp = datetime.now().isoformat()

        import_results = self.import_checker.check_all()
        test_results = self._simulate_test_results()

        overall_pass = all(r.success for r in import_results) and \
                       all(r.failed == 0 for r in test_results)

        return E2EReport(
            timestamp=timestamp,
            import_results=import_results,
            test_results=test_results,
            overall_pass=overall_pass,
            summary="ALL PASS ✅" if overall_pass else "FAILURES ❌"
        )

    def _simulate_test_results(self) -> List[TestResult]:
        return [
            TestResult("d1_test.py", passed=10, failed=0),
            TestResult("d21_test.py", passed=8, failed=0),
            TestResult("d22_test.py", passed=15, failed=0),
            TestResult("d27_test.py", passed=17, failed=0),
            TestResult("d28_test.py", passed=15, failed=0),
            TestResult("d29_test.py", passed=12, failed=0),
        ]

    def _parse_pytest_output(self, output: str) -> Tuple[int, int, int]:
        passed = failed = skipped = 0
        for line in output.split("\n"):
            if "passed" in line and "failed" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "passed":
                        passed = int(parts[i - 1])
                    elif p == "failed":
                        failed = int(parts[i - 1])
        return passed, failed, skipped


class DashboardIntegrator:
    def __init__(self, e2e_report: E2EReport):
        self.report = e2e_report

    def generate(self) -> str:
        lines = ["━━━ AI 测试平台 E2E 仪表盘 ━━━",
                 f"时间: {self.report.timestamp}",
                 f"状态: {self.report.summary}",
                 "",
                 "── 导入检查 ──"]
        for r in self.report.import_results:
            lines.append(f"  {'✓' if r.success else '✗'} {r.module}")

        total_passed = sum(r.passed for r in self.report.test_results)
        total_failed = sum(r.failed for r in self.report.test_results)
        lines.extend(["", "── 测试汇总 ──",
                      f"  通过: {total_passed}", f"  失败: {total_failed}"])
        return "\n".join(lines)


def demo():
    print("=" * 60)
    print("Day 30 代码示例：综合端到端测试演示")
    print("=" * 60)

    runner = E2ETestRunner()

    print("\n[1] 模拟 E2E 完整流程")
    print("-" * 40)
    report = runner.run_full_e2e()

    dashboard = DashboardIntegrator(report)
    print(dashboard.generate())

    print("\n" + "=" * 60)
    print("演示完成 - 整个平台完工 ✅")
    print("=" * 60)


if __name__ == "__main__":
    demo()
```

---

## 练习题

### 练习 1：实现测试覆盖率追踪

**要求：**
在 E2E 测试中增加测试覆盖率统计功能。

**提示：**
```python
class CoverageTracker:
    """覆盖率追踪器"""
    def __init__(self):
        self._covered_modules: Set[str] = set()
        self._total_modules: Set[str] = set()

    def record_coverage(self, modules: List[str]) -> None:
        """记录已覆盖的模块"""
        pass

    @property
    def coverage_rate(self) -> float:
        """计算覆盖率"""
        pass
```

**验收标准：**
- 追踪所有测试模块的覆盖情况
- 计算覆盖率百分比
- 生成覆盖率报告

---

### 练习 2：实现测试执行历史版本化

**要求：**
为每次 E2E 测试执行生成唯一的版本标识，便于历史追踪。

**提示：**
```python
class TestVersion:
    """测试版本"""
    version: str
    timestamp: str
    git_commit: str
    test_hash: str

def generate_version() -> TestVersion:
    """生成版本信息"""
    pass
```

**验收标准：**
- 包含时间戳和版本号
- 包含 Git 提交哈希（如果可用）
- 生成测试结果的哈希值

---

### 练习 3：实现自动化回归测试选择

**要求：**
基于代码变更，自动选择需要运行的测试子集。

**提示：**
```python
class SmartTestSelector:
    """智能测试选择器"""
    def __init__(self):
        self._module_map: Dict[str, List[str]] = {}

    def select_tests(
        self,
        changed_files: List[str]
    ) -> List[str]:
        """根据变更选择需要运行的测试"""
        pass
```

**验收标准：**
- 分析变更的文件
- 映射到相关测试模块
- 返回需要运行的测试列表

---

## 七、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d30_comprehensive.py` | 综合端到端测试 | [OK] |
| `tests/d30_test_comprehensive.py` | 4 个导入检查测试 | [OK] 4/4 PASS |
| `day30_study.md` | 本文档 | [OK] 已创建 |
