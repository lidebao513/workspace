"""
D29 — 质量门禁仪表盘测试
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.d29_dashboard import MetricIndicator, HealthItem, DashboardReport, DashboardBuilder


def test_metric_indicator_green():
    m = MetricIndicator("通过率", 0.97, 0.95, 0.80)
    assert m.color == "green"
    assert m.emoji == "🟢"


def test_metric_indicator_yellow():
    m = MetricIndicator("通过率", 0.85, 0.95, 0.80)
    assert m.color == "yellow"
    assert m.emoji == "🟡"


def test_metric_indicator_red():
    m = MetricIndicator("通过率", 0.70, 0.95, 0.80)
    assert m.color == "red"
    assert m.emoji == "🔴"


def test_health_item():
    h = HealthItem("通过率", "PASS", "All good")
    assert h.status == "PASS"
    assert h.name == "通过率"


def test_dashboard_report_display():
    report = DashboardReport(
        timestamp="2026-04-30T19:00:00",
        pass_rate=0.97,
        module_count=5,
        unstable_count=0,
        indicators=[MetricIndicator("通过率", 0.97)],
        health_items=[HealthItem("测试", "PASS", "OK")],
        summary="✅ All good",
    )
    display = report.display()
    assert "AI 测试平台仪表盘" in display
    assert "通过率" in display
    assert "🟢" in display


def test_builder_all_green():
    builder = DashboardBuilder()
    builder.add_pass_rate(0.97)
    builder.add_module_stability(total=20, unstable=0)
    builder.add_pass_rate_check(0.97)
    builder.add_runs_count(10)
    builder.add_total_time(45)
    report = builder.build()
    assert report.summary.startswith("✅")
    assert len(report.indicators) >= 2
    assert len(report.health_items) >= 5


def test_builder_partial_warn():
    builder = DashboardBuilder()
    builder.add_pass_rate(0.88)
    builder.add_module_stability(total=20, unstable=4)
    builder.add_pass_rate_check(0.88)
    builder.add_runs_count(2)
    builder.add_total_time(90)
    report = builder.build()
    assert "🟡" in report.summary or "🔴" in report.summary or "全部检查通过" not in report.summary


def test_builder_red_fail():
    builder = DashboardBuilder()
    builder.add_pass_rate(0.70)
    builder.add_module_stability(total=10, unstable=5)
    builder.add_pass_rate_check(0.70)
    report = builder.build()
    assert "🔴" in report.summary or "未通过" in report.summary


def test_builder_custom_check():
    builder = DashboardBuilder()
    builder.add_custom_check("API 连通性", True, "API 正常", "API 异常")
    builder.add_custom_check("配置检查", False, "OK", "配置缺失")
    report = builder.build()
    pass_count = sum(1 for h in report.health_items if h.status == "PASS")
    fail_count = sum(1 for h in report.health_items if h.status == "FAIL")
    assert pass_count == 1
    assert fail_count == 1


def test_builder_high_module_stability():
    builder = DashboardBuilder()
    builder.add_module_stability(total=30, unstable=0)
    report = builder.build()
    health = [h for h in report.health_items if "模块稳定性" in h.name]
    assert len(health) > 0
    assert health[0].status == "PASS"


def test_builder_low_runs():
    builder = DashboardBuilder()
    builder.add_runs_count(1)
    report = builder.build()
    health = [h for h in report.health_items if "测试频次" in h.name]
    assert len(health) > 0
    assert health[0].status == "WARN"


def test_dashboard_report_empty():
    builder = DashboardBuilder()
    report = builder.build()
    assert report.pass_rate == 1.0
    assert len(report.health_items) == 0
