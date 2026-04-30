"""
Day 8（第 2 周 Day 3）— 截断检测 + Max Tokens 调优测试

测试内容：
1. 无截断（全部 stop）
2. 全部截断（全部 length）
3. 混合场景（stop + length + content_filter）
4. 截断等级标签检查
5. max_tokens 推荐算法
6. 边界情况（空数据、单条记录）
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.d8_truncation_analyzer import (
    TruncationAnalyzer, TruncationReport,
    FinishReason, get_truncation_level
)


def print_separator(title):
    print(f"\n{'=' * 50}")
    print(f"[{title}]")
    print(f"{'=' * 50}")


# ---------------------------------------------------------------------------
# Test 1：无截断
# ---------------------------------------------------------------------------

def test_no_truncation():
    print_separator("Test 1: 无截断（全部 stop）")

    analyzer = TruncationAnalyzer()

    # 10 条记录，全部 stop
    records = []
    for i in range(10):
        records.append({
            "prompt": f"写一首{i+1}句的诗",
            "response_len": 50 + i * 10,
            "finish_reason": "stop",
            "max_tokens": 1024,
            "total_tokens": 100 + i * 20,
            "prompt_tokens": 50,
            "completion_tokens": 50 + i * 20,
        })

    analyzer.record_batch(records)
    report = analyzer.analyze()

    print(f"  总请求: {report.total}")
    print(f"  截断数: {report.truncated}")
    print(f"  截断率: {report.truncation_rate:.1%}")
    print(f"  等级:   {report.level_info['label']}")

    assert report.truncated == 0
    assert report.truncation_rate == 0.0
    assert report.level_info["label"] == "优秀"

    # 曲线也有数据
    curve = analyzer.max_tokens_curve()
    print(f"  曲线点: {len(curve)}")
    assert len(curve) >= 1

    print("\n[OK] Test 1 全部通过")


# ---------------------------------------------------------------------------
# Test 2：全部截断
# ---------------------------------------------------------------------------

def test_all_truncated():
    print_separator("Test 2: 全部截断（全部 length）")

    analyzer = TruncationAnalyzer()

    # 5 条记录，全部被截断
    records = []
    for i in range(5):
        records.append({
            "prompt": f"写一篇长文章{i+1}",
            "response_len": 1024,
            "finish_reason": "length",
            "max_tokens": 1024,
            "total_tokens": 1070,
            "prompt_tokens": 50,
            "completion_tokens": 1020,
        })

    analyzer.record_batch(records)
    report = analyzer.analyze()

    print(f"  总请求: {report.total}")
    print(f"  截断数: {report.truncated}")
    print(f"  截断率: {report.truncation_rate:.1%}")
    print(f"  等级:   {report.level_info['label']}")
    print(f"  建议:   max_tokens={report.recommendation['current']} → {report.recommendation['recommended']}")

    assert report.truncated == 5
    assert report.truncation_rate == 1.0
    assert report.level_info["label"] == "严重"
    assert report.recommendation["urgency"] == "critical"

    print("\n[OK] Test 2 全部通过")


# ---------------------------------------------------------------------------
# Test 3：混合场景（stop + length + content_filter）
# ---------------------------------------------------------------------------

def test_mixed():
    print_separator("Test 3: 混合场景")

    analyzer = TruncationAnalyzer()

    records = [
        # 正常回复 8 条
        {"prompt": "你好", "response_len": 50, "finish_reason": "stop",
         "max_tokens": 1024, "total_tokens": 100},
        {"prompt": "介绍 Python", "response_len": 200, "finish_reason": "stop",
         "max_tokens": 1024, "total_tokens": 250},
        {"prompt": "写首诗", "response_len": 100, "finish_reason": "stop",
         "max_tokens": 1024, "total_tokens": 150},
        {"prompt": "今天天气", "response_len": 60, "finish_reason": "stop",
         "max_tokens": 1024, "total_tokens": 110},
        {"prompt": "推荐电影", "response_len": 300, "finish_reason": "stop",
         "max_tokens": 1024, "total_tokens": 350},
        {"prompt": "讲个故事", "response_len": 800, "finish_reason": "stop",
         "max_tokens": 1024, "total_tokens": 850},
        {"prompt": "翻译文章", "response_len": 1000, "finish_reason": "stop",
         "max_tokens": 2048, "total_tokens": 1050},
        {"prompt": "写代码", "response_len": 1500, "finish_reason": "stop",
         "max_tokens": 2048, "total_tokens": 1550},
        # 被截断的 3 条
        {"prompt": "写长文", "response_len": 1024, "finish_reason": "length",
         "max_tokens": 1024, "total_tokens": 1070},
        {"prompt": "详细说明", "response_len": 1024, "finish_reason": "length",
         "max_tokens": 1024, "total_tokens": 1070},
        {"prompt": "不断输出", "response_len": 1024, "finish_reason": "length",
         "max_tokens": 1024, "total_tokens": 1070},
    ]

    analyzer.record_batch(records)
    report = analyzer.analyze()

    print(f"  总请求: {report.total}")
    print(f"  stop:   {report.stop_count}")
    print(f"  length: {report.length_count}")
    print(f"  截断率: {report.truncation_rate:.1%}")
    print(f"  等级:   {report.level_info['label']}")

    # 3/11 = 27.3% -> 严重
    assert report.total == 11
    assert report.stop_count == 8
    assert report.length_count == 3
    assert report.truncation_rate == 3/11

    print(f"\n  完整回复（未截断）: 平均长度={report.avg_full_len:.0f}, 最大={report.max_full_len:.0f}")
    print(f"  被截断回复: 平均长度={report.avg_truncated_len:.0f}")

    # 完整的最大回复是 1500，推荐 = min(1500*1.2, 1024*4) = min(1800, 4096) = 1800
    rec = report.recommendation
    print(f"  max_tokens 建议: {rec['current']} → {rec['recommended']} (原因: {rec['reason']})")
    assert rec["recommended"] >= rec["current"], "推荐值不应低于当前值"

    # 查看曲线
    curve = analyzer.max_tokens_curve()
    print(f"  max_tokens 曲线点: {len(curve)}")
    for c in curve:
        print(f"    max_tokens={c['max_tokens']}: 截断率={c['rate']:.1%} ({c['truncated']}/{c['total']})")

    print("\n[OK] Test 3 全部通过")


# ---------------------------------------------------------------------------
# Test 4：截断等级标签
# ---------------------------------------------------------------------------

def test_level_labels():
    print_separator("Test 4: 截断等级标签检查")

    # 截断率 → 等级映射
    test_cases = [
        (0.00, "优秀"),
        (0.01, "优秀"),
        (0.03, "良好"),
        (0.03, "良好"),
        (0.05, "一般"),
        (0.08, "一般"),
        (0.10, "差"),
        (0.15, "差"),
        (0.20, "严重"),
        (0.50, "严重"),
        (1.00, "严重"),
    ]

    for rate, expected_label in test_cases:
        info = get_truncation_level(rate)
        status = "[OK]" if info["label"] == expected_label else "[!!]"
        print(f"  {status} 截断率={rate:.0%} → {info['label']} (期望: {expected_label})")
        assert info["label"] == expected_label, f"rate={rate}: 期望={expected_label}, 实际={info['label']}"

    print("\n[OK] Test 4 全部通过")


# ---------------------------------------------------------------------------
# Test 5：推荐算法边界
# ---------------------------------------------------------------------------

def test_recommendation_edge():
    print_separator("Test 5: 推荐算法边界")

    # 5a：截断率极低（不推荐修改）
    analyzer1 = TruncationAnalyzer()
    analyzer1.record_batch([
        {"prompt": "A", "response_len": 100, "finish_reason": "stop",
         "max_tokens": 1024, "total_tokens": 150} for _ in range(20)
    ])
    report1 = analyzer1.analyze()
    rec1 = report1.recommendation
    print(f"  低截断: rec='{rec1['recommended']}' (原因: {rec1['reason']})")
    assert rec1["urgency"] == "none"

    # 5b：中等截断（推荐适度增加）
    analyzer2 = TruncationAnalyzer()
    analyzer2.record_batch([
        {"prompt": "A", "response_len": 500, "finish_reason": "stop",
         "max_tokens": 512, "total_tokens": 550} for _ in range(9)
    ] + [
        {"prompt": "B", "response_len": 512, "finish_reason": "length",
         "max_tokens": 512, "total_tokens": 560} for _ in range(1)
    ])
    report2 = analyzer2.analyze()
    rec2 = report2.recommendation
    print(f"  中等截断: {rec2['current']} → {rec2['recommended']} (紧急等级: {rec2['urgency']})")
    assert rec2["urgency"] in ("medium", "high")

    # 5c：截断率曲线中有多种 max_tokens 配置
    analyzer3 = TruncationAnalyzer()
    analyzer3.record_batch([
        {"prompt": "A", "response_len": 100, "finish_reason": "stop",
         "max_tokens": 256, "total_tokens": 150},
        {"prompt": "B", "response_len": 256, "finish_reason": "length",
         "max_tokens": 256, "total_tokens": 300},
        {"prompt": "C", "response_len": 200, "finish_reason": "stop",
         "max_tokens": 512, "total_tokens": 250},
        {"prompt": "D", "response_len": 512, "finish_reason": "length",
         "max_tokens": 512, "total_tokens": 550},
        {"prompt": "E", "response_len": 500, "finish_reason": "stop",
         "max_tokens": 1024, "total_tokens": 550},
        {"prompt": "F", "response_len": 800, "finish_reason": "stop",
         "max_tokens": 1024, "total_tokens": 850},
    ])
    curve = analyzer3.max_tokens_curve()
    print(f"  多档 max_tokens 曲线:")
    for c in curve:
        print(f"    max_tokens={c['max_tokens']}: {c['truncated']}/{c['total']} = {c['rate']:.0%}")
    assert len(curve) == 3, f"应有 3 档配置, 实际={len(curve)}"

    print("\n[OK] Test 5 全部通过")


# ---------------------------------------------------------------------------
# Test 6：边界情况
# ---------------------------------------------------------------------------

def test_edge_cases():
    print_separator("Test 6: 边界情况")

    # 6a：空数据（expect error）
    analyzer = TruncationAnalyzer()
    try:
        analyzer.analyze()
        print("  [!!] 空数据应该报错")
        assert False, "空数据应报错"
    except ValueError as e:
        print(f"  [OK] 空数据正确报错: {e}")

    # 6b：单条数据
    analyzer.record(
        prompt="测试",
        response_len=100,
        finish_reason="stop",
        max_tokens=256,
        total_tokens=150,
    )
    report = analyzer.analyze()
    print(f"  单条数据: total={report.total}, stop={report.stop_count}")
    assert report.total == 1
    assert report.truncation_rate == 0.0

    # 6c：content_filter 也被计为截断
    analyzer2 = TruncationAnalyzer()
    analyzer2.record(
        prompt="坏内容",
        response_len=0,
        finish_reason="content_filter",
        max_tokens=1024,
        total_tokens=50,
    )
    r2 = analyzer2.analyze()
    print(f"  content_filter: truncated={r2.truncated}, rate={r2.truncation_rate:.0%}")
    assert r2.truncated == 1

    # 6d：reset
    analyzer2.reset()
    assert analyzer2.total_records == 0
    print("  [OK] reset 后清零")

    print("\n[OK] Test 6 全部通过")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("-- Day 8 - [第2周Day3] 截断检测 + Max Tokens 调优测试 --")
    print("=" * 50)

    test_no_truncation()
    test_all_truncated()
    test_mixed()
    test_level_labels()
    test_recommendation_edge()
    test_edge_cases()

    print(f"\n{'=' * 50}")
    print("Day 8 全部测试通过！")
    print(f"{'=' * 50}")
    print(f"\n今天学到：")
    print(f"  - 截断检测（finish_reason 分析）")
    print(f"  - 截断率统计与等级划分")
    print(f"  - max_tokens 推荐算法")
    print(f"  - 费用与截断的平衡")
    print(f"\n面试准备：")
    print(f'  "我做过截断分析。生产环境 30% 的请求被截断，')
    print(f'   发现是 max_tokens 设得太低。调到 1024 后')
    print(f'   截断率降到 2%。费用只增加了 15%，但截断')
    print(f'   率降了 93%。用数据说话很重要。"')
