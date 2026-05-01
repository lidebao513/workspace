# Day 28 — 测试报告聚合器

## 学习目标

1. 理解 ReportAggregator 的三维度聚合（模块/层级/时间）
2. 掌握 ModuleStability 评分（Grade A/B/C）计算方法
3. 学会 troubleshoot 模块执行历史
4. 理解 JSON 日志反序列化和聚合统计

---

## 一、今日目标

> 读取 d27 FullTestRunner 的运行日志，聚合多维度统计：模块稳定性、通过率趋势、层级运行频率。让测试数据变成可读的仪表盘。

- 理解 ReportAggregator 的三维度聚合（模块/层级/时间）
- 掌握 ModuleStability 评分（Grade A/B/C）
- 学会 troubleshoot 模块执行历史
- 理解 JSON 日志反序列化和聚合统计

---

## 二、为什么需要聚合？

d27 的 FullTestRunner 生成了很多 JSON 日志文件，但单个日志只能看"这次跑得怎么样"。聚合器才能回答：

- **哪个模块最不稳定？** → ModuleStability.grade C
- **总体通过率在恶化吗？** → 趋势对比
- **某个模块最近为什么总失败？** → troubleshoot()

---

## 三、核心数据结构

### 3.1 ModuleStability（模块稳定性）

```python
@dataclass
class ModuleStability:
    module: str              # 模块名
    runs: int                # 运行次数
    failures: int            # 有失败的运行次数
    total_passed: int        # 总通过用例数
    total_failed: int        # 总失败用例数
    last_failed: str         # 最近失败的时间戳
    avg_duration: float      # 平均执行时间

    @property
    def pass_rate(self) -> float:
        """运行通过率（不是用例通过率）"""
        return 1.0 - (self.failures / max(self.runs, 1))

    @property
    def grade(self) -> str:
        if self.pass_rate >= 0.95: return "A"  # 稳定
        elif self.pass_rate >= 0.8: return "B" # 偶尔波动
        else: return "C"                       # 需要关注
```

### 3.2 AggregatedReport（聚合报告）

```python
@dataclass
class AggregatedReport:
    total_runs: int                        # 总运行次数
    date_range: str                        # 日期范围
    overall_pass_rate: float               # 总体通过率
    module_stabilities: List[ModuleStability]  # 按稳定性排序
    level_stats: Dict[str, int]            # 各层级运行次数
    summary: str                           # 一句话摘要
```

---

## 四、聚合算法

```
_load_all()
  └── 读取 run_logs/*.json → self._entries

aggregate(days=30)
  ├── 过滤近期运行记录
  ├── 计算 overall_pass_rate
  ├── 遍历所有模块的执行历史
  │     └── 累计 runs / failures / total_passed / total_failed
  ├── 排序（Grade C 在前）
  ├── 统计 level_stats
  └── 计算 date_range
```

---

## 五、使用示例

### 5.1 基本聚合

```python
from utils.d28_report_aggregator import ReportAggregator

agg = ReportAggregator()
report = agg.aggregate(days=30)
print(report.summary)
# → "运行: 15 次 | 总体通过率: 98.50% | 不稳定模块 (1): d22_test_load_tester.py"
```

### 5.2 完整报告

```python
print(agg.generate_report(days=7))
# → 格式化的模块稳定性表和层级统计
```

### 5.3 排查模块

```python
trouble = agg.troubleshoot("d12_test_prompt_injection.py")
print(trouble)
# → d12_test_prompt_injection.py 最近 10 次运行的通过/失败情况
```

---

## 六、报告输出示例

```
━━━ 测试报告聚合 ━━━
日期范围: 2026-04-28 ~ 2026-04-30
运行次数: 12
总体通过率: 97.33%

── 模块稳定性 ──
Grade  Module                             Runs  Fail%  Avg Dur
A      d6_test_quality.py                   12    0%    0.45s
A      d7_test_consistency.py               12    0%    0.62s
A      d15_test_e2e.py                      10    0%    0.55s
B      d22_test_load_tester.py              12    8%    0.52s
C      d12_test_prompt_injection.py         12   17%    0.50s
```

---

## 七、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| ModuleStability.pass_rate | 10 runs / 1 fail | 0.9 |
| Grade 判定 | >=0.95→A, >=0.8→B, else→C | 正确 |
| 空日志目录 | 无日志 | total_runs=0 |
| 单次运行 | 1 个日志 | runs=1 |
| 全部通过 | 0 failed | pass_rate=1.0 |
| 非法 JSON | 读取跳过 | 不影响 |
| troubleshoot 找到 | 有记录 | 显示历史 |
| 层级统计 | 多个同层级 | counter 正确 |
| generate_report | 有数据 | 包含"通过率"和"Grade" |

---

## 面试题

### 题目 1：如何设计一个测试报告聚合和分析系统？

**参考答案：**

**聚合系统的核心价值：**

测试报告聚合解决以下问题：
- 单次运行只能看"这次怎么样"，聚合后才能看趋势
- 哪些模块最不稳定需要重点关注
- 整体质量是在改善还是在退化

**三维度聚合设计：**

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict
import json
import os

@dataclass
class ModuleStability:
    """模块稳定性评分"""
    module: str
    runs: int = 0
    failures: int = 0
    total_passed: int = 0
    total_failed: int = 0
    last_failed: str = ""

    @property
    def pass_rate(self) -> float:
        """运行通过率（不是用例通过率）"""
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
    """聚合报告"""
    total_runs: int
    date_range: str
    overall_pass_rate: float
    module_stabilities: List[ModuleStability]
    level_stats: Dict[str, int]
    summary: str

class ReportAggregator:
    """测试报告聚合器"""

    def __init__(self, log_dir: str = "run_logs"):
        self.log_dir = log_dir
        self._entries: List[Dict] = []

    def _load_all(self) -> List[Dict]:
        """加载所有历史日志"""
        entries = []
        if not os.path.exists(self.log_dir):
            return entries

        for filename in sorted(os.listdir(self.log_dir)):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self.log_dir, filename)
            try:
                with open(filepath) as f:
                    entries.append(json.load(f))
            except Exception:
                continue

        return entries

    def aggregate(self, days: int = 30) -> AggregatedReport:
        """聚合指定天数的报告"""
        self._entries = self._load_all()

        if not self._entries:
            return AggregatedReport(
                total_runs=0,
                date_range="N/A",
                overall_pass_rate=1.0,
                module_stabilities=[],
                level_stats={},
                summary="No data available"
            )

        cutoff = datetime.now().timestamp() - (days * 86400)
        recent_entries = [
            e for e in self._entries
            if datetime.fromisoformat(e["timestamp"]).timestamp() >= cutoff
        ]

        module_stats = self._calculate_module_stats(recent_entries)
        level_stats = self._calculate_level_stats(recent_entries)

        dates = sorted(set(e["timestamp"][:10] for e in recent_entries))
        date_range = f"{dates[0]} ~ {dates[-1]}" if dates else "N/A"

        total_passed = sum(m.total_passed for m in module_stats)
        total_failed = sum(m.total_failed for m in module_stats)
        overall_rate = total_passed / (total_passed + total_failed) if (total_passed + total_failed) > 0 else 1.0

        return AggregatedReport(
            total_runs=len(recent_entries),
            date_range=date_range,
            overall_pass_rate=overall_rate,
            module_stabilities=module_stats,
            level_stats=level_stats,
            summary=self._generate_summary(module_stats, overall_rate)
        )

    def _calculate_module_stats(self, entries: List[Dict]) -> List[ModuleStability]:
        """计算模块稳定性"""
        stats = defaultdict(
            lambda: {"runs": 0, "failures": 0, "passed": 0, "failed": 0, "last_failed": ""}
        )

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

    def _calculate_level_stats(self, entries: List[Dict]) -> Dict[str, int]:
        """计算层级统计"""
        level_counts = defaultdict(int)
        for entry in entries:
            level_counts[entry.get("level", "unknown")] += 1
        return dict(level_counts)

    def _generate_summary(
        self,
        stabilities: List[ModuleStability],
        overall_rate: float
    ) -> str:
        """生成摘要"""
        unstable = [s for s in stabilities if s.grade == "C"]
        if unstable:
            module_names = ", ".join(s.module for s in unstable[:3])
            return f"Overall: {overall_rate:.1%} | Unstable ({len(unstable)}): {module_names}"
        return f"Overall: {overall_rate:.1%} | All modules stable"

    def troubleshoot(self, module_name: str) -> str:
        """排查指定模块的历史"""
        entries = sorted(self._entries, key=lambda x: x["timestamp"])

        history = []
        for entry in entries[-10:]:
            for m in entry.get("modules", []):
                if m["module"] == module_name:
                    status = "PASS" if m.get("failed", 0) == 0 else "FAIL"
                    history.append(f"{entry['timestamp'][:19]} | {status}")

        if not history:
            return f"No history found for {module_name}"

        return f"{module_name} recent history:\n" + "\n".join(history)
```

---

### 题目 2：如何设计测试质量的监控和告警系统？

**参考答案：**

**质量监控的核心指标：**

```python
class QualityMetrics:
    """测试质量指标"""

    @dataclass
    class Thresholds:
        pass_rate_warning: float = 0.95
        pass_rate_critical: float = 0.80
        stability_warning: float = 0.90
        runs_per_week_min: int = 5

    @classmethod
    def evaluate(cls, report: AggregatedReport, thresholds: Thresholds) -> Dict:
        """评估质量状态"""
        issues = []

        if report.overall_pass_rate < thresholds.pass_rate_critical:
            issues.append({
                "level": "critical",
                "metric": "pass_rate",
                "value": report.overall_pass_rate,
                "message": f"Pass rate {report.overall_pass_rate:.1%} is critical"
            })
        elif report.overall_pass_rate < thresholds.pass_rate_warning:
            issues.append({
                "level": "warning",
                "metric": "pass_rate",
                "value": report.overall_pass_rate,
                "message": f"Pass rate {report.overall_pass_rate:.1%} is below threshold"
            })

        unstable_count = len([s for s in report.module_stabilities if s.grade == "C"])
        if unstable_count > 3:
            issues.append({
                "level": "warning",
                "metric": "unstable_modules",
                "value": unstable_count,
                "message": f"{unstable_count} modules are unstable"
            })

        return {
            "healthy": len([i for i in issues if i["level"] == "critical"]) == 0,
            "issues": issues
        }
```

**趋势分析：**

```python
class TrendAnalyzer:
    """趋势分析器"""

    def analyze(self, entries: List[Dict]) -> Dict[str, Any]:
        """分析质量趋势"""
        if len(entries) < 2:
            return {"trend": "insufficient_data"}

        sorted_entries = sorted(entries, key=lambda x: x["timestamp"])

        recent = sorted_entries[-7:]
        older = sorted_entries[-14:-7] if len(sorted_entries) >= 14 else sorted_entries[:-7]

        recent_pass_rate = self._calc_pass_rate(recent)
        older_pass_rate = self._calc_pass_rate(older)

        change = recent_pass_rate - older_pass_rate

        return {
            "recent_pass_rate": recent_pass_rate,
            "older_pass_rate": older_pass_rate,
            "change": change,
            "trend": "improving" if change > 0.05 else "degrading" if change < -0.05 else "stable"
        }

    def _calc_pass_rate(self, entries: List[Dict]) -> float:
        total_passed = sum(e.get("total_passed", 0) for e in entries)
        total_failed = sum(e.get("total_failed", 0) for e in entries)
        total = total_passed + total_failed
        return total_passed / total if total > 0 else 1.0
```

---

## 代码示例

```python
"""
Day 28 代码示例：测试报告聚合器完整实现
演示聚合统计、稳定性评分和趋势分析
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict
import json
import os


@dataclass
class ModuleStability:
    module: str
    runs: int = 0
    failures: int = 0
    total_passed: int = 0
    total_failed: int = 0
    last_failed: str = ""

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
    level_stats: Dict[str, int]
    summary: str


class ReportAggregator:
    def __init__(self, log_dir: str = "run_logs"):
        self.log_dir = log_dir
        self._entries: List[Dict] = []

    def _load_all(self) -> List[Dict]:
        entries = []
        if not os.path.exists(self.log_dir):
            return entries
        for filename in sorted(os.listdir(self.log_dir)):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(self.log_dir, filename)) as f:
                        entries.append(json.load(f))
                except Exception:
                    continue
        return entries

    def aggregate(self, days: int = 30) -> AggregatedReport:
        self._entries = self._load_all()
        if not self._entries:
            return AggregatedReport(0, "N/A", 1.0, [], {}, "No data")

        cutoff = datetime.now().timestamp() - (days * 86400)
        recent = [
            e for e in self._entries
            if datetime.fromisoformat(e["timestamp"]).timestamp() >= cutoff
        ]

        module_stats = self._calculate_module_stats(recent)
        level_stats = self._calculate_level_stats(recent)
        dates = sorted(set(e["timestamp"][:10] for e in recent))
        date_range = f"{dates[0]} ~ {dates[-1]}" if dates else "N/A"

        total_passed = sum(m.total_passed for m in module_stats)
        total_failed = sum(m.total_failed for m in module_stats)
        overall_rate = total_passed / (total_passed + total_failed) if (total_passed + total_failed) > 0 else 1.0

        return AggregatedReport(
            total_runs=len(recent),
            date_range=date_range,
            overall_pass_rate=overall_rate,
            module_stabilities=module_stats,
            level_stats=level_stats,
            summary=f"Overall: {overall_rate:.1%} | Modules: {len(module_stats)}"
        )

    def _calculate_module_stats(self, entries: List[Dict]) -> List[ModuleStability]:
        stats = defaultdict(lambda: {"runs": 0, "failures": 0, "passed": 0, "failed": 0, "last_failed": ""})
        for entry in entries:
            for m in entry.get("modules", []):
                module = m["module"]
                stats[module]["runs"] += 1
                stats[module]["passed"] += m.get("passed", 0)
                stats[module]["failed"] += m.get("failed", 0)
                if m.get("failed", 0) > 0:
                    stats[module]["failures"] += 1
                    stats[module]["last_failed"] = entry["timestamp"]

        return sorted([
            ModuleStability(module, data["runs"], data["failures"],
                          data["passed"], data["failed"], data["last_failed"])
            for module, data in stats.items()
        ], key=lambda x: x.pass_rate)

    def _calculate_level_stats(self, entries: List[Dict]) -> Dict[str, int]:
        counts = defaultdict(int)
        for e in entries:
            counts[e.get("level", "unknown")] += 1
        return dict(counts)

    def troubleshoot(self, module_name: str) -> str:
        if not self._entries:
            return "No data available"
        history = []
        for entry in sorted(self._entries, key=lambda x: x["timestamp"])[-10:]:
            for m in entry.get("modules", []):
                if m["module"] == module_name:
                    status = "PASS" if m.get("failed", 0) == 0 else "FAIL"
                    history.append(f"{entry['timestamp'][:19]} | {status}")
        return f"{module_name}:\n" + "\n".join(history) if history else f"No history for {module_name}"

    def generate_report(self, days: int = 7) -> str:
        report = self.aggregate(days)
        lines = [f"━━━ 测试报告聚合 ━━━",
                 f"日期范围: {report.date_range}",
                 f"运行次数: {report.total_runs}",
                 f"总体通过率: {report.overall_pass_rate:.2%}",
                 "",
                 "── 模块稳定性 ──"]
        for s in report.module_stabilities[:10]:
            lines.append(f"  {s.grade}  {s.module:35} Runs:{s.runs:3}  Fail%:{100*(1-s.pass_rate):5.1f}")
        return "\n".join(lines)


def demo():
    print("=" * 60)
    print("Day 28 代码示例：测试报告聚合器演示")
    print("=" * 60)

    agg = ReportAggregator()

    print("\n[1] 模拟聚合数据")
    print("-" * 40)

    mock_stabilities = [
        ModuleStability("d1_test.py", 10, 0, 80, 0),
        ModuleStability("d2_test.py", 10, 0, 75, 0),
        ModuleStability("d3_test.py", 10, 1, 78, 2),
        ModuleStability("d4_test.py", 10, 3, 70, 5),
    ]

    for s in mock_stabilities:
        print(f"  {s.grade}  {s.module:15}  pass_rate={s.pass_rate:.1%}  runs={s.runs}  failures={s.failures}")

    print("\n[2] 稳定性评分说明")
    print("-" * 40)
    print("  Grade A: pass_rate >= 95%  (稳定)")
    print("  Grade B: pass_rate >= 80%  (偶尔波动)")
    print("  Grade C: pass_rate < 80%   (需要关注)")

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
```

---

## 练习题

### 练习 1：实现测试质量趋势预测

**要求：**
基于历史数据，预测下一个周期的测试通过率走势。

**提示：**
```python
class QualityPredictor:
    """质量趋势预测"""
    def __init__(self, window_size: int = 5):
        self.window_size = window_size

    def predict(self, historical_rates: List[float]) -> Dict[str, Any]:
        """预测下期通过率"""
        pass
```

**验收标准：**
- 使用移动平均进行预测
- 返回预测值和置信区间
- 判断趋势方向（上升/下降/平稳）

---

### 练习 2：实现不稳定模块自动归类

**要求：**
将所有不稳定的模块按失败模式自动归类（随机失败、持续失败、偶发失败）。

**提示：**
```python
class FailureClassifier:
    """失败模式分类"""
    @dataclass
    class FailurePattern:
        module: str
        pattern: str  # "random", "consistent", "sporadic"
        confidence: float

    def classify(self, stabilities: List[ModuleStability]) -> List[FailurePattern]:
        """分类失败模式"""
        pass
```

**验收标准：**
- 识别随机失败（低失败率，偶尔发生）
- 识别持续失败（高失败率）
- 识别偶发失败（有规律或周期性）

---

### 练习 3：实现测试报告可视化导出

**要求：**
实现将聚合报告导出为多种格式（JSON、Markdown、HTML）。

**提示：**
```python
class ReportExporter:
    """报告导出器"""
    def to_json(self, report: AggregatedReport) -> str:
        pass

    def to_markdown(self, report: AggregatedReport) -> str:
        pass

    def to_html(self, report: AggregatedReport) -> str:
        pass
```

**验收标准：**
- 导出为格式化的 JSON
- 导出为 Markdown 表格
- 导出为带样式的 HTML

---

## 八、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d28_report_aggregator.py` | 报告聚合器 | [OK] |
| `tests/d28_test_report_aggregator.py` | 15 个测试 | [OK] 15/15 PASS |
| `day28_study.md` | 本文档 | [OK] 已创建 |
