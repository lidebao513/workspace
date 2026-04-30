# Day 25 — 生产级错误体系

## 一、今日目标

> 学会设计分级异常体系：FATAL / ERROR / WARN 三级，配合 ErrorClassifier 自动分类、RetryEngine 决策、告警触发。这是 Week 5 的收尾——d22 压测发现问题，d23 重试解决瞬时故障，d24 熔断防止持续故障，d25 把故障标准化管理。

- 理解 5 种 AppError 子类的设计意图
- 掌握 ErrorClassifier 自动分类和决策规则
- 学会 should_retry / should_alert / is_fatal 判断逻辑
- 理解错误体系如何与重试、熔断、告警三层联动

---

## 二、异常分级设计

### 2.1 三级体系

| 级别 | 含义 | 处理动作 | 是否告警 | 是否重试 |
|------|------|----------|---------|---------|
| **FATAL** | 致命错误，不可恢复 | 立即停止 | ✅ | ❌ |
| **ERROR** | 可恢复错误，需关注 | 重试，仍然失败则告警 | ✅ | ✅ |
| **WARN** | 不严重，只需记录 | 记录日志 | ❌ | ❌ |

### 2.2 5 种错误子类

| 错误类 | 级别 | 触发条件 | 处理建议 |
|--------|------|---------|---------|
| `ConfigError` | FATAL | 配置文件缺失、格式错误 | 检查 .env / 环境变量 |
| `AuthError` | FATAL | API Key 无效、认证过期 | 检查凭证，重试无用 |
| `APIError` | ERROR | 5xx、连接异常、超时 | 重试 3-5 次，仍失败则告警 |
| `RateLimitError` | WARN | 429 Too Many Requests | 等待后重试（尊重 Retry-After） |
| `ValidationError` | WARN | 输入参数非法 | 校验入参，记录日志 |

### 2.3 AppErrorBase 数据模型

```python
@dataclass
class AppErrorBase(Exception):
    message: str                    # 人类可读的描述
    code: str                       # 机器可读的错误码
    severity: str                   # "FATAL" / "ERROR" / "WARN"
    component: str = ""             # 出错组件
    context: Dict = field(default_factory=dict)  # 运行时上下文
    timestamp: str = ""             # ISO 时间戳
```

---

## 三、ErrorClassifier 分类器

### 3.1 分类规则

```python
from utils.d25_error_system import (
    ErrorClassifier,
    ConfigError, AuthError, APIError,
    RateLimitError, ValidationError,
)

# 自动分类
error_cls = ErrorClassifier.classify(ConnectionError("Connection refused"))
# → APIError (severity=ERROR, should_retry=True, should_alert=True)
```

映射表：

| 原始异常 | 映射为 | 级别 | 重试 | 告警 | 致命 |
|---------|--------|------|------|------|------|
| `AppErrorBase` 子类 | 保持原类 | 原severity | ✅ | ✅ | 按级别 |
| `ConnectionError` | `APIError` | ERROR | ✅ | ✅ | ❌ |
| `TimeoutError` | `APIError` | ERROR | ✅ | ✅ | ❌ |
| `ValueError` | `ValidationError` | WARN | ❌ | ❌ | ❌ |
| 未知异常 | `AppErrorBase(code="UNKNOWN")` | ERROR | ❌ | ✅ | ❌ |

### 3.2 决策接口

```python
# 该不该重试？
cls.should_retry(ConfigError("missing key"))     # → False（致命错误重试也没用）
cls.should_retry(APIError("500 Internal"))        # → True（瞬时故障）

# 该不该告警？
cls.should_alert(RateLimitError("rate limited"))  # → True（需关注限流频率）
cls.should_alert(ValidationError("bad param"))    # → False（只记录日志）

# 是不是致命？
cls.is_fatal(ConfigError("missing key"))          # → True
cls.is_fatal(APIError("500"))                     # → False
```

---

## 四、三层联动体系

```
d22 LoadTester ── 发现问题
     │
     ▼
d23 RetryEngine ── 解决瞬时故障（超时/5xx）
     │
     ▼
d24 CircuitBreaker ── 保护持续故障（服务下线）
     │
     ▼
d25 ErrorSystem ── 分类 + 决策(重试/告警/停止) + 上下文
     │
     ├── should_retry() → 传给 RetryEngine
     ├── should_alert() → 传给告警系统
     └── is_fatal()     → 传给熔断器加快熔断
```

---

## 五、to_dict 序列化（事件追踪）

```python
error = ConfigError("DEEPSEEK_API_KEY not found", component="key_manager")
error_dict = error.to_dict()
# → {
#   "type": "ConfigError",
#   "message": "DEEPSEEK_API_KEY not found",
#   "code": "CONFIG_ERROR",
#   "severity": "FATAL",
#   "component": "key_manager",
#   "context": {},
#   "timestamp": "2026-04-30T19:00:00",
# }
```

可以直接序列化为 JSON 写入日志或监控系统。

---

## 六、完整使用示例

```python
from utils.d25_error_system import (
    APIError, ConfigError, ErrorClassifier,
)
from utils.d23_retry_engine import RetryEngine
from utils.d24_circuit_breaker import CircuitBreaker

engine = RetryEngine(max_retries=3, base_delay=1.0)
cb = CircuitBreaker(failure_threshold=5)

def safe_api_call(prompt):
    try:
        return cb.call(
            lambda: engine.execute(api_request, args=(prompt,)),
            fallback=lambda: {"degraded": True, "text": ""}
        )
    except Exception as e:
        cls = ErrorClassifier.classify(e)
        if cls.is_fatal(e):
            raise  # 致命错误传播出去
        if cls.should_alert(e):
            send_alert(f"[{e.severity}] {e}")
        return {"error": str(e), "code": e.code}
```

---

## 七、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| 各错误子类创建 | 设置 message, code | 属性正确 |
| to_dict 结构 | 序列化 | code/severity/message 都在 |
| 分类 ConnectionError | classify | → APIError |
| 分类 TimeoutError | classify | → APIError |
| 分类 ValueError | classify | → ValidationError |
| 分类 AppError | classify | 保持原类 |
| 未知异常 | classify | → code="UNKNOWN" |
| should_retry | FATAL | False |
| should_retry | ERROR | True |
| should_alert | ERROR | True |
| should_alert | WARN | False |
| is_fatal | ConfigError | True |
| is_fatal | APIError | False |

---

## 八、面试话术

> "我设计了一套三级错误体系：FATAL（配置/认证错误）直接终止因为重试也解决不了，ERROR（5xx/超时）先重试再告警，WARN（参数校验/限流）只记录日志。ErrorClassifier 自动把通用 Python 异常（ConnectionError、TimeoutError、ValueError）映射到标准的 AppError 子类。"

> "这套体系与 d23 RetryEngine 和 d24 CircuitBreaker 联动。ErrorClassifier 的 `should_retry()` 直接决定 RetryEngine 是否重试，`is_fatal()` 加速熔断器熔断，`should_alert()` 触发告警。三层形成一个闭环——压测发现问题、重试解决瞬时故障、熔断保护持续故障、错误分类做最终决策。"

---

## 九、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d25_error_system.py` | 错误体系（5 子类 + 分类器） | [OK] |
| `tests/d25_test_error_system.py` | 20 个测试 | [OK] 20/20 PASS |
| `day25_study.md` | 本文档 | [OK] 已升级 |
