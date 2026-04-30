# Day 28 — 测试报告聚合器

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

## 八、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d28_report_aggregator.py` | 报告聚合器 | [OK] |
| `tests/d28_test_report_aggregator.py` | 15 个测试 | [OK] 15/15 PASS |
| `day28_study.md` | 本文档 | [OK] 已创建 |
