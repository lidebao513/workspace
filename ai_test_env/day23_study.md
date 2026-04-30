# Day 23 — 指数退避重试

## 一、今日目标

> 学会三种重试策略的实现和选择：固定间隔、指数退避、Decorrelated Jitter。这是让压测更稳定的基础——API 限流时立刻失败而不重试，RPS 和 P99 都会很难看。

- 理解三种重试策略的适用场景和数学公式
- 掌握 `RetryEngine` 的 `execute()` 模式和装饰器模式
- 理解 Jitter（抖动）如何防止惊群效应
- 学会 RetryStats 解读和重试参数调优

---

## 二、三种重试策略

### 2.1 固定间隔（FIXED）

```
delay = base_delay
```

每次重试都等同样的时间。最简单但不够智能。

**适用场景**：
- 定时任务，可预测的负载
- 重试次数很少（1-2 次）
- 对延迟不敏感的任务

### 2.2 指数退避（EXPONENTIAL）

```
delay = base_delay × 2^attempt
```

attempt=1 → 2s, attempt=2 → 4s, attempt=3 → 8s, attempt=4 → 16s...

**适用场景**：
- API 限流（429 Too Many Requests）
- 临时网络错误（5xx 状态码）
- 服务端负载过高时自然降速

**注意**：不设 `max_delay` 的话，attempt=10 时 delay = 1024s（~17 分钟），所以上限很重要。

### 2.3 Decorrelated Jitter（DECORRELATED）

```
delay = min(max_delay, base + random.random × previous_delay)
```

每次的延迟 = 基础值 + 随机因子 × 上次延迟。这是一种"有记忆"的退避——如果上次等了 8s，这次大概率也在 4-12s 范围。

**适用场景**：
- 高并发场景，防止 thundering herd（惊群效应）
- 多个客户端同时重试，需要分散时间
- 比纯随机 jitter 更平滑（方差更小）

---

## 三、Jitter（抖动）的作用

### 3.1 惊群效应（Thundering Herd）

没有 jitter 时，1 万个请求同时在 t=8s 醒来重试，服务端再次被打垮。有 jitter 后：

```
无 jitter:  1万请求 × 8s = 瞬间 1万 QPS
有 jitter:  1万请求 × [4s, 12s] = 分散到 8s 窗口内
```

### 3.2 实现方式

```python
jitter_factor = 1 + random.uniform(-0.5, 0.5)  # [-50%, +50%]
delay *= jitter_factor
delay = max(0.001, min(delay, max_delay))  # 确保在范围内
```

---

## 四、RetryEngine API

### 4.1 基本使用

```python
from utils.d23_retry_engine import RetryEngine, RetryStrategy

engine = RetryEngine(
    strategy=RetryStrategy.EXPONENTIAL,
    max_retries=3,       # 失败后重试 3 次
    base_delay=1.0,      # 基础间隔 1s
    max_delay=30.0,      # 最长 30s
    jitter=True,         # 加抖动
)

def call_api():
    # 可能抛出异常
    return requests.get("https://api.example.com/chat")

try:
    result, stats = engine.execute(call_api)
    print(f"成功，尝试了 {stats.attempts} 次")
    print(f"总等待时间: {stats.total_delay:.2f}s")
except Exception as e:
    print(f"所有重试都失败: {e}")
```

### 4.2 装饰器模式

```python
from utils.d23_retry_engine import retry, RetryStrategy

@retry(strategy=RetryStrategy.EXPONENTIAL, max_retries=5, base_delay=0.5)
def fetch_data(prompt: str) -> str:
    # 自动重试 5 次，指数退避
    return api_call(prompt)
```

### 4.3 可控重试的异常类型

```python
# 只重试 RateLimitError 和 TimeoutError
# 401 AuthError 直接抛出不重试
result, stats = engine.execute(
    call_api,
    retryable_exceptions=(RateLimitError, TimeoutError),
)
```

---

## 五、RetryStats 解读

```python
@dataclass
class RetryStats:
    attempts: int           # 总尝试次数
    total_delay: float      # 总等待时间 (s)
    first_success_at: int   # 第几次成功（0=从未成功）
    delays: List[float]     # 每次的等待时间
    errors: List[str]       # 每次的错误信息
```

解读：
- `attempts = 1` + `first_success_at = 1` → 一次成功，零重试（理想情况）
- `attempts = 4` + `first_success_at = 4` → 前 3 次失败，第 4 次成功
- `attempts = 4` + `first_success_at = 0` → 全部失败（异常被 re-raise）
- `total_delay` 很大 → 服务端频繁限流，需要降速或提额

---

## 六、策略选择决策树

```
错误类型？
├── 401 / 403 / 4xx（非限流） → 不重试，直接失败
├── 429 Too Many Requests    → 指数退避 + jitter
├── 5xx（服务端错误）         → 指数退避 + jitter
├── 网络超时 / ConnectionError → 指数退避，max_retries 可大一些
└── 本地逻辑错误（ValueError等）→ 不重试，修代码

场景？
├── 定时任务，预测负载均匀    → 固定间隔
├── 高并发，多客户端同时      → Decorrelated Jitter
└── 一般 API 调用            → 指数退避
```

---

## 七、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| 一次成功 | 调用立即返回 | attempts=1, first_success_at=1 |
| 重试后成功 | 前 2 次失败，第 3 次成功 | attempts=3, first_success_at=3 |
| 全部失败 | 一直失败 | 抛出最后一次异常 |
| 固定间隔 | strategy=FIXED | delay = base_delay |
| 指数退避 | strategy=EXPONENTIAL | delay 翻倍增长 |
| Decorrelated Jitter | strategy=DECORRELATED | delay 在 base 到 max 之间 |
| 不可重试异常 | 传入空元组 | 不重试，直接抛出 |
| 装饰器 | @retry(max_retries=3) | 自动重试 |

---

## 八、面试话术

> "我实现了一个可配置的重试引擎，支持三种策略。指数退避公式是 `base × 2^attempt`，同时设 `max_delay=30` 防止无限增长。Jitter 加 [-50%, +50%] 随机偏移，防止惊群效应——上万请求在 1 秒内同时醒来重试会把服务打垮。Decorrelated Jitter 在高并发时比纯指数退避更平滑，因为它的延迟有记忆，方差更小。"

> "不可重试的异常需要精确控制——401 AuthError 重试也没用，直接报错。429 限流要尊重 Retry-After Header。重试次数设 3-5 次就够了，超过 5 次往往是架构问题，不是重试能解决的。"

---

## 九、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d23_retry_engine.py` | 重试引擎（3 种策略 + 装饰器） | [OK] |
| `tests/d23_test_retry_engine.py` | 16 个测试 | [OK] 16/16 PASS |
| `day23_study.md` | 本文档 | [OK] 已升级 |
