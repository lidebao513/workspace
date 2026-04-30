# Day 22 — 并发压测

## 一、今日目标

> 学会用线程池对 AI API 做并发压力测试，掌握 P50/P95/P99 延迟和 RPS 吞吐量分析。

- 理解并发压测的核心指标（P50/P95/P99、RPS、成功率）
- 掌握 `LoadTester` 的 ThreadPoolExecutor 实现
- 学会预热排除冷启动偏差

---

## 二、核心技术

### P50/P95/P99 百分位延迟

| 指标 | 含义 | 面试常问 |
|------|------|----------|
| P50 | 一半的请求快于这个值 | "中位数延迟" |
| P95 | 95% 的请求快于这个值 | "用户侧真实体验" |
| P99 | 99% 的请求快于这个值 | "长尾优化目标" |

**面试话术：** "我们当时以 P95 < 2s 为 SLA 目标。因为平均延迟会被慢请求拉高，P95 更能反映真实用户体验。"

### 计算方式

```python
def _percentile(data, p):
    sorted_data = sorted(data)               # 排序
    idx = int(len(sorted_data) * p / 100)    # 位置
    return sorted_data[min(idx, len - 1)]
```

### LoadTester 架构

```
LoadTester.run(total_requests)
  ├── warmup（不计入统计）
  ├── ThreadPoolExecutor.submit(_worker)
  ├── as_completed 收集结果
  └── LatencyReport
```

---

## 三、运行验证

```
20 passed in 0.45s
```

---

## 四、面试话术

**架构相关：** "我用 ThreadPoolExecutor 做并发，预热轮次排除冷启动偏差。P50/P95/P99 用排序后插值法计算，RPS = 总请求 / 总时间。高并发时注意线程安全和锁竞争。"

**优化相关：** "从串行 10 RPS 优化到并行 50 RPS。瓶颈在 API 端，本地并发度调优后稳定在 8 线程最佳。"
