"""
结构化输出格式验证器 — 测试文件

测试内容：
1. 代码块检测（完整/缺失标签/空内容/语言标签）
2. 行内代码（成对性/长度）
3. JSON 解析（合法/非法）
4. Markdown 表格（列对齐/格式）
5. 列表（编号连续性/嵌套）
6. URL 检测
7. 引用块
8. 标题层级
9. 格式要求（FormatRequirement）
10. 批量验证
11. 边界情况
12. 格式记分器
"""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.d8c_format_validator import (
    FormatValidator, FormatValidationReport, FormatCheckResult,
    FormatCategory, FormatScorer, FormatRequirement, BatchFormatValidator,
)


def print_separator(title):
    print(f"\n{'=' * 50}")
    print(f"[{title}]")
    print(f"{'=' * 50}")


# ──────────────────────────────────────────────
# Test 1: 完整代码块
# ──────────────────────────────────────────────

def test_valid_code_block():
    """测试: 完整的代码块"""
    print_separator("Test 1: 完整代码块")

    text = """这是一个 Python 例子：
```python
def hello():
    print("Hello, World!")
```"""
    validator = FormatValidator()
    report = validator.validate(text)

    code_checks = [c for c in report.checks if c.category == FormatCategory.CODE_BLOCK]
    assert len(code_checks) == 1
    assert code_checks[0].passed, f"代码块应当通过: {code_checks[0].issues}"
    assert code_checks[0].count == 1
    print(f"  代码块: {code_checks[0].count}x, passed={code_checks[0].passed}")
    print(f"  Overall: {'PASS' if report.overall_passed else 'FAIL'}")
    print("  [OK] 完整代码块通过")


# ──────────────────────────────────────────────
# Test 2: 代码块缺少语言标签
# ──────────────────────────────────────────────

def test_code_block_no_lang():
    """测试: 代码块缺少语言标签"""
    print_separator("Test 2: 代码块缺少语言标签")

    text = """```\ndef hello():\n    pass\n```"""
    validator = FormatValidator()
    report = validator.validate(text)

    code_checks = [c for c in report.checks if c.category == FormatCategory.CODE_BLOCK]
    assert not code_checks[0].passed, "缺少语言标签应标记为问题"
    assert any("缺少语言标签" in i for i in code_checks[0].issues)
    print(f"  Issues: {code_checks[0].issues}")
    print("  [OK] 缺少语言标签检测通过")


# ──────────────────────────────────────────────
# Test 3: 代码块标记不匹配
# ──────────────────────────────────────────────

def test_unmatched_code_blocks():
    """测试: 代码块标记不匹配"""
    print_separator("Test 3: 不匹配的代码块标记")

    text = """```python\nprint("hello")\n```\n一些文本\n```\n更多"""
    validator = FormatValidator()
    report = validator.validate(text)

    code_checks = [c for c in report.checks if c.category == FormatCategory.CODE_BLOCK]
    assert not code_checks[0].passed
    assert any("标记不匹配" in i for i in code_checks[0].issues)
    print(f"  Issues: {code_checks[0].issues}")
    print("  [OK] 不匹配标记检测通过")


# ──────────────────────────────────────────────
# Test 4: JSON 合法解析
# ──────────────────────────────────────────────

def test_json_valid():
    """测试: 合法 JSON 解析"""
    print_separator("Test 4: 合法 JSON")

    text = """这是返回的 JSON：
```json
{"name": "test", "value": 123, "items": [1, 2, 3]}
```"""
    validator = FormatValidator()
    report = validator.validate(text)

    json_checks = [c for c in report.checks if c.category == FormatCategory.JSON]
    assert len(json_checks) == 1
    assert json_checks[0].passed, f"JSON 应通过: {json_checks[0].issues}"
    print(f"  JSON 块: {json_checks[0].count}x, passed={json_checks[0].passed}")
    print("  [OK] 合法 JSON 通过")


# ──────────────────────────────────────────────
# Test 5: JSON 非法格式
# ──────────────────────────────────────────────

def test_json_invalid():
    """测试: 非法 JSON"""
    print_separator("Test 5: 非法 JSON")

    # 使用能被正则捕获但 json.loads 解析失败的内容
    # {"a": "b" extra} 中第一个 } 是 "b" 后，extra 导致 parse 失败
    text = """```json
{"a": "b" extra}
```"""
    validator = FormatValidator()
    report = validator.validate(text)

    json_checks = [c for c in report.checks if c.category == FormatCategory.JSON]
    assert not json_checks[0].passed, "非法 JSON 应标记为问题"
    assert any("解析失败" in i for i in json_checks[0].issues)
    print(f"  Issues: {json_checks[0].issues}")
    print("  [OK] 非法 JSON 检测通过")


# ──────────────────────────────────────────────
# Test 6: Markdown 表格
# ──────────────────────────────────────────────

def test_table_valid():
    """测试: 格式正确的 Markdown 表格"""
    print_separator("Test 6: 正确表格")

    text = """| 名称 | 价格 |
|------|------|
| 苹果 | 5    |
| 香蕉 | 3    |"""
    validator = FormatValidator()
    report = validator.validate(text)

    table_checks = [c for c in report.checks if c.category == FormatCategory.TABLE]
    assert table_checks[0].passed, f"表格应通过: {table_checks[0].issues}"
    assert table_checks[0].count == 1
    print(f"  表格: {table_checks[0].count}x, passed={table_checks[0].passed}")
    print("  [OK] 表格验证通过")


# ──────────────────────────────────────────────
# Test 7: 表格列不匹配
# ──────────────────────────────────────────────

def test_table_column_mismatch():
    """测试: 表格行/列数不匹配"""
    print_separator("Test 7: 表格列数不匹配")

    text = """| 名称 | 价格 | 库存 |
|------|------|------|
| 苹果 | 5    |"""
    validator = FormatValidator()
    report = validator.validate(text)

    table_checks = [c for c in report.checks if c.category == FormatCategory.TABLE]
    assert not table_checks[0].passed, "列数不匹配应标记问题"
    print(f"  Issues: {table_checks[0].issues}")
    print("  [OK] 列数不匹配检测通过")


# ──────────────────────────────────────────────
# Test 8: 有序列表编号
# ──────────────────────────────────────────────

def test_ordered_list():
    """测试: 有序列表编号连续性"""
    print_separator("Test 8: 有序列表编号")

    text = """步骤：
1. 打开应用
2. 登录账号
3. 点击设置"""
    validator = FormatValidator()
    report = validator.validate(text)

    list_checks = [c for c in report.checks if c.category == FormatCategory.LIST]
    assert list_checks[0].passed, f"连续编号应通过: {list_checks[0].issues}"
    print(f"  列表: {list_checks[0].count}x, passed={list_checks[0].passed}")

    # 不连续的编号
    text2 = """步骤：
1. 打开应用
3. 登录账号
4. 点击设置"""
    report2 = validator.validate(text2)
    list_checks2 = [c for c in report2.checks if c.category == FormatCategory.LIST]
    assert not list_checks2[0].passed, "跳号应标记问题"
    print(f"  跳号 issues: {list_checks2[0].issues}")
    print("  [OK] 列表编号检测通过")


# ──────────────────────────────────────────────
# Test 9: URL 检测
# ──────────────────────────────────────────────

def test_url_detection():
    """测试: URL 检测"""
    print_separator("Test 9: URL 检测")

    text = """访问 https://example.com 了解更多。
API 地址: https://api.deepseek.com/v1/chat"""
    validator = FormatValidator()
    report = validator.validate(text)

    url_checks = [c for c in report.checks if c.category == FormatCategory.URL]
    assert url_checks[0].count == 2
    assert url_checks[0].passed
    print(f"  URL: {url_checks[0].count}x")
    print("  [OK] URL 检测通过")


# ──────────────────────────────────────────────
# Test 10: 标题层级跳跃
# ──────────────────────────────────────────────

def test_heading_level_jump():
    """测试: 标题层级跳跃检测"""
    print_separator("Test 10: 标题层级跳跃")

    text = """# 一级标题
### 三级标题（跳级）"""
    validator = FormatValidator()
    report = validator.validate(text)

    heading_checks = [c for c in report.checks if c.category == FormatCategory.HEADING]
    assert not heading_checks[0].passed, "跳级应标记问题"
    assert any("跳跃" in i for i in heading_checks[0].issues)
    print(f"  Issues: {heading_checks[0].issues}")
    print("  [OK] 标题跳级检测通过")


# ──────────────────────────────────────────────
# Test 11: 格式要求（FormatRequirement）
# ──────────────────────────────────────────────

def test_format_requirement():
    """测试: 格式要求检查"""
    print_separator("Test 11: 格式要求")

    validator = FormatValidator()

    # 要求回复包含代码块
    text_with_code = "看这个：\n```python\nx = 1\n```"
    report = validator.validate(text_with_code)

    req = FormatRequirement("代码要求")
    req.require(FormatCategory.CODE_BLOCK, min_count=1)
    violations = req.check(report)
    assert len(violations) == 0, f"应无违规: {violations}"
    print(f"  有代码块: 无违规 [OK]")

    # 要求回复不含表格
    text_with_table = "| A | B |\n|---|---|"
    report2 = validator.validate(text_with_table)
    req2 = FormatRequirement("禁止表格")
    req2.forbid(FormatCategory.TABLE)
    violations2 = req2.check(report2)
    assert len(violations2) > 0, "有表格时应违规"
    print(f"  有表格但禁止: {violations2} [OK]")

    # 要求包含但实际没有
    text_plain = "一些普通的文本回复"
    report3 = validator.validate(text_plain)
    req3 = FormatRequirement("需要代码")
    req3.require(FormatCategory.CODE_BLOCK)
    violations3 = req3.check(report3)
    assert len(violations3) > 0, "无代码块时应违规"
    print(f"  需要代码但无: {violations3} [OK]")

    print("  [OK] 格式要求检查通过")


# ──────────────────────────────────────────────
# Test 12: 格式记分器
# ──────────────────────────────────────────────

def test_format_scorer():
    """测试: 格式记分器"""
    print_separator("Test 12: 格式记分器")

    validator = FormatValidator()
    text = """# 标题

```python
print("hello")
```

| A | B |
|---|---|
| 1 | 2 |"""
    report = validator.validate(text)
    score = FormatScorer.score(report)
    print(f"  Score: {score}")
    print(FormatScorer.format_report(score))

    assert score["composite_score"] >= 0.8
    assert "code_block" in score["dimensions"]
    print("  [OK] 格式记分器通过")


# ──────────────────────────────────────────────
# Test 13: 批量验证
# ──────────────────────────────────────────────

def test_batch_format():
    """测试: 批量格式验证"""
    print_separator("Test 13: 批量验证")

    batch = BatchFormatValidator()
    batch.add("普通文本")
    batch.add("```python\nx = 1\n```")
    batch.add("| a | b |\n|---|---|\n| 1 | 2 |")

    summary = batch.summary()
    print(summary[:200])
    assert "Batch Format Validation Summary" in summary
    print("  [OK] 批量验证通过")


# ──────────────────────────────────────────────
# Test 14: 边界情况
# ──────────────────────────────────────────────

def test_edge_cases():
    """测试: 边界情况"""
    print_separator("Test 14: 边界情况")

    validator = FormatValidator()

    # 空文本
    report = validator.validate("")
    assert report.total_issues == 0
    assert report.overall_passed
    print(f"  空文本: overall_passed={report.overall_passed} [OK]")

    # 纯文本（无格式）
    report2 = validator.validate("今天天气不错。这是一个普通的回复。")
    print(f"  纯文本: checks={len(report2.checks)}, issues={report2.total_issues}")
    assert report2.total_issues == 0
    print("  [OK] 纯文本通过")

    # 多代码块混合
    text = """```python\nx = 1\n```\n一些文字\n```javascript\nlet y = 2;\n```"""
    report3 = validator.validate(text)
    code_checks = [c for c in report3.checks if c.category == FormatCategory.CODE_BLOCK]
    assert code_checks[0].count == 2
    print(f"  多代码块: {code_checks[0].count}x [OK]")

    # 非法语言标签
    text4 = """```weirdlang\ncode\n```"""
    report4 = validator.validate(text4)
    code_checks4 = [c for c in report4.checks if c.category == FormatCategory.CODE_BLOCK]
    assert any("语言标签" in i for i in code_checks4[0].issues)
    print(f"  非法语言标签: {code_checks4[0].issues} [OK]")

    print("  [OK] 边界情况通过")


# ──────────────────────────────────────────────
# Test 15: 引用块检测
# ──────────────────────────────────────────────

def test_quote_detection():
    """测试: 引用块检测"""
    print_separator("Test 15: 引用块检测")

    validator = FormatValidator()

    text = "> 这是一段引用\n>\n> 这是另一段引用"
    report = validator.validate(text)
    quote_checks = [c for c in report.checks if c.category == FormatCategory.QUOTE]
    # 多数版本只检测序列数量
    assert quote_checks[0].count >= 1, f"应有引用块: count={quote_checks[0].count}"
    print(f"  引用块: {quote_checks[0].count}x [OK]")

    # 无引用
    text2 = "普通文本"
    report2 = validator.validate(text2)
    quote_checks2 = [c for c in report2.checks if c.category == FormatCategory.QUOTE]
    assert quote_checks2[0].count == 0
    print(f"  无引用: {quote_checks2[0].count}x [OK]")

    print("  [OK] 引用块检测通过")


# ──────────────────────────────────────────────
# Test 16: 无序列表
# ──────────────────────────────────────────────

def test_unordered_list():
    """测试: 无序列表"""
    print_separator("Test 16: 无序列表")

    validator = FormatValidator()

    text = """水果：
- 苹果
- 香蕉
- 橙子"""
    report = validator.validate(text)
    list_checks = [c for c in report.checks if c.category == FormatCategory.LIST]
    # 无序列表也计入 list count
    assert list_checks[0].count == 3
    assert list_checks[0].passed
    print(f"  无序列表: {list_checks[0].count}x [OK]")

    print("  [OK] 无序列表检测通过")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("Test 1: 完整代码块", test_valid_code_block),
        ("Test 2: 代码块缺少语言标签", test_code_block_no_lang),
        ("Test 3: 不匹配的代码块标记", test_unmatched_code_blocks),
        ("Test 4: 合法 JSON", test_json_valid),
        ("Test 5: 非法 JSON", test_json_invalid),
        ("Test 6: 正确表格", test_table_valid),
        ("Test 7: 表格列数不匹配", test_table_column_mismatch),
        ("Test 8: 有序列表编号", test_ordered_list),
        ("Test 9: URL 检测", test_url_detection),
        ("Test 10: 标题层级跳跃", test_heading_level_jump),
        ("Test 11: 格式要求", test_format_requirement),
        ("Test 12: 格式记分器", test_format_scorer),
        ("Test 13: 批量验证", test_batch_format),
        ("Test 14: 边界情况", test_edge_cases),
        ("Test 15: 引用块检测", test_quote_detection),
        ("Test 16: 无序列表", test_unordered_list),
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
            print(f"  [!!] {name}: 异常 -- {type(e).__name__}: {str(e)}\n")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"  测试汇总: {passed}/{passed + failed} 通过")
    if failed:
        print(f"  [!!] 失败 {failed} 个")
    else:
        print(f"  [OK] 全部通过")
    print(f"{'=' * 50}")
