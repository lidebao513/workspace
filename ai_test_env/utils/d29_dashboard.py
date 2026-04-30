"""
Day 29 — 质量门禁仪表盘

功能：
    整合 d17 TestSuiteManager（分层）、d18 CIGate（门禁）、
    d23 RetryEngine（重试）、d28 ReportAggregator（报告）
    到一个统一的 Dashboard 中。

    通过率、模块稳定性、运行次数等关键指标用颜色标记：
    - 🟢 正常（通过率 >= 95%）
    - 🟡 警告（通过率 >= 80%）
    - 🔴 危险（通过率 < 80%）

面试话术：
    "我整合了分层管理、门禁策略和报告聚合三个模块，
    做成一个 Dashboard。关键指标用颜色标记：
    绿色正常、黄色需要关注、红色必须处理。
    每天早上 CI 运行结束后自动输出，一眼看到项目健康状态。"
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MetricIndicator:
    """指标指示器"""
    name: str
    value: float
    threshold_good: float = 0.95
    threshold_warn: float = 0.80
    unit: str = ""

    @property
    def color(self) -> str:
        if self.value >= self.threshold_good:
            return "green"
        elif self.value >= self.threshold_warn:
            return "yellow"
        else:
            return "red"

    @property
    def emoji(self) -> str:
        return {"green": "🟢", "yellow": "🟡", "red": "🔴"}[self.color]


@dataclass
class HealthItem:
    """健康检查项"""
    name: str
    status: str          # "PASS" / "WARN" / "FAIL"
    message: str
    details: str = ""


@dataclass
class DashboardReport:
    """仪表盘报告"""
    timestamp: str
    pass_rate: float
    module_count: int
    unstable_count: int
    indicators: List[MetricIndicator]
    health_items: List[HealthItem]
    summary: str = ""

    def display(self) -> str:
        lines = [
            "━━━ AI 测试平台仪表盘 ━━━",
            f"生成时间: {self.timestamp[:19]}",
            "",
            "── 关键指标 ──",
        ]
        for ind in self.indicators:
            display_val = f"{ind.value:.1%}" if ind.value <= 1 else f"{ind.value:.1f}"
            lines.append(
                f"  {ind.emoji} {ind.name}: {display_val}{ind.unit}"
            )

        lines.extend(["", "── 健康检查 ──"])
        for h in self.health_items:
            s_emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}[h.status]
            lines.append(f"  {s_emoji} {h.name}: {h.message}")

        lines.extend(["", f"总结: {self.summary}"])
        return "\n".join(lines)


class DashboardBuilder:
    """
    仪表盘构建器

    整合各模块的检查结果，生成统一 DashboardReport。
    """

    def __init__(self):
        self._items: List[HealthItem] = []
        self._indicators: List[MetricIndicator] = []
        self._pass_rate: float = 1.0
        self._module_count: int = 0
        self._unstable_count: int = 0

    def add_pass_rate(self, rate: float):
        """添加通过率指标"""
        self._pass_rate = rate
        self._indicators.append(MetricIndicator(
            name="测试通过率",
            value=rate,
            threshold_good=0.95,
            threshold_warn=0.80,
            unit="",
        ))

    def add_module_stability(self, total: int, unstable: int):
        """添加模块稳定性指标"""
        self._module_count = total
        self._unstable_count = unstable
        stability = 1.0 - (unstable / max(total, 1))
        self._indicators.append(MetricIndicator(
            name="模块稳定率",
            value=stability,
            threshold_good=0.90,
            threshold_warn=0.75,
            unit="",
        ))
        if unstable > 0:
            self._items.append(HealthItem(
                name="不稳定模块",
                status="WARN" if unstable <= 3 else "FAIL",
                message=f"{unstable}/{total} 个模块稳定性为 Grade C",
                details=f"需排查: {unstable} 个模块",
            ))
        else:
            self._items.append(HealthItem(
                name="模块稳定性",
                status="PASS",
                message=f"全部 {total} 个模块稳定",
            ))

    def add_pass_rate_check(self, rate: float):
        """门禁通过率检查"""
        if rate >= 0.95:
            self._items.append(HealthItem(
                name="整体通过率",
                status="PASS",
                message=f"通过率 {rate:.1%} >= 95%",
            ))
        elif rate >= 0.80:
            self._items.append(HealthItem(
                name="整体通过率",
                status="WARN",
                message=f"通过率 {rate:.1%} < 95%，需关注",
            ))
        else:
            self._items.append(HealthItem(
                name="整体通过率",
                status="FAIL",
                message=f"通过率 {rate:.1%} < 80%，必须处理",
            ))

    def add_runs_count(self, count: int):
        """运行次数检查"""
        if count >= 5:
            self._indicators.append(MetricIndicator(
                name="运行次数",
                value=float(count),
                threshold_good=5,
                threshold_warn=2,
                unit="次/周期",
            ))
            self._items.append(HealthItem(
                name="测试频次",
                status="PASS",
                message=f"最近运行 {count} 次（>= 5 次/周期）",
            ))
        else:
            self._items.append(HealthItem(
                name="测试频次",
                status="WARN",
                message=f"最近仅运行 {count} 次，建议增加频率",
            ))

    def add_total_time(self, seconds: float):
        """总耗时检查"""
        if seconds < 60:
            status = "PASS"
            msg = f"全量测试 {seconds:.1f}s，运行效率良好"
        elif seconds < 120:
            status = "WARN"
            msg = f"全量测试 {seconds:.1f}s，考虑分层优化"
        else:
            status = "WARN"
            msg = f"全量测试 {seconds:.1f}s，建议 CI 只跑 smoke+security"
        self._items.append(HealthItem("运行耗时", status, msg))
        self._indicators.append(MetricIndicator(
            name="全量耗时",
            value=seconds,
            threshold_good=60,
            threshold_warn=120,
            unit="s",
        ))

    def add_custom_check(self, name: str, passed: bool,
                          pass_message: str, fail_message: str):
        """自定义检查项"""
        self._items.append(HealthItem(
            name=name,
            status="PASS" if passed else "FAIL",
            message=pass_message if passed else fail_message,
        ))

    def build(self) -> DashboardReport:
        """构建报告"""
        # 生成摘要
        all_pass = all(h.status == "PASS" for h in self._items)
        red_count = sum(1 for h in self._items if h.status == "FAIL")

        if all_pass:
            summary = "✅ 全部检查通过，项目健康"
        elif red_count > 0:
            summary = f"🔴 {red_count} 项未通过，需立即处理"
        else:
            summary = "🟡 部分检查处于警告状态，建议关注"

        return DashboardReport(
            timestamp=datetime.now().isoformat(),
            pass_rate=self._pass_rate,
            module_count=self._module_count,
            unstable_count=self._unstable_count,
            indicators=self._indicators,
            health_items=self._items,
            summary=summary,
        )
