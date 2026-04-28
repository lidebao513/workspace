"""AI 测试环境 - API 客户端封装模块

功能说明：
    封装 DeepSeek API 的调用逻辑，提供统一的客户端接口，支持环境变量配置、
    错误处理、Token 消耗统计等功能。

作者：测试团队
创建日期：2024年
版本：1.0.0

模块结构：
    - AITestClient: 核心客户端类，封装 API 调用逻辑
    - 支持从 .env 文件或系统环境变量读取配置
    - 提供聊天、Token 统计、响应解析等方法

面试话术参考：
    "我搭过完整的 AI 测试环境，环境变量分离、降级策略都是标配。"
"""
import os
import json
from typing import Optional, List, Dict

from openai import OpenAI, APIError, APIConnectionError, RateLimitError


class AITestClient:
    """AI 测试客户端，封装大模型 API 调用

    提供统一的 API 调用接口，包含环境配置、错误处理、响应解析等功能。

    典型用法：
        client = AITestClient()
        response = client.chat([{"role": "user", "content": "你好"}])
        print(client.get_reply_text(response))
    """

    def __init__(self, env_path: str = None):
        """
        初始化客户端，从环境变量或 .env 读取配置

        Args:
            env_path: .env 文件路径，None 表示从系统环境变量读取

        Raises:
            ValueError: 当 API Key 未配置或配置无效时抛出
        """
        # 加载环境变量（如果提供了 .env 路径）
        if env_path:
            from dotenv import load_dotenv
            load_dotenv(env_path)

        # 读取配置参数
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        # 环境配置检查（确保必要参数已配置）
        self._check_environment()

        # 初始化 OpenAI 兼容客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def _check_environment(self):
        """检查环境配置完整性

        验证 API Key 和基础 URL 是否已正确配置，确保客户端可以正常工作。

        Raises:
            ValueError: 当必要配置缺失时抛出详细错误信息
        """
        # 检查 API Key
        if not self.api_key or self.api_key == "your_deepseek_api_key_here":
            raise ValueError(
                "DEEPSEEK_API_KEY 未配置！\n"
                "请复制 .env.example 为 .env，填入你的 API Key。\n"
                "注册地址: https://platform.deepseek.com"
            )
        
        # 检查基础 URL
        if not self.base_url:
            raise ValueError("DEEPSEEK_BASE_URL 未配置")

        # 打印配置信息供调试
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
            temperature: 温度参数，控制回复随机性，范围 0-2，默认 0.7
            max_tokens: 最大生成 Token 数，默认 1024
            timeout: 请求超时时间（秒），默认 300

        Returns:
            API 响应完整结构（OpenAI 格式）

        Raises:
            RuntimeError: 当 API 调用失败时抛出，包含具体错误信息
        """
        try:
            # 调用 OpenAI 兼容的聊天接口
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
        """从 API 响应中提取回复文本

        Args:
            response: API 响应对象

        Returns:
            回复内容字符串，若响应无效则返回空字符串
        """
        # 安全检查：确保 choices 列表存在且非空
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content or ""
        return ""

    def get_token_usage(self, response) -> Dict:
        """从 API 响应中提取 Token 使用情况

        Args:
            response: API 响应对象

        Returns:
            Token 使用字典，包含 prompt_tokens、completion_tokens、total_tokens
        """
        # 处理 usage 字段可能为空的情况
        if not response.usage:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # 提取各 Token 消耗字段
        return {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    def print_response_summary(self, response):
        """打印 API 响应摘要

        输出回复长度、Token 消耗、回复预览等信息，便于调试和日志记录。

        Args:
            response: API 响应对象
        """
        content = self.get_reply_text(response)
        usage = self.get_token_usage(response)

        # 打印格式化的响应摘要
        print(f"\n--- 响应摘要 ---")
        print(f"回复长度: {len(content)} 字符")
        print(f"Prompt Tokens: {usage['prompt_tokens']}")
        print(f"生成 Tokens: {usage['completion_tokens']}")
        print(f"总 Tokens: {usage['total_tokens']}")
        
        # 根据回复长度决定输出完整内容还是前 100 字
        if len(content) > 100:
            print(f"回复前 100 字: {content[:100]}...")
        else:
            print(f"回复全文: {content}")
        
        # 输出 finish_reason（用于判断回复是否完整）
        finish_reason = response.choices[0].finish_reason if response.choices else 'N/A'
        print(f"finish_reason: {finish_reason}")

    def chat_with_params(self, messages, **kwargs):
        """
        带自定义参数的聊天请求，用于边界测试。

        支持额外的参数如 seed，便于进行参数边界测试和复现测试。

        Args:
            messages: 消息列表，格式同 chat 方法
            **kwargs: 可选参数，包括:
                - temperature: 温度 (0-2)，默认 0.7
                - max_tokens: 最大 Token 数，默认 1024
                - timeout: 超时秒数，默认 30
                - seed: 随机种子，固定后可复现回复（DeepSeek 支持）

        Returns:
            API 响应完整结构

        Raises:
            RuntimeError: 当 API 调用失败时抛出
        """
        # 构建基础参数字典
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
            "timeout": kwargs.get("timeout", 30),
        }

        # 添加额外参数（如 seed）
        if "seed" in kwargs:
            params["extra_body"] = {"seed": kwargs["seed"]}

        # 执行 API 调用
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
        """打印带参数的响应详情，用于边界测试对比

        输出格式紧凑，便于在多次测试中对比不同参数下的响应差异。

        Args:
            response: API 响应对象
            label: 测试标签，用于标识不同的测试用例
        """
        content = self.get_reply_text(response)
        usage = self.get_token_usage(response)
        finish_reason = response.choices[0].finish_reason if response.choices else "N/A"

        # 添加标签前缀（如果提供）
        prefix = f"[{label}] " if label else ""
        print(f"\n{prefix}--- 参数响应 ---")
        print(f"  回复长度: {len(content)} 字符")
        print(f"  Prompt Tokens: {usage['prompt_tokens']}")
        print(f"  Completion Tokens: {usage['completion_tokens']}")
        print(f"  finish_reason: {finish_reason}")
        
        # 根据长度决定输出方式
        if len(content) > 60:
            print(f"  回复前 60 字: {content[:60]}...")
        else:
            print(f"  回复全文: {content}")
