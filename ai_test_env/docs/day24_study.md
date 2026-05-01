# Day 24 — 熔断器（Circuit Breaker）

## 学习目标

1. 理解熔断器三态状态机（CLOSED → OPEN → HALF_OPEN → CLOSED）的工作原理
2. 掌握熔断阈值、恢复超时、半开探测的关键参数调优
3. 学会设计 Fallback 降级策略保证用户体验
4. 理解熔断器与重试引擎的互补关系

---

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

## 面试题

### 题目 1：熔断器的工作原理是什么？如何设计一个生产级别的熔断器？

**参考答案：**

**熔断器的核心思想：**

熔断器借鉴了电路保险丝的概念。当电流过大时，保险丝熔断，切断电路以防止火灾。在软件系统中，熔断器在检测到下游服务持续故障时，"熔断"后续请求，快速失败以保护系统不被拖垮。

**三态状态机：**

```
CLOSED（闭合）→ OPEN（熔断）→ HALF_OPEN（半开）→ CLOSED（闭合）
     ↑                                                   ↓
     ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
```

1. **CLOSED（闭合状态）**：正常状态，所有请求直接通过。统计成功/失败次数。
2. **OPEN（熔断状态）**：检测到连续失败达到阈值，立即开启熔断。后续请求直接快速失败，不调用下游服务。
3. **HALF_OPEN（半开状态）**：等待 `recovery_timeout` 后，允许少量探测请求通过。如果探测成功率达到阈值，回到 CLOSED；否则回到 OPEN。

**关键参数设计：**

```python
class CircuitBreakerConfig:
    failure_threshold: int = 5        # 连续失败次数阈值
    recovery_timeout: float = 30.0    # OPEN 到 HALF_OPEN 的等待时间
    half_open_max_requests: int = 3   # 半开期最大探测请求数
    half_open_success_ratio: float = 0.5  # 探测成功阈值
```

**生产级实现要点：**

```python
class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig):
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_requests = 0

    def call(self, func, fallback=None):
        # 1. OPEN 状态：直接快速失败
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._to_half_open()
            else:
                return fallback() if fallback else self._create_open_error()

        # 2. 执行请求
        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            if fallback:
                return fallback()
            raise

    def _should_attempt_reset(self) -> bool:
        """检查是否应该进入 HALF_OPEN 试探恢复"""
        if self._last_failure_time is None:
            return False
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.config.recovery_timeout
```

**Fallback 降级策略：**

```python
# 熔断时的降级策略
result = cb.call(
    get_user_profile,
    fallback=lambda: {"name": "Guest", "cached": True}
)
# 用户看到的是友好的缓存提示，而非 500 错误
```

---

### 题目 2：熔断器和重试引擎有什么区别？什么时候用哪个？

**参考答案：**

**核心区别：**

| 特性 | 重试引擎 | 熔断器 |
|------|---------|--------|
| **解决问题** | 瞬时故障（偶尔超时、限流） | 持续故障（服务宕机、断网） |
| **策略方向** | 乐观：相信下次会成功 | 悲观：保护系统不受伤害 |
| **对负载的影响** | 增加负载（每次重试都是新请求） | 减少负载（快速失败，不调下游） |
| **持续时间** | 固定次数（3-5 次）后放弃 | 直到服务恢复为止 |
| **副作用** | 可能加剧服务端压力 | 可能导致部分请求失败 |

**决策树：**

```
遇到错误
├── 是否可重试的错误？
│   ├── 401/403 认证错误 → ❌ 不重试，直接报错
│   ├── 429 限流 → ⚠️ 可以重试，但要用指数退避
│   └── 500/超时/连接错误 → 需要判断
│       ├── 单次偶发 → 重试 1-2 次
│       └── 持续发生 → 触发熔断
```

**两者配合使用：**

```python
# 外层熔断器：保护整体调用链
cb = CircuitBreaker(failure_threshold=5)

# 内层重试：处理每次调用的瞬时故障
engine = RetryEngine(max_retries=3)

def safe_api_call(prompt):
    try:
        # 熔断器判断整体健康度
        # 重试引擎处理每次调用的瞬时故障
        return cb.call(lambda: engine.execute(api_request, args=(prompt,)))
    except CircuitBreakerOpenError:
        # 熔断期间返回降级数据
        return {"degraded": True, "data": cached_response}
```

**实际案例：**

假设支付服务宕机 30 秒：
- **仅有重试引擎**：30 秒内每个请求重试 3 次 = 9 倍负载，服务可能雪崩
- **仅有熔断器**：5 次失败后熔断，后续请求直接返回失败，用户体验差
- **两者配合**：5 次失败后熔断，30 秒后半开探测，服务恢复后自动合闸

**总结：**
- 重试解决"这次运气不好"
- 熔断解决"这服务不太行"
- 两者是互补关系，不是替代关系

---

## 代码示例

```python
"""
Day 24 代码示例：熔断器完整实现
演示三态状态机、Fallback 机制和参数配置
"""

import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any
from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """熔断器开启时抛出的异常"""
    def __init__(self, message: str = "Circuit breaker is OPEN"):
        self.message = message
        super().__init__(self.message)


@dataclass
class CircuitBreakerStats:
    """熔断器统计信息"""
    success_count: int = 0
    failure_count: int = 0
    total_calls: int = 0
    rejected_calls: int = 0
    state_changes: int = 0


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_requests: int = 3
    half_open_success_ratio: float = 0.5


class CircuitBreaker:
    """三态熔断器实现"""

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_requests = 0
        self._half_open_successes = 0
        self.stats = CircuitBreakerStats()

    @property
    def state(self) -> CircuitState:
        return self._state

    def call(self, func: Callable, fallback: Optional[Callable] = None) -> Any:
        """执行函数调用，受熔断器保护"""
        self.stats.total_calls += 1

        if self._state == CircuitState.OPEN:
            return self._handle_open_state(fallback)

        if self._state == CircuitState.HALF_OPEN:
            return self._handle_half_open_state(func, fallback)

        return self._execute_normal(func, fallback)

    def _handle_open_state(self, fallback: Optional[Callable]) -> Any:
        """处理 OPEN 状态的请求"""
        self.stats.rejected_calls += 1

        if self._should_attempt_reset():
            self._to_half_open()
        else:
            if fallback:
                return fallback()
            raise CircuitBreakerOpenError()

    def _handle_half_open_state(
        self,
        func: Callable,
        fallback: Optional[Callable]
    ) -> Any:
        """处理 HALF_OPEN 状态的请求"""
        if self._half_open_requests >= self.config.half_open_max_requests:
            if fallback:
                return fallback()
            raise CircuitBreakerOpenError()

        self._half_open_requests += 1
        return self._execute_normal(func, fallback)

    def _execute_normal(self, func: Callable, fallback: Optional[Callable]) -> Any:
        """正常执行函数"""
        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            if fallback:
                return fallback()
            raise

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试恢复"""
        if self._last_failure_time is None:
            return False
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.config.recovery_timeout

    def _on_success(self):
        """处理成功调用"""
        self.stats.success_count += 1
        self._failure_count = 0

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_successes += 1
            if self._half_open_successes >= self.config.half_open_max_requests * self.config.half_open_success_ratio:
                self._to_closed()

    def _on_failure(self):
        """处理失败调用"""
        self.stats.failure_count += 1
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._to_open()
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.config.failure_threshold:
                self._to_open()

    def _to_open(self):
        """转换到 OPEN 状态"""
        if self._state != CircuitState.OPEN:
            self._state = CircuitState.OPEN
            self.stats.state_changes += 1
            self._half_open_requests = 0
            self._half_open_successes = 0

    def _to_half_open(self):
        """转换到 HALF_OPEN 状态"""
        self._state = CircuitState.HALF_OPEN
        self.stats.state_changes += 1
        self._half_open_requests = 0
        self._half_open_successes = 0

    def _to_closed(self):
        """转换到 CLOSED 状态"""
        self._state = CircuitState.CLOSED
        self.stats.state_changes += 1
        self._failure_count = 0
        self._half_open_requests = 0
        self._half_open_successes = 0

    def reset(self):
        """手动重置熔断器"""
        self._to_closed()
        self.stats = CircuitBreakerStats()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "state": self._state.value,
            "success_count": self.stats.success_count,
            "failure_count": self.stats.failure_count,
            "total_calls": self.stats.total_calls,
            "rejected_calls": self.stats.rejected_calls,
            "state_changes": self.stats.state_changes,
        }


def demo():
    """演示熔断器的工作流程"""
    print("=" * 60)
    print("Day 24 代码示例：熔断器演示")
    print("=" * 60)

    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=2.0,
        half_open_max_requests=3,
        half_open_success_ratio=0.5
    )
    cb = CircuitBreaker(config)

    call_count = {"value": 0}

    def unreliable_service():
        call_count["value"] += 1
        if call_count["value"] <= 3:
            raise ConnectionError(f"Connection failed #{call_count['value']}")
        return {"status": "ok", "calls": call_count["value"]}

    def fallback():
        return {"status": "degraded", "data": "fallback_response"}

    print("\n[1] CLOSED -> OPEN 状态转换")
    print("-" * 40)
    for i in range(5):
        try:
            result = cb.call(unreliable_service, fallback)
            print(f"Call #{i+1}: SUCCESS -> {result}")
        except CircuitBreakerOpenError:
            print(f"Call #{i+1}: REJECTED (Circuit OPEN)")
        except Exception as e:
            print(f"Call #{i+1}: ERROR -> {e}")
        print(f"  State: {cb.state.value}, Stats: {cb.get_stats()}")

    print("\n[2] 等待恢复超时")
    print("-" * 40)
    print(f"Waiting {config.recovery_timeout}s for recovery timeout...")
    time.sleep(config.recovery_timeout)
    print(f"State after timeout: {cb.state.value}")

    print("\n[3] HALF_OPEN 探测")
    print("-" * 40)
    call_count["value"] = 3
    for i in range(5):
        try:
            result = cb.call(unreliable_service, fallback)
            print(f"Probe #{i+1}: SUCCESS -> {result}")
        except CircuitBreakerOpenError:
            print(f"Probe #{i+1}: REJECTED")
        except Exception as e:
            print(f"Probe #{i+1}: ERROR -> {e}")
        print(f"  State: {cb.state.value}")

    print("\n[4] 熔断期间 Fallback 演示")
    print("-" * 40)
    cb.reset()
    call_count["value"] = 0

    def service_always_fails():
        raise ConnectionError("Service down")

    for i in range(3):
        result = cb.call(service_always_fails, fallback)
        print(f"Call #{i+1}: {result}")
        print(f"  State: {cb.state.value}")

    print("\n[5] 最终状态统计")
    print("-" * 40)
    print(f"Final state: {cb.state.value}")
    print(f"Stats: {cb.get_stats()}")

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
```

---

## 练习题

### 练习 1：实现基于成功率的熔断器

**要求：**
将当前的"连续失败次数"触发熔断改为"滑动窗口内成功率"触发熔断。这种方式更平滑，能适应偶发的成功，避免因为短暂抖动而熔断。

**提示：**
```python
@dataclass
class SlidingWindowStats:
    """滑动窗口统计"""
    timestamps: List[float] = field(default_factory=list)
    successes: int = 0
    failures: int = 0

    def add_result(self, success: bool, timestamp: float):
        """添加一次结果"""
        pass

    @property
    def success_rate(self) -> float:
        """计算窗口内的成功率"""
        pass

    def clean_old_entries(self, window_seconds: float, current_time: float):
        """清理过期的数据"""
        pass
```

**验收标准：**
- 滑动窗口内成功率低于阈值时触发熔断
- 窗口自动过期旧数据
- 统计信息实时更新

---

### 练习 2：实现嵌套熔断器（Bulkhead Pattern）

**要求：**
实现舱壁模式（Bulkhead Pattern），限制同时对某个服务的最大并发数，防止一个服务的故障影响其他服务。

**提示：**
```python
class BulkheadCircuitBreaker:
    """带舱壁限制的熔断器"""
    def __init__(self, max_concurrent: int, **kwargs):
        self._semaphore = Semaphore(max_concurrent)
        self._circuit_breaker = CircuitBreaker(**kwargs)
        pass

    def call(self, func: Callable, fallback: Callable = None):
        """执行调用，带并发限制"""
        pass
```

**验收标准：**
- 并发数超过限制时快速失败
- 与熔断器联动
- 支持 fallback

---

### 练习 3：实现熔断器可视化监控面板

**要求：**
实现一个 ASCII 可视化函数，实时展示熔断器的状态、健康度和历史状态变化。

**提示：**
```python
def visualize_circuit_breaker(cb: CircuitBreaker) -> str:
    """生成熔断器状态可视化"""
    pass

# 期望输出示例：
# ┌─────────────────────────────────────────────────┐
# │  Circuit Breaker Status                         │
# ├─────────────────────────────────────────────────┤
# │  State: [CLOSED]  ●────────────────────────────  │
# │  Stats: ✓ 10 | ✗ 0 | Total: 10                  │
# │  Health: 100% ██████████████████████████████   │
# │  Last Failure: 5 minutes ago                   │
# └─────────────────────────────────────────────────┘
```

**验收标准：**
- 显示当前状态（CLOSED/OPEN/HALF_OPEN）
- 显示成功/失败统计
- 显示健康度百分比
- 状态用颜色或 emoji 区分

---

## 九、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d24_circuit_breaker.py` | 三态熔断器 | [OK] |
| `tests/d24_test_circuit_breaker.py` | 19 个测试 | [OK] 19/19 PASS |
| `day24_study.md` | 本文档 | [OK] 已升级 |
