"""
Day 25 — 生产级错误体系测试

覆盖：
1. 5 种异常类型的 severity/action/retryable
2. AppError 基类的 to_dict
3. ErrorClassifier 异常分类
4. should_retry / should_alert / is_fatal
5. RateLimitError 额外属性
6. 通用异常映射（ConnectionError / TimeoutError / ValueError）
7. ConfigError FATAL 终止
8. APIError RETRY_THEN_ALERT
"""
import sys
import os
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d25_error_system import (
    AppError, ConfigError, APIError, RateLimitError,
    AuthError, ValidationError,
    ErrorClassifier, ErrorSeverity, ErrorAction,
)


class TestErrorTypes(unittest.TestCase):
    """各异常类型属性"""

    def test_config_error(self):
        e = ConfigError("Missing API key")
        self.assertEqual(e.severity, ErrorSeverity.FATAL)
        self.assertEqual(e.action, ErrorAction.STOP)
        self.assertFalse(e.retryable)

    def test_api_error(self):
        e = APIError("500 Internal Server Error")
        self.assertEqual(e.severity, ErrorSeverity.ERROR)
        self.assertEqual(e.action, ErrorAction.RETRY_THEN_ALERT)
        self.assertTrue(e.retryable)

    def test_rate_limit_error(self):
        e = RateLimitError("Too many requests", retry_after=30.0)
        self.assertEqual(e.severity, ErrorSeverity.WARN)
        self.assertEqual(e.action, ErrorAction.RETRY)
        self.assertTrue(e.retryable)
        self.assertEqual(e.retry_after, 30.0)

    def test_auth_error(self):
        e = AuthError("Invalid API key")
        self.assertEqual(e.severity, ErrorSeverity.FATAL)
        self.assertEqual(e.action, ErrorAction.STOP)
        self.assertFalse(e.retryable)

    def test_validation_error(self):
        e = ValidationError("Invalid temperature")
        self.assertEqual(e.severity, ErrorSeverity.WARN)
        self.assertEqual(e.action, ErrorAction.LOG)
        self.assertFalse(e.retryable)


class TestAppErrorBase(unittest.TestCase):
    """AppError 基类"""

    def test_default_attributes(self):
        """默认属性"""
        e = AppError("generic error")
        self.assertEqual(e.severity, ErrorSeverity.ERROR)
        self.assertEqual(e.action, ErrorAction.STOP)

    def test_to_dict_structure(self):
        """to_dict 包含所有字段"""
        e = ConfigError("bad config", context={"key": "API_KEY"})
        d = e.to_dict()
        self.assertEqual(d["type"], "ConfigError")
        self.assertEqual(d["severity"], "FATAL")
        self.assertEqual(d["action"], "STOP")
        self.assertEqual(d["retryable"], False)
        self.assertEqual(d["context"]["key"], "API_KEY")

    def test_context_default_empty(self):
        e = ConfigError("test")
        self.assertEqual(e.context, {})


class TestErrorClassifier(unittest.TestCase):
    """异常分类器"""

    def test_classify_app_error(self):
        """AppError 子类保持原属性"""
        e = APIError("API down")
        c = ErrorClassifier.classify(e)
        self.assertEqual(c["severity"], ErrorSeverity.ERROR)
        self.assertEqual(c["action"], ErrorAction.RETRY_THEN_ALERT)
        self.assertTrue(c["retryable"])

    def test_classify_connection_error(self):
        """ConnectionError → ERROR / RETRY_THEN_ALERT"""
        c = ErrorClassifier.classify(ConnectionError("refused"))
        self.assertEqual(c["severity"], ErrorSeverity.ERROR)
        self.assertEqual(c["action"], ErrorAction.RETRY_THEN_ALERT)
        self.assertTrue(c["retryable"])

    def test_classify_timeout_error(self):
        """TimeoutError → ERROR / RETRY_THEN_ALERT"""
        c = ErrorClassifier.classify(TimeoutError("timed out"))
        self.assertEqual(c["severity"], ErrorSeverity.ERROR)

    def test_classify_value_error(self):
        """ValueError → WARN / LOG"""
        c = ErrorClassifier.classify(ValueError("bad param"))
        self.assertEqual(c["severity"], ErrorSeverity.WARN)
        self.assertEqual(c["action"], ErrorAction.LOG)
        self.assertFalse(c["retryable"])

    def test_classify_unknown(self):
        """未知异常 → ERROR / ALERT"""
        c = ErrorClassifier.classify(RuntimeError("unknown"))
        self.assertEqual(c["severity"], ErrorSeverity.ERROR)
        self.assertEqual(c["action"], ErrorAction.ALERT)
        self.assertFalse(c["retryable"])

    def test_should_retry_true(self):
        self.assertTrue(ErrorClassifier.should_retry(APIError("timeout")))
        self.assertTrue(ErrorClassifier.should_retry(ConnectionError("refused")))

    def test_should_retry_false(self):
        self.assertFalse(ErrorClassifier.should_retry(ConfigError("bad")))
        self.assertFalse(ErrorClassifier.should_retry(ValueError("bad")))

    def test_should_alert_true(self):
        self.assertTrue(ErrorClassifier.should_alert(APIError("timeout")))

    def test_should_alert_false(self):
        self.assertFalse(ErrorClassifier.should_alert(ValidationError("bad")))
        self.assertFalse(ErrorClassifier.should_alert(RateLimitError("slow")))

    def test_is_fatal_true(self):
        self.assertTrue(ErrorClassifier.is_fatal(ConfigError("bad")))
        self.assertTrue(ErrorClassifier.is_fatal(AuthError("unauthorized")))

    def test_is_fatal_false(self):
        self.assertFalse(ErrorClassifier.is_fatal(APIError("timeout")))
        self.assertFalse(ErrorClassifier.is_fatal(ValidationError("bad")))

    def test_classify_rate_limit_preserves_retry_after(self):
        """RateLimitError 的 retry_after 属性保留"""
        e = RateLimitError("slow", retry_after=15.0)
        self.assertEqual(e.retry_after, 15.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
