# Day 23 — 指数退避重试

## 一、今日目标

> 学会三种重试策略的实现和选择：固定间隔、指数退避、Decorrelated Jitter。

- 理解重试策略对 API 稳定性的影响
- 掌握 `RetryEngine` 的 execute 模式和装饰器模式
- 学会 RetryStats 重试统计

---

## 二、三种策略对比

| 策略 | 公式 | 适用场景 |
|------|------|----------|
| FIXED | `base_delay` | 定时任务、可预测负载 |
| EXPONENTIAL | `2^attempt × base` | API 限流、网络错误 |
| DECORRELATED | `min(max, base + random × prev)` | 高并发、thundering herd 防止 |

### 指数退避公式

```
delay = base × 2^attempt  （attempt=1 → 2s, attempt=2 → 4s, attempt=3 → 8s）
```

### 加抖动

```python
delay *= 1 + random.uniform(-0.5, 0.5)  # [-50%, +50%]
```

抖动防止**惊群效应**——大量请求同时恢复导致再次熔断。

---

## 三、运行验证

```
16 passed in 0.29s
```

---

## 四、面试话术

**策略选择：** "网络错误用指数退避 — 第一次等 1s，第二次 2s，第三次 4s。再加上 jitter 防止所有客户端同时重试。流量低且可预测的场景用固定间隔更简单。"

**注意点：** "max_delay 必须设置上限，否则指数增长一会儿就到天级别。重试次数也不能太大，3-5 次够了。可重试异常要精确控制 — 401 认证错误重试也没用，直接报错。"
