"""
Day 25 — 生产级错误体系

功能说明：
    分级错误系统：FATAL / ERROR / WARN / INFO。
    定义了 AppError 基类 + 5 个子异常类，提供异常分类和处理规则。

面试话术：
    "我设计了一套分级错误体系。FATAL 级错误直接终止流程并告警，
    ERROR 级触发重试+告警，WARN 只记录日志不中断流程。
    ErrorClassifier 能自动判断异常属于哪个级别，以及该采取什么行动。"
"""
import enum
import logging
from dataclasses import dataclass, field
from typing import Optional, ClassVar, Dict, Tuple


logger = logging.getLogger(__name__)


class ErrorSeverity(enum.Enum):
    """错误严重级别"""
    FATAL = "FATAL"       # 致命，流程终止+告警
    ERROR = "ERROR"       # 错误，重试+告警
    WARN = "WARN"         # 警告，记录+不中断
    INFO = "INFO"         # 信息，仅记录


class ErrorAction(enum.Enum):
    """错误处理动作"""
    STOP = "STOP"              # 终止流程
    RETRY = "RETRY"            # 重试
    ALERT = "ALERT"            # 告警
    LOG = "LOG"                # 仅记录
    RETRY_THEN_ALERT = "RETRY_THEN_ALERT"  # 重试后告警


class AppError(Exception):
    """应用异常基类

    Attributes:
        message: 错误描述
        severity: 严重级别
        action: 建议处理动作
        retryable: 是否可重试
        context: 附带上下文
    """

    severity: ClassVar[ErrorSeverity] = ErrorSeverity.ERROR
    action: ClassVar[ErrorAction] = ErrorAction.STOP
    retryable: ClassVar[bool] = False

    def __init__(self, message: str = "",
                 context: Optional[dict] = None):
        self.message = message
        self.context = context or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "type": type(self).__name__,
            "severity": self.severity.value,
            "action": self.action.value,
            "retryable": self.retryable,
            "message": self.message,
            "context": self.context,
        }


class ConfigError(AppError):
    """配置错误（如缺少 API Key、无效参数）"""
    severity = ErrorSeverity.FATAL
    action = ErrorAction.STOP
    retryable = False


class APIError(AppError):
    """API 调用错误（如 500、超时）"""
    severity = ErrorSeverity.ERROR
    action = ErrorAction.RETRY_THEN_ALERT
    retryable = True


class RateLimitError(AppError):
    """速率限制错误（429）"""
    severity = ErrorSeverity.WARN
    action = ErrorAction.RETRY
    retryable = True

    def __init__(self, message: str = "",
                 retry_after: float = 0.0,
                 context: Optional[dict] = None):
        super().__init__(message, context)
        self.retry_after = retry_after


class AuthError(AppError):
    """认证错误（401/403）"""
    severity = ErrorSeverity.FATAL
    action = ErrorAction.STOP
    retryable = False


class ValidationError(AppError):
    """验证错误（参数校验失败）"""
    severity = ErrorSeverity.WARN
    action = ErrorAction.LOG
    retryable = False


# 异常到错误类型的映射规则
ERROR_RULES: Dict[str, Tuple[type, str]] = {
    "timeout": (APIError, "Request timeout"),
    "rate_limit": (RateLimitError, "Rate limit exceeded"),
    "auth_failed": (AuthError, "Authentication failed"),
    "invalid_config": (ConfigError, "Invalid configuration"),
    "validation": (ValidationError, "Validation failed"),
}


class ErrorClassifier:
    """异常分类器

    将异常分类为错误严重级别和建议处理动作。
    """

    SEVERITY_MAP: ClassVar[Dict[str, ErrorSeverity]] = {
        "FATAL": ErrorSeverity.FATAL,
        "ERROR": ErrorSeverity.ERROR,
        "WARN": ErrorSeverity.WARN,
        "INFO": ErrorSeverity.INFO,
    }

    @classmethod
    def classify(cls, error: Exception) -> dict:
        """异常分类

        Args:
            error: 待分类的异常

        Returns:
            {
                "severity": ErrorSeverity,
                "action": ErrorAction,
                "retryable": bool,
                "type": str
            }
        """
        if isinstance(error, AppError):
            return {
                "severity": error.severity,
                "action": error.action,
                "retryable": error.retryable,
                "type": type(error).__name__,
            }

        # 通用异常映射
        if isinstance(error, ConnectionError):
            return {
                "severity": ErrorSeverity.ERROR,
                "action": ErrorAction.RETRY_THEN_ALERT,
                "retryable": True,
                "type": "ConnectionError",
            }

        if isinstance(error, TimeoutError):
            return {
                "severity": ErrorSeverity.ERROR,
                "action": ErrorAction.RETRY_THEN_ALERT,
                "retryable": True,
                "type": "TimeoutError",
            }

        if isinstance(error, ValueError):
            return {
                "severity": ErrorSeverity.WARN,
                "action": ErrorAction.LOG,
                "retryable": False,
                "type": "ValueError",
            }

        # 默认
        return {
            "severity": ErrorSeverity.ERROR,
            "action": ErrorAction.ALERT,
            "retryable": False,
            "type": type(error).__name__,
        }

    @classmethod
    def should_retry(cls, error: Exception) -> bool:
        """判断异常是否需要重试"""
        return cls.classify(error)["retryable"]

    @classmethod
    def should_alert(cls, error: Exception) -> bool:
        """判断异常是否需要告警"""
        action = cls.classify(error)["action"]
        return action in (ErrorAction.ALERT, ErrorAction.RETRY_THEN_ALERT)

    @classmethod
    def is_fatal(cls, error: Exception) -> bool:
        """判断异常是否致命"""
        return cls.classify(error)["severity"] == ErrorSeverity.FATAL
