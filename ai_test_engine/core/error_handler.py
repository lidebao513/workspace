"""
Day 27 — 错误处理器

分级错误系统，配合 ErrorClassifier 自动判断错误类型和处理策略。
"""
import enum
import logging
from dataclasses import dataclass
from typing import Optional, Dict, ClassVar

logger = logging.getLogger(__name__)


class ErrorSeverity(enum.Enum):
    """错误严重级别"""
    FATAL = "FATAL"
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"


class ErrorAction(enum.Enum):
    """错误处理动作"""
    STOP = "STOP"
    RETRY = "RETRY"
    ALERT = "ALERT"
    LOG = "LOG"
    RETRY_THEN_ALERT = "RETRY_THEN_ALERT"


class AppError(Exception):
    """应用异常基类"""
    severity: ClassVar[ErrorSeverity] = ErrorSeverity.ERROR
    action: ClassVar[ErrorAction] = ErrorAction.STOP
    retryable: ClassVar[bool] = False

    def __init__(self, message: str = "", context: Optional[dict] = None):
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
    severity = ErrorSeverity.FATAL
    action = ErrorAction.STOP
    retryable = False


class APIError(AppError):
    severity = ErrorSeverity.ERROR
    action = ErrorAction.RETRY_THEN_ALERT
    retryable = True


class RateLimitError(AppError):
    severity = ErrorSeverity.WARN
    action = ErrorAction.RETRY
    retryable = True

    def __init__(self, message: str = "", retry_after: float = 0.0,
                 context: Optional[dict] = None):
        super().__init__(message, context)
        self.retry_after = retry_after


class AuthError(AppError):
    severity = ErrorSeverity.FATAL
    action = ErrorAction.STOP
    retryable = False


class ValidationError(AppError):
    severity = ErrorSeverity.WARN
    action = ErrorAction.LOG
    retryable = False


class ErrorHandler:
    """错误处理器

    组合异常分类 + 处理策略，对外提供 handle() 接口。
    """

    @classmethod
    def classify(cls, error: Exception) -> dict:
        """异常分类"""
        if isinstance(error, AppError):
            return {
                "severity": error.severity,
                "action": error.action,
                "retryable": error.retryable,
                "type": type(error).__name__,
            }

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

        return {
            "severity": ErrorSeverity.ERROR,
            "action": ErrorAction.ALERT,
            "retryable": False,
            "type": type(error).__name__,
        }

    @classmethod
    def handle(cls, error: Exception, context: Optional[dict] = None) -> dict:
        """处理异常，返回建议动作

        Returns:
            {"action": ErrorAction, "severity": ErrorSeverity, "message": str}
        """
        classification = cls.classify(error)
        logger.warning(f"[{classification['severity'].value}] {error}")
        return classification

    @classmethod
    def should_retry(cls, error: Exception) -> bool:
        return cls.classify(error)["retryable"]

    @classmethod
    def should_alert(cls, error: Exception) -> bool:
        action = cls.classify(error)["action"]
        return action in (ErrorAction.ALERT, ErrorAction.RETRY_THEN_ALERT)

    @classmethod
    def is_fatal(cls, error: Exception) -> bool:
        return cls.classify(error)["severity"] == ErrorSeverity.FATAL
