# Day 29 — 质量门禁仪表盘

## 学习目标

1. 理解 MetricIndicator 的三色阈值机制（绿/黄/红）
2. 掌握 DashboardBuilder 的链式构建模式
3. 学会整合多个模块的检查结果
4. 理解"门禁"概念：通过率低于阈值阻止发布

---

## 一、今日目标

> 整合全量运行器（d27）、报告聚合器（d28）、门禁策略到统一的 Dashboard 中。用颜色标记健康状态：🟢绿色正常、🟡黄色警告、🔴红色危险。一张仪表盘看到所有模块的健康度。

- 理解 MetricIndicator 的三色阈值机制
- 掌握 DashboardBuilder 的链式构建模式
- 学会整合多个模块的检查结果
- 理解"门禁"概念：通过率 < 80% 就是 FAIL

---

## 二、为什么需要仪表盘？

FullTestRunner 跑完测试，ReportAggregator 聚合数据——但最终输出的文本还不够直观。需要一个**一目了然**的仪表盘：

- 绿色 = 不需要看
- 黄色 = 瞄一眼
- 红色 = 必须处理

这就是"门禁"（Gate）的概念：低于阈值的项阻止发布。

---

## 三、核心结构

### 3.1 MetricIndicator（指标指示器）

```python
@dataclass
class MetricIndicator:
    name: str                     # 指标名称
    value: float                  # 当前值
    threshold_good: float = 0.95  # 绿色阈值（>= 此值）
    threshold_warn: float = 0.80  # 黄色阈值（>= 此值）
    unit: str = ""                # 单位

    @property
    def color(self) -> str:       # "green" / "yellow" / "red"
    @property
    def emoji(self) -> str:       # "🟢" / "🟡" / "🔴"
```

### 3.2 HealthItem（健康检查项）

```python
@dataclass
class HealthItem:
    name: str     # 检查项名称
    status: str   # "PASS" / "WARN" / "FAIL"
    message: str  # 描述
    details: str  # 详情（可选）
```

### 3.3 DashboardReport（仪表盘报告）

```python
@dataclass
class DashboardReport:
    timestamp: str
    pass_rate: float
    module_count: int
    unstable_count: int
    indicators: List[MetricIndicator]   # 关键指标
    health_items: List[HealthItem]      # 健康检查
    summary: str                        # 一句话总结

    def display(self) -> str:
        # 格式化为可读仪表盘
```

---

## 四、仪表盘示例输出

```
━━━ AI 测试平台仪表盘 ━━━
生成时间: 2026-04-30T19:25:12

── 关键指标 ──
  🟢 测试通过率: 97.0%
  🟢 模块稳定率: 100.0%
  🟢 运行次数: 10.0次/周期
  🟢 全量耗时: 45.0s

── 健康检查 ──
  ✅ 模块稳定性: 全部 20 个模块稳定
  ✅ 整体通过率: 通过率 97.0% >= 95%
  ✅ 测试频次: 最近运行 10 次（>= 5 次/周期）
  ✅ 运行耗时: 全量测试 45.0s，运行效率良好

总结: ✅ 全部检查通过，项目健康
```

---

## 五、Builder 使用流程

```
DashboardBuilder()
  ├── .add_pass_rate(0.97)           → 添加通过率指标 + 通过率检查
  ├── .add_module_stability(20, 0)   → 添加稳定性指标 + 不稳定模块检查
  ├── .add_pass_rate_check(0.97)     → 门禁通过率检查
  ├── .add_runs_count(10)            → 添加运行次数检查
  ├── .add_total_time(45)            → 添加运行耗时检查
  ├── .add_custom_check(...)         → 自定义检查项
  └── .build()                       → 返回 DashboardReport
```

---

## 六、门禁策略

| 指标 | 🟢 正常（PASS） | 🟡 警告（WARN） | 🔴 危险（FAIL） |
|------|-----------------|-----------------|----------------|
| 通过率 | >= 95% | >= 80% | < 80% |
| 模块稳定率 | >= 90% | >= 75% | < 75% |
| 不稳定模块数 | 0 | 1-3 个 | 3+ 个 |
| 运行次数/周期 | >= 5 | >= 2 | < 2 |

---

## 七、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| 指标颜色 | 97% / 85% / 70% | 🟢 / 🟡 / 🔴 |
| 全部通过 | pass_rate=97%, unstable=0 | 摘要以 ✅ 开头 |
| 部分警告 | pass_rate=88%, unstable=4 | 摘要含 🟡/🔴 |
| 严重失败 | pass_rate=70%, unstable=5 | 摘要含 🔴+未通过 |
| 自定义检查 | 传入 passed=True/False | 对应 PASS/FAIL |
| 低运行频次 | runs_count=1 | 状态 WARN |
| 空仪表盘 | 无检查项 | health_items=0 |

---

## 面试题

### 题目 1：如何设计一个测试质量门禁系统？

**参考答案：**

**门禁系统的核心价值：**

质量门禁（Quality Gate）是 CI/CD 流程中的关键关卡，用于：
- 确保发布前质量达标
- 防止不合格代码进入生产环境
- 提供客观的质量评估标准

**三色预警机制设计：**

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from datetime import datetime


class HealthLevel(Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class ThresholdConfig:
    """阈值配置"""
    green_threshold: float = 0.95
    yellow_threshold: float = 0.80
    warning_unstable_count: int = 3
    critical_unstable_count: int = 5


@dataclass
class HealthItem:
    """健康检查项"""
    name: str
    value: float
    level: HealthLevel
    message: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class GateResult:
    """门禁结果"""
    passed: bool
    health_items: List[HealthItem]
    overall_level: HealthLevel
    summary: str
    blocked: bool = False


class MetricIndicator:
    """指标指示器"""

    def __init__(self, thresholds: Optional[ThresholdConfig] = None):
        self.thresholds = thresholds or ThresholdConfig()

    def evaluate(self, name: str, value: float) -> HealthItem:
        """评估指标值并返回健康级别"""
        if value >= self.thresholds.green_threshold:
            level = HealthLevel.GREEN
            message = f"{name}: {value:.2%} (OK)"
        elif value >= self.thresholds.yellow_threshold:
            level = HealthLevel.YELLOW
            message = f"{name}: {value:.2%} (Warning)"
        else:
            level = HealthLevel.RED
            message = f"{name}: {value:.2%} (Critical)"

        return HealthItem(name=name, value=value, level=level, message=message)


class DashboardBuilder:
    """仪表盘构建器（链式调用）"""

    def __init__(self):
        self._checks: List[HealthItem] = []
        self._thresholds = ThresholdConfig()

    def with_threshold(self, thresholds: ThresholdConfig) -> "DashboardBuilder":
        """设置阈值配置"""
        self._thresholds = thresholds
        return self

    def add_check(self, name: str, value: float) -> "DashboardBuilder":
        """添加检查项"""
        indicator = MetricIndicator(self._thresholds)
        self._checks.append(indicator.evaluate(name, value))
        return self

    def add_custom_check(
        self,
        name: str,
        passed: bool,
        message: str = ""
    ) -> "DashboardBuilder":
        """添加自定义检查"""
        level = HealthLevel.GREEN if passed else HealthLevel.RED
        self._checks.append(HealthItem(
            name=name,
            value=1.0 if passed else 0.0,
            level=level,
            message=message or (f"{name}: {'PASS' if passed else 'FAIL'}")
        ))
        return self

    def build(self) -> GateResult:
        """构建门禁结果"""
        if not self._checks:
            return GateResult(
                passed=True,
                health_items=[],
                overall_level=HealthLevel.GREEN,
                summary="No checks performed"
            )

        red_items = [c for c in self._checks if c.level == HealthLevel.RED]
        yellow_items = [c for c in self._checks if c.level == HealthLevel.YELLOW]

        overall_level = HealthLevel.RED if red_items else (
            HealthLevel.YELLOW if yellow_items else HealthLevel.GREEN
        )

        passed = len(red_items) == 0

        summary_parts = []
        if overall_level == HealthLevel.GREEN:
            summary_parts.append("🟢 All checks passed")
        elif overall_level == HealthLevel.YELLOW:
            summary_parts.append(f"🟡 {len(yellow_items)} warning(s)")
        else:
            summary_parts.append(f"🔴 {len(red_items)} failure(s)")

        return GateResult(
            passed=passed,
            health_items=self._checks,
            overall_level=overall_level,
            summary=" | ".join(summary_parts),
            blocked=not passed
        )

    def render(self) -> str:
        """渲染仪表盘文本"""
        result = self.build()
        lines = ["━━━ 质量门禁仪表盘 ━━━", f"状态: {result.summary}", ""]

        for item in result.health_items:
            icon = "🟢" if item.level == HealthLevel.GREEN else (
                "🟡" if item.level == HealthLevel.YELLOW else "🔴"
            )
            lines.append(f"  {icon} {item.message}")

        if result.blocked:
            lines.append("")
            lines.append("━━━ 发布被阻止 ━━━")

        return "\n".join(lines)
```

---

### 题目 2：如何在测试框架中实现多维度质量评估？

**参考答案：**

**多维度质量评估框架：**

```python
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime


@dataclass
class QualityDimension:
    """质量维度"""
    name: str
    weight: float
    score: float
    threshold: float


@dataclass
class QualityReport:
    """质量报告"""
    timestamp: str
    dimensions: List[QualityDimension]
    overall_score: float
    grade: str
    recommendations: List[str]


class QualityEvaluator:
    """多维度质量评估器"""

    def __init__(self):
        self._dimensions: List[QualityDimension] = []

    def add_dimension(
        self,
        name: str,
        score: float,
        weight: float = 1.0,
        threshold: float = 0.8
    ) -> "QualityEvaluator":
        """添加质量维度"""
        self._dimensions.append(QualityDimension(
            name=name,
            weight=weight,
            score=score,
            threshold=threshold
        ))
        return self

    def evaluate(self) -> QualityReport:
        """执行评估"""
        total_weight = sum(d.weight for d in self._dimensions)
        weighted_score = sum(d.score * d.weight for d in self._dimensions)
        overall = weighted_score / total_weight if total_weight > 0 else 0.0

        recommendations = []
        for d in self._dimensions:
            if d.score < d.threshold:
                recommendations.append(f"Improve {d.name}: {d.score:.1%} < {d.threshold:.1%}")

        grade = self._calculate_grade(overall)

        return QualityReport(
            timestamp=datetime.now().isoformat(),
            dimensions=self._dimensions,
            overall_score=overall,
            grade=grade,
            recommendations=recommendations
        )

    def _calculate_grade(self, score: float) -> str:
        if score >= 0.95:
            return "A"
        elif score >= 0.85:
            return "B"
        elif score >= 0.70:
            return "C"
        return "D"
```

---

## 代码示例

```python
"""
Day 29 代码示例：质量门禁仪表盘完整实现
演示三色预警机制和链式构建模式
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


class HealthLevel(Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class ThresholdConfig:
    green_threshold: float = 0.95
    yellow_threshold: float = 0.80
    warning_unstable_count: int = 3


@dataclass
class HealthItem:
    name: str
    value: float
    level: HealthLevel
    message: str


@dataclass
class GateResult:
    passed: bool
    health_items: List[HealthItem]
    overall_level: HealthLevel
    summary: str
    blocked: bool = False


class MetricIndicator:
    def __init__(self, thresholds: Optional[ThresholdConfig] = None):
        self.thresholds = thresholds or ThresholdConfig()

    def evaluate(self, name: str, value: float) -> HealthItem:
        if value >= self.thresholds.green_threshold:
            level = HealthLevel.GREEN
            message = f"{name}: {value:.2%} (OK)"
        elif value >= self.thresholds.yellow_threshold:
            level = HealthLevel.YELLOW
            message = f"{name}: {value:.2%} (Warning)"
        else:
            level = HealthLevel.RED
            message = f"{name}: {value:.2%} (Critical)"
        return HealthItem(name=name, value=value, level=level, message=message)


class DashboardBuilder:
    def __init__(self):
        self._checks: List[HealthItem] = []
        self._thresholds = ThresholdConfig()

    def with_threshold(self, thresholds: ThresholdConfig) -> "DashboardBuilder":
        self._thresholds = thresholds
        return self

    def add_check(self, name: str, value: float) -> "DashboardBuilder":
        indicator = MetricIndicator(self._thresholds)
        self._checks.append(indicator.evaluate(name, value))
        return self

    def add_custom_check(
        self,
        name: str,
        passed: bool,
        message: str = ""
    ) -> "DashboardBuilder":
        level = HealthLevel.GREEN if passed else HealthLevel.RED
        self._checks.append(HealthItem(
            name=name,
            value=1.0 if passed else 0.0,
            level=level,
            message=message or f"{name}: {'PASS' if passed else 'FAIL'}"
        ))
        return self

    def build(self) -> GateResult:
        if not self._checks:
            return GateResult(True, [], HealthLevel.GREEN, "No checks")

        red_items = [c for c in self._checks if c.level == HealthLevel.RED]
        yellow_items = [c for c in self._checks if c.level == HealthLevel.YELLOW]

        overall_level = HealthLevel.RED if red_items else (
            HealthLevel.YELLOW if yellow_items else HealthLevel.GREEN
        )

        summary_parts = []
        if overall_level == HealthLevel.GREEN:
            summary_parts.append("🟢 All passed")
        elif overall_level == HealthLevel.YELLOW:
            summary_parts.append(f"🟡 {len(yellow_items)} warning(s)")
        else:
            summary_parts.append(f"🔴 {len(red_items)} failure(s)")

        return GateResult(
            passed=len(red_items) == 0,
            health_items=self._checks,
            overall_level=overall_level,
            summary=" | ".join(summary_parts),
            blocked=len(red_items) > 0
        )

    def render(self) -> str:
        result = self.build()
        lines = ["━━━ 质量门禁仪表盘 ━━━", f"状态: {result.summary}", ""]
        for item in result.health_items:
            icon = "🟢" if item.level == HealthLevel.GREEN else (
                "🟡" if item.level == HealthLevel.YELLOW else "🔴"
            )
            lines.append(f"  {icon} {item.message}")
        if result.blocked:
            lines.extend(["", "━━━ 发布被阻止 ━━━"])
        return "\n".join(lines)


def demo():
    print("=" * 60)
    print("Day 29 代码示例：质量门禁仪表盘演示")
    print("=" * 60)

    print("\n[1] 正常情况 - 所有检查通过")
    print("-" * 40)
    dashboard1 = (
        DashboardBuilder()
        .add_check("通过率", 0.98)
        .add_check("稳定性", 0.96)
        .add_custom_check("安全扫描", True)
    )
    print(dashboard1.render())

    print("\n[2] 警告情况 - 部分指标不达标")
    print("-" * 40)
    dashboard2 = (
        DashboardBuilder()
        .add_check("通过率", 0.88)
        .add_check("稳定性", 0.92)
        .add_custom_check("代码覆盖", True)
    )
    print(dashboard2.render())

    print("\n[3] 危险情况 - 发布被阻止")
    print("-" * 40)
    dashboard3 = (
        DashboardBuilder()
        .add_check("通过率", 0.75)
        .add_check("稳定性", 0.70)
        .add_custom_check("安全扫描", False, "发现高危漏洞")
    )
    print(dashboard3.render())

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
```

---

## 练习题

### 练习 1：实现自定义阈值配置

**要求：**
扩展 DashboardBuilder，支持针对不同类型指标使用不同的阈值配置。

**提示：**
```python
class TieredThresholdConfig:
    """分层阈值配置"""
    pass_rate_thresholds: ThresholdConfig
    stability_thresholds: ThresholdConfig
    coverage_thresholds: ThresholdConfig

def add_check_with_type(
    self,
    name: str,
    value: float,
    check_type: str  # "pass_rate", "stability", "coverage"
) -> "DashboardBuilder":
    """根据类型使用不同阈值"""
    pass
```

**验收标准：**
- 不同指标类型可使用不同阈值
- 支持自定义阈值配置
- 链式调用保持正常工作

---

### 练习 2：实现历史趋势健康检查

**要求：**
基于历史数据，判断当前指标是"改善"还是"退化"。

**提示：**
```python
class TrendIndicator:
    """趋势指示器"""
    def __init__(self, window_size: int = 5):
        self.window_size = window_size

    def check_trend(
        self,
        current_value: float,
        historical_values: List[float]
    ) -> HealthLevel:
        """检查趋势健康状态"""
        pass
```

**验收标准：**
- 持续上升趋势返回 GREEN
- 持续下降趋势返回 RED 或 YELLOW
- 趋势平稳返回 GREEN

---

### 练习 3：实现门禁拦截通知

**要求：**
当门禁失败时，生成详细的拦截报告并支持通知。

**提示：**
```python
class GateNotifier:
    """门禁通知器"""
    def __init__(self):
        self._handlers: List[Callable] = []

    def add_handler(self, handler: Callable) -> "GateNotifier":
        """添加通知处理器"""
        pass

    def notify_blocked(self, result: GateResult) -> None:
        """发送拦截通知"""
        pass

    def generate_block_report(self, result: GateResult) -> str:
        """生成拦截报告"""
        pass
```

**验收标准：**
- 支持多个通知处理器
- 生成包含所有失败项的报告
- 包含修复建议

---

## 八、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d29_dashboard.py` | 仪表盘构建器 | [OK] |
| `tests/d29_test_dashboard.py` | 12 个测试 | [OK] 12/12 PASS |
| `day29_study.md` | 本文档 | [OK] 已创建 |
