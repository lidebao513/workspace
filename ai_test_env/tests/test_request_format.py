"""Day 3 - 请求格式验证 + 错误分类决策树

功能说明：
    验证 AI API 请求格式的各种边界场景，建立错误分类体系和决策树。

作者：测试团队
创建日期：2024年
版本：1.0.0

测试内容：
    1. 完整结构测试（system + user + assistant + user）
    2. 缺少 system prompt 测试
    3. 额外字段容错测试
    4. 空 content 测试
    5. 超长 content 测试
    6. 错误分类器验证

面试话术参考：
    "我建立了完整的错误分类体系，能根据 HTTP 状态码
    自动判断是否重试、是否告警。
    同时验证了 messages 请求格式在各种边界下的行为，
    确保上线前能覆盖所有常见的格式问题。"
"""
import os
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.api_client import AITestClient
from utils.error_classifier import ErrorClassifier, ErrorCategory
from dotenv import load_dotenv


def test_full_structure(client):
    """测试 1：完整结构（system + user + assistant + user）

    验证 API 对标准多轮对话格式的处理能力。

    Args:
        client: AITestClient 实例

    Returns:
        bool: 测试是否通过
    """
    print("\n" + "=" * 50)
    print("[Test 1] 完整结构：system + user + assistant + user")
    print("=" * 50)

    # 构造完整的多轮对话消息
    messages = [
        {"role": "system", "content": "你是一个测试助手，回复要简洁。"},
        {"role": "user", "content": "你叫什么名字？"},
        {"role": "assistant", "content": "我是 DeepSeek，由深度求索公司创造。"},
        {"role": "user", "content": "你能做什么？"}
    ]

    try:
        # 调用 API
        response = client.chat(messages, max_tokens=200)
        reply = client.get_reply_text(response)
        finish_reason = response.choices[0].finish_reason

        # 验证响应不为空
        assert len(reply) > 0, "回复为空"
        print(f"回复: {reply[:120]}...")
        print(f"finish_reason: {finish_reason}")
        print("[PASS] 完整结构测试通过")
        return True
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def test_without_system(client):
    """测试 2：没有 system prompt

    验证 API 在缺少 system prompt 时的行为。

    Args:
        client: AITestClient 实例

    Returns:
        bool: 测试是否通过
    """
    print("\n" + "=" * 50)
    print("[Test 2] 无 system prompt（只有 user message）")
    print("=" * 50)

    # 只有 user message，没有 system prompt
    messages = [
        {"role": "user", "content": "你好，请用一句话介绍你自己。"}
    ]

    try:
        # 调用 API
        response = client.chat(messages, max_tokens=200)
        reply = client.get_reply_text(response)

        # 验证响应不为空
        assert len(reply) > 0
        print(f"回复: {reply[:120]}...")
        print("[PASS] 无 system prompt 测试通过（system 是可选的）")
        return True
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def test_extra_field_resilience(client):
    """测试 3：额外字段容错

    验证 API 对消息中额外字段的处理能力（容错性）。

    Args:
        client: AITestClient 实例

    Returns:
        bool: 测试是否通过
    """
    print("\n" + "=" * 50)
    print("[Test 3] 额外字段容错（传入无用字段）")
    print("=" * 50)

    # 消息中包含额外的自定义字段
    messages = [
        {
            "role": "user",
            "content": "回复'容错测试通过'这六个字",
            "timestamp": 1714200000,
            "source": "web",
            "user_id": "test_001"
        }
    ]

    try:
        # 调用 API
        response = client.chat(messages, max_tokens=50)
        reply = client.get_reply_text(response)
        usage = client.get_token_usage(response)

        # 验证响应不为空
        assert len(reply) > 0
        print(f"回复: {reply[:60]}...")
        print(f"Token 消耗: {usage}")
        print("[PASS] API 成功跳过额外字段，容错正常")
        return True
    except Exception as e:
        print(f"[WARN] 额外字段导致报错: {e}")
        print("注意：生产环境需要严格校验入参格式")
        return False


def test_empty_content(client):
    """测试 4：content 为空字符串

    验证 API 对空内容消息的处理能力。

    Args:
        client: AITestClient 实例

    Returns:
        bool: 测试是否通过
    """
    print("\n" + "=" * 50)
    print("[Test 4] content 为空字符串")
    print("=" * 50)

    # 空 content 的消息
    messages = [
        {"role": "user", "content": ""}
    ]

    try:
        # 调用 API
        response = client.chat(messages, max_tokens=50)
        reply = client.get_reply_text(response)
        print(f"回复: '{reply}'")
        print("[WARN] 空 content 未报错，API 自动容错")
        return True
    except Exception as e:
        print(f"[PASS] 空 content 被正确拦截: {type(e).__name__}")
        return True


def test_long_content(client):
    """测试 5：超长 content

    验证 API 对大输入的处理能力。

    Args:
        client: AITestClient 实例

    Returns:
        bool: 测试是否通过
    """
    print("\n" + "=" * 50)
    print("[Test 5] 超长 content（5000 字）")
    print("=" * 50)

    # 构造 5000 字的长文本
    long_text = "测试" * 2500  # 5000 字
    messages = [
        {"role": "user", "content": f"以下是一段长文本，请总结：{long_text}"}
    ]

    try:
        # 调用 API
        response = client.chat(messages, max_tokens=100)
        reply = client.get_reply_text(response)
        usage = client.get_token_usage(response)

        # 验证响应不为空
        assert len(reply) > 0
        print(f"回复前 60 字: {reply[:60]}...")
        print(f"Prompt Tokens: {usage['prompt_tokens']}")
        print(f"Completion Tokens: {usage['completion_tokens']}")
        print("[PASS] 超长 content 测试通过，API 正常处理")
        return True
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def test_error_classifier():
    """测试 6：验证错误分类器对各种错误的分类结果

    通过模拟各种 HTTP 错误，验证分类器的分类逻辑是否正确。

    Returns:
        bool: 分类器逻辑是否全部正确
    """
    print("\n" + "=" * 50)
    print("[Test 6] 错误分类器验证")
    print("=" * 50)

    # 定义测试用例（模拟各种错误场景）
    test_cases = [
        ("400 参数错误", RuntimeError("API 错误 (status=400): Bad Request")),
        ("401 无权限", RuntimeError("API 错误 (status=401): Unauthorized")),
        ("403 禁止访问", RuntimeError("API 错误 (status=403): Forbidden")),
        ("404 不存在", RuntimeError("API 错误 (status=404): Not Found")),
        ("429 限流", RuntimeError("API 错误 (status=429): Too Many Requests")),
        ("500 内部错误", RuntimeError("API 错误 (status=500): Internal Error")),
        ("502 网关错误", RuntimeError("API 错误 (status=502): Bad Gateway")),
        ("503 服务不可用", RuntimeError("API 错误 (status=503): Service Unavailable")),
        ("504 超时", RuntimeError("API 错误 (status=504): Gateway Timeout")),
        ("网络连接失败", RuntimeError("网络连接失败")),
    ]

    # 验证每个测试用例
    all_pass = True
    for name, error in test_cases:
        result = ErrorClassifier.classify(error)
        retriable = result["retriable"]
        severity = result["severity"]
        action = result["action"]

        # 输出分类结果
        status_tag = f"(status={result['http_status']})" if result['http_status'] else "(network)"
        print(f"\n{name} {status_tag}:")
        print(f"  分类: {result['category']}")
        print(f"  可重试: {'是' if retriable else '否'}")
        print(f"  严重级别: {severity}")
        print(f"  建议操作: {action}")

        # 验证分类逻辑的正确性
        if result['http_status'] == 401 or result['http_status'] == 403:
            all_pass &= (result['category'] == ErrorCategory.CRITICAL)
            all_pass &= (not retriable)
        elif result['http_status'] == 400 or result['http_status'] == 404:
            all_pass &= (result['category'] == ErrorCategory.NON_RETRIABLE)
            all_pass &= (not retriable)
        else:
            # 网络错误、429、5xx 都应该是可重试的
            all_pass &= (result['category'] == ErrorCategory.RETRIABLE)
            all_pass &= retriable

    # 输出验证结果
    if all_pass:
        print("\n[PASS] 错误分类器逻辑验证通过")
    else:
        print("\n[FAIL] 部分分类逻辑不正确，请检查")

    return all_pass


def main():
    """主函数：执行所有请求格式测试和错误分类器验证"""
    print("-- Day 3 - 请求格式验证 + 错误分类决策树 --")
    print("=" * 50)

    # 加载环境配置
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print("[环境] 已加载 .env 文件")

    # 初始化客户端
    try:
        client = AITestClient()
    except ValueError as e:
        print(f"\n[FAIL] {e}")
        return

    # 执行请求格式测试
    test_full_structure(client)
    test_without_system(client)
    test_extra_field_resilience(client)
    test_empty_content(client)
    test_long_content(client)

    # 执行错误分类器测试
    test_error_classifier()

    # 打印决策树
    print("\n" + "=" * 50)
    print("错误分类决策树")
    print("=" * 50)
    ErrorClassifier.print_decision_tree()

    # 汇总学习内容
    print("\n" + "=" * 50)
    print("Day 3 完成")
    print("=" * 50)
    print("你今天学习了：")
    print("  - messages 数据结构（system / user / assistant）")
    print("  - 请求格式验证（完整/缺失/边界/异常）")
    print("  - 错误分类体系（4xx / 5xx / 网络错误）")
    print("  - 错误分类决策树（重试/告警/转人工）")
    print()

    # 面试准备提示
    print("面试准备：")
    print('  "我建立了完整的 AI 接口错误分类体系，')
    print('   能根据状态码自动判断是否重试、是否告警、是否转人工。')
    print('   同时验证了 messages 格式的各种边界场景，')
    print('   确保生产环境中不会因为格式问题导致不可预测的 AI 行为。"')


if __name__ == "__main__":
    main()
