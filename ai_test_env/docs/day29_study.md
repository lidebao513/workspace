# Day 29 — 质量门禁仪表盘

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

## 八、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d29_dashboard.py` | 仪表盘构建器 | [OK] |
| `tests/d29_test_dashboard.py` | 12 个测试 | [OK] 12/12 PASS |
| `day29_study.md` | 本文档 | [OK] 已创建 |
