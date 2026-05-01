# Day 22 — 并发压测

## 学习目标

1. **理解并发压测指标**：掌握 P50/P95/P99 百分位延迟、RPS、QPS 的含义和计算方式
2. **掌握 LoadTester**：熟练使用 ThreadPoolExecutor 实现并发压测
3. **理解预热机制**：掌握 warmup 轮次排除冷启动偏差的原理
4. **解读 LatencyReport**：能够从延迟报告中找到性能瓶颈
5. **调优性能参数**：理解并发度与 RPS、延迟的关系

---

## 一、今日目标

> 学会用线程池对 AI API 做并发压力测试，计算 P50/P95/P99 延迟百分位、RPS 吞吐量、成功率和总耗时。这是性能测试的基础能力。

- 理解并发压测的核心指标含义（P50/P95/P99、RPS、QPS）
- 掌握 `LoadTester` 的 ThreadPoolExecutor 实现
- 学会预热（warmup）排除冷启动偏差
- 能解读 LatencyReport 找到性能瓶颈

---

## 二、核心指标详解

### 2.1 P50 / P95 / P99 百分位延迟

| 指标 | 含义 | 计算公式 | 典型值 |
|------|------|---------|--------|
| **P50** | 一半的请求快于这个值 | `data[0.5 × N]` | 200ms（中位体验） |
| **P95** | 95% 的请求快于这个值 | `data[0.95 × N]` | 800ms（SLA 目标） |
| **P99** | 99% 的请求快于这个值 | `data[0.99 × N]` | 2s（长尾优化目标） |
| **Avg** | 算术平均 | `sum / len` | 受极端值影响大 |
| **Min** | 最小延迟 | `min(data)` | 可能来自缓存 |
| **Max** | 最大延迟 | `max(data)` | 排查优化的起点 |

**为什么要用百分位而不是平均值？**
- 5% 的慢请求（1-2s）会拉高平均值，掩盖"95% 的用户体验其实很好"
- P95 比 Avg 更适合做 SLA：`P95 < 2s` 意味着 95% 的请求在 2 秒内完成
- P99 反映"最差的那 1%"有多差——对实时交互类产品至关重要

### 2.2 RPS（Requests Per Second）

```
RPS = total_requests / total_time
```

- 衡量系统吞吐量
- 高 RPS 不一定好——如果请求质量低（空回复、截断），RPS 再高也没用
- 需结合成功率一起看

---

## 三、LoadTester 架构

### 3.1 核心流程

```
run(total_requests)
  │
  ├── warmup 轮次（不计入统计）
  │     └── for _ in range(warmup): target_fn()
  │
  ├── start_time = time.perf_counter()
  │
  ├── ThreadPoolExecutor.submit(_worker) × total_requests
  │     └── _worker()
  │           ├── t0 = time.time_ns()
  │           ├── try: target_fn() → elapsed_ms = (time_ns - t0) / 1e6 → latencies.append()
  │           └── except Exception: elapsed_ms → latencies.append()
  │
  ├── as_completed 收集
  ├── end_time = time.perf_counter()
  └── 返回 LatencyReport
```

### 3.2 关键设计点

- **`time.perf_counter()`** 用于总耗时——高精度（纳秒级），不会因为耗时极短返回 0
- **`time.time_ns()`** 用于单次延迟——纳秒精度，除以 1,000,000 转换为毫秒
- **`threading.Lock()`** 保护 `latencies` 列表和计数器——多线程并发写入必须锁
- **预热轮次**：服务端首次响应可能涉及缓存填充、连接池初始化，预热 10 轮后 P95 可能降 30%

### 3.3 API 参考

```python
from utils.d22_load_tester import LoadTester

# 基础使用
tester = LoadTester(
    target_fn=my_api_call,   # 待压测函数
    concurrency=5,            # 5 个并发线程
    warmup=3,                 # 3 轮预热
)
report = tester.run(total_requests=100)

# 带参数
report = tester.run(total_requests=100,
                    fn_args=("prompt_text",),
                    fn_kwargs={"temperature": 0.7})

# 查看报告
print(report.summary())
print(f"成功率: {report.success_rate():.1%}")
print(f"P95: {report.p95:.1f}ms, RPS: {report.rps:.1f}")
```

### 3.4 LatencyReport 数据模型

```python
@dataclass
class LatencyReport:
    p50: float              # P50 延迟 (ms)
    p95: float              # P95 延迟 (ms)
    p99: float              # P99 延迟 (ms)
    avg: float              # 平均延迟 (ms)
    min_latency: float      # 最小延迟 (ms)
    max_latency: float      # 最大延迟 (ms)
    rps: float              # 每秒请求数
    total_time: float       # 总耗时 (s)
    total_requests: int     # 总请求数
    success_count: int      # 成功数
    fail_count: int         # 失败数
    individual_latencies: List[float]  # 所有延迟值
```

---

## 四、性能分析示例

```python
from utils.d22_load_tester import LoadTester
import time

# 模拟一个 API 调用（随机延迟 50-300ms）
def mock_api(*args, **kwargs):
    delay = 0.05 + (kwargs.get("seed", 0) % 51) * 0.005
    time.sleep(delay)
    return f"response {delay:.2f}s"

# 不同并发度对比
for concurrency in [1, 5, 10, 20]:
    tester = LoadTester(mock_api, concurrency=concurrency, warmup=5)
    report = tester.run(100, fn_kwargs={"seed": 42})
    print(f"并发={concurrency}: RPS={report.rps:.1f}  "
          f"P50={report.p50:.1f}ms  P95={report.p95:.1f}ms  "
          f"成功={report.success_rate():.0%}")
```

输出示例：
```
并发=1: RPS=9.5  P50=100.4ms  P95=152.1ms  成功=100%
并发=5: RPS=32.1  P50=110.2ms  P95=210.5ms  成功=100%
并发=10: RPS=38.8  P50=175.0ms  P95=350.2ms  成功=100%
并发=20: RPS=42.0  P50=250.1ms  P95=510.8ms  成功=100%
```

**解读**：并发从 1→5 时 RPS 提升 3.4x（接近线性）；5→10 时只提升 1.2x（开始瓶颈）；10→20 几乎无提升（达到系统上限，延迟还翻倍了）。最优并发度 = 5-10。

---

## 五、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| 单请求 | `run(1)` | 1 次成功，total_time > 0 |
| 多请求 | `run(10)` | 10 次成功，latencies 长度 = 10 |
| 零请求 | `run(0)` | 报告为空 |
| 全部失败 | `run(5)` on err_fn | fail_count=5, total_time > 0 |
| 部分失败 | 交替成功/失败 | success > 0, fail > 0 |
| 预热 | warmup=3 | 3 轮不记账 |
| 百分位 | 50 个均匀数据 | P50=49, P95=94, P99=98 |
| 空数据 | `_percentile([], 50)` | 0.0 |

---

## 六、面试话术

> "我用 ThreadPoolExecutor 做并发压测，预热轮次排除冷启动偏差。P50/P95/P99 用排序后取位置值计算，不依赖统计分布假设。RPS = 总请求 / 总耗时。高并发时注意线程安全——延迟列表用 `threading.Lock` 保护，避免并发 append 引起数据竞态。time 用 `perf_counter()` 保证纳秒级精度，不会因为请求太快返回 0。"

> "我们当时以 P95 < 2s 为 SLA 目标，因为平均延迟会被慢请求拉高，P95 更能反映真实用户体验。压测结果指导了并发度调优——从 1 并发到 10 并发，RPS 提升 4 倍，超过 10 后进入瓶颈区，延迟反而翻倍。"

---

## 七、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d22_load_tester.py` | 并发压测模块 | [OK] |
| `tests/d22_test_load_tester.py` | 20 个测试 | [OK] 20/20 PASS |
| `day22_study.md` | 本文档 | [OK] 已升级 |

---

## 面试题

### 面试题 1：如何设计一个生产级的并发压测系统？

**答案：**

设计生产级并发压测系统需要考虑精确度、稳定性和可扩展性：

**1. 核心指标设计**
- P50/P95/P99 百分位：排序后取对应位置值
- RPS = 总请求数 / 总耗时
- 成功率 = 成功请求数 / 总请求数

**2. 线程安全实现**
```python
from threading import Lock

class ThreadSafeList:
    def __init__(self):
        self._data = []
        self._lock = Lock()
    
    def append(self, item):
        with self._lock:
            self._data.append(item)
```

**3. 预热机制**
- 首次请求涉及缓存填充、连接池初始化
- 预热 3-10 轮后 P95 可能降低 30%
- 预热轮次不计入统计

**4. 时间精度**
- `time.perf_counter()` 用于总耗时（纳秒级）
- `time.time_ns()` 用于单次延迟，除以 1e6 转为毫秒

**5. 异常处理**
- 单次请求失败不影响整体统计
- 失败延迟记为 -1 或特殊值
- 区分超时和系统错误

### 面试题 2：如何根据压测结果进行性能调优？

**答案：**

根据压测结果进行性能调优的步骤：

**1. 分析延迟分布**
- P50 过高 → 中位数性能差
- P95 过高 → 存在慢请求
- P99 过高 → 长尾问题严重

**2. 并发度调优**
```
1 并发 → 基准 RPS
10 并发 → RPS 提升 4-6 倍
超过瓶颈 → 延迟翻倍，RPS 下降
```

**3. 瓶颈定位**
- CPU 瓶颈：执行时间占比高
- I/O 瓶颈：等待时间占比高
- 连接池瓶颈：并发数受限于连接数

**4. 调优策略**
- 增加并发度（线程池大小）
- 优化连接池配置
- 实施缓存策略
- 异步化改造

---

## 代码示例

### 并发压测器实现

```python
import time
import threading
from typing import List, Callable, Optional, Dict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

@dataclass
class LatencyReport:
    total_requests: int
    success_count: int
    failure_count: int
    latencies_ms: List[float]
    total_time_ms: float
    
    @property
    def success_rate(self) -> float:
        return self.success_count / self.total_requests if self.total_requests > 0 else 0.0
    
    @property
    def rps(self) -> float:
        return self.total_requests / (self.total_time_ms / 1000) if self.total_time_ms > 0 else 0.0
    
    def percentile(self, p: float) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        index = int(len(sorted_latencies) * p / 100)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]
    
    def display(self) -> str:
        return f"""Latency Report:
  Total Requests: {self.total_requests}
  Success: {self.success_count} ({self.success_rate:.1%})
  Failure: {self.failure_count}
  RPS: {self.rps:.2f}
  Latency:
    Min: {min(self.latencies_ms):.2f}ms
    P50: {self.percentile(50):.2f}ms
    P95: {self.percentile(95):.2f}ms
    P99: {self.percentile(99):.2f}ms
    Max: {max(self.latencies_ms):.2f}ms
    Avg: {statistics.mean(self.latencies_ms):.2f}ms"""

class LoadTester:
    """并发压测器"""
    
    def __init__(
        self,
        concurrency: int = 10,
        warmup_rounds: int = 3
    ):
        self.concurrency = concurrency
        self.warmup_rounds = warmup_rounds
    
    def run(
        self,
        target_fn: Callable,
        total_requests: int,
        timeout_ms: int = 30000
    ) -> LatencyReport:
        latencies = []
        success_count = 0
        failure_count = 0
        lock = threading.Lock()
        
        # 预热阶段
        for _ in range(self.warmup_rounds):
            try:
                target_fn()
            except Exception:
                pass
        
        # 并发压测阶段
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = []
            for _ in range(total_requests):
                future = executor.submit(self._worker, target_fn, timeout_ms, latencies, lock)
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    success, latency = future.result()
                    with lock:
                        if success:
                            success_count += 1
                            latencies.append(latency)
                        else:
                            failure_count += 1
                except Exception:
                    with lock:
                        failure_count += 1
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        return LatencyReport(
            total_requests=total_requests,
            success_count=success_count,
            failure_count=failure_count,
            latencies_ms=latencies,
            total_time_ms=total_time_ms
        )
    
    def _worker(
        self,
        target_fn: Callable,
        timeout_ms: int,
        latencies: List,
        lock: threading.Lock
    ) -> tuple:
        t0 = time.time_ns()
        try:
            result = target_fn()
            latency_ms = (time.time_ns() - t0) / 1_000_000
            return True, latency_ms
        except Exception as e:
            latency_ms = (time.time_ns() - t0) / 1_000_000
            return False, latency_ms

def mock_api_call() -> str:
    """模拟 API 调用"""
    time.sleep(0.1)  # 100ms 延迟
    return "response"

# 使用示例
tester = LoadTester(concurrency=10, warmup_rounds=3)

def slow_api():
    time.sleep(0.2)
    return "ok"

report = tester.run(slow_api, total_requests=100)
print(report.display())
print(f"RPS: {report.rps:.2f}")
print(f"P95 Latency: {report.percentile(95):.2f}ms")
```

---

## 练习题

### 练习题 1：实现异步压测器

**要求：**
使用 asyncio 实现异步版本的压测器。

**步骤：**
1. 使用 asyncio.create_task 创建异步任务
2. 实现异步延迟统计
3. 支持协程池控制并发
4. 对比同步 vs 异步性能

### 练习题 2：实现压测结果可视化

**要求：**
实现压测结果的可视化报告生成器。

**步骤：**
1. 实现延迟分布直方图
2. 生成时间序列图
3. 支持导出 HTML 报告
4. 添加响应时间趋势分析

### 练习题 3：实现分布式压测客户端

**要求：**
实现支持多节点协同的分布式压测客户端。

**步骤：**
1. 设计 Master-Worker 架构
2. 实现任务分发和结果汇总
3. 支持节点健康检测
4. 生成汇总报告

---
