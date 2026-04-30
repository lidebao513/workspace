"""
D8f — 时效性/时间感知测试

覆盖：
1. TimelinessCaseGenerator 用例生成（6 种时效类型）
2. TimelinessRuleBase 规则库
3. TimelinessTester 执行与评估
4. 报告生成 + 批量运行
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d8f_timeliness_tester import (
    TimelinessType, TimelinessCase, TimelinessResult, TimelinessReport,
    TimelinessRuleBase, TimelinessCaseGenerator, TimelinessTester,
)
import pytest


def print_separator(title):
    print(f"\n{'=' * 50}")
    print(f"[{title}]")
    print(f"{'=' * 50}")


# ===================================================================
# Test 1: TimelinessRuleBase 规则库
# ===================================================================

def test_rule_has_year():
    assert TimelinessRuleBase.has_year("今天是2024年")
    assert TimelinessRuleBase.has_year("2025年1月")
    assert not TimelinessRuleBase.has_year("今天是几号？")


def test_rule_has_date():
    assert TimelinessRuleBase.has_date("2024年12月25日")
    assert TimelinessRuleBase.has_date("2024-12-25")
    assert not TimelinessRuleBase.has_date("你好吗？")


def test_rule_knowledge_cutoff():
    assert TimelinessRuleBase.has_knowledge_cutoff("我的知识截止到2024年")
    assert TimelinessRuleBase.has_knowledge_cutoff("training data cutoff")
    assert not TimelinessRuleBase.has_knowledge_cutoff("今天天气很好")


def test_rule_detect_obsolete():
    obsolete = TimelinessRuleBase.detect_obsolete_tech("你可以用 Python 2 来写")
    assert "Python 2" in obsolete

    obsolete2 = TimelinessRuleBase.detect_obsolete_tech("推荐用 React 开发")
    assert len(obsolete2) == 0


# ===================================================================
# Test 2: TimelinessCaseGenerator 用例生成
# ===================================================================

def test_generator_has_all_types():
    gen = TimelinessCaseGenerator()
    cases = gen.generate_all()
    types = set(c.type for c in cases)
    expected = set(TimelinessType)
    assert types == expected, f"缺少类型: {expected - types}"


def test_generator_case_count():
    gen = TimelinessCaseGenerator()
    cases = gen.generate_all()
    assert len(cases) >= 15, f"用例数不足: {len(cases)}"


def test_generator_each_type_has_multiple():
    gen = TimelinessCaseGenerator()
    cases = gen.generate_all()
    for ttype in TimelinessType:
        count = len([c for c in cases if c.type == ttype])
        assert count >= 2, f"{ttype.value} 类型用例数不足: {count}"


def test_generator_case_id_format():
    gen = TimelinessCaseGenerator()
    cases = gen.generate_all()
    for c in cases:
        assert c.id.startswith("TL-"), f"ID 格式错误: {c.id}"


def test_generator_severity_coverage():
    """检查严重等级分布"""
    gen = TimelinessCaseGenerator()
    cases = gen.generate_all()
    severities = set(c.severity for c in cases)
    # 应该覆盖多种 severity
    assert "critical" in severities or "high" in severities


# ===================================================================
# Test 3: TimelinessTester 执行与评估
# ===================================================================

def test_tester_mock_all_pass():
    """全部匹配期望模式 → all pass"""
    tester = TimelinessTester()
    cases = [
        TimelinessCase("C1", "今天几号？", TimelinessType.TIME_AWARENESS,
                       r"\d{4}年"),
        TimelinessCase("C2", "What is knowledge cutoff?", TimelinessType.KNOWLEDGE_CUTOFF,
                       r"(?:20|19)\d{2}"),
    ]
    mock = {
        "C1": "今天是2024年12月25日。",
        "C2": "My knowledge cutoff is 2024年。",
    }
    report = tester.run(cases=cases, mock_responses=mock)
    assert report.total_cases == 2
    assert report.passed == 2
    assert report.failed == 0
    assert report.pass_rate == 1.0


def test_tester_mock_all_fail():
    """全都不匹配 → all fail"""
    tester = TimelinessTester()
    cases = [TimelinessCase("C3", "今天日期？", TimelinessType.TIME_AWARENESS,
                            r"\d{4}年")]
    mock = {"C3": "我不知道今天的日期。"}
    report = tester.run(cases=cases, mock_responses=mock)
    assert report.passed == 0
    assert report.failed == 1


def test_tester_forbidden_match():
    """命中禁止模式 → fail"""
    tester = TimelinessTester()
    cases = [
        TimelinessCase("C4", "2025年总统？", TimelinessType.TIMELINESS_CLAIM,
                       r"不确定", r"确认")
    ]
    mock = {"C4": "2025年的总统是..."}  # 没有不确定 + 确认式回答
    report = tester.run(cases=cases, mock_responses=mock)
    assert report.passed == 0
    assert len(report.details[0].issues) > 0


def test_tester_empty_cases():
    tester = TimelinessTester()
    report = tester.run(cases=[])
    assert report.total_cases == 0
    assert report.pass_rate == 1.0


def test_tester_no_mock_no_api():
    tester = TimelinessTester()
    cases = [TimelinessCase("C5", "hi", TimelinessType.TIME_AWARENESS, r"\d+")]
    report = tester.run(cases=cases)
    assert report.total_cases == 0


def test_tester_with_builtin_cases():
    """使用内置用例集"""
    tester = TimelinessTester()
    gen = TimelinessCaseGenerator()
    builtin = gen.generate_all()
    mock = {}
    for c in builtin:
        # 全部 mock 为有时效信息的回复
        mock[c.id] = "截至2024年，这个问题的答案是..."
    report = tester.run(cases=builtin, mock_responses=mock)
    assert report.total_cases >= 15


def test_tester_report_breakdown():
    """报告按时效类型细分"""
    tester = TimelinessTester()
    cases = [
        TimelinessCase("R1", "今天日期", TimelinessType.TIME_AWARENESS,
                       r"\d{4}年"),
        TimelinessCase("R2", "Python 2", TimelinessType.OBSOLETE_INFO,
                       r"Python\s*3"),
    ]
    mock = {"R1": "2024年。", "R2": "推荐使用Python 3。"}
    report = tester.run(cases=cases, mock_responses=mock)
    assert "time_awareness" in report.breakdown
    assert "obsolete_info" in report.breakdown


def test_tester_report_display():
    """报告可读输出"""
    tester = TimelinessTester()
    cases = [TimelinessCase("D1", "今天日期", TimelinessType.TIME_AWARENESS,
                            r"\d{4}年")]
    mock = {"D1": "2024年。"}
    report = tester.run(cases=cases, mock_responses=mock)
    display = report.display()
    assert "总用例" in display
    assert "通过率" in display
    assert "总结" in display


def test_tester_last_report():
    tester = TimelinessTester()
    assert tester.last_report is None
    cases = [TimelinessCase("L1", "hi", TimelinessType.TIME_AWARENESS, r"\d+")]
    mock = {"L1": "2024"}
    tester.run(cases=cases, mock_responses=mock)
    assert tester.last_report is not None
    assert tester.last_report.passed == 1


# ===================================================================
# Test 4: 对象属性
# ===================================================================

def test_result_status_emoji():
    r_pass = TimelinessResult(
        case=TimelinessCase("T1", "hi", TimelinessType.TIME_AWARENESS, r"\d+"),
        response="2024", expected_found=True, forbidden_found=False,
        score=0.85,
    )
    assert r_pass.status_emoji == "[OK]"

    r_fail = TimelinessResult(
        case=TimelinessCase("T2", "hi", TimelinessType.TIME_AWARENESS, r"\d+"),
        response="我不知道", expected_found=False, forbidden_found=False,
        score=0.4,
    )
    assert r_fail.status_emoji == "[!!]"


def test_case_short_display():
    c = TimelinessCase("TL-001", "测试", TimelinessType.TIME_AWARENESS, r"\d+")
    display = c.short_display()
    assert "TL-001" in display
    assert "time_awareness" in display


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])

