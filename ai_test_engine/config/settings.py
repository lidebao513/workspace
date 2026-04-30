"""
Day 27 — AI Test Engine: 项目骨架 + 核心模块
"""
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class Settings:
    """全局配置"""
    api_key: str = ""
    api_base: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    max_retries: int = 3
    timeout: float = 30.0
    max_tokens: int = 1024
    temperature: float = 0.7

    @classmethod
    def load_from_env(cls) -> "Settings":
        """从环境变量加载配置"""
        import os
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
        """验证配置，返回错误信息或 None"""
        if not self.api_key:
            return "DEEPSEEK_API_KEY is required"
        if not self.api_base.startswith(("http://", "https://")):
            return "API_BASE must start with http:// or https://"
        if self.max_retries < 0:
            return "max_retries must be >= 0"
        if self.timeout <= 0:
            return "timeout must be > 0"
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "api_base": self.api_base,
            "model": self.model,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
