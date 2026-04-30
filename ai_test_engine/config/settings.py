"""
AI 测试引擎 - 配置管理模块

功能说明：
    提供灵活的配置管理，支持默认值、环境变量加载、
    参数验证和配置序列化等功能。

设计理念：
    "配置与代码分离——不要在代码里硬写 API Key、
    超时时间这些值，让它们可配置、可安全管理。"

作者：测试团队
创建日期：2024年
版本：1.0.0

学习要点：
    1. 如何用 dataclass 定义配置类（Python 3.7+）
    2. 如何从环境变量读取配置（12-Factor App）
    3. 如何实现配置验证逻辑
    4. 如何设计安全的配置序列化

面试话术参考：
    "我设计的配置系统用 dataclass 定义结构，
    支持环境变量覆盖、启动时验证，
    序列化时还会自动过滤敏感信息（比如 API Key）。"
"""
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class Settings:
    """
    全局配置类 - 用 dataclass 定义的好处
    
    为什么用 dataclass？
    1. 自动生成 __init__、__repr__、__eq__ 等方法
    2. 代码更简洁，可读性更好
    3. IDE 能提供更好的类型提示和自动补全
    4. 可以方便地添加默认值
    
    配置项说明：
        api_key: API 密钥（敏感！）
        api_base: API 服务地址
        model: 默认模型名称
        max_retries: 最大重试次数
        timeout: 请求超时时间（秒）
        max_tokens: 最大生成 Token 数
        temperature: 温度参数（0-2）
    """
    # API 相关配置
    api_key: str = ""
    api_base: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    
    # 重试与超时配置
    max_retries: int = 3
    timeout: float = 30.0
    
    # AI 生成配置
    max_tokens: int = 1024
    temperature: float = 0.7

    @classmethod
    def load_from_env(cls) -> "Settings":
        """
        从环境变量加载配置（推荐方式！）
        
        为什么从环境变量读？
        1. 12-Factor App 最佳实践
        2. 安全：不会把 Key 提交到代码仓库
        3. 灵活：不同环境（开发/测试/生产）用不同配置
        4. 容器化友好：Docker、Kubernetes 都支持环境变量
        
        环境变量命名规则：
            全部大写，用下划线分隔
            比如：api_key → DEEPSEEK_API_KEY
        
        Returns:
            Settings: 加载好的配置对象
        """
        import os
        
        # 用 os.getenv 读取环境变量，第二个参数是默认值
        return cls(
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            api_base=os.getenv("API_BASE", "https://api.deepseek.com"),
            model=os.getenv("MODEL_NAME", "deepseek-chat"),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            timeout=float(os.getenv("TIMEOUT", "30.0")),
            max_tokens=int(os.getenv("MAX_TOKENS", "1024")),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
        )

    def validate(self) -> Optional[str]:
        """
        验证配置的有效性
        
        什么时候用？
            - 应用启动时（早失败，快发现）
            - 配置更新后（确保新配置没问题）
        
        验证原则：
            "快速失败（Fail Fast）—— 有问题
            早点发现，不要等运行时才报错。"
        
        Returns:
            str: 错误信息（如果验证失败），None（验证通过）
        """
        # 检查 1：API Key 必须配置
        if not self.api_key:
            return "DEEPSEEK_API_KEY is required"
        
        # 检查 2：API 地址格式要对
        if not self.api_base.startswith(("http://", "https://")):
            return "API_BASE must start with http:// or https://"
        
        # 检查 3：重试次数不能是负数
        if self.max_retries < 0:
            return "max_retries must be >= 0"
        
        # 检查 4：超时时间必须大于 0
        if self.timeout <= 0:
            return "timeout must be > 0"
        
        # 所有检查通过！
        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        将配置转换为字典（用于日志、API 返回等）
        
        重要安全措施：
            不包含 api_key！防止敏感信息泄露！
        
        什么时候用？
            - 要把配置存入数据库
            - 要在日志中记录当前配置（脱敏版）
            - 要通过管理 API 展示配置
        
        Returns:
            安全的配置字典（不含敏感信息）
        """
        return {
            "api_base": self.api_base,
            "model": self.model,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
