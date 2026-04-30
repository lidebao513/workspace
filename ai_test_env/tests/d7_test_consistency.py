"""
Day 7（第 2 周 Day 2）— 回复一致性检查器测试

测试内容：
1. 完全一致（理想的 temperature=0）
2. 部分一致（temperature=0.5）
3. 完全不一致（temperature=2.0 极端）
4. 一致性等级标签检查
5. 温度曲线对比
6. 边界情况（2 次、大量回复、相同回复不同长度）
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.d7_consistency_checker import (
    ConsistencyChecker, get_consistency_level,
    ConsistencyResult
)


def print_separator(title):
    print(f"\n{'=' * 50}")
    print(f"[{title}]")
    print(f"{'=' * 50}")


# ---------------------------------------------------------------------------
# Test 1：完全一致的回复
# ---------------------------------------------------------------------------

def test_perfect_consistency():
    print_separator("Test 1: 完全一致的回复")

    checker = ConsistencyChecker()

    # 5 次回复完全相同
    responses = [
        "Python 是一种高级编程语言。",
    ] * 5

    result = checker.analyze_responses(
        prompt="Python 是什么？",
        responses=responses,
        temperature=0.0,
    )

    print(f"  回复次数: {result.n_runs}")
    print(f"  unique 数: {result.unique_count}")
    print(f"  unique 比例: {result.unique_ratio}")
    print(f"  一致性评分: {result.consistency_score}")
    print(f"  一致性等级: {result.level}")

    assert result.unique_count == 1, "完全相同应该只有 1 个 unique"
    # 5 次完全相同: unique_ratio=0.2, score = (1-0.2)*0.6 + 1.0*0.4 = 0.48+0.4=0.88
    assert result.consistency_score >= 0.80, f"完全一致评分应 >= 0.80, 实际={result.consistency_score}"
    print(f"  [分析] unique_ratio={result.unique_ratio}, score=(1-{result.unique_ratio})*0.6 + 1.0*0.4 = {result.consistency_score}")

    print("\n[OK] Test 1 全部通过")


# ---------------------------------------------------------------------------
# Test 2：部分一致的回复
# ---------------------------------------------------------------------------

def test_partial_consistency():
    print_separator("Test 2: 部分一致的回复")

    checker = ConsistencyChecker()

    # 5 次回复，有部分相同
    responses = [
        "Python 是一种编程语言。",
        "Python 是一种编程语言。",
        "Python 是一种高级编程语言。",
        "Python 是一种脚本语言。",
        "Python 是一种高级编程语言。",
    ]

    result = checker.analyze_responses(
        prompt="Python 是什么？",
        responses=responses,
        temperature=0.5,
    )

    print(f"  回复次数: {result.n_runs}")
    print(f"  unique 数: {result.unique_count}")
    print(f"  unique 比例: {result.unique_ratio}")
    print(f"  一致性评分: {result.consistency_score}")
    print(f"  一致性等级: {result.level}")

    # 应该有 3 个 unique（"编程语言"、"高级编程语言"、"脚本语言"）
    assert result.unique_count == 3, f"同一回复应该有 3 种变体, 实际={result.unique_count}"
    # 评分应该在中间范围
    assert 0.3 < result.consistency_score < 0.95, f"部分一致评分应在中间范围, 实际={result.consistency_score}"

    print("\n[OK] Test 2 全部通过")


# ---------------------------------------------------------------------------
# Test 3：完全不一致的回复
# ---------------------------------------------------------------------------

def test_low_consistency():
    print_separator("Test 3: 完全不一致的回复")

    checker = ConsistencyChecker()

    # 5 次完全不同的回复
    responses = [
        "苹果是一种水果。",
        "今天天气真好。",
        "Python 是编程语言。",
        "上海是中国的一个城市。",
        "我喜欢看电影。",
    ]

    result = checker.analyze_responses(
        prompt="随便说点什么",
        responses=responses,
        temperature=2.0,
    )

    print(f"  回复次数: {result.n_runs}")
    print(f"  unique 数: {result.unique_count}")
    print(f"  unique 比例: {result.unique_ratio}")
    print(f"  一致性评分: {result.consistency_score}")
    print(f"  一致性等级: {result.level}")

    assert result.unique_count == 5, "完全不同应该 5 个 unique"
    assert result.consistency_score < 0.5, f"完全不一致评分应很低, 实际={result.consistency_score}"

    print("\n[OK] Test 3 全部通过")


# ---------------------------------------------------------------------------
# Test 4：一致性等级标签检查
# ---------------------------------------------------------------------------

def test_level_labels():
    print_separator("Test 4: 一致性等级标签检查")

    test_cases = [
        (1.00, "极高"),
        (0.92, "极高"),
        (0.80, "高"),
        (0.75, "高"),
        (0.60, "中等"),
        (0.50, "中等"),
        (0.35, "低"),
        (0.10, "极低"),
        (0.00, "极低"),
    ]

    for score, expected_label in test_cases:
        actual = get_consistency_level(score)
        status = "[OK]" if actual == expected_label else "[!!]"
        print(f"  {status} score={score:.2f} → {actual} (期望: {expected_label})")
        assert actual == expected_label, f"score={score}: 期望={expected_label}, 实际={actual}"

    print("\n[OK] Test 4 全部通过")


# ---------------------------------------------------------------------------
# Test 5：温度曲线对比
# ---------------------------------------------------------------------------

def test_temperature_curve():
    print_separator("Test 5: 温度曲线对比（离线模拟）")

    checker = ConsistencyChecker()

    # 模拟不同 temperature 下的一致性表现
    # temperature 越高，回复差异越大
    curve_data = {
        0.0: [
            "Python 是一种高级编程语言。",
            "Python 是一种高级编程语言。",
            "Python 是一种高级编程语言。",
            "Python 是一种高级编程语言。",
            "Python 是一种高级编程语言。",
        ],
        0.5: [
            "Python 是一种编程语言。",
            "Python 是一种高级编程语言。",
            "Python 是一种编程语言。",
            "Python 是解释型语言。",
            "Python 是一种高级编程语言。",
        ],
        1.0: [
            "Python 是一种编程语言。",
            "Python 是解释型语言.",
            "Python 是一门动态语言。",
            "Python 很流行。",
            "Python 是脚本语言。",
        ],
        2.0: [
            "苹果很好吃。",
            "Java 也不错。",
            "上海是直辖市。",
            "编程很有趣。",
            "今天是星期三。",
        ],
    }

    results = []
    for temp, responses in curve_data.items():
        r = checker.analyze_responses(
            prompt="Python 是什么？",
            responses=responses,
            temperature=temp,
        )
        results.append(r)
        print(f"  temp={temp:.1f}: score={r.consistency_score:.2f}, "
              f"unique={r.unique_count}/{r.n_runs}, "
              f"level={r.level}")

    # 验证一致性随温度上升而下降
    scores = [r.consistency_score for r in results]
    assert scores[0] > scores[2], f"temp=0 的一致性应高于 temp=1.0"
    assert scores[2] > scores[3], f"temp=1.0 的一致性应高于 temp=2.0"
    print(f"\n  一致性下降趋势验证: {[f'{s:.2f}' for s in scores]} （分数递减）")

    # 验证 compare_consistency
    comparison = checker.compare_consistency(results)
    print(f"\n  最佳温度: {comparison['best_temperature']} (score={comparison['best_score']})")
    print(f"  建议: {comparison['recommendation']}")

    print("\n[OK] Test 5 全部通过")


# ---------------------------------------------------------------------------
# Test 6：边界情况
# ---------------------------------------------------------------------------

def test_edge_cases():
    print_separator("Test 6: 边界情况")

    checker = ConsistencyChecker()

    # 6a. 最少 2 次回复
    r1 = checker.analyze_responses(
        prompt="hi",
        responses=["Hello!", "Hello!"],
        temperature=0.0,
    )
    print(f"  最少 2 次: n={r1.n_runs}, score={r1.consistency_score}")
    assert r1.consistency_score >= 0.6, f"n={r1.n_runs}, score={r1.consistency_score}"

    # 6b. 大量回复（10 次，模拟更多数据）
    responses = [
        "这是第 %d 次回复。" % (i % 3) for i in range(10)
    ]
    r2 = checker.analyze_responses(
        prompt="测试大量回复",
        responses=responses,
        temperature=0.5,
    )
    print(f"  大量回复: n={r2.n_runs}, unique={r2.unique_count}, score={r2.consistency_score}")
    assert r2.n_runs == 10

    # 6c. 附带 Token 和延迟数据
    r3 = checker.analyze_responses(
        prompt="带指标",
        responses=["A", "A", "B", "A"],
        temperature=0.3,
        tokens_used=[50, 55, 60, 48],
        latencies_ms=[1200, 1350, 1500, 1100],
    )
    print(f"  附带指标: avg_tokens={r3.avg_tokens:.0f}, avg_latency={r3.avg_latency_ms:.0f}ms")
    assert r3.avg_tokens > 0
    assert r3.avg_latency_ms > 1000

    # 6d. 检查 history
    history = checker.history()
    print(f"  检查历史记录数: {len(history)}")
    assert len(history) >= 3  # 至少包含 r1, r2, r3

    print("\n[OK] Test 6 全部通过")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("-- Day 7 - [第2周Day2] 回复一致性检查器测试 --")
    print("=" * 50)

    test_perfect_consistency()
    test_partial_consistency()
    test_low_consistency()
    test_level_labels()
    test_temperature_curve()
    test_edge_cases()

    print(f"\n{'=' * 50}")
    print("Day 7 全部测试通过！")
    print(f"{'=' * 50}")
    print(f"\n今天学到：")
    print(f"  - 回复一致性评估（多轮重复提问）")
    print(f"  - 一致性评分算法（unique_ratio + 变异系数）")
    print(f"  - 五个一致性等级标签（极高→极低）")
    print(f"  - Temperature 对一致性的影响曲线")
    print(f"  - 最佳温度推荐算法")
    print(f"\n面试准备：")
    print(f'  "一致性测试是我发现的最大隐患之一。temperature=0')
    print(f'   时回复几乎完全一致，但调到 0.8 后方差大到不可接受。')
    print(f'   我们通过曲线测试把金融场景锁定在 0.3 以下，')
    print(f'   聊天场景用 0.7，用数据说话。"')
