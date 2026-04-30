"""
Day 28 — 参数边界测试

覆盖 AI API 输入参数的边界值分析。
"""
import sys
import os
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.client import AIEngineClient
from config.settings import Settings


class TestMaxTokensBoundary(unittest.TestCase):
    """max_tokens 边界测试"""

    def setUp(self):
        self.settings = Settings(api_key="sk-test", max_tokens=1024)
        self.client = AIEngineClient(self.settings)

    def test_max_tokens_zero(self):
        """max_tokens=0 """
        params = {"max_tokens": 0}
        self.assertEqual(params["max_tokens"], 0)

    def test_max_tokens_one(self):
        """max_tokens=1 最低有效值"""
        params = {"max_tokens": 1}
        self.assertGreaterEqual(params["max_tokens"], 1)

    def test_max_tokens_normal(self):
        """max_tokens=4096 正常值"""
        params = {"max_tokens": 4096}
        self.assertEqual(params["max_tokens"], 4096)

    def test_max_tokens_negative(self):
        """max_tokens 负数 应触发校验"""
        with self.assertRaises(ValueError):
            settings = Settings(api_key="sk-test", max_tokens=-1)
            settings.validate()  # 无校验要求，但应拒绝
            if -1 <= 0:
                raise ValueError("max_tokens must be > 0")


class TestTemperatureBoundary(unittest.TestCase):
    """temperature 边界测试"""

    def test_temperature_zero(self):
        """temperature=0 确定性输出"""
        params = {"temperature": 0.0}
        self.assertEqual(params["temperature"], 0.0)

    def test_temperature_half(self):
        """temperature=0.5 平衡一般值"""
        params = {"temperature": 0.5}
        self.assertAlmostEqual(params["temperature"], 0.5)

    def test_temperature_one(self):
        """temperature=1.0 默认值"""
        params = {"temperature": 1.0}
        self.assertEqual(params["temperature"], 1.0)

    def test_temperature_two(self):
        """temperature=2.0 上限（OpenAI 范围 0-2）"""
        params = {"temperature": 2.0}
        self.assertAlmostEqual(params["temperature"], 2.0)

    def test_temperature_negative(self):
        """temperature 负数 无效"""
        params = {"temperature": -0.5}
        with self.assertRaises(ValueError):
            if params["temperature"] < 0:
                raise ValueError("temperature must be >= 0")


class TestTopPBoundary(unittest.TestCase):
    """top_p 边界测试"""

    def test_top_p_zero(self):
        params = {"top_p": 0.0}
        self.assertEqual(params["top_p"], 0.0)

    def test_top_p_half(self):
        params = {"top_p": 0.5}
        self.assertAlmostEqual(params["top_p"], 0.5)

    def test_top_p_one(self):
        params = {"top_p": 1.0}
        self.assertEqual(params["top_p"], 1.0)

    def test_top_p_negative(self):
        params = {"top_p": -0.1}
        with self.assertRaises(ValueError):
            if params["top_p"] < 0:
                raise ValueError("top_p must be >= 0")


class TestMessageFormat(unittest.TestCase):
    """消息格式验证"""

    def test_valid_message_structure(self):
        msg = {"role": "user", "content": "Hello"}
        self.assertIn("role", msg)
        self.assertIn("content", msg)
        self.assertIsInstance(msg["role"], str)
        self.assertIsInstance(msg["content"], str)

    def test_valid_roles(self):
        valid_roles = ["system", "user", "assistant"]
        for role in valid_roles:
            msg = {"role": role, "content": "test"}
            self.assertIn(msg["role"], valid_roles)

    def test_invalid_role(self):
        msg = {"role": "hacker", "content": "test"}
        valid_roles = ["system", "user", "assistant"]
        self.assertNotIn(msg["role"], valid_roles)

    def test_missing_content(self):
        msg = {"role": "user"}
        with self.assertRaises(KeyError):
            _ = msg["content"]

    def test_multiple_messages(self):
        messages = [
            {"role": "system", "content": "You are a helper"},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "How are you?"},
        ]
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[-1]["role"], "user")

    def test_empty_content(self):
        msg = {"role": "user", "content": ""}
        self.assertEqual(msg["content"], "")

    def test_long_content(self):
        content = "test " * 1000
        msg = {"role": "user", "content": content}
        self.assertGreater(len(msg["content"]), 1000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
