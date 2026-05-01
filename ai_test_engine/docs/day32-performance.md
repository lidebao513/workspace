# Day 32 — 性能测试模块

## 学习目标

1. 理解 P50/P90/P95/P99 百分位数的含义，学会计算和解读性能指标
2. 掌握吞吐量计算方法，学会评估系统的处理能力
3. 理解熔断器三态机制，学会实现服务保护
4. 掌握 Token 计费模式，学会成本估算和异常检测

## 一、引言

性能测试回答三个问题：能撑住多少并发？服务会不会被拖死？Token 烧了多少钱？

## 二、前置知识讲解

### 2.1 P95/P99 是什么？

**一句话定义：** 把所有请求按耗时排序，排在第 95%（P95）和第 99%（P99）位置的耗时值。

**面试话术：** "平均延迟会说谎。5 个请求 0.1/0.1/0.1/0.1/10 秒，平均 2 秒——但其实 4 个请求都快。P99 能告诉你最慢的 1% 有多慢。AI API 的常见模式是 80% 请求 0.3 秒，但偶尔有 3 秒的 outlier。"

### 2.2 什么是吞吐量（Throughput）？

**一句话定义：** 单位时间内完成的请求数（Requests Per Second, RPS）。

**公式：**
```
Throughput = total_requests / total_time
```

**面试话术：** "吞吐量和并发数不是线性关系。从 1 并发到 2 并发吞吐量翻倍，但从 10 到 20 可能只涨 30%。找到拐点是压测的核心目标。"

### 2.3 熔断器三态

```
CLOSED → (失败超过阈值) → OPEN → (超时恢复) → HALF_OPEN → (成功) → CLOSED
                                          ↑                    ↓
                                          +— (再次失败) —————→ OPEN
```

**面试话术：** "熔断器和重试是两回事。重试是**微观**层面——这次请求失败了再试一次。熔断器是**宏观**层面——你的服务已经扛不住了，停止所有请求让它喘口气。熔断要内嵌足够的信息来判断服务是否恢复。"

### 2.4 Token 计费模式

**一句话定义：** AI API 按 Token 数计费，输入和输出 Token 价格不同。

| 类型 | DeepSeek 参考价 |
|------|----------------|
| 输入 Token | $0.0005 /1K |
| 输出 Token | $0.0015 /1K |

**面试话术：** "输出 Token 是输入的 3 倍价格。测试时如果发现输出太长，先看是不是 max_tokens 设置过大——我曾见过 max_tokens=4096 导致单次调用成本 $0.006，改成 1024 后成本降到 $0.001。"

## 三、需求分析

17 个测试用例：
| 分组 | 数量 | 测试内容 |
|------|------|----------|
| LoadTester | 5 个 | 并发、吞吐量、P50/P90/P99、空数据 |
| CircuitBreaker | 8 个 | 三态切换、阈值、超时恢复、call 方法 |
| TokenAuditor | 5 个 | 计费、汇总、成本累积、空报告 |

## 四、运行结果

```
17 passed (performance: 17)
```

## 五、工作场景

- 上线前压测确认性能基线
- API 降级时熔断器自动保护
- 每周 Token 审计报告

## 六、面试问题

**Q: 熔断器的 recovery_timeout 怎么设置？**
A: 主要看 API 恢复的平均时间。我的经验是设成 API P99 的 3 倍。比如 P99 是 2 秒，recovery_timeout 设 6 秒。

**Q: Token 审计里的异常检测怎么做的？**
A: 环比——对比前一天的总 Token 消耗。增长超过 50% 标记为 SPIKE，下降超过 50% 标记为 DROP，连续 3 天增长标记为 STEADY_INCREASE。

**Q: P95/P99 为什么比平均延迟更重要？**
A: 平均延迟会被极端值影响，不能反映真实用户体验。P99 告诉你最慢的 1% 请求有多慢，这部分用户可能会遇到严重的性能问题，是优化的重点。

**Q: 熔断器和重试机制有什么区别？**
A: 重试是微观层面的——针对单个失败请求进行重试；熔断器是宏观层面的——当服务持续失败时，主动停止所有请求，让服务有时间恢复。两者是互补的，不是互斥的。

## 七、代码示例

### 熔断器实现

```python
from dataclasses import dataclass
from enum import Enum
import time
from typing import Callable, Optional, Any

class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态，允许请求
    OPEN = "open"          # 熔断状态，拒绝请求
    HALF_OPEN = "half_open"  # 半开状态，允许少量试探请求

@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5      # 失败阈值
    recovery_timeout: float = 60.0  # 恢复超时时间（秒）
    reset_timeout: float = 10.0     # 半开状态试探间隔（秒）

class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._last_attempt_time = 0.0
    
    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        if self._state == CircuitState.OPEN:
            # 检查是否可以进入半开状态
            if time.time() - self._last_failure_time >= self.config.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state
    
    def _record_success(self):
        """记录成功，重置失败计数"""
        self._failure_count = 0
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
    
    def _record_failure(self):
        """记录失败，更新状态"""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.config.failure_threshold:
            self._state = CircuitState.OPEN
    
    def call(self, func: Callable, *args, fallback: Optional[Callable] = None, **kwargs) -> Any:
        """执行函数，带熔断保护"""
        current_state = self.state
        
        if current_state == CircuitState.OPEN:
            if fallback:
                return fallback()
            raise Exception("Circuit breaker is open")
        
        # 半开状态下限制请求频率
        if current_state == CircuitState.HALF_OPEN:
            if time.time() - self._last_attempt_time < self.config.reset_timeout:
                if fallback:
                    return fallback()
                raise Exception("Circuit breaker is in half-open state, too soon")
            self._last_attempt_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise e

### Token 审计实现

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict
import os

@dataclass
class TokenRecord:
    """Token 记录"""
    timestamp: datetime
    prompt_tokens: int
    completion_tokens: int
    model: str = "deepseek-chat"

@dataclass
class DailyReport:
    """每日报告"""
    date: str
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    call_count: int = 0
    cost_usd: float = 0.0

class TokenAuditor:
    """Token 审计器"""
    
    # DeepSeek 价格（美元/1K Token）
    PRICING = {
        "prompt": 0.0005,
        "completion": 0.0015
    }
    
    def __init__(self):
        self._records: List[TokenRecord] = []
    
    def record_call(self, prompt_tokens: int, completion_tokens: int, 
                   model: str = "deepseek-chat") -> None:
        """记录一次 API 调用"""
        self._records.append(TokenRecord(
            timestamp=datetime.now(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model
        ))
    
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """计算单次调用成本"""
        prompt_cost = (prompt_tokens / 1000) * self.PRICING["prompt"]
        completion_cost = (completion_tokens / 1000) * self.PRICING["completion"]
        return prompt_cost + completion_cost
    
    def daily_report(self, date: str = None) -> DailyReport:
        """生成每日报告"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        day_records = [r for r in self._records 
                      if r.timestamp.strftime("%Y-%m-%d") == date]
        
        report = DailyReport(date=date)
        for record in day_records:
            report.total_prompt_tokens += record.prompt_tokens
            report.total_completion_tokens += record.completion_tokens
            report.call_count += 1
            report.cost_usd += self.calculate_cost(
                record.prompt_tokens, record.completion_tokens
            )
        
        return report
    
    def total_cost(self) -> float:
        """计算累积总费用"""
        return sum(self.calculate_cost(r.prompt_tokens, r.completion_tokens) 
                  for r in self._records)
    
    def detect_anomaly(self, baseline: DailyReport, current: DailyReport) -> str:
        """检测 Token 消耗异常"""
        if baseline.total_prompt_tokens == 0:
            return "NO_BASELINE"
        
        prompt_ratio = current.total_prompt_tokens / baseline.total_prompt_tokens
        completion_ratio = current.total_completion_tokens / baseline.total_completion_tokens
        
        if prompt_ratio > 1.5 or completion_ratio > 1.5:
            return "SPIKE"
        elif prompt_ratio < 0.5 or completion_ratio < 0.5:
            return "DROP"
        return "NORMAL"

# 使用示例
if __name__ == "__main__":
    # 测试熔断器
    breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2, recovery_timeout=5))
    
    def unstable_service():
        import random
        if random.random() > 0.3:
            raise Exception("Service unavailable")
        return "Success"
    
    # 模拟多次失败
    try:
        for _ in range(3):
            breaker.call(unstable_service)
    except Exception as e:
        print(f"熔断器触发: {e}")
    
    print(f"熔断器状态: {breaker.state}")
    
    # 测试 Token 审计
    auditor = TokenAuditor()
    auditor.record_call(100, 200)
    auditor.record_call(150, 250)
    
    report = auditor.daily_report()
    print(f"每日报告: {report}")
    print(f"总费用: ${auditor.total_cost():.4f}")
```

## 八、产出物

- `tests/performance/test_performance.py` — 17 个测试

## 九、练习题

1. **基础题：** 实现一个 `calculate_percentile()` 函数，接受耗时列表和百分位值（如 50、90、95、99），返回对应的百分位数值。

2. **进阶题：** 为 `CircuitBreaker` 添加 `get_metrics()` 方法，返回熔断器的统计信息，包括总调用次数、成功次数、失败次数、状态切换次数。

3. **挑战题：** 实现一个 `LoadTester` 类，支持并发压测，能够计算吞吐量、P50/P90/P95/P99 延迟，并生成压测报告。

## 十、自检清单

- [ ] LoadTester 能跑并发并计算吞吐量
- [ ] percentile 计算正确（P50/P90/P99）
- [ ] CircuitBreaker 三态切换正确
- [ ] HALF_OPEN 失败回到 OPEN
- [ ] Token 审计输入/输出分开计费
