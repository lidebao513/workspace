# Day 24 — 熔断器（Circuit Breaker）

## 一、今日目标

> 学会三态熔断器保护 API 调用链：CLOSED → OPEN → HALF_OPEN → CLOSED。这是重试引擎的"安全阀"——重试解决瞬时故障，熔断解决持续故障。

- 理解熔断器三态状态机和工作原理
- 掌握熔断阈值、恢复超时、半开探测的关键参数调优
- 学会 fallback 降级策略保证用户体验
- 理解熔断 vs 重试的互补关系

---

## 二、什么是熔断器？

熔断器源自电路保护中的"保险丝"概念——电流过大时熔断断电，防止火灾。在软件中：
- API 持续超时/错误时，触发熔断器的 `OPEN` 状态
- 后续调用**快速失败**（不真正发请求），保护下游系统和用户线程
- 一段时间后自动尝试恢复（`HALF_OPEN`），如果下游恢复了就合闸（`CLOSED`）

---

## 三、三态状态机

### 3.1 状态转换

```
     ┌─────────────────────────┐
     │        CLOSED           │  ←── 一切正常，请求直接通过
     └──────────┬──────────────┘
                │ failures >= failure_threshold
                ▼
     ┌─────────────────────────┐
     │         OPEN            │  ←── 熔断，请求快速失败（不调用目标）
     └──────────┬──────────────┘
                │ timeout >= recovery_timeout
                ▼
     ┌─────────────────────────┐
     │       HALF_OPEN         │  ←── 试探性放行少量请求
     └──────────┬──────────────┘
       ┌────────┴────────┐
       ▼                 ▼
    CLOSED              OPEN
  (成功率达标)      (探测失败)
```

### 3.2 关键参数

| 参数 | 默认值 | 说明 | 调优建议 |
|------|--------|------|---------|
| `failure_threshold` | 5 | 连续失败次数触发熔断 | 3-10，看服务 SLA |
| `recovery_timeout` | 30s | OPEN 到 HALF_OPEN 的等待 | 15-60s，别太短（来回抖动）|
| `half_open_max_requests` | 3 | 半开期间最大探测请求数 | 3-5，太少不够判断 |
| `half_open_success_ratio` | 0.5 | 探测成功率阈值 | 0.5-0.8 |

---

## 四、CircuitBreaker API

### 4.1 基本使用

```python
from utils.d24_circuit_breaker import CircuitBreaker

cb = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30,
    half_open_max_requests=3,
)

def call_api():
    # 可能失败
    return requests.get("https://api.example.com/chat")

for i in range(20):
    try:
        result = cb.call(call_api)
        print(f"[{i}] 成功")
    except Exception as e:
        print(f"[{i}] 失败: {e}")
```

### 4.2 带 fallback

```python
result = cb.call(
    call_api,
    fallback=lambda: {"status": "degraded", "data": cached_data}
)
# 熔断时不会抛异常，返回兜底数据
```

### 4.3 状态查询

```python
state = cb.state  # CircuitState.CLOSED / OPEN / HALF_OPEN
stats = cb.get_stats()
# → {"state": "CLOSED", "success_count": 42, "failure_count": 0, ...}
```

### 4.4 手动重置

```python
cb.reset()  # 回到 CLOSED
```

---

## 五、熔断器 vs 重试引擎

| 特性 | 重试（RetryEngine） | 熔断（CircuitBreaker） |
|------|-------------------|----------------------|
| 解决 | 瞬时故障（超时、限流） | 持续故障（服务下线、网络断连） |
| 策略 | 乐观：再试一次就好 | 悲观：保护系统不受伤 |
| 副作用 | 增加负载 | 减少负载 |
| 最大重试 | 3-5 次 | 直到状态恢复 |
| 何时用 | 5xx 偶尔出错 | 5xx 持续出错 |

**两者配合使用**：外层熔断器判断整体健康度，内层重试引擎处理每次调用的瞬态故障。

---

## 六、参数调优原则

### 6.1 threshold 太小（比如 2）
- 服务稍微抖动就熔断，用户体验差
- 需要高频半开探测，增加开销

### 6.2 threshold 太大（比如 50）
- 服务已经挂了很久才意识到
- 这段时间所有请求都白费了

### 6.3 recovery_timeout 太小
- 不断在 OPEN ↔ HALF_OPEN 之间来回切换（thrashing）
- 前端表现为"时好时坏"

### 6.4 recovery_timeout 太大
- 下游恢复后，用户继续受熔断影响
- 建议 15-30s，根据 SLA 调整

---

## 七、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| 正常调用 | 一直成功 | 保持在 CLOSED |
| 阈值触发 | 连续失败 >= threshold | 转到 OPEN |
| OPEN 后快速失败 | 调用 | 抛出 CircuitBreakerOpenError |
| 超时后自动恢复 | sleep 后 | 转 HALF_OPEN |
| HALF_OPEN 成功够多 | 放行探测，都成功 | 回到 CLOSED |
| HALF_OPEN 继续失败 | 放行探测，都失败 | 回到 OPEN |
| 重置 | reset() | 清空计数，回到 CLOSED |
| 状态统计 | get_stats() | 包含 state、成功/失败数 |

---

## 八、面试话术

> "我用三态熔断器保护 API 调用链。CLOSED 正常通行，连续 5 次失败后切到 OPEN 快速失败（不实际调用），30s 后自动进入 HALF_OPEN 试探恢复。配合 fallback 参数返回兜底数据——熔断时用户看到的是缓存提示，不是 500 白页。"

> "熔断器和重试引擎是互补的。重试解决瞬时故障（超时第一次，等 2s 再试试），熔断解决持续故障（服务已经挂了，别白费力气重试了）。两者配合——外层熔断器判断健康，内层重试处理每次调用的瞬态错误。"

> "调参要避免来回抖动。`recovery_timeout` 设 30s 而非 5s，防止下游还没完全恢复又被打垮。`half_open_success_ratio` 设 0.5——探测成功一半以上就认为恢复了，太严格容易反复熔断。"

---

## 九、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d24_circuit_breaker.py` | 三态熔断器 | [OK] |
| `tests/d24_test_circuit_breaker.py` | 19 个测试 | [OK] 19/19 PASS |
| `day24_study.md` | 本文档 | [OK] 已升级 |
