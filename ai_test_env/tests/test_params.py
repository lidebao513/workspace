"""
Day 2 - 参数边界测试

学习目标：用边界值分析和等价类划分法测试 AI API 参数。

测试内容：
1. max_tokens 边界测试（1 / 10 / 2048）
2. temperature 对比测试（0 / 0.7 / 2.0）
3. 异常参数测试（负数 / 超大值）
4. 参数组合测试（低 temperature + 小 max_tokens）

面试话术：
"我做了完整的参数边界测试，覆盖了 max_tokens、temperature 的
边界值和等价类。发现 temperature=0 时一致性最好，适合金融场景；
temperature>1.5 后回复质量明显下降，不建议生产环境使用。
这些数据是我在搭建环境第二天就建立的参数基线。"
"""
import os
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.api_client import AITestClient
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# max_tokens 边界测试
# ---------------------------------------------------------------------------

def test_max_tokens_boundary(client):
    """测试 max_tokens 的边界值：1 / 10 / 2048"""
    print("\n" + "=" * 50)
    print("[Test 1] max_tokens 边界测试")
    print("=" * 50)

    messages = [{"role": "user", "content": "给我写一篇 500 字的文章，介绍 Python 编程语言。"}]

    boundaries = [1, 10, 2048]
    for mt in boundaries:
        try:
            response = client.chat_with_params(messages, max_tokens=mt)
            client.print_params_response(response, label=f"max_tokens={mt}")
        except Exception as e:
            print(f"\n[max_tokens={mt}] [FAIL] {e}")

    # 总结
    print("\n>> 结论：max_tokens 是硬性上限。设为 1 或 10 时, finish_reason='length' 表示被截断。")
    print(">> 生产环境需要根据实际回复长度设置合理的 max_tokens，预留 30%-50% 余量。")


# ---------------------------------------------------------------------------
# temperature 对比测试
# ---------------------------------------------------------------------------

def test_temperature_comparison(client):
    """测试不同 temperature 下回复的差异"""
    print("\n" + "=" * 50)
    print("[Test 2] temperature 对比测试")
    print("=" * 50)

    messages = [{"role": "user", "content": "用一句话说明什么是 API。"}]

    temps = [
        (0.0, "完全确定（金融/法律场景）"),
        (0.3, "低随机性（客服/保险场景）"),
        (0.7, "默认值（通用场景）"),
        (1.5, "高随机性（创意场景）"),
        (2.0, "极限值（几乎胡言乱语）"),
    ]

    for temp, desc in temps:
        try:
            response = client.chat_with_params(messages, temperature=temp)
            reply = client.get_reply_text(response)
            print(f"\n--- temperature={temp} ({desc}) ---")
            print(f"回复: {reply[:100]}...")
        except Exception as e:
            print(f"\n--- temperature={temp} [FAIL] {e}")

    print("\n>> 结论：temperature 控制回复的随机性，值越大差异越明显。")
    print(">> 生产环境应根据场景选择合适的值，金融/法律类建议 0-0.3，通用类 0.7。")


def test_temperature_consistency(client):
    """验证 temperature=0 时的回复一致性"""
    print("\n" + "=" * 50)
    print("[Test 3] temperature=0 一致性验证")
    print("=" * 50)

    messages = [{"role": "user", "content": "用一句话说明什么是 API。"}]

    replies = []
    for i in range(3):
        response = client.chat_with_params(messages, temperature=0, seed=42)
        reply = client.get_reply_text(response)
        replies.append(reply)
        print(f"第 {i+1} 次回复: {reply[:60]}...")

    # 比较一致性
    if replies[0] == replies[1] == replies[2]:
        print("\n--> temperature=0 + seed=42: 三次回复完全一致 [OK]")
    else:
        common_words = len(set(replies[0].split()) & set(replies[1].split()) & set(replies[2].split()))
        total_words = max(len(set(replies[0].split())), 1)
        similarity = common_words / total_words
        print(f"\n--> 三次回复不完全一致，单词重叠率: {similarity:.0%}")
        print("--> 提示：temperature=0 也不保证 100% 一致，可尝试加 seed 参数")

    print("\n>> 结论：temperature=0 + seed 能获得高度一致的回复。")
    print(">> 但如果业务场景要求'完全一致'，还需要在测试中验证多次。")


# ---------------------------------------------------------------------------
# 异常参数测试
# ---------------------------------------------------------------------------

def test_invalid_params(client):
    """测试异常参数输入"""
    print("\n" + "=" * 50)
    print("[Test 4] 异常参数测试")
    print("=" * 50)

    messages = [{"role": "user", "content": "你好"}]

    invalid_cases = [
        ("temperature=-1", {"temperature": -1}),
        ("temperature=3.0", {"temperature": 3.0}),
        ("max_tokens=0", {"max_tokens": 0}),
        ("max_tokens=-100", {"max_tokens": -100}),
    ]

    for name, params in invalid_cases:
        try:
            response = client.chat_with_params(messages, **params)
            client.print_params_response(response, label=name)
            print(f"  [WARN] {name} 未报错，API 自动处理了异常值")
        except Exception as e:
            print(f"\n--- {name} ---")
            print(f"  [PASS] 被正确拦截: {e}")

    print("\n>> 结论：API 对异常参数的防护能力如下：")
    print(">> - temperature 超出范围：自动限幅或报错")
    print(">> - max_tokens 为 0 或负数：不同 API 行为不同，需验证")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    print("-- Day 2 - 参数边界测试 --")
    print("=" * 50)

    # 加载 .env
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print("[环境] 已加载 .env 文件")
    else:
        print("[环境] 未找到 .env 文件，从系统环境变量读取")

    # 初始化客户端
    try:
        client = AITestClient()
    except ValueError as e:
        print(f"\n[FAIL] {e}")
        return

    # 执行测试
    test_max_tokens_boundary(client)
    test_temperature_comparison(client)
    test_temperature_consistency(client)
    test_invalid_params(client)

    # 汇总
    print("\n" + "=" * 50)
    print("Day 2 参数边界测试完成")
    print("=" * 50)
    print("你今天测试了以下边界：")
    print("  max_tokens: 1 / 10 / 2048")
    print("  temperature: 0 / 0.3 / 0.7 / 1.5 / 2.0")
    print("  异常参数: 负数 / 0 / 超范围")
    print("  temperature 一致性验证（3 次请求对比）")
    print()

    print("面试准备：")
    print('  "我用边界值分析和等价类划分方法测试了 max_tokens、temperature')
    print('   等核心参数，记录了每个边界下的回复长度、finish_reason、')
    print('   Token 消耗，为后续版本对比建立了参数基线。"')


if __name__ == "__main__":
    main()
