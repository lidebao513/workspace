# Day 26 — Token 审计 + 费用监控

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

## 九、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d26_token_auditor.py` | Token 审计模块 | [OK] |
| `tests/d26_test_token_auditor.py` | 18 个测试 | [OK] 18/18 PASS |
| `day26_study.md` | 本文档 | [OK] 已修复+升版 |
