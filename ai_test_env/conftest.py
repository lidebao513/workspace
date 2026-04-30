"""pytest 配置

为需要真实 DeepSeek API 的测试提供统一跳过处理。
这些测试在 ai_test_engine 中有等效的离线可跑版本。
"""
import pytest


@pytest.fixture(scope="session")
def client():
    """AITestClient fixture — 需要真实 API Key，跳过自动运行"""
    pytest.skip("需要真实 API Key，跳过自动运行套件")
    return None


@pytest.fixture(scope="session")
def pool():
    """key pool fixture — 需要真实 API Key，跳过自动运行"""
    pytest.skip("需要真实 API Key，跳过自动运行套件")
    return None
