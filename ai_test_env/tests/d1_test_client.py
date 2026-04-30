"""
Day 1 — API 客户端测试

测试内容：
1. 客户端初始化（有 VPN 降级提示）
2. get_reply_text 提取回复
3. get_token_usage 提取 Token
4. chat_with_params 自定义参数

该测试套件使用 mock 环境变量来避免真实 API 调用，
重点验证 AITestClient 类的接口和边界条件处理能力。
"""
import sys
import os
from pathlib import Path

# 将项目根目录添加到 Python 路径，使得测试可以导入 utils 模块
# Path(__file__).resolve().parent.parent 指向 ai_test_env/ 目录
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_client_init_defaults():
    """测试客户端默认初始化

    验证点：
    - 清空环境变量后，客户端使用默认配置
    - model 默认为 "deepseek-chat"
    - API Key 能正确从环境变量 DEEPSEEK_API_KEY 读取
    """
    # 清除可能存在的环境变量，确保测试隔离
    os.environ.pop("DEEPSEEK_API_KEY", None)
    os.environ.pop("DEEPSEEK_URL", None)
    # 设置 mock key 以避免拉起浏览器（某些 SDK 实现会尝试打开认证页面）
    os.environ["DEEPSEEK_API_KEY"] = "sk-test-mock-key"
    os.environ.pop("DEEPSEEK_API_BASE", None)

    from utils.d1_api_client import AITestClient
    client = AITestClient()
    assert client.model == "deepseek-chat"
    assert "sk-test" in client.api_key


def test_client_custom_init():
    """测试自定义初始化参数

    验证点：
    - 客户端实例具有必要的属性
    - model 属性已被正确设置
    - 内部 client 对象已初始化
    """
    from utils.d1_api_client import AITestClient
    client = AITestClient()
    assert client.model is not None
    assert hasattr(client, "client")


def test_chat_with_params_empty_messages():
    """测试空消息列表的 chat_with_params——应引发异常

    验证点：
    - 传入空列表 [] 时，API 应该返回错误
    - 客户端应能正确捕获并传播异常
    - 确保 API 调用前有输入验证
    """
    from utils.d1_api_client import AITestClient
    client = AITestClient()
    try:
        client.chat_with_params([])
        # 不应该成功——空消息应报错
        success = True
    except Exception:
        success = False
    assert not success, "空消息应该抛出异常"


def test_get_reply_text_valid():
    """模拟一个有效的 API 响应对象，测试 get_reply_text

    验证点：
    - 从 API 响应中正确提取 assistant 的回复文本
    - 处理带有 choices[0].message.content 结构的响应

    该测试不依赖真实 API，而是通过 mock 对象模拟响应结构。
    """
    from utils.d1_api_client import AITestClient
    client = AITestClient()

    class MockChoice:
        class Message:
            content = "Hello from AI"
        message = Message()

    class MockResponse:
        choices = [MockChoice()]

    text = client.get_reply_text(MockResponse())
    assert text == "Hello from AI"


def test_get_reply_text_empty():
    """测试 get_reply_text 空响应

    验证点：
    - 当 API 返回空 choices 列表时，方法应返回空字符串
    - 具备良好的防御性处理空数据的能力
    """
    from utils.d1_api_client import AITestClient
    client = AITestClient()

    class MockResponse:
        choices = []

    text = client.get_reply_text(MockResponse())
    assert text == ""


def test_get_token_usage():
    """模拟 API 响应对象，测试 get_token_usage

    验证点：
    - 正确解析 usage.prompt_tokens（输入 token 数量）
    - 正确解析 usage.completion_tokens（输出 token 数量）
    - 正确解析 usage.total_tokens（总 token 数量）
    """
    from utils.d1_api_client import AITestClient
    client = AITestClient()

    class MockUsage:
        prompt_tokens = 50
        completion_tokens = 100
        total_tokens = 150

    class MockResponse:
        usage = MockUsage()

    usage = client.get_token_usage(MockResponse())
    assert usage["prompt_tokens"] == 50
    assert usage["completion_tokens"] == 100
    assert usage["total_tokens"] == 150


def test_get_token_usage_none():
    """测试 get_token_usage 当 usage 为 None

    验证点：
    - 当 API 响应中 usage 字段为 None 时，应返回默认值
    - prompt_tokens、completion_tokens、total_tokens 均应返回 0
    - 避免空指针异常，提高系统健壮性
    """
    from utils.d1_api_client import AITestClient
    client = AITestClient()

    class MockResponse:
        usage = None

    usage = client.get_token_usage(MockResponse())
    assert usage["prompt_tokens"] == 0
    assert usage["completion_tokens"] == 0
    assert usage["total_tokens"] == 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
