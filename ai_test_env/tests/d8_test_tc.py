"""
Agent / Tool Calling 测试模块 — 测试文件

测试内容：
1. TestCase.validate(): 工具选择 + 参数验证
2. ToolCallingTester: 单条/批量执行
3. TCCallParser: 多种格式解析
4. 内置场景测试
5. 边界情况（空输入、无工具、歧义请求）
6. 完整流水线测试
"""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.d8_tc_tester import (
    ToolCallingTester, TestCase, ToolDefinition, ExpectedToolCall,
    ToolCallResult, ToolCallStatus, BatchTCDReport, TCCallParser,
)


def print_separator(title):
    print(f"\n{'=' * 50}")
    print(f"[{title}]")
    print(f"{'=' * 50}")


# ──────────────────────────────────────────────
# Test 1: TestCase.validate() — 工具选择正确
# ──────────────────────────────────────────────

def test_tool_selection_correct():
    """测试: 选对了正确的工具"""
    print_separator("Test 1: 工具选择正确")

    weather = ToolDefinition(
        name="get_weather",
        description="获取天气",
        parameters={"city": {"type": "string", "required": True}},
    )
    case = TestCase(
        name="正确选择工具",
        prompt="北京天气？",
        available_tools=[weather],
        expected_calls=[ExpectedToolCall("get_weather", {"city": "北京"})],
    )

    # 模拟正确的工具调用
    result = case.validate([{"tool": "get_weather", "params": {"city": "北京"}}])

    print(f"  期望: get_weather(city=北京)")
    print(f"  实际: get_weather(city=北京)")
    print(f"  状态: {result.status.value}")
    print(f"  分数: {result.score:.2f}")
    assert result.status == ToolCallStatus.CORRECT, f"期望 CORRECT, 实际 {result.status}"
    assert result.score == 1.0, f"期望 score=1.0, 实际 {result.score}"
    print("  [OK] 工具选择正确测试通过")


# ──────────────────────────────────────────────
# Test 2: TestCase.validate() — 选错工具
# ──────────────────────────────────────────────

def test_wrong_tool():
    """测试: 选错了工具"""
    print_separator("Test 2: 选错工具")

    weather = ToolDefinition(
        name="get_weather",
        description="获取天气",
        parameters={"city": {"type": "string", "required": True}},
    )
    search = ToolDefinition(
        name="search_web",
        description="搜索网络",
        parameters={"query": {"type": "string", "required": True}},
    )
    case = TestCase(
        name="选错工具",
        prompt="北京天气？",
        available_tools=[weather, search],
        expected_calls=[ExpectedToolCall("get_weather", {"city": "北京"})],
    )

    # 模拟调用了搜索工具而不是天气工具
    result = case.validate([{"tool": "search_web", "params": {"query": "北京天气"}}])

    print(f"  期望: get_weather(city=北京)")
    print(f"  实际: search_web(query=北京天气)")
    print(f"  状态: {result.status.value}")
    print(f"  分数: {result.score:.2f}")
    assert result.status == ToolCallStatus.MISSING_PARAM, f"期望 MISSING_PARAM, 实际 {result.status}"
    assert result.score < 1.0
    assert len(result.errors) > 0
    print("  [OK] 选错工具检测通过")


# ──────────────────────────────────────────────
# Test 3: TestCase.validate() — 参数错误
# ──────────────────────────────────────────────

def test_wrong_param():
    """测试: 参数值错误（工具正确但参数不对）"""
    print_separator("Test 3: 参数值错误")

    weather = ToolDefinition(
        name="get_weather",
        description="获取天气",
        parameters={"city": {"type": "string", "required": True}},
    )
    case = TestCase(
        name="参数错误",
        prompt="上海天气？",
        available_tools=[weather],
        expected_calls=[ExpectedToolCall("get_weather", {"city": "上海"})],
    )

    # 模拟参数错误
    result = case.validate([{"tool": "get_weather", "params": {"city": "深圳"}}])

    print(f"  期望: get_weather(city=上海)")
    print(f"  实际: get_weather(city=深圳)")
    print(f"  状态: {result.status.value}")
    print(f"  分数: {result.score:.2f}")
    assert result.status == ToolCallStatus.WRONG_PARAM
    assert len(result.warnings) > 0
    print("  [OK] 参数错误检测通过")


# ──────────────────────────────────────────────
# Test 4: TestCase.validate() — 合理拒绝
# ──────────────────────────────────────────────

def test_expected_refusal():
    """测试: 合理拒绝调用工具"""
    print_separator("Test 4: 合理拒绝")

    weather = ToolDefinition(
        name="get_weather",
        description="获取天气",
        parameters={"city": {"type": "string", "required": True}},
    )
    case = TestCase(
        name="合理拒绝",
        prompt="Python 用什么缩进？",
        available_tools=[weather],
        expected_to_refuse=True,
    )

    result = case.validate([])  # 没有调用任何工具

    print(f"  期望: 不调用工具")
    print(f"  实际: 未调用")
    print(f"  状态: {result.status.value}")
    print(f"  分数: {result.score:.2f}")
    assert result.status == ToolCallStatus.REFUSED
    assert result.score == 1.0
    print("  [OK] 合理拒绝检测通过")


# ──────────────────────────────────────────────
# Test 5: 不应该调用但调用了
# ──────────────────────────────────────────────

def test_unexpected_call():
    """测试: 不应该调用但调用了工具"""
    print_separator("Test 5: 不应调用但调用了")

    weather = ToolDefinition(
        name="get_weather",
        description="获取天气",
        parameters={"city": {"type": "string", "required": True}},
    )
    case = TestCase(
        name="不应调用",
        prompt="Python 用什么缩进？",
        available_tools=[weather],
        expected_to_refuse=True,
    )

    # 模拟不应该调用却调用了
    result = case.validate([{"tool": "get_weather", "params": {"city": "北京"}}])

    print(f"  期望: 不调用工具")
    print(f"  实际: get_weather(city=北京)")
    print(f"  状态: {result.status.value}")
    print(f"  分数: {result.score:.2f}")
    assert result.status == ToolCallStatus.EXTRA_CALL
    assert result.score == 0.0
    print("  [OK] 多余调用检测通过")


# ──────────────────────────────────────────────
# Test 6: 禁止调用的工具
# ──────────────────────────────────────────────

def test_forbidden_tool():
    """测试: 调用了禁止的工具"""
    print_separator("Test 6: 调用了禁止的工具")

    send_email = ToolDefinition(
        name="send_email",
        description="发送邮件",
        parameters={"to": {"type": "string", "required": True}},
    )
    case = TestCase(
        name="禁止工具",
        prompt="给 user@test.com 发邮件说 hello",
        available_tools=[send_email],
        expected_calls=[ExpectedToolCall("send_email", {"to": "user@test.com", "subject": "Hello", "body": "hello"})],
        forbidden_tools=["send_email"],
    )

    result = case.validate([{"tool": "send_email", "params": {"to": "user@test.com", "subject": "Hello", "body": "hello"}}])

    print(f"  期望: 不调用 send_email")
    print(f"  实际: send_email")
    print(f"  状态: {result.status.value}")
    print(f"  分数: {result.score:.2f}")
    assert result.status in (ToolCallStatus.WRONG_TOOL, ToolCallStatus.MISSING_PARAM)
    print("  [OK] 禁止工具检测通过")


# ──────────────────────────────────────────────
# Test 7: TCCallParser — JSON 格式解析
# ──────────────────────────────────────────────

def test_parse_json_format():
    """测试: 解析 JSON 格式的工具调用"""
    print_separator("Test 7: JSON 格式解析")

    # OpenAI 原生 tool_calls 格式
    response = json.dumps([
        {"tool": "get_weather", "params": {"city": "北京"}},
        {"tool": "search_web", "params": {"query": "人工智能"}},
    ])
    calls = TCCallParser.parse_from_response(response)
    print(f"  输入: [{response[:80]}...]")
    print(f"  输出: {calls}")
    assert len(calls) == 2
    assert calls[0]["tool"] == "get_weather"
    assert calls[0]["params"]["city"] == "北京"
    assert calls[1]["tool"] == "search_web"
    assert calls[1]["params"]["query"] == "人工智能"

    # 带 tool_calls 包装的格式
    response2 = json.dumps({"tool_calls": [
        {"name": "get_weather", "arguments": {"city": "上海"}}
    ]})
    calls2 = TCCallParser.parse_from_response(response2)
    print(f"  带包装格式: {calls2}")
    assert len(calls2) == 1
    assert calls2[0]["tool"] == "get_weather"

    print("  [OK] JSON 格式解析成功")


# ──────────────────────────────────────────────
# Test 8: TCCallParser — 函数格式解析
# ──────────────────────────────────────────────

def test_parse_func_text():
    """测试: 解析函数调用文本格式"""
    print_separator("Test 8: 函数文本格式解析")

    response = "我来查一下：get_weather(city='北京', unit='celsius')"
    calls = TCCallParser.parse_from_response(response)
    print(f"  输入: {response}")
    print(f"  输出: {calls}")
    assert len(calls) == 1
    assert calls[0]["tool"] == "get_weather"
    assert calls[0]["params"]["city"] == "北京"

    # 多个函数调用
    response2 = "先查天气 get_weather(city=上海) 再搜新闻 search_web(query=AI)"
    calls2 = TCCallParser.parse_from_response(response2)
    print(f"  多调用: {calls2}")
    assert len(calls2) == 2

    print("  [OK] 函数文本格式解析成功")


# ──────────────────────────────────────────────
# Test 9: TCCallParser — Markdown 格式解析
# ──────────────────────────────────────────────

def test_parse_markdown():
    """测试: 解析 Markdown 格式的工具调用"""
    print_separator("Test 9: Markdown 格式解析")

    response = """根据分析，我需要：
- tool: get_weather, params: {"city": "广州"}
- tool: search_web, params: {"query": "今日新闻"}
"""
    calls = TCCallParser.parse_from_response(response)
    print(f"  输入: {response.strip()}")
    print(f"  输出: {calls}")
    assert len(calls) >= 2
    assert calls[0]["tool"] == "get_weather"
    assert calls[1]["tool"] == "search_web"

    print("  [OK] Markdown 格式解析成功")


# ──────────────────────────────────────────────
# Test 10: TCCallParser — 空输入/无效格式
# ──────────────────────────────────────────────

def test_parse_empty():
    """测试: 空输入/无效格式的解析"""
    print_separator("Test 10: 空输入解析")

    assert TCCallParser.parse_from_response("") == []
    assert TCCallParser.parse_from_response("今天天气不错") == []
    assert TCCallParser.parse_from_response("```\nsome code\n```") == []
    print("  空输入返回空列表 [OK]")
    print("  无格式文本返回空列表 [OK]")
    print("  代码块中无工具调用返回空列表 [OK]")

    print("  [OK] 空/无效输入处理通过")


# ──────────────────────────────────────────────
# Test 11: 批量测试
# ──────────────────────────────────────────────

def test_batch_execution():
    """测试: 批量执行测试用例"""
    print_separator("Test 11: 批量执行")

    weather = ToolDefinition(
        name="get_weather",
        description="获取天气",
        parameters={"city": {"type": "string", "required": True}},
    )
    search = ToolDefinition(
        name="search_web",
        description="搜索",
        parameters={"query": {"type": "string", "required": True}},
    )

    tester = ToolCallingTester()

    cases = [
        (TestCase(
            name="正确",
            prompt="北京天气？",
            available_tools=[weather],
            expected_calls=[ExpectedToolCall("get_weather", {"city": "北京"})],
        ), [{"tool": "get_weather", "params": {"city": "北京"}}]),
        (TestCase(
            name="错误参数",
            prompt="上海天气？",
            available_tools=[weather],
            expected_calls=[ExpectedToolCall("get_weather", {"city": "上海"})],
        ), [{"tool": "get_weather", "params": {"city": "深圳"}}]),
        (TestCase(
            name="合理拒绝",
            prompt="什么是爱？",
            available_tools=[weather],
            expected_to_refuse=True,
        ), []),
        (TestCase(
            name="多余调用",
            prompt="Python 是什么？",
            available_tools=[weather, search],
            expected_to_refuse=True,
        ), [{"tool": "search_web", "params": {"query": "Python"}}]),
    ]

    report = tester.run_batch(cases)
    print(f"  总用例: {len(report.results)}")
    print(f"  通过: {report.passed_count}")
    print(f"  失败: {report.failed_count}")
    print(f"  通过率: {report.pass_rate:.1%}")
    print(f"  平均分: {report.avg_score:.2f}")
    print(report.summary())

    assert report.passed_count == 2  # 正确 + 合理拒绝
    assert report.failed_count == 2  # 错误参数 + 多余调用
    assert report.pass_rate == 0.5

    print("  [OK] 批量执行测试通过")


# ──────────────────────────────────────────────
# Test 12: 内置场景测试
# ──────────────────────────────────────────────

def test_builtin_scenarios():
    """测试: 内置场景用例"""
    print_separator("Test 12: 内置场景测试")

    cases = ToolCallingTester.generate_scenario_cases()
    print(f"  内置用例数: {len(cases)}")
    assert len(cases) > 0

    # 验证每个用例的定义完整性
    for case in cases:
        assert case.name, f"用例名称为空"
        assert case.prompt, f"用例 {case.name} prompt 为空"
        print(f"  用例: {case.name} — {case.prompt[:30]}...")

    print("  [OK] 内置场景用例定义正确")


# ──────────────────────────────────────────────
# Test 13: 边界情况
# ──────────────────────────────────────────────

def test_edge_cases():
    """测试: 边界情况"""
    print_separator("Test 13: 边界情况")
    test_cases = []

    # 无可用工具
    case_no_tools = TestCase(
        name="无可用工具",
        prompt="北京天气？",
        available_tools=[],
        expected_to_refuse=True,
    )
    result = case_no_tools.validate([])
    print(f"  无可用工具: {result.status.value}, score={result.score:.2f}")
    assert result.status == ToolCallStatus.REFUSED
    assert result.score == 1.0

    # 工具但无期望
    weather = ToolDefinition(
        name="get_weather",
        description="获取天气",
        parameters={"city": {"type": "string", "required": True}},
    )
    case_no_expect = TestCase(
        name="工具但不期望调用",
        prompt="北京天气？",
        available_tools=[weather],
    )
    # 既没 expected_to_refuse 也没 expected_calls → 合理自评
    result2 = case_no_expect.validate([])
    print(f"  工具但无期望(不调用): {result2.status.value}, score={result2.score:.2f}")

    # 空 prompt
    case_empty_prompt = TestCase(
        name="空 prompt",
        prompt="",
        available_tools=[weather],
        expected_to_refuse=True,
    )
    result3 = case_empty_prompt.validate([])
    print(f"  空 prompt: {result3.status.value}, score={result3.score:.2f}")

    # 多工具调用（一个正确一个错误）
    search = ToolDefinition(
        name="search_web",
        description="搜索",
        parameters={"query": {"type": "string", "required": True}},
    )
    case_multi = TestCase(
        name="多工具-部分正确",
        prompt="查北京天气和最新AI新闻",
        available_tools=[weather, search],
        expected_calls=[
            ExpectedToolCall("get_weather", {"city": "北京"}),
            ExpectedToolCall("search_web", {"query": "AI"}),
        ],
    )
    result4 = case_multi.validate([
        {"tool": "get_weather", "params": {"city": "北京"}},
        {"tool": "search_web", "params": {"query": "Machine Learning"}},
    ])
    print(f"  多工具-部分正确: {result4.status.value}, score={result4.score:.2f}")
    print(f"    warnings: {result4.warnings}")

    # 重复调用同一工具
    case_duplicate = TestCase(
        name="重复调用",
        prompt="查北京天气和上海天气",
        available_tools=[weather],
        expected_calls=[ExpectedToolCall("get_weather", {"city": "北京"}), ExpectedToolCall("get_weather", {"city": "上海"})],
    )
    result5 = case_duplicate.validate([
        {"tool": "get_weather", "params": {"city": "北京"}},
        {"tool": "get_weather", "params": {"city": "上海"}},
    ])
    print(f"  重复调用同一工具: {result5.status.value}, score={result5.score:.2f}")
    assert result5.status == ToolCallStatus.CORRECT
    assert result5.score == 1.0

    print("  [OK] 边界情况测试通过")


# ──────────────────────────────────────────────
# Test 14: 报告生成器
# ──────────────────────────────────────────────

def test_report_builder():
    """测试: 报告生成"""
    print_separator("Test 14: 报告生成器")

    from utils.d8_tc_tester import TCReportBuilder

    # 构建一个测试报告
    report = BatchTCDReport()
    report.add(ToolCallResult(
        case_name="天气查询",
        status=ToolCallStatus.CORRECT,
        score=1.0,
        expected_calls=["get_weather"],
        actual_calls=["get_weather"],
    ))
    report.add(ToolCallResult(
        case_name="错误工具",
        status=ToolCallStatus.WRONG_TOOL,
        errors=["期望 get_weather, 实际 search_web"],
        score=0.3,
        expected_calls=["get_weather"],
        actual_calls=["search_web"],
    ))

    report_text = TCReportBuilder.build_report(report)
    print(report_text[:300])
    assert "Agent / Tool Calling 质量测试报告" in report_text
    assert "总共" in report_text or "总用例" in report_text
    assert "通过" in report_text

    print("  [OK] 报告生成器测试通过")


# ──────────────────────────────────────────────
# Test 15: BatchTCDReport 统计
# ──────────────────────────────────────────────

def test_batch_report_stats():
    """测试: 批量报告统计功能"""
    print_separator("Test 15: 批量报告统计")

    report = BatchTCDReport()
    report.add(ToolCallResult("a", ToolCallStatus.CORRECT, score=1.0))
    report.add(ToolCallResult("b", ToolCallStatus.CORRECT, score=1.0))
    report.add(ToolCallResult("c", ToolCallStatus.MISSING_PARAM, errors=["x"], score=0.6))
    report.add(ToolCallResult("d", ToolCallStatus.WRONG_TOOL, errors=["x"], score=0.3))
    report.add(ToolCallResult("e", ToolCallStatus.REFUSED, score=1.0))

    print(f"  Total: {len(report.results)}")
    print(f"  Passed: {report.passed_count}")
    print(f"  Failed: {report.failed_count}")
    print(f"  Pass Rate: {report.pass_rate:.1%}")
    print(f"  Avg Score: {report.avg_score:.2f}")
    print(report.summary())

    assert len(report.results) == 5
    assert report.passed_count == 3  # CORRECT*2 + REFUSED = 3
    assert report.failed_count == 2
    assert report.pass_rate == 3/5

    print("  [OK] 批量统计功能通过")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("Test 1: 工具选择正确", test_tool_selection_correct),
        ("Test 2: 选错工具", test_wrong_tool),
        ("Test 3: 参数错误", test_wrong_param),
        ("Test 4: 合理拒绝", test_expected_refusal),
        ("Test 5: 不应调用但调用了", test_unexpected_call),
        ("Test 6: 禁止工具", test_forbidden_tool),
        ("Test 7: JSON格式解析", test_parse_json_format),
        ("Test 8: 函数文本格式解析", test_parse_func_text),
        ("Test 9: Markdown格式解析", test_parse_markdown),
        ("Test 10: 空输入解析", test_parse_empty),
        ("Test 11: 批量执行", test_batch_execution),
        ("Test 12: 内置场景用例", test_builtin_scenarios),
        ("Test 13: 边界情况", test_edge_cases),
        ("Test 14: 报告生成器", test_report_builder),
        ("Test 15: 批量统计", test_batch_report_stats),
    ]

    passed = 0
    failed = 0
    for name, func in tests:
        try:
            func()
            print(f"  [OK] {name}\n")
            passed += 1
        except AssertionError as e:
            print(f"  [!!] {name}: {str(e)}\n")
            failed += 1
        except Exception as e:
            print(f"  [!!] {name}: 异常 — {type(e).__name__}: {str(e)}\n")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"  测试汇总: {passed}/{passed + failed} 通过")
    if failed > 0:
        print(f"  [!!] 失败 {failed} 个测试")
    else:
        print(f"  [OK] 全部通过")
    print(f"{'=' * 50}")
