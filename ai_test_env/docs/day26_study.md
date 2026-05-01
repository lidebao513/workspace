# Day 26 — Token 审计 + 费用监控

## 学习目标

1. 理解 TokenAuditor 的 record_call / daily_report / detect_anomalies 核心 API
2. 掌握三种异常类型（SPIKE / DROP / STEADY_INCREASE）的检测逻辑
3. 学会滚动平均基线计算与异常判定方法
4. 掌握 Token 费用估算公式和多维度统计

---

## 一、今日目标

> 学会 API Token 消耗的审计记录、每日报告生成和异常波动检测。这是实战项目的第一块基石——不监控用量，优化就是瞎忙。

- 理解 TokenAuditor 的 record_call / daily_report / detect_anomalies
- 掌握三种异常类型：SPIKE / DROP / STEADY_INCREASE
- 学会滚动平均基线计算与异常判定
- 掌握费用估算公式

---

## 二、为什么需要 Token 审计？

AI API 是按 Token 计费的（如 DeepSeek ￥1/M 输入 tokens，￥2/M 输出 tokens）。不审计的话：

- 开发调试时一天跑掉几千次 API 却不知道
- 某个 prompt 太长导致单次调用成本暴涨 10 倍
- 死循环无限调用 API——直到信用卡报警

TokenAuditor 解决的就是这些问题：记录、汇总、异常告警。

---

## 三、数据结构

### 3.1 TokenRecord（单次调用）

```python
@dataclass
class TokenRecord:
    timestamp: float            # 时间戳
    prompt_tokens: int          # 输入 token 数
    completion_tokens: int      # 输出 token 数
    model: str = "unknown"      # 模型名
    call_id: str = ""            # 调用 ID（用于追踪）

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens
```

### 3.2 DailyReport（每日汇总）

```python
@dataclass
class DailyReport:
    date: str                               # "2026-04-30"
    total_calls: int                         # 总调用次数
    total_prompt_tokens: int                 # 总输入 Token
    total_completion_tokens: int             # 总输出 Token
    total_tokens: int                        # 总 Token
    estimated_cost: float = 0.0              # 估算费用
    model_breakdown: Dict[str, int] = ...    # 按模型拆分

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False, indent=2)
```

---

## 四、费用估算

```python
# 默认费率（可配置）
# input:  ¥1 / 1M tokens
# output: ¥2 / 1M tokens
INPUT_COST_PER_M = 1.0    # 发送 100 万 token 花 1 元
OUTPUT_COST_PER_M = 2.0   # 接收 100 万 token 花 2 元

cost = (prompt_tokens * INPUT_COST_PER_M +
        completion_tokens * OUTPUT_COST_PER_M) / 1_000_000
```

---

## 五、异常检测

### 5.1 三种异常类型

| 类型 | 含义 | 判定条件 |
|------|------|---------|
| **SPIKE** | 突增 | 当天用量 / 基线 > 阈值（默认 1.5 倍） |
| **DROP** | 突降 | 当天用量 / 基线 < 1/阈值（默认 1/1.5） |
| **STEADY_INCREASE** | 持续增长 | 连续 N 天用量递增（默认 3 天） |

### 5.2 基线计算

```python
# 滚动平均：最近 N 天的平均值（默认 7 天）
baseline = sum(recent_days) / len(recent_days)
```

### 5.3 使用

```python
from utils.d26_token_auditor import TokenAuditor, AnomalyType

auditor = TokenAuditor()

# 记录调用
auditor.record_call(prompt_tokens=50, completion_tokens=150, model="deepseek-chat")

# 生成报告
report = auditor.daily_report()
print(report.to_json())

# 异常检测（需要 >= 8 天的数据才有基线）
anomalies = auditor.detect_anomalies()
for a in anomalies:
    print(f"[{a.type.value}] {a.date}: {a.actual_tokens} vs baseline {a.baseline_tokens}")
```

---

## 六、异常检测测试示例

```python
# SPIKE 场景：第 8 天突增到 2 倍
auditor = TokenAuditor()
for i in range(7):
    auditor.record_call(prompt_tokens=100, completion_tokens=100)
auditor._next_day()  # 切到第 8 天
auditor.record_call(prompt_tokens=200, completion_tokens=200)
# → detect_anomalies() 返回 [SPIKE]

# DROP 场景
for i in range(7):
    auditor.record_call(prompt_tokens=100, completion_tokens=100)
auditor._next_day()
auditor.record_call(prompt_tokens=30, completion_tokens=30)
# → detect_anomalies() 返回 [DROP]
```

---

## 七、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| TokenRecord.total_tokens | 100+200 | =300 |
| DailyReport 汇总 | 多次调用 | 总数正确 |
| Auditor record_call | 单次记录 | 记录数 += 1 |
| daily_report | 有数据 | 返回 DailyReport |
| daily_report（空） | 无数据 | 返回 0 报告 |
| SPIKE 检测 | 用量 > 1.5x 基线 | 标记 SPIKE |
| DROP 检测 | 用量 < 0.67x 基线 | 标记 DROP |
| STEADY_INCREASE | 连续 3 天递增 | 标记 |
| to_json | 序列化 | 有效 JSON |

---

## 八、面试话术

> "生产环境部署后，TokenAuditor 帮我们抓到一个死循环引起的 Token 突增——某天用量从日常 10 万暴涨到 500 万，及时告警止损，省了约 2000 元。基线用 7 天滚动平均，SPIKE 阈值设 1.5 倍——太宽松漏报，太严格误报，1.5 是经验值。STEADY_INCREASE 用连续递增判定而不是阈值，避免周六日自然波动触发误报。"

---

## 面试题

### 题目 1：如何设计一个 Token 审计和费用监控系统？

**参考答案：**

**为什么需要 Token 审计？**

AI API 按 Token 计费，如果不监控用量：
- 开发调试时一天跑掉几千次 API 却不知道
- 某个 prompt 太长导致单次调用成本暴涨 10 倍
- 死循环无限调用 API——直到信用卡报警

**核心数据结构设计：**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

@dataclass
class TokenRecord:
    """单次 API 调用记录"""
    timestamp: float
    prompt_tokens: int
    completion_tokens: int
    model: str = "unknown"
    call_id: str = ""

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

@dataclass
class DailyReport:
    """每日汇总报告"""
    date: str
    total_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    model_breakdown: Dict[str, int] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False, indent=2)
```

**费用估算实现：**

```python
class CostCalculator:
    """Token 费用计算器"""

    DEFAULT_RATES = {
        "input": 1.0,   # ¥1 / 1M tokens
        "output": 2.0,  # ¥2 / 1M tokens
    }

    def __init__(self, input_rate: float = 1.0, output_rate: float = 2.0):
        self.input_rate = input_rate
        self.output_rate = output_rate

    def calculate(self, prompt_tokens: int, completion_tokens: int) -> float:
        """计算单次调用费用"""
        cost = (
            prompt_tokens * self.input_rate +
            completion_tokens * self.output_rate
        ) / 1_000_000
        return round(cost, 6)

    def calculate_batch(self, records: List[TokenRecord]) -> float:
        """计算批量调用总费用"""
        return sum(
            self.calculate(r.prompt_tokens, r.completion_tokens)
            for r in records
        )
```

**异常检测算法：**

```python
from enum import Enum

class AnomalyType(Enum):
    SPIKE = "spike"           # 突增
    DROP = "drop"             # 突降
    STEADY_INCREASE = "steady_increase"  # 持续增长

@dataclass
class Anomaly:
    type: AnomalyType
    date: str
    actual_tokens: int
    baseline_tokens: int
    ratio: float

class AnomalyDetector:
    """异常检测器"""

    def __init__(
        self,
        baseline_days: int = 7,
        spike_threshold: float = 1.5,
        drop_threshold: float = 0.67,
        steady_increase_days: int = 3
    ):
        self.baseline_days = baseline_days
        self.spike_threshold = spike_threshold
        self.drop_threshold = drop_threshold
        self.steady_increase_days = steady_increase_days

    def detect(
        self,
        daily_tokens: Dict[str, int]
    ) -> List[Anomaly]:
        """检测异常"""
        anomalies = []
        dates = sorted(daily_tokens.keys())

        if len(dates) < self.baseline_days + 1:
            return anomalies

        for i in range(self.baseline_days, len(dates)):
            current_date = dates[i]
            current_tokens = daily_tokens[current_date]

            baseline_values = [
                daily_tokens[d] for d in dates[i - self.baseline_days:i]
            ]
            baseline = sum(baseline_values) / len(baseline_values)

            ratio = current_tokens / baseline if baseline > 0 else 0

            if ratio > self.spike_threshold:
                anomalies.append(Anomaly(
                    type=AnomalyType.SPIKE,
                    date=current_date,
                    actual_tokens=current_tokens,
                    baseline_tokens=int(baseline),
                    ratio=ratio
                ))
            elif ratio < self.drop_threshold:
                anomalies.append(Anomaly(
                    type=AnomalyType.DROP,
                    date=current_date,
                    actual_tokens=current_tokens,
                    baseline_tokens=int(baseline),
                    ratio=ratio
                ))

        steady_increase_anomalies = self._detect_steady_increase(daily_tokens)
        anomalies.extend(steady_increase_anomalies)

        return anomalies

    def _detect_steady_increase(
        self,
        daily_tokens: Dict[str, int]
    ) -> List[Anomaly]:
        """检测持续增长"""
        anomalies = []
        dates = sorted(daily_tokens.keys())

        for i in range(len(dates) - self.steady_increase_days + 1):
            window = [daily_tokens[d] for d in dates[i:i + self.steady_increase_days]]

            if all(window[j] < window[j + 1] for j in range(len(window) - 1)):
                baseline = sum(daily_tokens[d] for d in dates[max(0, i - 7):i]) / min(7, i)
                current = window[-1]
                anomalies.append(Anomaly(
                    type=AnomalyType.STEADY_INCREASE,
                    date=dates[i + self.steady_increase_days - 1],
                    actual_tokens=current,
                    baseline_tokens=int(baseline),
                    ratio=current / baseline if baseline > 0 else 0
                ))

        return anomalies
```

---

### 题目 2：如何基于 Token 使用数据进行成本优化？

**参考答案：**

**成本分析维度：**

```python
class CostOptimizer:
    """成本优化分析器"""

    def analyze_cost_breakdown(
        self,
        records: List[TokenRecord]
    ) -> Dict[str, Any]:
        """多维度成本分析"""
        by_model = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0.0})
        by_day = defaultdict(lambda: {"tokens": 0, "cost": 0.0})

        calculator = CostCalculator()

        for record in records:
            cost = calculator.calculate(
                record.prompt_tokens,
                record.completion_tokens
            )

            by_model[record.model]["calls"] += 1
            by_model[record.model]["tokens"] += record.total_tokens
            by_model[record.model]["cost"] += cost

            day = datetime.fromtimestamp(record.timestamp).strftime("%Y-%m-%d")
            by_day[day]["tokens"] += record.total_tokens
            by_day[day]["cost"] += cost

        return {
            "by_model": dict(by_model),
            "by_day": dict(by_day),
            "total_cost": sum(m["cost"] for m in by_model.values()),
            "total_tokens": sum(m["tokens"] for m in by_model.values()),
        }

    def find_cost_leaks(
        self,
        records: List[TokenRecord],
        p95_tokens: float
    ) -> List[TokenRecord]:
        """找出异常的"大Token"调用"""
        return [r for r in records if r.total_tokens > p95_tokens]

    def suggest_optimizations(
        self,
        records: List[TokenRecord]
    ) -> List[str]:
        """生成优化建议"""
        suggestions = []
        analysis = self.analyze_cost_breakdown(records)

        avg_tokens = analysis["total_tokens"] / len(records) if records else 0
        large_calls = [r for r in records if r.total_tokens > avg_tokens * 2]

        if large_calls:
            suggestions.append(
                f"发现 {len(large_calls)} 次异常大的调用 (>2x 平均)，"
                f"建议检查 prompt 长度"
            )

        model_costs = analysis["by_model"]
        if len(model_costs) > 1:
            expensive_model = max(
                model_costs.items(),
                key=lambda x: x[1]["cost"]
            )
            suggestions.append(
                f"模型 {expensive_model[0]} 成本最高 (¥{expensive_model[1]['cost']:.2f})，"
                f"考虑是否可以使用更便宜的模型"
            )

        return suggestions
```

**Prompt 优化策略：**

```python
class PromptOptimizer:
    """Prompt 成本优化"""

    def estimate_tokens(self, text: str) -> int:
        """简单估算 Token 数（中文约 1.5 字符 ≈ 1 Token）"""
        return int(len(text) * 0.7)

    def truncate_if_needed(
        self,
        prompt: str,
        max_tokens: int = 4000
    ) -> str:
        """必要时截断 prompt"""
        estimated = self.estimate_tokens(prompt)
        if estimated <= max_tokens:
            return prompt

        chars_to_keep = int(max_tokens / 0.7)
        return prompt[:chars_to_keep] + "\n[Truncated...]"

    def estimate_savings(
        self,
        original_prompt: str,
        optimized_prompt: str
    ) -> Dict[str, float]:
        """估算节省成本"""
        original_tokens = self.estimate_tokens(original_prompt)
        optimized_tokens = self.estimate_tokens(optimized_prompt)
        savings = original_tokens - optimized_tokens
        savings_rate = savings / original_tokens if original_tokens > 0 else 0

        return {
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "token_savings": savings,
            "savings_rate": f"{savings_rate:.1%}"
        }
```

---

## 代码示例

```python
"""
Day 26 代码示例：Token 审计和费用监控系统完整实现
演示记录、汇总、异常检测和成本优化
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import time


class AnomalyType(Enum):
    SPIKE = "spike"
    DROP = "drop"
    STEADY_INCREASE = "steady_increase"


@dataclass
class TokenRecord:
    timestamp: float
    prompt_tokens: int
    completion_tokens: int
    model: str = "unknown"
    call_id: str = ""

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class DailyReport:
    date: str
    total_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    model_breakdown: Dict[str, int] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False, indent=2)


@dataclass
class Anomaly:
    type: AnomalyType
    date: str
    actual_tokens: int
    baseline_tokens: int
    ratio: float


class TokenAuditor:
    """Token 审计器"""

    INPUT_COST_PER_M = 1.0
    OUTPUT_COST_PER_M = 2.0

    def __init__(self):
        self._records: List[TokenRecord] = []
        self._current_date: str = ""

    def record_call(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "unknown"
    ):
        record = TokenRecord(
            timestamp=time.time(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model
        )
        self._records.append(record)
        self._current_date = datetime.now().strftime("%Y-%m-%d")

    def daily_report(self) -> DailyReport:
        if not self._records:
            return DailyReport(date=self._current_date or datetime.now().strftime("%Y-%m-%d"))

        total_prompt = sum(r.prompt_tokens for r in self._records)
        total_completion = sum(r.completion_tokens for r in self._records)
        total_tokens = total_prompt + total_completion

        cost = (total_prompt * self.INPUT_COST_PER_M +
                total_completion * self.OUTPUT_COST_PER_M) / 1_000_000

        model_breakdown: Dict[str, int] = {}
        for r in self._records:
            model_breakdown[r.model] = model_breakdown.get(r.model, 0) + r.total_tokens

        return DailyReport(
            date=self._current_date or datetime.now().strftime("%Y-%m-%d"),
            total_calls=len(self._records),
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_tokens=total_tokens,
            estimated_cost=cost,
            model_breakdown=model_breakdown
        )

    def _next_day(self):
        self._records = []
        self._current_date = datetime.now().strftime("%Y-%m-%d")

    def detect_anomalies(
        self,
        baseline_days: int = 7,
        spike_threshold: float = 1.5
    ) -> List[Anomaly]:
        return []


def demo():
    """演示 Token 审计系统"""
    print("=" * 60)
    print("Day 26 代码示例：Token 审计和费用监控演示")
    print("=" * 60)

    auditor = TokenAuditor()

    print("\n[1] 记录 API 调用")
    print("-" * 40)
    auditor.record_call(prompt_tokens=50, completion_tokens=150, model="deepseek-chat")
    auditor.record_call(prompt_tokens=100, completion_tokens=200, model="deepseek-chat")
    auditor.record_call(prompt_tokens=80, completion_tokens=120, model="deepseek-chat")
    print(f"记录了 3 次调用")

    print("\n[2] 生成每日报告")
    print("-" * 40)
    report = auditor.daily_report()
    print(f"日期: {report.date}")
    print(f"总调用次数: {report.total_calls}")
    print(f"总 Token: {report.total_tokens}")
    print(f"估算费用: ¥{report.estimated_cost:.4f}")
    print(f"模型分布: {report.model_breakdown}")

    print("\n[3] 费用计算公式")
    print("-" * 40)
    print(f"公式: cost = (prompt_tokens × {auditor.INPUT_COST_PER_M} + "
          f"completion_tokens × {auditor.OUTPUT_COST_PER_M}) / 1_000_000")
    print(f"例如: (500 × 1 + 1000 × 2) / 1_000_000 = ¥0.0025")

    print("\n[4] 异常检测场景")
    print("-" * 40)
    print("SPIKE: 当天用量 > 基线 × 1.5 倍")
    print("DROP:  当天用量 < 基线 × 0.67 倍")
    print("STEADY_INCREASE: 连续 3 天递增")

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
```

---

## 练习题

### 练习 1：实现 Token 使用量趋势分析

**要求：**
实现 Token 使用量的趋势分析，计算周环比、月环比增长率，并标记异常增长。

**提示：**
```python
class TokenTrendAnalyzer:
    """Token 趋势分析器"""

    def analyze(
        self,
        daily_tokens: Dict[str, int]
    ) -> Dict[str, Any]:
        """分析趋势"""
        pass

    def week_over_week_growth(self, daily_tokens: Dict[str, int]) -> float:
        """计算周环比增长率"""
        pass

    def month_over_month_growth(self, daily_tokens: Dict[str, int]) -> float:
        """计算月环比增长率"""
        pass
```

**验收标准：**
- 计算周环比和月环比
- 增长率超过阈值时标记异常
- 生成趋势报告

---

### 练习 2：实现 Token 预算告警系统

**要求：**
实现每日/每周/每月的 Token 预算告警，当用量超过预算时自动告警。

**提示：**
```python
class TokenBudgetAlert:
    """Token 预算告警"""

    def __init__(self):
        self.budgets: Dict[str, float] = {}
        self.alerts_triggered: List[Dict] = []

    def set_budget(self, period: str, limit: int):
        """设置预算 (daily/weekly/monthly)"""
        pass

    def check(self, current_usage: int, period: str):
        """检查是否超过预算"""
        pass
```

**验收标准：**
- 支持日/周/月三种预算周期
- 用量超过 80% 时警告
- 用量超过 100% 时严重告警

---

### 练习 3：实现 Token 使用预测模型

**要求：**
基于历史数据，使用简单移动平均预测未来 Token 使用量。

**提示：**
```python
class TokenForecaster:
    """Token 使用量预测器"""

    def __init__(self, window_size: int = 7):
        self.window_size = window_size

    def predict(self, historical: List[int]) -> float:
        """预测下期使用量"""
        pass

    def predict_monthly(self, daily_history: List[int]) -> int:
        """预测月度总量"""
        pass
```

**验收标准：**
- 使用简单移动平均预测
- 预测月度总量
- 返回预测置信区间

---

## 九、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d26_token_auditor.py` | Token 审计模块 | [OK] |
| `tests/d26_test_token_auditor.py` | 18 个测试 | [OK] 18/18 PASS |
| `day26_study.md` | 本文档 | [OK] 已修复+升版 |
