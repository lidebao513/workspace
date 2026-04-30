# Day 26 — Token 审计 + 费用监控

## 一、今日目标

> 学会 API Token 消耗的审计记录、每日报告生成和异常波动检测。

- 理解 TokenAuditor 的 record_call / daily_report / detect_anomalies
- 掌握三种异常类型：SPIKE / DROP / STEADY_INCREASE
- 学会滚动平均基线计算

---

## 二、审计体系

### TokenRecord（每次调用）

```
timestamp | prompt_tokens | completion_tokens | model | call_id
```

### DailyReport（每日汇总）

```
Calls: 142
Prompt Tokens: 50,000
Completion Tokens: 120,000
Total: 170,000
Est. Cost: 0.29 CNY
```

### 异常检测算法

```
基线 = 最近 N 天 Token 均值
SPIKE: 当天 / 基线 > 阈值（默认 1.5 倍）
DROP:  当天 / 基线 < 1/阈值
STEADY_INCREASE: 连续 N 天递增
```

### 费用估算

```
input_cost  = prompt_tokens × 1 / 1_000_000     # ￥1/M tokens
output_cost = completion_tokens × 2 / 1_000_000  # ￥2/M tokens
```

---

## 三、运行验证

```
18 passed in 0.04s
```

---

## 四、面试话术

**应用场景：** "生产环境部署后，TokenAuditor 帮我们抓到一个死循环引起的 Token 突增 — 某天用量从日常 10 万暴涨到 500 万。及时告警止损。"

**基线设计：** "用 7 天滚动平均做基线，周六日消费不同，所以 spike 对比的是同一时段的历史均值，不是绝对值。STEADY_INCREASE 用连续递增判定而不是阈值，避免频繁误报。"
