"""Day 4 - 响应结构验证 + Token 基线 + 响应时间基线

功能说明：
    建立完整的 API 响应验证体系和基线数据，包括响应结构验证、
    Token 消耗基线、响应时间基线和 finish_reason 行为验证。

作者：测试团队
创建日期：2024年
版本：1.0.0

测试内容：
    1. 完整结构验证（9 个字段逐一检查）
    2. Token 一致性验证（4 种场景）
    3. 响应时间记录（首次 + 平均）
    4. finish_reason 短回复验证
    5. finish_reason 截断验证
    6. 多次请求 Token 基线统计

面试话术参考：
    "我建立了完整的 API 响应验证体系和 Token 基线表。
    每个字段都有自动化验证，每次上线前跑一遍确保字段没有变化。
    同时记录了 Token 消耗和响应时间的基线数据，
    为性能测试和成本估算提供了依据。"
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
pytestmark = pytest.mark.filterwarnings("ignore::pytest.PytestReturnNotNoneWarning")

from utils.d1_api_client import AITestClient
from utils.d4_response_validator import ResponseValidator
from dotenv import load_dotenv


def test_full_structure_validation(client):
    """测试 1：响应结构完整验证（9 个字段）

    使用 ResponseValidator 对 API 响应的所有关键字段进行验证。

    Args:
        client: AITestClient 实例

    Returns:
        dict | None: 验证报告，失败返回 None
    """
    print("\n" + "=" * 60)
    print("[Test 1] 响应结构完整验证（9 个字段）")
    print("=" * 60)
    messages = [{"role": "user", "content": "你好，请简单介绍一下你自己。"}]
    try:
        response = client.chat(messages, max_tokens=200)
        report = ResponseValidator.validate(response)
        ResponseValidator.print_report(report)
        return report
    except Exception as e:
        print(f"[FAIL] API 调用失败: {e}")
        return None


def test_token_consistency(client):
    """测试 2：验证 prompt_tokens + completion_tokens = total_tokens

    确保 Token 统计的准确性和一致性。

    Args:
        client: AITestClient 实例

    Returns:
        bool: 所有场景是否都通过验证
    """
    print("\n" + "=" * 60)
    print("[Test 2] Token 使用一致性验证")
    print("=" * 60)
    cases = [
        ("简短问答", [{"role": "user", "content": "你好"}]),
        ("中等长度", [{"role": "user", "content": "请用 200 字介绍 Python 语言。"}]),
        ("带 system", [
            {"role": "system", "content": "你是一个 Python 专家，回复要简洁专业。"},
            {"role": "user", "content": "tuple 和 list 的区别是什么？"}
        ]),
        ("短回复", [{"role": "user", "content": "是"}]),
    ]
    all_pass = True
    for name, messages in cases:
        try:
            response = client.chat(messages, max_tokens=200)
            usage = client.get_token_usage(response)
            p, c, t = usage["prompt_tokens"], usage["completion_tokens"], usage["total_tokens"]
            eq = (p + c == t)
            flag = "[OK]" if eq else "[!!]"
            print(f"  {flag} {name}: P={p} + C={c} = T={t} {'(一致)' if eq else '(不一致!)'}")
            if not eq:
                all_pass = False
        except Exception as e:
            print(f"  [!!] {name}: {e}")
            all_pass = False
    print(f"\n{'[PASS]' if all_pass else '[FAIL]'} Token 一致性验证")
    return all_pass


def test_response_time(client):
    """测试 3：响应时间基线记录

    记录首次请求和多次请求的响应时间，建立时间基线。

    Args:
        client: AITestClient 实例
    """
    print("\n" + "=" * 60)
    print("[Test 3] 响应时间基线记录")
    print("=" * 60)
    messages = [{"role": "user", "content": "用一句话说明什么是 API。"}]
    for count in [1, 3, 5]:
        times = []
        for i in range(count):
            start = time.time()
            try:
                response = client.chat(messages, max_tokens=100)
                elapsed = time.time() - start
                times.append(elapsed)
                print(f"  第 {i+1} 次: {elapsed:.2f}s")
            except Exception as e:
                print(f"  第 {i+1} 次: 失败 - {e}")
        if times:
            avg = sum(times) / len(times)
            print(f"  最短: {min(times):.2f}s  最长: {max(times):.2f}s  平均: {avg:.2f}s")
            tag = "首次（含冷启动）" if count == 1 else f"{count} 次平均"
            print(f"  -> {tag}: {avg:.2f}s")
    print("\n>> 首次请求通常比后续慢（冷启动），稳定后波动 >50% 说明网络不稳")


def test_finish_reason_short(client):
    """测试 4：短回复时 finish_reason 应为 stop

    验证 API 在生成短回复时正确设置 finish_reason。

    Args:
        client: AITestClient 实例
    """
    print("\n" + "=" * 60)
    print("[Test 4] finish_reason 验证 - 短回复")
    print("=" * 60)
    cases = [
        ("是/否回答", [{"role": "user", "content": "1+1=2 对吗？只回答'对'或'错'"}], 50),
        ("单字回复", [{"role": "user", "content": "请只回复一个数字：7"}], 50),
        ("简短介绍", [{"role": "user", "content": "你叫什么？"}], 100),
    ]
    for name, messages, mt in cases:
        try:
            response = client.chat(messages, max_tokens=mt)
            reason = response.choices[0].finish_reason
            content = client.get_reply_text(response)
            flag = "[OK]" if reason == "stop" else "[??]"
            print(f"  {flag} {name}: finish={reason}, 长度={len(content)}")
        except Exception as e:
            print(f"  ❌ {name}: {e}")


def test_finish_reason_truncation(client):
    """测试 5：max_tokens 不够时 finish_reason=length

    验证 API 在被截断时正确设置 finish_reason。

    Args:
        client: AITestClient 实例
    """
    print("\n" + "=" * 60)
    print("[Test 5] finish_reason 验证 - 截断")
    print("=" * 60)
    messages = [{"role": "user", "content": "请写一篇 500 字的文章，介绍人工智能的发展历史。"}]
    for mt in [5, 20, 50]:
        try:
            response = client.chat(messages, max_tokens=mt)
            reason = response.choices[0].finish_reason
            content = client.get_reply_text(response)
            flag = "[OK]" if reason == "length" else "[??]"
            print(f"  {flag} max_tokens={mt}: finish={reason}, 回复前20={content[:20]}...")
        except Exception as e:
            print(f"  ❌ max_tokens={mt}: {e}")
    try:
        response = client.chat(messages, max_tokens=500)
        reason = response.choices[0].finish_reason
        print(f"  [OK] max_tokens=500: finish={reason}（足够时正常结束）")
    except Exception as e:
        print(f"  ❌ max_tokens=500: {e}")


def test_token_baseline(client):
    """测试 6：Token 消耗基线统计

    统计多种场景下的 Token 消耗，建立基线数据。

    Args:
        client: AITestClient 实例
    """
    print("\n" + "=" * 60)
    print("[Test 6] Token 消耗基线统计（5 种场景）")
    print("=" * 60)
    scenarios = [
        ("简短问答", [{"role": "user", "content": "你好"}]),
        ("普通回答", [{"role": "user", "content": "请介绍 Python 语言，100 字左右。"}]),
        ("带 system", [
            {"role": "system", "content": "你是一个技术专家，回复要简洁专业。"},
            {"role": "user", "content": "什么是 RESTful API？"}
        ]),
        ("多轮对话", [
            {"role": "user", "content": "你叫什么？"},
            {"role": "assistant", "content": "我叫 DeepSeek。"},
            {"role": "user", "content": "你能做什么？"}
        ]),
        ("长输入", [{"role": "user", "content": "请总结以下文本：AI 测试 " * 20}]),
    ]
    records = []
    for name, messages in scenarios:
        try:
            response = client.chat(messages, max_tokens=300)
            usage = client.get_token_usage(response)
            record = {
                "scenario": name,
                "prompt_tokens": usage["prompt_tokens"],
                "completion_tokens": usage["completion_tokens"],
                "total_tokens": usage["total_tokens"],
                "finish_reason": response.choices[0].finish_reason,
            }
            records.append(record)
            print(f"  {name}: P={record['prompt_tokens']:>5} + C={record['completion_tokens']:>4} = T={record['total_tokens']:>5}")
        except Exception as e:
            print(f"  ❌ {name}: {e}")
    if records:
        avg_p = sum(r["prompt_tokens"] for r in records) / len(records)
        avg_c = sum(r["completion_tokens"] for r in records) / len(records)
        print(f"\n  --- Token 基线 ---")
        print(f"  场景数: {len(records)}")
        print(f"  平均 Prompt Tokens:     {avg_p:>8.1f}")
        print(f"  平均 Completion Tokens: {avg_c:>8.1f}")
        print(f"  平均 Total Tokens:      {avg_p + avg_c:>8.1f}")
        cost = (avg_p * 0.14 + avg_c * 0.28) / 1_000_000 * len(records)
        print(f"  本次测试总费用: 约 {cost:.6f} 元")
        print(f"  （输入 0.14 元/百万, 输出 0.28 元/百万）")


def main():
    """主函数：执行所有响应结构和基线测试"""
    print("-- Day 4 - 响应结构验证 + Token 基线 + 响应时间基线 --")
    print("=" * 60)
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print("[环境] 已加载 .env 文件")
    try:
        client = AITestClient()
    except ValueError as e:
        print(f"\n[FAIL] {e}")
        return

    test_full_structure_validation(client)
    test_token_consistency(client)
    test_response_time(client)
    test_finish_reason_short(client)
    test_finish_reason_truncation(client)
    test_token_baseline(client)

    print("\n" + "=" * 60)
    print("Day 4 完成")
    print("=" * 60)
    print("今天学习了：")
    print("  - API 响应结构（id/object/created/model/choices/usage）")
    print("  - finish_reason 的 stop/length 区别")
    print("  - Token 一致性验证（prompt+completion=total）")
    print("  - 响应时间基线（首次 vs 后续）")
    print("  - Token 基线（5 种场景消耗对比）")
    print("  - 响应验证器（9 字段逐一检查）")


if __name__ == "__main__":
    main()
