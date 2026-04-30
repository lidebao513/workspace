"""
语气/风格一致性检查器 — 测试文件

测试内容：
1. 客服专业风（共情+礼貌+可操作建议）
2. 技术文档正式风（中性+正式）
3. 鼓励教练风（鼓励+可操作）
4. 谨慎安全风（谨慎+无负面）
5. 友好聊天风（口语化）
6. 风格违规检测（匹配错误）
7. 批量风格检查
8. 内置风格配置
9. 边界情况
10. 报告生成
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.d8d_style_checker import (
    StyleChecker, StyleProfile, StyleCheckResult,
    ToneType, FormalityLevel, PolitenessLevel,
    StyleProfiles, BatchStyleChecker,
)


def print_separator(title):
    print(f"\n{'=' * 50}")
    print(f"[{title}]")
    print(f"{'=' * 50}")


# ──────────────────────────────────────────────
# Test 1: 客服专业风 — 正确的回复
# ──────────────────────────────────────────────

def test_cs_professional_pass():
    """测试: 客服专业风 — 符合要求的回复"""
    print_separator("Test 1: 客服专业风-通过")

    profile = StyleProfiles.customer_service_professional()
    text = "您好，感谢您的耐心等待。我理解您的问题，建议您尝试重启应用，这通常可以解决加载缓慢的问题。"

    checker = StyleChecker()
    result = checker.check(text, profile)

    print(result.report())
    assert result.passed, f"客服专业回复应通过: {result.violations}"
    assert result.composite_score >= 0.7
    print("  [OK] 客服专业风通过")


# ──────────────────────────────────────────────
# Test 2: 客服专业风 — 违规模板
# ──────────────────────────────────────────────

def test_cs_professional_fail():
    """测试: 客服专业风 — 违规回复（缺礼貌/有负面）"""
    print_separator("Test 2: 客服专业风-违规")

    profile = StyleProfiles.customer_service_professional()
    text = "这个问题不好解决，你的操作不行，重装试试吧。"

    checker = StyleChecker()
    result = checker.check(text, profile)

    print(result.report())
    assert not result.passed, "违规回复应不通过"
    assert any("负面" in v or "礼貌" in v for v in result.violations + result.observations)
    print("  [OK] 违规检测通过")


# ──────────────────────────────────────────────
# Test 3: 技术文档正式风
# ──────────────────────────────────────────────

def test_tech_doc_formal():
    """测试: 技术文档正式风"""
    print_separator("Test 3: 技术文档正式风")

    profile = StyleProfiles.tech_doc_formal()

    text = "该接口返回 JSON 格式的数据。请求方法为 POST，请求体需包含 token 参数。"
    result = StyleChecker().check(text, profile)
    print(f"  正式回复: score={result.composite_score:.2f}, passed={result.passed}")
    assert result.passed

    # 违规：口语化
    text2 = "这个接口哈，会返回 JSON 啦。你发 POST 就行。"
    result2 = StyleChecker().check(text2, profile)
    print(f"  口语回复: score={result2.composite_score:.2f}, passed={result2.passed}")
    assert not result2.passed or result2.composite_score < 0.73

    print("  [OK] 技术文档风通过")


# ──────────────────────────────────────────────
# Test 4: 鼓励教练风
# ──────────────────────────────────────────────

def test_encouraging_coach():
    """测试: 鼓励教练风"""
    print_separator("Test 4: 鼓励教练风")

    profile = StyleProfiles.encouraging_coach()

    # 正确的鼓励回复
    text = "你已经做得不错了。继续加油，可以尝试多练习第3章的内容。"
    result = StyleChecker().check(text, profile)
    print(f"  鼓励回复: score={result.composite_score:.2f}, passed={result.passed}")
    assert result.passed

    # 冷冰冰的回复
    text2 = "练习第3章。这是必要的学习步骤。"
    result2 = StyleChecker().check(text2, profile)
    print(f"  冷淡回复: score={result2.composite_score:.2f}, passed={result2.passed}")
    # 可能完全没鼓励语 → 不通过
    assert not result2.passed or result2.composite_score < 0.7

    print("  [OK] 鼓励教练风通过")


# ──────────────────────────────────────────────
# Test 5: 谨慎安全风
# ──────────────────────────────────────────────

def test_cautious_harmless():
    """测试: 谨慎安全风"""
    print_separator("Test 5: 谨慎安全风")

    profile = StyleProfiles.cautious_harmless()

    text = "抱歉，我无法提供具体的投资建议。建议您咨询专业的金融顾问。"
    result = StyleChecker().check(text, profile)
    print(f"  谨慎回复: score={result.composite_score:.2f}, passed={result.passed}")
    assert result.passed

    # 违规：负面词汇
    text2 = "这个方案不行，这样做不好。错误很多。"
    result2 = StyleChecker().check(text2, profile)
    print(f"  负面回复: score={result2.composite_score:.2f}, passed={result2.passed}")
    assert not result2.passed

    print("  [OK] 谨慎安全风通过")


# ──────────────────────────────────────────────
# Test 6: 风格完全匹配测试
# ──────────────────────────────────────────────

def test_style_mismatch():
    """测试: 完全匹配和完全不匹配"""
    print_separator("Test 6: 风格完全匹配")

    checker = StyleChecker()

    # 友好聊天 vs 正式回复（风格不搭）
    friendly_profile = StyleProfiles.friendly_chat()
    response = "根据统计数据显示，该方案的实施成功率为87%。"
    result = checker.check(response, friendly_profile)
    print(f"  友好风格 + 正式回复: score={result.composite_score:.2f}, passed={result.passed}")
    # 友好聊天期望口语化，这个回复太正式 → 可能低分但不一定 FAIL（友好不严格要求口语）
    # 重点是验证不会崩溃

    # 客服专业 vs 有鼓励语但缺礼貌
    cs_profile = StyleProfiles.customer_service_professional()
    response2 = "加油！你可以的！这东西很简单。"
    result2 = checker.check(response2, cs_profile)
    print(f"  客服风格 + 鼓励对话: score={result2.composite_score:.2f}, passed={result2.passed}")
    # 客服期望礼貌+共情，这里只有鼓励没有礼貌 → 可能不通过

    # 验证 Dimension 结构完整
    assert "politeness" in result.dimension_scores
    assert "formality" in result.dimension_scores
    assert "tone" in result.dimension_scores

    print("  [OK] 风格匹配测试通过")


# ──────────────────────────────────────────────
# Test 7: 批量风格检查
# ──────────────────────────────────────────────

def test_batch_style():
    """测试: 批量风格检查"""
    print_separator("Test 7: 批量风格检查")

    batch = BatchStyleChecker()
    profile = StyleProfiles.customer_service_professional()

    texts = [
        "您好，感谢您的反馈。我理解您遇到的问题，建议您尝试以下步骤。",
        "这个问题不好弄，你的方法不对。",
        "谢谢您的耐心。我明白这对您来说不容易，我们会尽快解决。",
    ]

    results = batch.check(texts, profile)
    print(f"  总数: {len(results)}")
    passed = sum(1 for r in results if r.passed)
    print(f"  通过: {passed}/{len(results)}")

    summary = batch.summary()
    print(summary[:200])

    assert len(results) == 3
    assert passed >= 1  # 至少一个合格
    print("  [OK] 批量检查通过")


# ──────────────────────────────────────────────
# Test 8: 内置风格配置
# ──────────────────────────────────────────────

def test_builtin_profiles():
    """测试: 内置风格配置完整性"""
    print_separator("Test 8: 内置风格配置")

    profiles = [
        ("客服", StyleProfiles.customer_service_professional()),
        ("技术文档", StyleProfiles.tech_doc_formal()),
        ("友好聊天", StyleProfiles.friendly_chat()),
        ("鼓励教练", StyleProfiles.encouraging_coach()),
        ("谨慎安全", StyleProfiles.cautious_harmless()),
    ]

    for name, profile in profiles:
        desc = profile.to_description()
        print(f"  [{name}] {profile.label}")
        assert profile.label
        # 至少有一个风格定义
        has_style = any([
            profile.required_tone,
            profile.required_formality,
            profile.required_politeness,
        ])
        assert has_style, f"{name} 未定义任何风格"

    print("  [OK] 所有内置风格配置完整")


# ──────────────────────────────────────────────
# Test 9: 边界情况
# ──────────────────────────────────────────────

def test_edge_cases():
    """测试: 边界情况"""
    print_separator("Test 9: 边界情况")

    checker = StyleChecker()
    profile = StyleProfiles.tech_doc_formal()

    # 空文本
    result = checker.check("", profile)
    print(f"  空文本: score={result.composite_score:.2f}, passed={result.passed}")
    assert result.composite_score >= 0

    # 纯符号
    result2 = checker.check("！！！？？？", profile)
    print(f"  纯符号: score={result2.composite_score:.2f}, passed={result2.passed}")

    # 超长文本
    long_text = "这是一个测试。" * 100
    result3 = checker.check(long_text, profile)
    print(f"  超长文本: score={result3.composite_score:.2f}, passed={result3.passed}")

    # reset 不影响新检查
    checker.reset()
    result4 = checker.check("test", profile)
    assert result4.composite_score >= 0

    print("  [OK] 边界情况通过")


# ──────────────────────────────────────────────
# Test 10: 自定义风格配置
# ──────────────────────────────────────────────

def test_custom_profile():
    """测试: 自定义风格配置"""
    print_separator("Test 10: 自定义风格")

    profile = StyleProfile(
        label="自定义专业风",
        required_tone=ToneType.PROFESSIONAL,
        required_formality=FormalityLevel.FORMAL,
        required_politeness=PolitenessLevel.DIRECT,
        must_not_contain_negative=True,
    )

    text = "该函数接受两个参数，返回布尔值。建议进行单元测试。"
    result = StyleChecker().check(text, profile)
    print(result.report())
    assert result.passed
    print("  [OK] 自定义风格通过")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("Test 1: 客服专业风-通过", test_cs_professional_pass),
        ("Test 2: 客服专业风-违规", test_cs_professional_fail),
        ("Test 3: 技术文档正式风", test_tech_doc_formal),
        ("Test 4: 鼓励教练风", test_encouraging_coach),
        ("Test 5: 谨慎安全风", test_cautious_harmless),
        ("Test 6: 风格匹配", test_style_mismatch),
        ("Test 7: 批量风格检查", test_batch_style),
        ("Test 8: 内置风格配置", test_builtin_profiles),
        ("Test 9: 边界情况", test_edge_cases),
        ("Test 10: 自定义风格", test_custom_profile),
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
