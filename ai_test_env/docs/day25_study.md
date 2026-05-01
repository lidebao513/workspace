# Day 25 — 生产级错误体系

## 学习目标

1. 理解 5 种 AppError 子类的设计意图和分级原则
2. 掌握 ErrorClassifier 自动分类和决策规则
3. 学会 should_retry / should_alert / is_fatal 判断逻辑
4. 理解错误体系如何与重试、熔断、告警三层联动

---

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

## 面试题

### 题目 1：如何设计一个生产级别的错误处理体系？

**参考答案：**

**错误分类的重要性：**

生产环境中的错误多种多样，不是所有错误都需要重试，也不是所有错误都应该立即告警。一个好的错误体系需要：

1. **精确分类**：将错误分为 FATAL / ERROR / WARN 三级
2. **自动映射**：把通用的 Python 异常映射到业务错误类型
3. **决策自动化**：通过 `should_retry()`、`should_alert()`、`is_fatal()` 自动决定处理方式

**三级错误体系设计：**

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime

class ErrorSeverity(Enum):
    FATAL = "fatal"      # 致命错误，不可恢复
    ERROR = "error"      # 可恢复错误，需关注
    WARN = "warn"        # 不严重，只需记录

@dataclass
class AppError(Exception):
    message: str
    code: str
    severity: ErrorSeverity
    component: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

# 具体的错误子类
@dataclass
class ConfigError(AppError):
    """配置错误 - FATAL"""
    def __init__(self, message: str, component: str = ""):
        super().__init__(
            message=message,
            code="CONFIG_ERROR",
            severity=ErrorSeverity.FATAL,
            component=component
        )

@dataclass
class AuthError(AppError):
    """认证错误 - FATAL"""
    def __init__(self, message: str, component: str = ""):
        super().__init__(
            message=message,
            code="AUTH_ERROR",
            severity=ErrorSeverity.FATAL,
            component=component
        )

@dataclass
class APIError(AppError):
    """API 错误 - ERROR"""
    def __init__(self, message: str, status_code: int = 0, component: str = ""):
        super().__init__(
            message=message,
            code=f"API_ERROR_{status_code}" if status_code else "API_ERROR",
            severity=ErrorSeverity.ERROR,
            component=component,
            context={"status_code": status_code}
        )

@dataclass
class RateLimitError(AppError):
    """限流错误 - WARN"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(
            message=message,
            code="RATE_LIMIT_ERROR",
            severity=ErrorSeverity.WARN,
            context={"retry_after": retry_after} if retry_after else {}
        )
```

**错误分类器设计：**

```python
class ErrorClassifier:
    """错误分类器 - 自动将通用异常映射到业务错误"""

    EXCEPTION_MAP = {
        ConnectionError: (APIError, {"severity": ErrorSeverity.ERROR}),
        TimeoutError: (APIError, {"severity": ErrorSeverity.ERROR}),
        ValueError: (ValidationError, {"severity": ErrorSeverity.WARN}),
        KeyError: (ValidationError, {"severity": ErrorSeverity.WARN}),
    }

    @classmethod
    def classify(cls, exception: Exception) -> AppError:
        """将异常分类为 AppError"""
        if isinstance(exception, AppError):
            return exception

        for exc_type, (app_error_cls, defaults) in cls.EXCEPTION_MAP.items():
            if isinstance(exception, exc_type):
                return app_error_cls(
                    message=str(exception),
                    component=getattr(exception, 'component', ''),
                    **defaults
                )

        return AppError(
            message=str(exception),
            code="UNKNOWN_ERROR",
            severity=ErrorSeverity.ERROR
        )

    @classmethod
    def should_retry(cls, error: AppError) -> bool:
        """判断是否应该重试"""
        return error.severity in (ErrorSeverity.ERROR,)

    @classmethod
    def should_alert(cls, error: AppError) -> bool:
        """判断是否应该告警"""
        return error.severity in (ErrorSeverity.FATAL, ErrorSeverity.ERROR)

    @classmethod
    def is_fatal(cls, error: AppError) -> bool:
        """判断是否为致命错误"""
        return error.severity == ErrorSeverity.FATAL
```

**与重试、熔断的联动：**

```python
def safe_api_call(api_func, *args, **kwargs):
    error_classifier = ErrorClassifier()

    try:
        result = api_func(*args, **kwargs)
        return result
    except Exception as e:
        error = error_classifier.classify(e)

        if error_classifier.is_fatal(error):
            raise  # 致命错误直接传播

        if error_classifier.should_retry(error):
            # 交给重试引擎处理
            return retry_engine.execute(api_func, *args, **kwargs)

        if error_classifier.should_alert(error):
            # 触发告警
            send_alert(f"[{error.severity.value}] {error.code}: {error.message}")

        return None
```

---

### 题目 2：错误体系如何与监控告警系统集成？

**参考答案：**

**告警策略设计：**

不是所有错误都需要告警，过多的告警会导致"告警疲劳"。常见的告警策略：

| 错误级别 | 触发条件 | 处理方式 |
|---------|---------|---------|
| FATAL | 立即触发 | 立即告警 + 停止流程 |
| ERROR | 首次出现 + 频率超过阈值 | 首次告警 + 频率告警 |
| WARN | 不告警 | 只记录日志 |

**告警去重机制：**

```python
from collections import defaultdict
from datetime import datetime, timedelta

class AlertDeduplicator:
    """告警去重器 - 防止同一错误重复告警"""

    def __init__(self, dedup_window_seconds: int = 300):
        self.dedup_window = dedup_window_seconds
        self._alert_history: Dict[str, datetime] = {}

    def should_alert(self, error_code: str) -> bool:
        """检查是否应该告警（去重）"""
        now = datetime.now()

        if error_code not in self._alert_history:
            self._alert_history[error_code] = now
            return True

        last_alert = self._alert_history[error_code]
        if (now - last_alert).total_seconds() > self.dedup_window:
            self._alert_history[error_code] = now
            return True

        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取告警统计"""
        return {
            "total_tracked": len(self._alert_history),
            "errors": list(self._alert_history.keys())
        }
```

**告警分级：**

```python
class AlertManager:
    """告警管理器"""

    def __init__(self):
        self._deduplicator = AlertDeduplicator()
        self._alert_handlers = {
            "slack": SlackAlertHandler(),
            "pagerduty": PagerDutyHandler(),
            "email": EmailHandler(),
        }

    def send_alert(
        self,
        error: AppError,
        level: str = "medium",
        metadata: Optional[Dict] = None
    ):
        """发送告警"""
        if not self._deduplicator.should_alert(error.code):
            return  # 跳过重复告警

        alert = Alert(
            error_code=error.code,
            message=error.message,
            severity=error.severity.value,
            level=level,
            timestamp=error.timestamp,
            metadata=metadata or {}
        )

        handler = self._alert_handlers.get(level)
        if handler:
            handler.send(alert)

    def get_suppressed_count(self, error_code: str) -> int:
        """获取被抑制的告警数量"""
        # 用于监控告警抑制情况
        pass
```

**错误追踪集成：**

```python
class ErrorTracker:
    """错误追踪 - 集成 Sentry 等工具"""

    def __init__(self, dsn: str = None):
        self._enabled = dsn is not None

    def capture_exception(
        self,
        error: AppError,
        context: Optional[Dict] = None
    ):
        """捕获并上报异常"""
        if not self._enabled:
            return

        event = {
            "error_code": error.code,
            "severity": error.severity.value,
            "component": error.component,
            "message": error.message,
            "timestamp": error.timestamp,
            "context": error.context,
            "extra": context or {}
        }

        # 上报到 Sentry / Grafana / etc
        self._report(event)

    def add_breadcrumb(self, message: str, level: str = "info"):
        """添加面包屑导航"""
        pass
```

---

## 代码示例

```python
"""
Day 25 代码示例：生产级错误体系完整实现
演示错误分类、决策逻辑和告警集成
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, Type
from datetime import datetime
import time


class ErrorSeverity(Enum):
    FATAL = "fatal"
    ERROR = "error"
    WARN = "warn"


@dataclass
class AppError(Exception):
    message: str
    code: str
    severity: ErrorSeverity
    component: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "severity": self.severity.value,
            "component": self.component,
            "context": self.context,
            "timestamp": self.timestamp,
        }


class ConfigError(AppError):
    def __init__(self, message: str, component: str = ""):
        super().__init__(
            message=message, code="CONFIG_ERROR",
            severity=ErrorSeverity.FATAL, component=component
        )


class AuthError(AppError):
    def __init__(self, message: str, component: str = ""):
        super().__init__(
            message=message, code="AUTH_ERROR",
            severity=ErrorSeverity.FATAL, component=component
        )


class APIError(AppError):
    def __init__(self, message: str, status_code: int = 0, component: str = ""):
        super().__init__(
            message=message,
            code=f"API_ERROR_{status_code}" if status_code else "API_ERROR",
            severity=ErrorSeverity.ERROR,
            component=component,
            context={"status_code": status_code}
        )


class RateLimitError(AppError):
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(
            message=message, code="RATE_LIMIT_ERROR",
            severity=ErrorSeverity.WARN,
            context={"retry_after": retry_after} if retry_after else {}
        )


class ValidationError(AppError):
    def __init__(self, message: str, field: str = ""):
        super().__init__(
            message=message, code="VALIDATION_ERROR",
            severity=ErrorSeverity.WARN,
            context={"field": field} if field else {}
        )


class ErrorClassifier:
    """错误分类器 - 将通用异常映射到业务错误"""

    EXCEPTION_MAP: Dict[Type[Exception], Tuple[Type[AppError], Dict]] = {
        ConnectionError: (APIError, {}),
        TimeoutError: (APIError, {}),
        OSError: (APIError, {}),
        ValueError: (ValidationError, {}),
        KeyError: (ValidationError, {}),
        TypeError: (ValidationError, {}),
    }

    @classmethod
    def classify(cls, exception: Exception) -> AppError:
        if isinstance(exception, AppError):
            return exception

        for exc_type, (app_error_cls, defaults) in cls.EXCEPTION_MAP.items():
            if isinstance(exception, exc_type):
                return app_error_cls(
                    message=str(exception),
                    component=getattr(exception, 'component', ''),
                    **defaults
                )

        return AppError(
            message=str(exception),
            code="UNKNOWN_ERROR",
            severity=ErrorSeverity.ERROR
        )

    @classmethod
    def should_retry(cls, error: AppError) -> bool:
        return error.severity == ErrorSeverity.ERROR

    @classmethod
    def should_alert(cls, error: AppError) -> bool:
        return error.severity in (ErrorSeverity.FATAL, ErrorSeverity.ERROR)

    @classmethod
    def is_fatal(cls, error: AppError) -> bool:
        return error.severity == ErrorSeverity.FATAL


class AlertDeduplicator:
    """告警去重器"""

    def __init__(self, dedup_window_seconds: int = 300):
        self.dedup_window = dedup_window_seconds
        self._alert_history: Dict[str, datetime] = {}
        self._suppressed_count: Dict[str, int] = {}

    def should_alert(self, error_code: str) -> bool:
        now = datetime.now()
        if error_code not in self._alert_history:
            self._alert_history[error_code] = now
            return True

        last_alert = self._alert_history[error_code]
        if (now - last_alert).total_seconds() > self.dedup_window:
            self._alert_history[error_code] = now
            return True

        self._suppressed_count[error_code] = self._suppressed_count.get(error_code, 0) + 1
        return False

    def get_suppressed(self, error_code: str) -> int:
        return self._suppressed_count.get(error_code, 0)


class ProductionErrorHandler:
    """生产级错误处理器 - 整合所有组件"""

    def __init__(self):
        self.classifier = ErrorClassifier()
        self.deduplicator = AlertDeduplicator()
        self._error_log: list = []

    def handle(self, exception: Exception) -> Optional[Any]:
        error = self.classifier.classify(exception)
        self._error_log.append(error.to_dict())

        if self.classifier.is_fatal(error):
            self._send_alert(error)
            raise error

        if self.classifier.should_retry(error):
            return {"action": "retry", "error": error.to_dict()}

        if self.classifier.should_alert(error):
            self._send_alert(error)

        return {"action": "ignore", "error": error.to_dict()}

    def _send_alert(self, error: AppError):
        if self.deduplicator.should_alert(error.code):
            print(f"[ALERT] {error.severity.value.upper()}: {error.code} - {error.message}")
        else:
            suppressed = self.deduplicator.get_suppressed(error.code)
            print(f"[SUPPRESSED] {error.code} (suppressed {suppressed} times)")


def demo():
    """演示错误处理体系"""
    print("=" * 60)
    print("Day 25 代码示例：生产级错误体系演示")
    print("=" * 60)

    handler = ProductionErrorHandler()

    print("\n[1] FATAL 错误处理")
    print("-" * 40)
    try:
        handler.handle(ConfigError("API key not found", component="auth"))
    except AppError as e:
        print(f"Exception re-raised: {e.code}")

    print("\n[2] ERROR 错误处理（可重试）")
    print("-" * 40)
    result = handler.handle(APIError("Connection refused", status_code=503))
    print(f"Action: {result['action']}")

    print("\n[3] WARN 错误处理（仅记录）")
    print("-" * 40)
    result = handler.handle(RateLimitError("Rate limited", retry_after=30))
    print(f"Action: {result['action']}")

    print("\n[4] 未知异常自动分类")
    print("-" * 40)
    result = handler.handle(ConnectionError("Network unreachable"))
    print(f"Action: {result['action']}, Code: {result['error']['code']}")

    print("\n[5] 告警去重演示")
    print("-" * 40)
    for i in range(5):
        handler.handle(APIError("Service unavailable", status_code=500))
        time.sleep(0.01)

    print("\n[6] 错误日志统计")
    print("-" * 40)
    print(f"Total errors handled: {len(handler._error_log)}")
    severity_counts = {}
    for e in handler._error_log:
        sev = e['severity']
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    print(f"By severity: {severity_counts}")

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
```

---

## 练习题

### 练习 1：实现错误聚合和根因分析

**要求：**
实现一个错误聚合器，将相似的错误归类统计，并找出最可能的根因错误。

**提示：**
```python
class ErrorAggregator:
    """错误聚合器"""
    def __init__(self):
        self._errors: List[AppError] = []

    def add(self, error: AppError):
        """添加错误"""
        pass

    def get_root_cause(self) -> Optional[AppError]:
        """分析并返回最可能的根因错误"""
        pass

    def get_error_signature(self, error: AppError) -> str:
        """计算错误签名（用于聚合）"""
        pass
```

**验收标准：**
- 按错误签名聚合相似错误
- 计算每个错误的发生频率
- 识别最可能的根因错误

---

### 练习 2：实现错误恢复建议系统

**要求：**
基于错误类型和上下文，自动生成错误恢复建议。

**提示：**
```python
class RecoveryAdvisor:
    """错误恢复建议系统"""
    RECOVERY_SUGGESTIONS = {
        "CONFIG_ERROR": "检查配置文件和环境变量设置",
        "AUTH_ERROR": "刷新或重新获取 API 凭证",
        "API_ERROR_429": "等待后重试，或联系服务商提升限额",
        "API_ERROR_503": "服务暂时不可用，建议稍后重试",
    }

    def get_suggestion(self, error: AppError) -> str:
        """获取错误恢复建议"""
        pass
```

**验收标准：**
- 根据错误码返回对应的恢复建议
- 对未知错误返回通用建议
- 包含具体的操作步骤

---

### 练习 3：实现错误预算（Error Budget）监控

**要求：**
实现错误预算机制，监控一段时间内的错误率，当错误率超过阈值时触发告警。

**提示：**
```python
class ErrorBudget:
    """错误预算监控"""
    def __init__(self, window_seconds: int = 3600, max_error_rate: float = 0.05):
        # window_seconds: 时间窗口大小
        # max_error_rate: 最大允许的错误率
        pass

    def record(self, success: bool):
        """记录一次请求结果"""
        pass

    @property
    def error_rate(self) -> float:
        """计算当前错误率"""
        pass

    @property
    def is_healthy(self) -> bool:
        """检查是否在预算范围内"""
        pass
```

**验收标准：**
- 滑动窗口计算错误率
- 错误率超过阈值时返回不健康状态
- 提供预算消耗百分比

---

## 九、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d25_error_system.py` | 错误体系（5 子类 + 分类器） | [OK] |
| `tests/d25_test_error_system.py` | 20 个测试 | [OK] 20/20 PASS |
| `day25_study.md` | 本文档 | [OK] 已升级 |
