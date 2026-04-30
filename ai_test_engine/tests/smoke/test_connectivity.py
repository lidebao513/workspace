"""
Day 27 — 配置与核心模块测试

覆盖：
1. Settings 默认值、加载、验证
2. AIEngineClient 初始化
3. ErrorHandler 异常分类
4. KeyManager Key 轮换 + 降级
"""
import sys
import os
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.settings import Settings
from core.client import AIEngineClient
from core.error_handler import (
    ErrorHandler, ConfigError, APIError, AuthError,
    RateLimitError, ValidationError, ErrorSeverity, ErrorAction,
)
from core.key_manager import KeyManager


class TestSettings(unittest.TestCase):
    """Settings 配置"""

    def test_default_values(self):
        s = Settings()
        self.assertEqual(s.api_key, "")
        self.assertEqual(s.api_base, "https://api.deepseek.com")
        self.assertEqual(s.model, "deepseek-chat")
        self.assertEqual(s.max_retries, 3)

    def test_validate_missing_key(self):
        s = Settings(api_key="")
        self.assertIsNotNone(s.validate())

    def test_validate_valid(self):
        s = Settings(api_key="sk-test123")
        self.assertIsNone(s.validate())

    def test_validate_invalid_base(self):
        s = Settings(api_key="sk-test", api_base="not-a-url")
        self.assertIsNotNone(s.validate())

    def test_validate_negative_retries(self):
        s = Settings(api_key="sk-test", max_retries=-1)
        self.assertIsNotNone(s.validate())

    def test_to_dict(self):
        s = Settings(api_key="sk-secret", api_base="https://test.api.com")
        d = s.to_dict()
        self.assertEqual(d["api_base"], "https://test.api.com")
        self.assertNotIn("api_key", d)  # 不暴露敏感信息


class TestAIEngineClient(unittest.TestCase):
    """AIEngineClient"""

    def test_init_with_settings(self):
        s = Settings(api_key="sk-test")
        client = AIEngineClient(s)
        self.assertEqual(client.settings.api_key, "sk-test")

    def test_init_default(self):
        client = AIEngineClient()
        self.assertIsNotNone(client.settings)

    def test_get_reply_text_empty(self):
        self.assertEqual(AIEngineClient.get_reply_text(None), "")

    def test_get_token_usage_empty(self):
        usage = AIEngineClient.get_token_usage(None)
        self.assertEqual(usage["total_tokens"], 0)


class TestErrorHandler(unittest.TestCase):
    """ErrorHandler"""

    def test_config_error_fatal(self):
        e = ConfigError("bad config")
        self.assertEqual(e.severity, ErrorSeverity.FATAL)
        self.assertTrue(ErrorHandler.is_fatal(e))

    def test_api_error_retryable(self):
        e = APIError("500 error")
        self.assertTrue(ErrorHandler.should_retry(e))

    def test_auth_error_not_retryable(self):
        e = AuthError("unauthorized")
        self.assertFalse(ErrorHandler.should_retry(e))

    def test_rate_limit_has_retry_after(self):
        e = RateLimitError("slow", retry_after=30.0)
        self.assertEqual(e.retry_after, 30.0)

    def test_validation_error_log(self):
        e = ValidationError("bad param")
        c = ErrorHandler.classify(e)
        self.assertEqual(c["action"], ErrorAction.LOG)

    def test_handler_returns_dict(self):
        r = ErrorHandler.handle(ValueError("test"))
        self.assertIn("action", r)
        self.assertIn("severity", r)

    def test_classify_connection_error(self):
        c = ErrorHandler.classify(ConnectionError("refused"))
        self.assertTrue(c["retryable"])


class TestKeyManager(unittest.TestCase):
    """KeyManager"""

    def test_single_key(self):
        km = KeyManager(keys=["sk-key1"])
        self.assertEqual(km.current_key(), "sk-key1")

    def test_rotate_key(self):
        km = KeyManager(keys=["sk-key1", "sk-key2"])
        self.assertEqual(km.rotate_key(), "sk-key2")
        self.assertEqual(km.rotate_key(), "sk-key1")

    def test_empty_keys(self):
        km = KeyManager()
        self.assertIsNone(km.current_key())

    def test_degrade_switches_model(self):
        km = KeyManager(keys=["sk-key1"], models=["deepseek-chat", "deepseek-reasoner"])
        new_key = km.degrade()
        self.assertEqual(km.current_model(), "deepseek-reasoner")

    def test_degrade_switches_key(self):
        km = KeyManager(keys=["sk-key1", "sk-key2"], models=["deepseek-chat"])
        # degrade 已经在唯一模型上，应切换 Key
        self.assertIsNotNone(km.degrade())
        self.assertEqual(km.current_key(), "sk-key2")

    def test_degrade_exhausted(self):
        """降级耗尽后返回 None"""
        km = KeyManager(keys=["sk-key1"], models=["deepseek-chat"])
        # 只有一个 key 和一个 model
        result = km.degrade()
        self.assertIsNone(result)

    def test_add_key(self):
        km = KeyManager(keys=["sk-key1"])
        km.add_key("sk-key2")
        self.assertEqual(km.available_keys, 2)

    def test_mark_failure(self):
        km = KeyManager(keys=["sk-key1"])
        km.mark_failure("sk-key1")
        km.mark_failure("sk-key1")
        self.assertEqual(km.healthy_keys, 1)
        km.mark_failure("sk-key1")  # 3 failures
        self.assertEqual(km.healthy_keys, 0)

    def test_reset(self):
        km = KeyManager(keys=["sk-key1", "sk-key2"])
        km.rotate_key()
        km.mark_failure("sk-key1")
        km.reset()
        self.assertEqual(km.current_key(), "sk-key1")
        self.assertEqual(km.healthy_keys, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
