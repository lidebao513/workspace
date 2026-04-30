"""
AI 测试引擎 - 错误处理系统模块

功能说明：
    为 AI 测试引擎提供结构化的错误处理机制，包括错误分类、
    严重程度评级、处理策略建议等功能。这是任何健壮软件系统
    必不可少的核心组件。

设计理念：
    "不是所有错误都等价——有些应该重试，有些应该立即停止，
    有些只需记录日志。好的错误处理系统让系统更稳定。"

作者：测试团队
创建日期：2024年
版本：1.0.0

学习要点：
    1. 如何用枚举（Enum）定义固定选项集合
    2. 如何用类层次结构实现错误类型体系
    3. 如何用类变量（ClassVar）定义类型级配置
    4. 如何实现错误分类和策略判断

面试话术参考：
    "我设计过一套分级错误处理系统，
    根据错误类型自动决定是重试、报警还是直接停止，
    配合 Key 管理器实现优雅降级，大大提升了系统稳定性。"
"""
import enum
import logging
from dataclasses import dataclass
from typing import Optional, Dict, ClassVar

# 配置日志记录器（用于记录错误信息）
logger = logging.getLogger(__name__)


class ErrorSeverity(enum.Enum):
    """
    错误严重程度枚举
    
    为什么用枚举？
    - 限定可选值范围，防止拼写错误
    - 提供类型安全和代码提示
    - 语义清晰，便于理解
    
    严重程度定义（从高到低）：
    - FATAL: 致命错误，系统无法继续运行
    - ERROR: 一般错误，影响功能执行
    - WARN: 警告，不影响运行但需要关注
    - INFO: 信息级别，仅作记录
    """
    FATAL = "FATAL"    # 致命错误，必须停止
    ERROR = "ERROR"    # 普通错误，可能需要重试
    WARN = "WARN"      # 警告，需要关注但不阻塞
    INFO = "INFO"      # 信息级别，仅作记录


class ErrorAction(enum.Enum):
    """
    错误处理动作枚举
    
    对于每个错误类型，我们需要明确告诉调用者该怎么做：
    - STOP: 立即停止，不要再继续
    - RETRY: 尝试重试，可能成功
    - ALERT: 发送警报，需要人工介入
    - LOG: 记录日志，继续执行
    - RETRY_THEN_ALERT: 先重试，失败再报警
    """
    STOP = "STOP"                    # 立即停止执行
    RETRY = "RETRY"                  # 尝试重试
    ALERT = "ALERT"                  # 发送报警
    LOG = "LOG"                      # 仅记录日志
    RETRY_THEN_ALERT = "RETRY_THEN_ALERT"  # 先重试再报警


class AppError(Exception):
    """
    应用异常基类 - 所有自定义异常的父类
    
    设计要点：
    - 继承 Python 内置 Exception
    - 用类变量（ClassVar）定义类型级配置
    - 每个子类可以覆盖这些配置
    - 支持上下文信息记录，便于调试
    
    面向对象设计思想：
    "每个异常类型知道自己的严重程度、
    处理策略和是否可重试，而不是把这些
    判断逻辑散落在代码各处。"
    """
    # 类变量（ClassVar）：这个类型的所有实例共享这些值
    severity: ClassVar[ErrorSeverity] = ErrorSeverity.ERROR
    action: ClassVar[ErrorAction] = ErrorAction.STOP
    retryable: ClassVar[bool] = False

    def __init__(self, message: str = "", context: Optional[dict] = None):
        """
        初始化异常对象
        
        Args:
            message: 错误描述信息
            context: 额外上下文信息（字典形式，方便调试）
        """
        self.message = message
        self.context = context or {}  # 如果没有提供，默认为空字典
        super().__init__(self.message)  # 调用父类构造函数

    def to_dict(self) -> dict:
        """
        将异常转换为字典（便于序列化和日志记录）
        
        什么时候用？
        - 要把错误信息存入数据库
        - 要通过 API 返回给前端
        - 要写入结构化日志
        
        Returns:
            包含完整错误信息的字典
        """
        return {
            "type": type(self).__name__,              # 错误类型名称
            "severity": self.severity.value,          # 严重程度
            "action": self.action.value,              # 建议动作
            "retryable": self.retryable,              # 是否可重试
            "message": self.message,                  # 错误信息
            "context": self.context,                  # 上下文数据
        }


class ConfigError(AppError):
    """
    配置错误 - 环境变量、配置文件等问题
    
    为什么单独一类？
    - 配置问题通常是启动时就发现，应该立即停止
    - 不需要重试（重试也解决不了配置错误）
    - 需要用户介入修复配置
    """
    severity = ErrorSeverity.FATAL    # 致命级别
    action = ErrorAction.STOP         # 必须停止
    retryable = False                 # 不可重试


class APIError(AppError):
    """
    API 调用错误 - 网络问题、服务端错误等
    
    为什么可重试？
    - 网络抖动是暂时的，重试可能成功
    - 服务端临时过载，等一下可能恢复
    - 但重试多次失败后应该报警
    """
    severity = ErrorSeverity.ERROR
    action = ErrorAction.RETRY_THEN_ALERT  # 先重试，失败再报警
    retryable = True                       # 可重试


class RateLimitError(AppError):
    """
    API 限流错误 - 调用频率超限
    
    特殊之处：
    - 需要知道限流时间（retry_after）
    - 不是真正的错误，只是系统保护
    - 等待指定时间后重试即可
    """
    severity = ErrorSeverity.WARN
    action = ErrorAction.RETRY
    retryable = True

    def __init__(self, message: str = "", retry_after: float = 0.0,
                 context: Optional[dict] = None):
        """
        初始化限流错误
        
        Args:
            message: 错误描述
            retry_after: 需要等待多少秒后重试
            context: 额外上下文
        """
        super().__init__(message, context)
        self.retry_after = retry_after  # 保存需要等待的时间


class AuthError(AppError):
    """
    认证错误 - API Key 无效、权限不足等
    
    为什么不可重试？
    - Key 无效的话，重试多少次都一样
    - 应该立即停止，让用户检查 Key
    """
    severity = ErrorSeverity.FATAL
    action = ErrorAction.STOP
    retryable = False


class ValidationError(AppError):
    """
    验证错误 - 参数校验失败
    
    为什么只是警告？
    - 通常是客户端输入问题，不是系统问题
    - 记录日志，告诉调用者即可
    - 不需要重试（参数没变的话重试也会失败）
    """
    severity = ErrorSeverity.WARN
    action = ErrorAction.LOG
    retryable = False


class ErrorHandler:
    """
    错误处理器 - 统一的错误处理入口
    
    职责：
    1. 对异常进行分类（identify what happened）
    2. 判断该怎么处理（decide what to do）
    3. 记录日志（log what happened）
    
    设计模式：
    "门面模式（Facade）—— 提供一个统一接口，
    隐藏子系统的复杂性，让调用者使用更简单。"
    """

    @classmethod
    def classify(cls, error: Exception) -> dict:
        """
        异常分类 - 判断错误类型，返回分类信息
        
        工作原理：
        - 先检查是否是我们定义的 AppError
        - 再检查是否是常见的 Python 内置异常
        - 都不匹配的话返回默认分类
        
        Args:
            error: 任意异常对象
            
        Returns:
            分类信息字典，包含 severity、action、retryable、type
        """
        # 情况1：是我们定义的 AppError 及其子类
        if isinstance(error, AppError):
            return {
                "severity": error.severity,
                "action": error.action,
                "retryable": error.retryable,
                "type": type(error).__name__,
            }

        # 情况2：连接错误（网络断开、连接超时等）
        if isinstance(error, ConnectionError):
            return {
                "severity": ErrorSeverity.ERROR,
                "action": ErrorAction.RETRY_THEN_ALERT,
                "retryable": True,
                "type": "ConnectionError",
            }

        # 情况3：超时错误
        if isinstance(error, TimeoutError):
            return {
                "severity": ErrorSeverity.ERROR,
                "action": ErrorAction.RETRY_THEN_ALERT,
                "retryable": True,
                "type": "TimeoutError",
            }

        # 情况4：值错误（参数问题）
        if isinstance(error, ValueError):
            return {
                "severity": ErrorSeverity.WARN,
                "action": ErrorAction.LOG,
                "retryable": False,
                "type": "ValueError",
            }

        # 兜底情况：未知错误类型
        return {
            "severity": ErrorSeverity.ERROR,
            "action": ErrorAction.ALERT,
            "retryable": False,
            "type": type(error).__name__,
        }

    @classmethod
    def handle(cls, error: Exception, context: Optional[dict] = None) -> dict:
        """
        处理异常 - 对外的主接口
        
        做了什么：
        1. 对异常进行分类
        2. 记录日志
        3. 返回处理建议
        
        Args:
            error: 异常对象
            context: 额外上下文信息
            
        Returns:
            处理建议字典
        """
        classification = cls.classify(error)
        logger.warning(f"[{classification['severity'].value}] {error}")
        return classification

    @classmethod
    def should_retry(cls, error: Exception) -> bool:
        """
        判断是否应该重试（便利方法）
        
        使用场景：
            if ErrorHandler.should_retry(error):
                retry_the_operation()
            else:
                give_up()
        
        Args:
            error: 异常对象
            
        Returns:
            bool: 是否应该重试
        """
        return cls.classify(error)["retryable"]

    @classmethod
    def should_alert(cls, error: Exception) -> bool:
        """
        判断是否应该报警（便利方法）
        
        Args:
            error: 异常对象
            
        Returns:
            bool: 是否应该发送警报
        """
        action = cls.classify(error)["action"]
        return action in (ErrorAction.ALERT, ErrorAction.RETRY_THEN_ALERT)

    @classmethod
    def is_fatal(cls, error: Exception) -> bool:
        """
        判断是否是致命错误（便利方法）
        
        Args:
            error: 异常对象
            
        Returns:
            bool: 是否应该立即停止
        """
        return cls.classify(error)["severity"] == ErrorSeverity.FATAL
