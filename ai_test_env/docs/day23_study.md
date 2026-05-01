# Day 23 — 指数退避重试

## 学习目标

1. 理解三种重试策略（固定间隔、指数退避、Decorrelated Jitter）的适用场景和数学公式
2. 掌握 RetryEngine 的 execute() 模式和装饰器模式实现
3. 理解 Jitter（抖动）如何防止惊群效应（Thundering Herd）
4. 学会 RetryStats 解读和重试参数调优策略

---

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

## 面试题

### 题目 1：如何设计一个生产级别的重试机制？

**参考答案：**

一个生产级别的重试机制需要考虑以下几个核心方面：

**1. 重试策略选择**

根据不同场景选择合适的重试策略：
- **指数退避（Exponential Backoff）**：适用于大多数 API 调用，公式为 `delay = base × 2^attempt`，配合 `max_delay` 防止无限增长
- **Decorrelated Jitter**：适用于高并发场景，延迟具有"记忆性"，比纯指数退避更平滑
- **固定间隔**：仅适用于定时任务或对延迟极不敏感的场景

**2. Jitter（抖动）的必要性**

```python
# 无 jitter：10000 请求在 t=8s 同时醒来
# 有 jitter：10000 请求分散在 [4s, 12s] 窗口内
jitter_factor = 1 + random.uniform(-0.5, 0.5)  # [-50%, +50%]
delay *= jitter_factor
```

惊群效应（Thundering Herd）会让服务端再次被打垮，Jitter 是必需的防护手段。

**3. 不可重试异常的精确控制**

```python
# 只重试可恢复的错误
retryable = (RateLimitError, TimeoutError, ConnectionError)
non_retryable = (AuthError, ConfigError, ValidationError)

if isinstance(e, non_retryable):
    raise  # 直接抛出，不重试
```

**4. 重试参数的经验值**

| 参数 | 经验值 | 说明 |
|------|--------|------|
| max_retries | 3-5 | 超过往往是架构问题 |
| base_delay | 0.5-1.0s | 根据服务响应时间调整 |
| max_delay | 30s | 防止等待过长 |
| jitter_ratio | 50% | 平衡分散效果和延迟 |

**5. 与熔断器配合**

重试解决瞬时故障，熔断解决持续故障。两者配合形成完整的容错体系。

---

### 题目 2：为什么需要 Jitter？如何实现？

**参考答案：**

**问题背景：**

在没有 Jitter 的情况下，假设 10000 个客户端同时遇到 429 限流错误，它们都会在计算出的同一时刻同时发起重试：

```
无 Jitter: 10000 请求 × delay=8s → t=8s 时瞬间 10000 QPS
有 Jitter: 10000 请求 × [4s, 12s] → 分散到 8s 窗口内
```

这就是经典的"惊群效应"（Thundering Herd），会导致服务端再次过载。

**Jitter 的三种实现方式：**

```python
import random

# 1. Full Jitter（完全随机）
delay = random.uniform(0, base_delay * (2 ** attempt))

# 2. Equal Jitter（等量抖动）
delay = base_delay * (2 ** attempt)
delay += random.uniform(0, delay * 0.5)  # ±50%

# 3. Decorrelated Jitter（有记忆的抖动）
delay = min(max_delay, base_delay + random.random() * previous_delay)
```

**Decorrelated Jitter 的优势：**

```python
# 相比纯指数退避，Decorrelated Jitter 的特点：
# 1. 延迟有"记忆"：下次延迟受上次延迟影响
# 2. 方差更小：不会像纯随机那样出现极端值
# 3. 自适应：负载高时延迟自然拉长，负载低时延迟收缩
```

**实际生产建议：**

```python
class ProductionRetryEngine:
    def __init__(self):
        self.max_retries = 3
        self.base_delay = 1.0
        self.max_delay = 30.0
        self.jitter_ratio = 0.5  # ±50%
    
    def calculate_delay(self, attempt: int, previous_delay: float = None) -> float:
        # 使用 Decorrelated Jitter
        delay = self.base_delay * (2 ** attempt)
        if previous_delay:
            delay = min(self.max_delay, self.base_delay + random.random() * previous_delay)
        
        # 应用 jitter
        jitter = 1 + random.uniform(-self.jitter_ratio, self.jitter_ratio)
        return max(0.001, min(delay * jitter, self.max_delay))
```

---

---

## 代码示例

```python
"""
Day 23 代码示例：指数退避重试引擎完整实现
演示三种重试策略、Fallback 机制和装饰器模式
"""

import random
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Type, Tuple, Any
from enum import Enum
from functools import wraps


class RetryStrategy(Enum):
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    DECORRELATED = "decorrelated"


@dataclass
class RetryStats:
    attempts: int = 0
    total_delay: float = 0.0
    first_success_at: int = 0
    delays: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_attempt(self, delay: float, error: Optional[str] = None):
        self.attempts += 1
        if delay > 0:
            self.delays.append(delay)
            self.total_delay += delay
        if error:
            self.errors.append(error)
        elif self.first_success_at == 0:
            self.first_success_at = self.attempts


@dataclass
class RetryConfig:
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter: bool = True
    jitter_ratio: float = 0.5
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)


class RetryEngine:
    """指数退避重试引擎，支持三种策略"""

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Tuple[Any, RetryStats]:
        """执行带重试的函数调用"""
        stats = RetryStats()
        last_exception = None
        previous_delay = self.config.base_delay

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                if stats.first_success_at == 0:
                    stats.first_success_at = attempt
                return result, stats
            except Exception as e:
                last_exception = e

                if not self._is_retryable(e):
                    stats.errors.append(f"Non-retryable: {e}")
                    raise

                if attempt >= self.config.max_attempts:
                    stats.add_attempt(0, str(e))
                    break

                delay = self._calculate_delay(attempt, previous_delay)
                stats.add_attempt(delay, str(e))
                previous_delay = delay
                time.sleep(delay)

        raise last_exception

    def _calculate_delay(self, attempt: int, previous_delay: float) -> float:
        """根据策略计算延迟"""
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** (attempt - 1))
        elif self.config.strategy == RetryStrategy.DECORRELATED:
            delay = min(
                self.config.max_delay,
                self.config.base_delay + random.random() * previous_delay
            )
        else:
            raise ValueError(f"Unknown strategy: {self.config.strategy}")

        if self.config.jitter:
            jitter_factor = 1 + random.uniform(
                -self.config.jitter_ratio,
                self.config.jitter_ratio
            )
            delay *= jitter_factor

        return max(0.001, min(delay, self.config.max_delay))

    def _is_retryable(self, exception: Exception) -> bool:
        """判断异常是否可重试"""
        return isinstance(exception, self.config.retryable_exceptions)


def retry(
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True
):
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = RetryConfig(
                strategy=strategy,
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                jitter=jitter
            )
            engine = RetryEngine(config)
            result, _ = engine.execute(func, *args, **kwargs)
            return result
        return wrapper
    return decorator


class FallbackManager:
    """带 Fallback 的重试执行器"""

    def __init__(self, retry_engine: RetryEngine):
        self.retry_engine = retry_engine

    def execute_with_fallback(
        self,
        func: Callable,
        fallback: Callable,
        *args,
        **kwargs
    ) -> Any:
        """执行函数，失败时调用 fallback"""
        try:
            result, _ = self.retry_engine.execute(func, *args, **kwargs)
            return result
        except Exception as e:
            print(f"Retry exhausted, using fallback: {e}")
            return fallback()


def demo():
    """演示重试引擎的各种策略"""
    print("=" * 60)
    print("Day 23 代码示例：指数退避重试引擎演示")
    print("=" * 60)

    call_count = {"value": 0}

    def unreliable_api():
        call_count["value"] += 1
        if call_count["value"] < 3:
            raise TimeoutError(f"Attempt {call_count['value']} failed")
        return "Success!"

    config = RetryConfig(
        strategy=RetryStrategy.EXPONENTIAL,
        max_attempts=5,
        base_delay=0.5,
        max_delay=10.0,
        jitter=True,
        retryable_exceptions=(TimeoutError, ConnectionError)
    )

    engine = RetryEngine(config)

    print("\n[1] 指数退避 + Jitter 重试演示")
    print("-" * 40)
    result, stats = engine.execute(unreliable_api)
    print(f"Result: {result}")
    print(f"Attempts: {stats.attempts}")
    print(f"Total delay: {stats.total_delay:.2f}s")
    print(f"First success at: #{stats.first_success_at}")
    print(f"Delays: {[f'{d:.2f}s' for d in stats.delays]}")

    print("\n[2] 装饰器模式演示")
    print("-" * 40)
    call_count["value"] = 0

    @retry(strategy=RetryStrategy.EXPONENTIAL, max_attempts=3, base_delay=0.2)
    def decorated_api():
        call_count["value"] += 1
        if call_count["value"] < 2:
            raise ConnectionError("Connection refused")
        return "Decorated success!"

    try:
        result = decorated_api()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Failed: {e}")

    print("\n[3] Fallback 机制演示")
    print("-" * 40)
    call_count["value"] = 0

    def get_cached_data():
        return {"source": "cache", "data": "cached_value"}

    fm = FallbackManager(engine)
    result = fm.execute_with_fallback(
        unreliable_api,
        get_cached_data
    )
    print(f"Result with fallback: {result}")

    print("\n[4] 三种策略对比")
    print("-" * 40)

    for strategy in RetryStrategy:
        config = RetryConfig(
            strategy=strategy,
            max_attempts=4,
            base_delay=1.0,
            max_delay=30.0,
            jitter=False
        )
        engine = RetryEngine(config)

        delays = []
        prev_delay = config.base_delay
        for attempt in range(1, 5):
            delay = engine._calculate_delay(attempt, prev_delay)
            delays.append(f"{delay:.1f}s")
            if strategy == RetryStrategy.DECORRELATED:
                prev_delay = delay

        print(f"{strategy.value:12}: {', '.join(delays)}")

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
```

---

## 练习题

### 练习 1：实现带 Retry-After Header 支持的重试机制

**要求：**
在 RetryEngine 中添加对 HTTP 429 响应中 `Retry-After` Header 的支持。当服务端返回 429 状态码并带有 `Retry-After` Header 时，优先使用服务端指定的时间进行重试。

**提示：**
```python
def parse_retry_after(header_value: str) -> float:
    """解析 Retry-After Header"""
    # 支持两种格式：
    # 1. 整数秒数: "30"
    # 2. HTTP 日期: "Wed, 21 Oct 2015 07:28:00 GMT"
    pass
```

**验收标准：**
- 能解析整数秒数格式的 Retry-After
- 能解析 HTTP 日期格式的 Retry-After
- 优先使用 Retry-After 而非计算延迟

---

### 练习 2：实现重试预算（Retry Budget）机制

**要求：**
设计一个重试预算机制，限制在时间窗口内的最大重试次数，防止客户端过度重试导致雪崩效应。

**提示：**
```python
class RetryBudget:
    """滑动窗口重试预算"""
    def __init__(self, max_retries: int, window_seconds: float):
        # max_retries: 窗口内的最大重试次数
        # window_seconds: 时间窗口大小（秒）
        pass

    def acquire(self) -> bool:
        """尝试获取一次重试机会，返回是否允许"""
        pass

    @property
    def remaining(self) -> int:
        """剩余可用重试次数"""
        pass
```

**验收标准：**
- 滑动窗口计数，窗口内超过限制时拒绝重试
- 提供 `remaining` 属性查询剩余次数
- 支持时间窗口自动过期

---

### 练习 3：实现重试历史记录和可视化

**要求：**
扩展 RetryStats，添加重试历史的结构化记录，并实现一个简单的 ASCII 可视化函数，展示重试过程的时间线。

**提示：**
```python
@dataclass
class RetryAttempt:
    timestamp: float
    attempt_number: int
    delay_used: float
    error_type: Optional[str]
    error_message: str
    result: str  # "success" / "failure" / "retry"

def visualize_retry_history(stats: RetryStats) -> str:
    """生成 ASCII 时间线可视化"""
    pass
```

**验收标准：**
- 记录每次重试的时间戳、延迟、错误类型
- 生成类似如下的 ASCII 可视化：
```
Timeline:
  [0.00s] ──●── Attempt #1 (Error: TimeoutError)
  [1.23s] ──●── Attempt #2 (Error: 429 Rate Limited)
  [2.87s] ──●── Success!
```

---

## 九、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d23_retry_engine.py` | 重试引擎（3 种策略 + 装饰器） | [OK] |
| `tests/d23_test_retry_engine.py` | 16 个测试 | [OK] 16/16 PASS |
| `day23_study.md` | 本文档 | [OK] 已升级 |
