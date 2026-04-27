"""
AI 测试环境 - API 客户端封装

封装 DeepSeek API 的调用逻辑，提供统一的客户端接口。
面试话术："我搭过完整的 AI 测试环境，环境变量分离、降级策略都是标配。"
"""
import os
import json
from typing import Optional, List, Dict

from openai import OpenAI, APIError, APIConnectionError, RateLimitError


class AITestClient:
    """AI 测试客户端，封装大模型 API 调用"""

    def __init__(self, env_path: str = None):
        """
        初始化客户端，从环境变量或 .env 读取配置

        Args:
            env_path: .env 文件路径，None 表示从系统环境变量读取
        """
        if env_path:
            from dotenv import load_dotenv
            load_dotenv(env_path)

        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        # 环境检查
        self._check_environment()

        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def _check_environment(self):
        """检查环境配置完整性"""
        if not self.api_key or self.api_key == "your_deepseek_api_key_here":
            raise ValueError(
                "DEEPSEEK_API_KEY 未配置！\n"
                "请复制 .env.example 为 .env，填入你的 API Key。\n"
                "注册地址: https://platform.deepseek.com"
            )
        if not self.base_url:
            raise ValueError("DEEPSEEK_BASE_URL 未配置")

        print(f"[配置检查通过] 模型: {self.model}")
        print(f"[配置检查通过] 接口地址: {self.base_url}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        timeout: int = 300,
    ) -> Dict:
        """
        发送聊天请求

        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "你好"}]
            temperature: 温度参数，0-2
            max_tokens: 最大生成 Token 数
            timeout: 请求超时时间（秒）

        Returns:
            API 响应完整结构
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return response

        except RateLimitError as e:
            raise RuntimeError(f"API 限流: {e}")
        except APIConnectionError as e:
            raise RuntimeError(f"网络连接失败: {e}")
        except APIError as e:
            raise RuntimeError(f"API 错误 (status={e.status_code}): {e}")
        except Exception as e:
            raise RuntimeError(f"未知错误: {e}")

    def get_reply_text(self, response) -> str:
        """从 API 响应中提取回复文本"""
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content or ""
        return ""

    def get_token_usage(self, response) -> Dict:
        """从 API 响应中提取 Token 使用情况"""
        if not response.usage:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        return {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    def print_response_summary(self, response):
        """打印 API 响应摘要"""
        content = self.get_reply_text(response)
        usage = self.get_token_usage(response)

        print(f"\n--- 响应摘要 ---")
        print(f"回复长度: {len(content)} 字符")
        print(f"Prompt Tokens: {usage['prompt_tokens']}")
        print(f"生成 Tokens: {usage['completion_tokens']}")
        print(f"总 Tokens: {usage['total_tokens']}")
        print(f"回复前 100 字: {content[:100]}..." if len(content) > 100 else f"回复全文: {content}")
        print(f"finish_reason: {response.choices[0].finish_reason if response.choices else 'N/A'}")

    def chat_with_params(self, messages, **kwargs):
        """
        带自定义参数的聊天请求，用于边界测试。

        参数:
            messages: 消息列表
            temperature: 温度 (0-2)，默认 0.7
            max_tokens: 最大 Token 数，默认 1024
            timeout: 超时秒数，默认 30
            seed: 随机种子，固定后可复现回复（DeepSeek 支持）
        """
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
            "timeout": kwargs.get("timeout", 30),
        }

        if "seed" in kwargs:
            params["extra_body"] = {"seed": kwargs["seed"]}

        try:
            response = self.client.chat.completions.create(**params)
            return response
        except RateLimitError:
            raise RuntimeError("API 限流")
        except APIConnectionError:
            raise RuntimeError("网络连接失败")
        except APIError as e:
            raise RuntimeError(f"API 错误 (status={e.status_code}): {e}")
        except Exception as e:
            raise RuntimeError(f"未知错误: {e}")

    def print_params_response(self, response, label=""):
        """打印带参数的响应详情，用于边界测试对比"""
        content = self.get_reply_text(response)
        usage = self.get_token_usage(response)
        finish_reason = response.choices[0].finish_reason if response.choices else "N/A"

        prefix = f"[{label}] " if label else ""
        print(f"\n{prefix}--- 参数响应 ---")
        print(f"  回复长度: {len(content)} 字符")
        print(f"  Prompt Tokens: {usage['prompt_tokens']}")
        print(f"  Completion Tokens: {usage['completion_tokens']}")
        print(f"  finish_reason: {finish_reason}")
        if len(content) > 60:
            print(f"  回复前 60 字: {content[:60]}...")
        else:
            print(f"  回复全文: {content}")
