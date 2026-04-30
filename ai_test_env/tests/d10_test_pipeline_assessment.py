"""
Day 10（第 2 周 Day 5）— Week 2 收尾：统一质量评估流水线测试

测试内容：
1. 离线全量评估（四个步骤整合）
2. 综合评分计算验证
3. 版本对比（A vs B）
4. 自动生成改进建议
5. 报告格式化输出
6. 边界情况（空输入、单条数据、极端分数）
"""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.d10_pipeline_assessment import (
    AssessmentPipeline, QualityReport,
    compute_overall_score, compute_overall_grade,
    format_report_console, format_version_comparison,
)


def print_separator(title):
    print(f"\n{'=' * 50}")
    print(f"[{title}]")
    print(f"{'=' * 50}")


# ---------------------------------------------------------------------------
# 辅助：构造高质量的测试数据
# ---------------------------------------------------------------------------

def _make_good_quality_cases():
    """高质量回复的质检用例"""
    return [
        {"prompt": "Python 的特点", "response": "Python 是一种高级编程语言，支持面向对象编程。",
         "must_contain": ["高级", "编程语言", "面向对象"],
         "must_not_contain": ["Java", "编译型"]},
        {"prompt": "解释型 vs 编译型", "response": "解释型语言逐行执行，编译型语言先编译再执行。",
         "must_contain": ["解释型", "编译型", "逐行"],
         "must_not_contain": ["Java"]},
        {"prompt": "什么是 API", "response": "API 是应用程序编程接口，用于系统间通信。",
         "must_contain": ["应用程序", "接口", "通信"],
         "must_not_contain": ["编程语言"]},
    ]


def _make_bad_quality_cases():
    """低质量回复的质检用例"""
    return [
        {"prompt": "Python 的特点", "response": "Python 是一种语言。",
         "must_contain": ["高级", "面向对象", "动态类型"],
         "must_not_contain": ["Java", "JavaScript"]},
        {"prompt": "解释型 vs 编译型", "response": "我不太确定这个问题的答案。",
         "must_contain": ["解释型", "编译型", "区别"],
         "must_not_contain": ["C++"]},
    ]


def _make_consistency_cases(good: bool = True):
    """一致性测试用例"""
    if good:
        return [
            {"prompt": "Python 是什么？", "responses": [
                "Python 是一种高级编程语言。",
                "Python 是一种高级编程语言。",
                "Python 是一种高级编程语言。",
                "Python 是一种高级编程语言。",
                "Python 是一种高级编程语言。",
            ], "temperature": 0.0},
            {"prompt": "什么是 AI？", "responses": [
                "AI 是人工智能的简称。",
                "AI 是人工智能的简称。",
                "AI 是人工智能。",
                "AI 即人工智能。",
                "AI 是人工智能。",
            ], "temperature": 0.3},
        ]
    else:
        return [
            {"prompt": "Python 是什么？", "responses": [
                "Python 是一种语言。",
                "今天天气很好。",
                "苹果是水果。",
                "上海是城市。",
                "编程很有趣。",
            ], "temperature": 2.0},
        ]


def _make_truncation_records(good: bool = True):
    """截断分析记录"""
    if good:
        return [
            {"prompt": f"写诗{i}", "response_len": 50 + i * 20,
             "finish_reason": "stop", "max_tokens": 1024, "total_tokens": 100 + i * 20}
            for i in range(10)
        ]
    else:
        # 50% 截断率
        records = []
        for i in range(5):
            records.append({"prompt": f"正常{i}", "response_len": 200,
                            "finish_reason": "stop", "max_tokens": 1024, "total_tokens": 250})
            records.append({"prompt": f"截断{i}", "response_len": 1024,
                            "finish_reason": "length", "max_tokens": 1024, "total_tokens": 1070})
        return records


def _make_judge_cases(good: bool = True):
    """LLM 评分用例"""
    if good:
        return [
            {"prompt": "Python 的特点", "response": "Python 是一种高级解释型语言。",
             "judge_raw": json.dumps({
                 "accuracy": 9, "completeness": 8, "conciseness": 8,
                 "relevance": 9, "helpfulness": 8, "safety": 10,
                 "overall_comment": "回复准确完整。",
             })},
            {"prompt": "1+1=？", "response": "1+1=2。",
             "judge_raw": json.dumps({
                 "accuracy": 10, "completeness": 10, "conciseness": 10,
                 "relevance": 10, "helpfulness": 9, "safety": 10,
                 "overall_comment": "完美正确。",
             })},
            {"prompt": "什么是 API", "response": "API 是编程接口。",
             "judge_raw": json.dumps({
                 "accuracy": 8, "completeness": 7, "conciseness": 9,
                 "relevance": 9, "helpfulness": 8, "safety": 10,
                 "overall_comment": "简洁正确。",
             })},
        ]
    else:
        return [
            {"prompt": "Python 的特点", "response": "我不确定。",
             "judge_raw": json.dumps({
                 "accuracy": 3, "completeness": 2, "conciseness": 5,
                 "relevance": 4, "helpfulness": 2, "safety": 10,
                 "overall_comment": "回复无意义。",
             })},
            {"prompt": "2+2=？", "response": "等于5。",
             "judge_raw": json.dumps({
                 "accuracy": 1, "completeness": 2, "conciseness": 8,
                 "relevance": 3, "helpfulness": 1, "safety": 10,
                 "overall_comment": "答案错误。",
             })},
        ]


# ---------------------------------------------------------------------------
# Test 1：离线全量评估（高质量场景）
# ---------------------------------------------------------------------------

def test_full_offline_good():
    print_separator("Test 1: 离线全量评估（高质量场景）")

    pipeline = AssessmentPipeline()

    report = pipeline.run_offline(
        model_name="DeepSeek-v4",
        test_suite="high-quality-scenario",
        quality_cases=_make_good_quality_cases(),
        consistency_cases=_make_consistency_cases(good=True),
        truncation_records=_make_truncation_records(good=True),
        judge_cases=_make_judge_cases(good=True),
    )

    print(f"  模型: {report.model_name}")
    print(f"  用例数: {report.total_cases}")
    print(f"  Day6 质量分:     {report.quality_score:.2f}")
    print(f"  Day6 通过率:     {report.quality_pass_rate:.1f}%")
    print(f"  Day7 一致性分:   {report.consistency_score:.2f}")
    print(f"  Day7 等级:       {report.consistency_level}")
    print(f"  Day8 截断率:     {report.truncation_rate:.1%}")
    print(f"  Day8 等级:       {report.truncation_level}")
    print(f"  Day9 LLM 评分:   {report.judge_avg_score:.2f}")
    print(f"  ---")
    print(f"  综合评分:        {report.overall_score:.2f}")
    print(f"  综合等级:        {report.overall_grade}")
    print(f"  发现问题:        {len(report.issues)} 个")
    print(f"  改进建议:        {len(report.recommendations)} 条")

    # 高质量场景应该在 0.7 以上
    assert report.overall_score >= 0.7, \
        f"高质量场景综合分应 >= 0.7, 实际={report.overall_score}"
    assert report.quality_pass_rate >= 60.0, \
        f"通过率应 >= 60%, 实际={report.quality_pass_rate}%"
    assert report.truncation_rate == 0.0, "无截断记录"

    print("\n[OK] Test 1 全部通过")


# ---------------------------------------------------------------------------
# Test 2：离线全量评估（低质量场景）
# ---------------------------------------------------------------------------

def test_full_offline_bad():
    print_separator("Test 2: 离线全量评估（低质量场景）")

    pipeline = AssessmentPipeline()

    report = pipeline.run_offline(
        model_name="BadModel-v1",
        test_suite="low-quality",
        quality_cases=_make_bad_quality_cases(),
        consistency_cases=_make_consistency_cases(good=False),
        truncation_records=_make_truncation_records(good=False),
        judge_cases=_make_judge_cases(good=False),
    )

    print(f"  模型: {report.model_name}")
    print(f"  Day6 质量分:     {report.quality_score:.2f}")
    print(f"  Day7 一致性分:   {report.consistency_score:.2f}")
    print(f"  Day8 截断率:     {report.truncation_rate:.1%}")
    print(f"  Day9 LLM 评分:   {report.judge_avg_score:.2f}")
    print(f"  综合评分:        {report.overall_score:.2f}")
    print(f"  综合等级:        {report.overall_grade}")
    print(f"  发现问题:        {len(report.issues)} 个")

    # 低质量场景应该触发问题
    assert len(report.issues) >= 1, f"低质量场景应有 >=1 个问题, 实际={len(report.issues)}"
    assert len(report.recommendations) >= 1, f"应有改进建议"

    print("\n[OK] Test 2 全部通过")


# ---------------------------------------------------------------------------
# Test 3：综合评分计算验证
# ---------------------------------------------------------------------------

def test_overall_scoring():
    print_separator("Test 3: 综合评分计算验证")

    # 场景 3a：全满分
    s1 = compute_overall_score(
        quality=1.0, consistency=1.0, truncation=0.0, judge=1.0
    )
    print(f"  全满分: {s1:.2f}")
    assert s1 == 1.0, f"全满分应 = 1.0, 实际={s1}"

    # 场景 3b：全零分
    s2 = compute_overall_score(
        quality=0.0, consistency=0.0, truncation=1.0, judge=0.0
    )
    # quality=0*0.25 + consistency=0*0.15 + truncation=(1-1)*0.10 + judge=0*0.50
    print(f"  全零分: {s2:.2f}")
    assert s2 == 0.0, f"全零分应 = 0.0, 实际={s2}"

    # 场景 3c：中等水平
    s3 = compute_overall_score(
        quality=0.80, consistency=0.70, truncation=0.05, judge=0.75
    )
    # 0.80*0.25 + 0.70*0.15 + (1-0.05)*0.10 + 0.75*0.50
    # = 0.20 + 0.105 + 0.095 + 0.375 = 0.775
    expected = 0.80 * 0.25 + 0.70 * 0.15 + (1 - 0.05) * 0.10 + 0.75 * 0.50
    print(f"  中等水平: {s3:.2f} (期望 ≈ {expected:.2f})")
    assert abs(s3 - round(expected, 2)) < 0.01, \
        f"中等水平评分偏差过大: {s3} vs {expected}"

    # 等级映射
    assert compute_overall_grade(0.95) == "A+"
    assert compute_overall_grade(0.85) == "A"
    assert compute_overall_grade(0.75) == "B+"
    assert compute_overall_grade(0.65) == "B"
    assert compute_overall_grade(0.55) == "C"
    assert compute_overall_grade(0.40) == "D"

    print(f"  等级映射验证通过")
    print("\n[OK] Test 3 全部通过")


# ---------------------------------------------------------------------------
# Test 4：版本对比
# ---------------------------------------------------------------------------

def test_version_comparison():
    print_separator("Test 4: 版本对比（A vs B）")

    pipeline = AssessmentPipeline()

    # 版本 A（旧版，质量差一些）
    report_a = pipeline.run_offline(
        model_name="Model-v1.0",
        test_suite="version-compare",
        quality_cases=_make_bad_quality_cases(),
        consistency_cases=_make_consistency_cases(good=False),
        truncation_records=_make_truncation_records(good=False),
        judge_cases=_make_judge_cases(good=False),
    )

    # 版本 B（新版，质量明显提升）
    report_b = pipeline.run_offline(
        model_name="Model-v2.0",
        test_suite="version-compare",
        quality_cases=_make_good_quality_cases(),
        consistency_cases=_make_consistency_cases(good=True),
        truncation_records=_make_truncation_records(good=True),
        judge_cases=_make_judge_cases(good=True),
    )

    comparison = pipeline.compare_versions(report_a, report_b)

    print(f"  版本 A: {comparison['version_a']} -> {comparison['v1_grade']}")
    print(f"  版本 B: {comparison['version_b']} -> {comparison['v2_grade']}")
    print(f"  综合评分变化: {comparison['deltas']['overall']:+0.2f}")
    print(f"  新问题: {comparison['new_issues']:+d}")
    print(f"  状态: {comparison['status']}")

    # 新版应该优于旧版
    assert comparison["status"] == "PASS", \
        f"新版应优于旧版, status={comparison['status']}"
    assert comparison["deltas"]["overall"] > 0, \
        "新版综合分应高于旧版"

    # 验证内容
    compare_text = format_version_comparison(comparison)
    lines = compare_text.strip().split("\n")
    print(f"\n{compare_text[:300]}...")

    assert "PASS" in compare_text or "通过" in compare_text

    print("\n[OK] Test 4 全部通过")


# ---------------------------------------------------------------------------
# Test 5：报告格式化输出
# ---------------------------------------------------------------------------

def test_report_formatting():
    print_separator("Test 5: 报告格式化输出")

    pipeline = AssessmentPipeline()

    report = pipeline.run_offline(
        model_name="TestModel",
        test_suite="format-check",
        quality_cases=_make_good_quality_cases(),
        consistency_cases=_make_consistency_cases(good=True),
        truncation_records=_make_truncation_records(good=True),
        judge_cases=_make_judge_cases(good=True),
    )

    # 生成控制台报告
    formatted = format_report_console(report)
    lines = formatted.split("\n")

    print("  报告内容（前 20 行）：")
    for line in lines[:20]:
        print(f"  {line}")

    # 验证报告包含所有部分
    assert "综合质量评分" in formatted
    assert "质量检查分" in formatted
    assert "一致性评分" in formatted
    assert "截断率" in formatted
    assert "LLM 评分" in formatted
    assert "发现的问题" in formatted
    assert "改进建议" in formatted

    # to_dict
    d = report.to_dict()
    assert "overall_score" in d
    assert "overall_grade" in d
    assert "quality" in d
    assert "consistency" in d
    assert "truncation" in d
    assert "judge" in d
    print(f"\n  to_dict keys: {list(d.keys())}")

    print("\n[OK] Test 5 全部通过")


# ---------------------------------------------------------------------------
# Test 6：边界情况
# ---------------------------------------------------------------------------

def test_edge_cases():
    print_separator("Test 6: 边界情况")

    # 6a：空输入（所有数据传 None）
    pipeline = AssessmentPipeline()
    report_empty = pipeline.run_offline(
        model_name="empty-test",
    )
    print(f"  空输入综合分: {report_empty.overall_score}")
    assert report_empty.overall_score == 0.0, "空输入应得 0 分"
    assert report_empty.overall_grade == "D", f"空输入等级应为 D"
    assert len(report_empty.issues) == 0

    # 6b：仅传一个模块的数据
    pipeline2 = AssessmentPipeline()
    report_partial = pipeline2.run_offline(
        model_name="partial-test",
        quality_cases=_make_good_quality_cases(),
    )
    print(f"  仅质量检查: quality={report_partial.quality_score:.2f}, "
          f"overall={report_partial.overall_score:.2f}")
    assert report_partial.quality_score > 0
    # 只有 quality 模块有数据，综合分 = quality 自身分
    assert report_partial.overall_score == report_partial.quality_score, \
        f"仅质量分综合计算错误: {report_partial.overall_score} vs {report_partial.quality_score}"

    # 6c：极高截断率
    pipeline3 = AssessmentPipeline()
    report_high_trunc = pipeline3.run_offline(
        model_name="high-truncation",
        truncation_records=_make_truncation_records(good=False),
    )
    print(f"  高截断: rate={report_high_trunc.truncation_rate:.1%}, "
          f"等级={report_high_trunc.truncation_level}")
    assert report_high_trunc.truncation_rate > 0
    assert report_high_trunc.truncation_level in ("差", "严重")

    print("\n[OK] Test 6 全部通过")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("-- Day 10 - [第2周Day5] Week 2 收尾：统一质量评估流水线测试 --")
    print("=" * 50)

    test_full_offline_good()
    test_full_offline_bad()
    test_overall_scoring()
    test_version_comparison()
    test_report_formatting()
    test_edge_cases()

    print(f"\n{'=' * 50}")
    print("Day 10 全部测试通过！")
    print(f"{'=' * 50}")
    print(f"\n今天学到：")
    print(f"  - Week 2 四个工具整合为一条评估流水线")
    print(f"  - 综合评分计算（Day6×0.25 + Day7×0.15 + Day8×0.10 + Day9×0.50）")
    print(f"  - 版本对比（v1 vs v2 的质量回归监控）")
    print(f"  - 自动问题检测和改进建议生成")
    print(f"  - 全量评估报告格式化输出")
    print(f"\n面试准备（Week 2 收尾）：")
    print(f'  "我搭建了一套端到端的 AI 回复质量评估流水线，')
    print(f'   整合了质检查、一致性验证、截断监控和 LLM-as-Judge 四种方法。')
    print(f'   每个版本发布前跑 500 条用例，从四个维度评估质量变化，')
    print(f'   自动生成报告和门禁决策。上线后质量评估从 4 天缩短到 30 分钟。"')
