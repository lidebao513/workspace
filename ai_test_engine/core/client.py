"""
Day 27 — AI Engine Client

核心 API 客户端，封装 OpenAI SDK 的 chat 调用。
"""
import sys
import os
import time
from typing import List, Dict, Optional, Any, Generator

# 确保项目根目录在路径中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.settings import Settings


class AIEngineClient:
    """AI 引擎客户端

    封装 OpenAI SDK 的 chat.completions.create 调用。
    支持同步和流式两种模式。

    Args:
        settings: Settings 配置对象
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings.load_from_env()
        self._client = None

    def _get_client(self):
        """延迟初始化 OpenAI 客户端"""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.settings.api_key,
                base_url=self.settings.api_base,
                timeout=self.settings.timeout,
            )
        return self._client

    def chat(self, messages: List[Dict[str, str]],
             **kwargs) -> Any:
        """发送聊天请求

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            **kwargs: 覆盖 Settings 的参数

        Returns:
            OpenAI API 响应对象
        """
        client = self._get_client()
        params = {
            "model": kwargs.get("model", self.settings.model),
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.settings.max_tokens),
            "temperature": kwargs.get("temperature", self.settings.temperature),
        }
        return client.chat.completions.create(**params)

    def chat_stream(self, messages: List[Dict[str, str]],
                    **kwargs) -> Generator[str, None, None]:
        """流式聊天，逐 token 产出文本"""
        client = self._get_client()
        params = {
            "model": kwargs.get("model", self.settings.model),
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.settings.max_tokens),
            "temperature": kwargs.get("temperature", self.settings.temperature),
            "stream": True,
        }
        response = client.chat.completions.create(**params)
        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    @staticmethod
    def get_reply_text(response: Any) -> str:
        """从 API 响应中提取回复文本"""
        if hasattr(response, "choices") and response.choices:
            return response.choices[0].message.content or ""
        return ""

    @staticmethod
    def get_token_usage(response: Any) -> Dict[str, int]:
        """提取 Token 使用统计"""
        if hasattr(response, "usage") and response.usage:
            return {
                "prompt_tokens": response.usage.prompt_tokens or 0,
                "completion_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0,
            }
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    @staticmethod
    def print_response_summary(response: Any) -> None:
        """打印响应摘要"""
        text = AIEngineClient.get_reply_text(response)
        usage = AIEngineClient.get_token_usage(response)
        print(f"  Model: {response.model if hasattr(response, 'model') else 'N/A'}")
        print(f"  Reply: {text[:100]}..." if len(text) > 100 else f"  Reply: {text}")
        print(f"  Tokens: {usage}")
