"""
Day 9（第 2 周 Day 4）— LLM-as-Judge + Schema 验证器测试

测试内容：
1. 离线评分（模拟评委输出）— 完整 JSON
2. 离线评分 — JSON 在代码块内
3. 离线评分 — 解析失败（默认分+错误标记）
4. A/B 对比测试
5. 批量评分
6. Schema 验证（字段存在性、类型、值范围）
"""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.d9_llm_judge import LLMJudge, JudgeResult, BatchJudgeReport, ABCompareResult


def print_separator(title):
    print(f"\n{'=' * 50}")
    print(f"[{title}]")
    print(f"{'=' * 50}")


# ---------------------------------------------------------------------------
# 辅助函数：模拟评委 API 调用
# ---------------------------------------------------------------------------

def _api_stub(prompt: str) -> str:
    """模拟评委 API 返回 JSON"""
    return json.dumps({
        "accuracy": 8,
        "completeness": 7,
        "conciseness": 6,
        "relevance": 9,
        "helpfulness": 8,
        "safety": 10,
        "overall_comment": "回复整体质量不错，准确性和相关性较高。",
    })


def _api_partial_stub(prompt: str) -> str:
    """模拟不完整的评委回复"""
    return json.dumps({
        "accuracy": 9,
        "completeness": 8,
    })


def _api_invalid_stub(prompt: str) -> str:
    """模拟非 JSON 回复"""
    return "这个回复质量不错，但我无法输出JSON格式。"


# ---------------------------------------------------------------------------
# Test 1：离线评分（模拟完整 JSON 输出）
# ---------------------------------------------------------------------------

def test_offline_scoring():
    print_separator("Test 1: 离线评分 - 完整 JSON")

    judge = LLMJudge(api_func=None)  # 离线模式

    result = judge.score_offline(
        prompt="Python 是什么？",
        response="Python 是一种高级编程语言。",
        judge_raw_output=json.dumps({
            "accuracy": 8,
            "completeness": 7,
            "conciseness": 6,
            "relevance": 9,
            "helpfulness": 8,
            "safety": 10,
            "overall_comment": "回复清晰准确，安全性满分。",
        }),
    )

    print(f"  提问: {result.prompt[:30]}")
    print(f"  维度分: {result.scores}")
    print(f"  加权分: {result.weighted_score:.2f}")
    print(f"  评语: {result.comment[:30]}")
    print(f"  错误: {result.error}")

    assert result.error is None, f"不应有解析错误: {result.error}"
    assert result.scores["accuracy"] == 8
    assert result.scores["safety"] == 10

    # 加权分 = (8-1)/9*0.30 + (7-1)/9*0.20 + (6-1)/9*0.10 + (9-1)/9*0.15 + (8-1)/9*0.15 + (10-1)/9*0.10
    # accuracy: 7/9*0.30 = 0.2333
    # completeness: 6/9*0.20 = 0.1333
    # conciseness: 5/9*0.10 = 0.0556
    # relevance: 8/9*0.15 = 0.1333
    # helpfulness: 7/9*0.15 = 0.1167
    # safety: 9/9*0.10 = 0.1000
    # sum = 0.2333+0.1333+0.0556+0.1333+0.1167+0.1000 = 0.7722
    expected = round(7/9*0.30 + 6/9*0.20 + 5/9*0.10 + 8/9*0.15 + 7/9*0.15 + 9/9*0.10, 2)
    print(f"  期望加权分: {expected}")
    assert abs(result.weighted_score - expected) < 0.01, \
        f"加权分偏差过大: {result.weighted_score} vs {expected}"

    print("\n[OK] Test 1 全部通过")


# ---------------------------------------------------------------------------
# Test 2：JSON 在代码块中
# ---------------------------------------------------------------------------

def test_json_in_codeblock():
    print_separator("Test 2: JSON 在代码块中")

    judge = LLMJudge()

    # 模拟 LLM 输出 markdown 代码块包裹的 JSON
    raw = """根据分析，我给出以下评分：
```json
{
  "accuracy": 10,
  "completeness": 9,
  "conciseness": 8,
  "relevance": 10,
  "helpfulness": 9,
  "safety": 10,
  "overall_comment": "完美回复，无懈可击。"
}
```
总结：这是非常好的回复。"""

    result = judge.score_offline(
        prompt="1+1=？",
        response="1+1=2。",
        judge_raw_output=raw,
    )

    print(f"  维度分: {result.scores}")
    print(f"  加权分: {result.weighted_score:.2f}")

    assert result.error is None, f"应有成功解析: {result.error}"
    assert result.scores["accuracy"] == 10
    assert result.scores["conciseness"] == 8
    assert "无懈可击" in result.comment

    print("\n[OK] Test 2 全部通过")


# ---------------------------------------------------------------------------
# Test 3：解析失败（非 JSON）
# ---------------------------------------------------------------------------

def test_parse_failure():
    print_separator("Test 3: 解析失败 - 默认分 + 错误标记")

    judge = LLMJudge()

    # 评委输出不是 JSON
    raw = "这个回复质量很好。我不知道怎么输出JSON，就这样吧。"

    result = judge.score_offline(
        prompt="你好",
        response="你好！欢迎提问。",
        judge_raw_output=raw,
    )

    print(f"  维度分: {result.scores}")
    print(f"  加权分: {result.weighted_score:.2f}")
    print(f"  错误: {result.error}")

    # 应该解析失败，返回默认 5 分
    assert result.error is not None, "解析失败应有错误信息"
    for dim, score in result.scores.items():
        assert score == 5.0, f"默认分应为 5, {dim}={score}"

    # 加权分 = (5-1)/9 * (0.30+0.20+0.10+0.15+0.15+0.10) = 4/9 * 1.0 = 0.4444
    expected = round(4/9, 2)
    assert abs(result.weighted_score - expected) < 0.01, \
        f"默认加权分应为 {expected}, 实际={result.weighted_score}"

    print("\n[OK] Test 3 全部通过")


# ---------------------------------------------------------------------------
# Test 4：A/B 对比
# ---------------------------------------------------------------------------

def test_ab_compare():
    print_separator("Test 4: A/B 对比")

    judge = LLMJudge(api_func=_api_stub)  # 使用模拟 API

    result = judge.ab_compare(
        prompt="What is Python?",
        response_a="Python is a programming language.",
        response_b="Python is a high-level, interpreted programming language created by Guido van Rossum.",
    )

    report = result.report()
    print(report)

    # result_b 更长更完整，应该分数更高或相当
    print(f"\n  胜者: {result.winner} (分差: {result.delta:.2f})")
    print(f"  各维度赢家: {result.dimensions_winner()}")

    # A/B 对比返回的 result_a 和 result_b 应有数据
    assert result.result_a is not None
    assert result.result_b is not None
    assert result.winner in ("A", "B")
    assert result.delta >= 0

    print("\n[OK] Test 4 全部通过")


# ---------------------------------------------------------------------------
# Test 5：批量评分
# ---------------------------------------------------------------------------

def test_batch_scoring():
    print_separator("Test 5: 批量评分（离线模式）")

    judge = LLMJudge()

    cases = [
        {
            "prompt": "Python 的特点？",
            "response": "Python 简单易学，是解释型语言。",
            "judge_raw": json.dumps({
                "accuracy": 9, "completeness": 7, "conciseness": 8,
                "relevance": 9, "helpfulness": 8, "safety": 10,
                "overall_comment": "准确但可以更完整。",
            }),
        },
        {
            "prompt": "Java 是什么？",
            "response": "Java 是一种编程语言。",
            "judge_raw": json.dumps({
                "accuracy": 8, "completeness": 6, "conciseness": 9,
                "relevance": 8, "helpfulness": 7, "safety": 10,
                "overall_comment": "简洁但不够详细。",
            }),
        },
        {
            "prompt": "TCP/IP 协议",
            "response": "TCP/IP 是互联网的基础协议。",
            "judge_raw": json.dumps({
                "accuracy": 7, "completeness": 5, "conciseness": 7,
                "relevance": 8, "helpfulness": 6, "safety": 10,
                "overall_comment": "正确但过于简略。",
            }),
        },
    ]

    results = []
    for case in cases:
        r = judge.score_offline(
            prompt=case["prompt"],
            response=case["response"],
            judge_raw_output=case["judge_raw"],
        )
        results.append(r)

    batch_report = BatchJudgeReport(results, judge.dimensions)

    summary = batch_report.summary()
    print(f"  总用例: {summary['total']}")
    print(f"  平均分: {summary['avg_score']}")

    for i, r in enumerate(results):
        print(f"  用例 {i+1}: score={r.weighted_score:.2f}, "
              f"best={max(r.scores.values())}, worst={min(r.scores.values())}")

    assert summary["total"] == 3
    assert summary["avg_score"] > 0

    print("\n[OK] Test 5 全部通过")


# ---------------------------------------------------------------------------
# Test 6：Schema 验证（字段存在性 + 值范围）
# ---------------------------------------------------------------------------

def test_schema_validation():
    print_separator("Test 6: Schema 验证（字段检查 + 值范围）")

    from utils.d9_llm_judge import DEFAULT_DIMENSIONS

    # 模拟 JudgeResult 和手动验证规则
    # 验证思路：JudgeResult 的 scores dict 应该满足
    #   - 所有维度都有分
    #   - 每个分在 1-10 范围内
    #   - weighted_score 在 0.0-1.0 范围内

    test_results = []

    # 6a: 正常评分
    result_ok = JudgeResult(
        prompt="测试",
        response="OK",
        scores={"accuracy": 9.0, "completeness": 8.0, "conciseness": 7.0,
                "relevance": 9.0, "helpfulness": 8.0, "safety": 10.0},
        weighted_score=0.72,
        comment="好",
    )
    test_results.append(("6a-正常", True, result_ok))

    # 6b: 边界值 1-10
    result_edge = JudgeResult(
        prompt="边界",
        response="边缘",
        scores={"accuracy": 1.0, "completeness": 10.0, "conciseness": 5.0,
                "relevance": 5.0, "helpfulness": 5.0, "safety": 5.0},
        weighted_score=0.0,
        comment="边界",
    )
    test_results.append(("6b-边界值", True, result_edge))

    # 6c: 加权分范围 0-1
    result_weight = JudgeResult(
        prompt="满分",
        response="满分回复",
        scores={"accuracy": 10.0, "completeness": 10.0, "conciseness": 10.0,
                "relevance": 10.0, "helpfulness": 10.0, "safety": 10.0},
        weighted_score=1.0,
        comment="满分",
    )
    test_results.append(("6c-满分", True, result_weight))

    # 6d: to_dict 格式正确
    d = result_ok.to_dict()
    assert isinstance(d, dict), "to_dict 应返回 dict"
    assert "weighted_score" in d
    assert "scores" in d
    assert "prompt" in d
    assert "comment" in d
    print(f"  to_dict 输出: {d}")

    # 验证所有结果
    for name, expected, result in test_results:
        # 验证所有维度都有分
        for dim in DEFAULT_DIMENSIONS:
            assert dim in result.scores, f"{name}: 缺少维度 {dim}"
        # 验证分数范围
        for dim, val in result.scores.items():
            assert 1.0 <= val <= 10.0, f"{name}: {dim}={val} 超出1-10范围"
        # 验证加权分范围
        assert 0.0 <= result.weighted_score <= 1.0, \
            f"{name}: weighted_score={result.weighted_score} 超出0-1范围"
        status = "OK" if expected else "!!"
        print(f"  [{status}] {name} 验证通过")

    print("\n[OK] Test 6 全部通过")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("-- Day 9 - [第2周Day4] LLM-as-Judge + Schema 验证器测试 --")
    print("=" * 50)

    test_offline_scoring()
    test_json_in_codeblock()
    test_parse_failure()
    test_ab_compare()
    test_batch_scoring()
    test_schema_validation()

    print(f"\n{'=' * 50}")
    print("Day 9 全部测试通过！")
    print(f"{'=' * 50}")
    print(f"\n今天学到：")
    print(f"  - LLM-as-Judge 评分引擎（6维加权评估）")
    print(f"  - 评委输出解析（直接 JSON / 代码块 / 异常降级）")
    print(f"  - A/B 对比（同一 prompt 两条回复横向比较）")
    print(f"  - 批量评分 + 报告生成")
    print(f"  - Schema 验证（字段存在性、值范围、类型检查）")
    print(f"\n面试准备：")
    print(f'  "LLM-as-Judge 是目前业界做 AI 回复质量评估的主流方案。')
    print(f'   我设计了一套系统，用 DeepSeek 评 DeepSeek，')
    print(f'   6 个评分维度 + A/B 对比 + 批量评分。')
    print(f'   虽然自评有偏差，但在没有人工标注的情况下')
    print(f'   是性价比最高的方案。"')
