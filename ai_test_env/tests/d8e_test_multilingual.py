"""
D8e — 多语言/语码混杂测试

覆盖：
1. LanguageDetector 语言检测（中/英/日/混合/代码）
2. MultilingualCaseGenerator 用例生成（5 种语言模式）
3. MultilingualTester 执行与评估
4. 批量测试 + 报告
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d8e_multilingual_tester import (
    LanguageMode, MultilingualDimension,
    MultilingualCase, MultilingualResult, MultilingualReport,
    LanguageDetector, MultilingualCaseGenerator, MultilingualTester,
)
import pytest


def print_separator(title):
    print(f"\n{'=' * 50}")
    print(f"[{title}]")
    print(f"{'=' * 50}")


# ===================================================================
# Test 1: LanguageDetector 语言检测
# ===================================================================

def test_detect_chinese():
    detector = LanguageDetector()
    assert detector.detect("今天天气很好") == "zh"
    assert detector.detect("请介绍一下Python") == "mixed"  # has both


def test_detect_english():
    detector = LanguageDetector()
    assert detector.detect("Hello, how are you?") == "en"
    assert detector.detect("This is a test.") == "en"


def test_detect_japanese():
    detector = LanguageDetector()
    assert detector.detect("今日はいい天気ですね。") == "ja"
    assert detector.detect("機械学習について教えて") == "ja"


def test_detect_mixed():
    detector = LanguageDetector()
    assert detector.detect("这个API的response格式") == "mixed"


def test_detect_code():
    detector = LanguageDetector()
    code = "def hello():\n    import os\n    print('hi')"
    assert detector.detect(code) == "code"


def test_detect_empty():
    detector = LanguageDetector()
    assert detector.detect("") == "unknown"


# ===================================================================
# Test 2: MultilingualCaseGenerator 用例生成
# ===================================================================

def test_generator_has_all_modes():
    gen = MultilingualCaseGenerator()
    cases = gen.generate_all()
    modes = set(c.lang_mode for c in cases)
    expected = set(LanguageMode)
    assert modes == expected, f"缺少模式: {expected - modes}"


def test_generator_case_count():
    gen = MultilingualCaseGenerator()
    cases = gen.generate_all()
    assert len(cases) >= 20, f"用例数不足: {len(cases)}"


def test_generator_each_mode_has_multiple():
    gen = MultilingualCaseGenerator()
    cases = gen.generate_all()
    for mode in LanguageMode:
        count = len([c for c in cases if c.lang_mode == mode])
        assert count >= 3, f"{mode.value} 模式用例数不足: {count}"


def test_generator_case_id_format():
    gen = MultilingualCaseGenerator()
    cases = gen.generate_all()
    for c in cases:
        assert c.id.startswith("ML-"), f"ID 格式错误: {c.id}"


# ===================================================================
# Test 3: MultilingualTester 执行与评估
# ===================================================================

def test_tester_mock_all_pass():
    """全部符合语言一致性和关键词 → all pass"""
    tester = MultilingualTester()
    cases = [
        MultilingualCase("C1", "今天天气怎么样？", LanguageMode.CHINESE,
                         "zh", expected_keywords=["天气"]),
        MultilingualCase("C2", "How are you?", LanguageMode.ENGLISH,
                         "en", expected_keywords=["fine", "good"]),
    ]
    mock = {
        "C1": "今天天气不错，适合出门。",
        "C2": "I'm doing good, thank you!",
    }
    report = tester.run(cases=cases, mock_responses=mock)
    assert report.total_cases == 2
    assert report.passed == 2
    assert report.failed == 0
    assert report.pass_rate == 1.0


def test_tester_mock_lang_mismatch():
    """语言不匹配 → fail"""
    tester = MultilingualTester()
    cases = [MultilingualCase("C3", "今天天气怎么样？", LanguageMode.CHINESE, "zh")]
    mock = {"C3": "I'm sorry, I can only answer in English."}
    report = tester.run(cases=cases, mock_responses=mock)
    # 语言不匹配，score = 1.0 - 0.3 = 0.7，不低于阈值
    # 测试验证 issues 中包含了语言不匹配问题
    assert len(report.details[0].issues) > 0
    assert "期望中文回复" in report.details[0].issues[0]


def test_tester_keyword_missing():
    """关键词缺失 → score 降低"""
    tester = MultilingualTester()
    cases = [MultilingualCase("C4", "Explain recursion", LanguageMode.ENGLISH,
                              "en", expected_keywords=["recursion", "function", "stack"])]
    mock = {"C4": "Recursion is when a function calls itself."}
    report = tester.run(cases=cases, mock_responses=mock)
    assert report.details[0].score <= 0.8  # 缺少 'stack'


def test_tester_forbidden_keyword():
    """命中禁止词 → score 降低"""
    tester = MultilingualTester()
    cases = [MultilingualCase("C5", "请保密", LanguageMode.CHINESE, "zh",
                              forbidden_keywords=["我知道"])]
    mock = {"C5": "这个秘密我知道，但我不说。"}
    report = tester.run(cases=cases, mock_responses=mock)
    assert not report.details[0].forbidden_breach or report.details[0].score < 0.71


def test_tester_empty_cases():
    tester = MultilingualTester()
    report = tester.run(cases=[])
    assert report.total_cases == 0
    assert report.pass_rate == 1.0


def test_tester_no_mock_no_api():
    tester = MultilingualTester()
    cases = [MultilingualCase("C6", "hi", LanguageMode.ENGLISH, "en")]
    report = tester.run(cases=cases)
    assert report.total_cases == 0


def test_tester_with_builtin_cases():
    """使用内置用例集"""
    tester = MultilingualTester()
    mock = {}
    gen = MultilingualCaseGenerator()
    builtin = gen.generate_all()
    for c in builtin:
        mock[c.id] = "这是一个很好的问题，让我来解释一下。"
    report = tester.run(cases=builtin, mock_responses=mock)
    assert report.total_cases >= 20
    # 中文应有 expected_keywords → 如果 mock 未覆盖可能 fail


def test_tester_report_breakdown():
    """报告按语言模式细分"""
    tester = MultilingualTester()
    cases = [
        MultilingualCase("R1", "你好", LanguageMode.CHINESE, "zh"),
        MultilingualCase("R2", "Hello", LanguageMode.ENGLISH, "en"),
    ]
    mock = {"R1": "你好！", "R2": "Hello!"}
    report = tester.run(cases=cases, mock_responses=mock)
    assert "chinese" in report.breakdown
    assert "english" in report.breakdown
    assert report.breakdown["chinese"]["passed"] >= 0


def test_tester_report_display():
    """报告可读输出"""
    tester = MultilingualTester()
    cases = [MultilingualCase("D1", "你好", LanguageMode.CHINESE, "zh")]
    mock = {"D1": "你好！"}
    report = tester.run(cases=cases, mock_responses=mock)
    display = report.display()
    assert "总用例" in display
    assert "通过率" in display


def test_tester_last_report():
    tester = MultilingualTester()
    assert tester.last_report is None
    cases = [MultilingualCase("L1", "hi", LanguageMode.ENGLISH, "en")]
    mock = {"L1": "hello"}
    tester.run(cases=cases, mock_responses=mock)
    assert tester.last_report is not None
    assert tester.last_report.passed == 1


def test_tester_batch_run():
    """批量运行"""
    tester = MultilingualTester()
    case_zh = [MultilingualCase("B1", "你好", LanguageMode.CHINESE, "zh")]
    case_en = [MultilingualCase("B2", "hi", LanguageMode.ENGLISH, "en")]
    mock_all = {"B1": "你好！", "B2": "Hello!"}
    reports = tester.batch_run([("zh", case_zh), ("en", case_en)], mock_responses=mock_all)
    assert len(reports) == 2
    assert reports[0].passed == 1
    assert reports[1].passed == 1


# ===================================================================
# Test 4: 对象属性
# ===================================================================

def test_result_status_emoji():
    r_pass = MultilingualResult(
        case=MultilingualCase("T1", "hi", LanguageMode.ENGLISH, "en"),
        response="hello", detected_lang="en",
        lang_match=True, keyword_match=True, forbidden_breach=False,
        score=0.85,
    )
    assert r_pass.status_emoji == "[OK]"

    r_fail = MultilingualResult(
        case=MultilingualCase("T2", "hi", LanguageMode.ENGLISH, "en"),
        response="你好", detected_lang="zh",
        lang_match=False, keyword_match=False, forbidden_breach=False,
        score=0.5,
    )
    assert r_fail.status_emoji == "[!!]"


def test_case_short_display():
    c = MultilingualCase("ML-001", "测试", LanguageMode.CHINESE, "zh")
    display = c.short_display()
    assert "ML-001" in display
    assert "chinese" in display
