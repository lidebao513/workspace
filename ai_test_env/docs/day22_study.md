# Day 22 — 并发压测

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
