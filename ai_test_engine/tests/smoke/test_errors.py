"""
Day 28 — 异常错误测试

覆盖 API 返回的各种错误状态码和异常类型。
"""
import sys
import os
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.error_handler import (
    ErrorHandler, APIError, AuthError, RateLimitError,
    ConfigError, ValidationError, ErrorSeverity, ErrorAction,
)


class Test4xxErrors(unittest.TestCase):
    """4xx 错误"""

    def test_400_bad_request(self):
        """400 Bad Request"""
        err = ValueError("Bad request: invalid message format")
        c = ErrorHandler.classify(err)
        self.assertEqual(c["severity"], ErrorSeverity.WARN)

    def test_401_unauthorized(self):
        """401 Unauthorized"""
        err = AuthError("Invalid API key")
        c = ErrorHandler.classify(err)
        self.assertEqual(c["severity"], ErrorSeverity.FATAL)
        self.assertEqual(c["action"], ErrorAction.STOP)

    def test_403_forbidden(self):
        """403 Forbidden"""
        err = AuthError("API key lacks permission")
        self.assertTrue(ErrorHandler.is_fatal(err))
        self.assertFalse(ErrorHandler.should_retry(err))

    def test_429_rate_limit(self):
        """429 Rate Limit"""
        err = RateLimitError("Too many requests", retry_after=30.0)
        c = ErrorHandler.classify(err)
        self.assertEqual(c["severity"], ErrorSeverity.WARN)
        self.assertEqual(c["action"], ErrorAction.RETRY)
        self.assertTrue(c["retryable"])
        self.assertEqual(err.retry_after, 30.0)


class Test5xxErrors(unittest.TestCase):
    """5xx 错误"""

    def test_500_internal(self):
        """500 Internal Server Error"""
        err = APIError("Internal server error")
        self.assertTrue(ErrorHandler.should_retry(err))
        self.assertTrue(ErrorHandler.should_alert(err))

    def test_502_bad_gateway(self):
        """502 Bad Gateway"""
        err = APIError("Bad gateway")
        self.assertTrue(err.retryable)

    def test_503_service_unavailable(self):
        """503 Service Unavailable"""
        err = APIError("Service unavailable")
        c = ErrorHandler.classify(err)
        self.assertEqual(c["severity"], ErrorSeverity.ERROR)


class TestNetworkErrors(unittest.TestCase):
    """网络错误"""

    def test_timeout(self):
        """超时"""
        err = TimeoutError("Request timed out after 30s")
        c = ErrorHandler.classify(err)
        self.assertEqual(c["severity"], ErrorSeverity.ERROR)
        self.assertEqual(c["action"], ErrorAction.RETRY_THEN_ALERT)

    def test_connection_refused(self):
        """连接被拒绝"""
        err = ConnectionError("Connection refused")
        c = ErrorHandler.classify(err)
        self.assertEqual(c["severity"], ErrorSeverity.ERROR)
        self.assertTrue(c["retryable"])

    def test_connection_reset(self):
        """连接重置"""
        err = ConnectionError("Connection reset by peer")
        c = ErrorHandler.classify(err)
        self.assertTrue(c["retryable"])


class TestConfigErrors(unittest.TestCase):
    """配置错误"""

    def test_missing_api_key(self):
        """缺少 API Key"""
        err = ConfigError("DEEPSEEK_API_KEY is not set")
        c = ErrorHandler.classify(err)
        self.assertEqual(c["severity"], ErrorSeverity.FATAL)
        self.assertFalse(c["retryable"])

    def test_invalid_base_url(self):
        """无效 API Base URL"""
        err = ConfigError("Invalid API base URL")
        self.assertTrue(ErrorHandler.is_fatal(err))

    def test_wrong_model_name(self):
        """错误的模型名称"""
        err = ConfigError("Model 'gpt-5' not found")
        self.assertFalse(ErrorHandler.should_retry(err))


class TestValidationErrors(unittest.TestCase):
    """校验错误"""

    def test_invalid_temperature(self):
        """temperature 超出范围"""
        err = ValidationError("temperature must be between 0 and 2")
        c = ErrorHandler.classify(err)
        self.assertEqual(c["severity"], ErrorSeverity.WARN)

    def test_missing_required_field(self):
        """缺少必填字段"""
        err = ValidationError("messages field is required")
        self.assertFalse(ErrorHandler.should_alert(err))

    def test_invalid_parameter_type(self):
        """参数类型错误"""
        err = ValidationError("max_tokens must be an integer")
        c = ErrorHandler.classify(err)
        self.assertEqual(c["action"], ErrorAction.LOG)


if __name__ == "__main__":
    unittest.main(verbosity=2)
