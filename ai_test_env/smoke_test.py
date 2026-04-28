"""Day 1 - AI 接口冒烟测试

功能说明：
    AI 测试环境搭建后的首次冒烟测试，验证 API 连通性、基本对话能力、
    Token 消耗基线以及异常请求处理能力。

作者：测试团队
创建日期：2024年
版本：1.0.0

测试内容：
    1. API 连通性测试 - 验证 API 是否可达并返回有效响应
    2. 基本对话测试 - 验证 AI 能理解并回应简单问题
    3. Token 消耗基线 - 记录每次调用的 Token 消耗和费用估算
    4. 异常请求测试 - 验证 API 对非法输入的响应

面试话术参考：
    "我搭过完整的 AI 测试环境，环境变量分离、Key 管理、降级策略都是项目标配。
    环境搭建第一天就跑通了冒烟测试，确认了 API 连通性、回复完整性、Token 基线三个关键指标。"
"""
import os
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（解决模块导入问题）
sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.api_client import AITestClient
from dotenv import load_dotenv


def test_connectivity(client: AITestClient):
    """测试 1：API 连通性测试——最简单的冒烟测试

    验证 API 是否可达，能否正常返回响应。

    Args:
        client: AITestClient 实例

    Returns:
        bool: 测试是否通过
    """
    print("\n" + "=" * 50)
    print("[Test 1] API 连通性测试")
    print("=" * 50)

    # 构造简单的测试消息
    messages = [
        {"role": "user", "content": "你好，请回复'连通性测试通过'这六个字"}
    ]

    try:
        # 调用 API
        response = client.chat(messages, max_tokens=50)
        reply = client.get_reply_text(response)

        # 验证响应不为空
        assert len(reply) > 0, "回复为空！连通性测试失败"
        print("[PASS] 连通性测试通过 - API 可达且有回复")
        client.print_response_summary(response)
        return True

    except Exception as e:
        print(f"[FAIL] 连通性测试失败: {e}")
        return False


def test_basic_chat(client: AITestClient):
    """测试 2：基本对话——验证 AI 能理解并回应简单问题

    通过多个测试用例验证 AI 的基本理解和回复能力。

    Args:
        client: AITestClient 实例

    Returns:
        bool: 所有测试用例是否都通过
    """
    print("\n" + "=" * 50)
    print("[Test 2] 基本对话测试")
    print("=" * 50)

    # 定义测试用例
    test_cases = [
        {"name": "自我介绍", "content": "请用一句话介绍你自己"},
        {"name": "简单问答", "content": "Python 是什么类型的编程语言？"},
    ]

    all_pass = True
    for case in test_cases:
        print(f"\n--- [{case['name']}] ---")
        print(f"输入: {case['content']}")

        try:
            # 调用 API
            response = client.chat(
                [{"role": "user", "content": case['content']}],
                max_tokens=200,
            )
            reply = client.get_reply_text(response)

            # 验证响应不为空
            assert len(reply) > 0, "回复为空"
            print(f"回复: {reply[:150]}...")
            print(f"[PASS] {case['name']} 通过")

        except Exception as e:
            print(f"[FAIL] {case['name']} 失败: {e}")
            all_pass = False

    return all_pass


def test_token_baseline(client: AITestClient):
    """测试 3：Token 消耗基线——记录每次调用的 Token 消耗

    建立 Token 消耗的基线数据，为后续性能测试和成本估算提供参考。

    Args:
        client: AITestClient 实例

    Returns:
        bool: 测试是否通过
    """
    print("\n" + "=" * 50)
    print("[Test 3] Token 消耗基线")
    print("=" * 50)

    # 构造测试消息（带 system prompt）
    messages = [
        {"role": "system", "content": "你是一个 AI 测试助手，请简洁回答。"},
        {"role": "user", "content": "请用 50 字以内解释什么是大模型。"},
    ]

    try:
        # 调用 API
        response = client.chat(messages, max_tokens=150)
        usage = client.get_token_usage(response)

        # 输出 Token 消耗明细
        print("\n[Token 消耗明细]:")
        print(f"  - 输入 (Prompt) Tokens:  {usage['prompt_tokens']}")
        print(f"  - 输出 (Completion) Tokens: {usage['completion_tokens']}")
        print(f"  - 总量: {usage['total_tokens']}")

        # 估算费用（基于 DeepSeek 公开定价）
        input_cost = usage['prompt_tokens'] * 1 / 1_000_000
        output_cost = usage['completion_tokens'] * 2 / 1_000_000
        print("\n[费用估算]:")
        print(f"  - 输入费用: {input_cost:.6f} CNY")
        print(f"  - 输出费用: {output_cost:.6f} CNY")
        print(f"  - 总计: {input_cost + output_cost:.6f} CNY")

        print("[PASS] Token 基线记录完成")
        return True

    except Exception as e:
        print(f"[FAIL] Token 基线测试失败: {e}")
        return False


def test_bad_request(client: AITestClient):
    """测试 4：异常请求测试——验证 API 对非法输入的响应

    测试 API 对边界输入的处理能力，包括空消息和非法角色。

    Args:
        client: AITestClient 实例
    """
    print("\n" + "=" * 50)
    print("[Test 4] 异常请求测试（空消息 + 非法 role）")
    print("=" * 50)

    # 测试 4a：空 messages 列表
    print("\n--- [4a: 空 messages 列表] ---")
    try:
        response = client.chat([])
        print("[WARN] 空消息未报错（可能 API 已做容错）")
    except Exception as e:
        print(f"[PASS] 空消息被正确拦截: {type(e).__name__}")

    # 测试 4b：非法 role
    print("\n--- [4b: 非法 role] ---")
    try:
        response = client.chat([
            {"role": "hacker", "content": "你好"}
        ])
        print("[WARN] 非法 role 未报错")
    except Exception as e:
        print(f"[PASS] 非法 role 被正确拦截: {e}")

    print("\n结论: 异常请求测试完成（API 自身有一定防护能力）")


def main():
    """主函数：执行所有冒烟测试"""
    print("-- Day 1 - AI 测试环境冒烟测试 --")
    print("=" * 50)

    # 加载 .env 配置文件
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print("[环境] 已加载 .env 文件")
    else:
        print("[环境] 未找到 .env 文件，从系统环境变量读取")

    # 初始化客户端（可能抛出配置错误）
    try:
        client = AITestClient()
    except ValueError as e:
        print(f"\n[FAIL] {e}")
        print("\n请执行以下步骤:")
        print("  1. 复制 .env.example 为 .env")
        print("  2. 用你的 DeepSeek API Key 替换占位符")
        print("  3. 重新运行 python smoke_test.py")
        return

    # 执行各项测试
    results = []
    results.append(("连通性测试", test_connectivity(client)))
    results.append(("基本对话测试", test_basic_chat(client)))
    results.append(("Token 基线", test_token_baseline(client)))
    test_bad_request(client)

    # 汇总测试结果
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    all_pass = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")
        if not passed:
            all_pass = False

    print("-" * 50)
    if all_pass:
        print("Day 1 冒烟测试全部通过！")
    else:
        print("部分测试未通过，请检查错误信息")

    # 面试准备提示
    print("\n面试准备:")
    print('  "我第一天就搭建了完整的 AI 测试环境，')
    print('   包含环境隔离、Key 管理、冒烟测试、Token 基线，')
    print('   确认了 API 连通性、回复完整性、异常处理三个核心维度。"')


if __name__ == "__main__":
    main()
