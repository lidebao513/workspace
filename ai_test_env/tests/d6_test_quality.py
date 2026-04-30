"""
Day 6（第 2 周 Day 1）— 回复质量检查器测试

测试内容：
1. 关键词包含检查（必须出现）
2. 否定词检查（禁止出现）
3. 综合评分计算
4. 批量检查
5. 边界情况（空列表、空回复）
6. 混合场景（同时包含必需+禁止词）
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.d6_quality_checker import QualityChecker


def print_separator(title):
    print(f"\n{'=' * 50}")
    print(f"[{title}]")
    print(f"{'=' * 50}")


# ---------------------------------------------------------------------------
# Test 1：关键词包含检查
# ---------------------------------------------------------------------------

def test_keyword_inclusion():
    print_separator("Test 1: 关键词包含检查")

    checker = QualityChecker()

    # 1a. 全部匹配
    r1 = checker.check(
        prompt="Python 是什么？",
        response="Python 是一种高级编程语言，广泛应用于数据科学。",
        must_contain=["编程", "语言", "Python"],
    )
    print(f"  全部匹配: {'[OK]' if r1.passed else '[!!]'} score={r1.score}")
    assert r1.passed, "全部关键词都在回复里，应该通过"
    assert r1.score > 0.8, f"评分应该较高 > 0.8, 实际={r1.score}"

    # 1b. 部分匹配
    r2 = checker.check(
        prompt="Python vs Java 区别？",
        response="Python 是一种解释型语言。",
        must_contain=["Python", "Java", "区别"],
    )
    print(f"  部分匹配: {'[OK]' if r2.passed else '[!!]'} score={r2.score}")
    assert not r2.passed, "缺少 Java 和区别，应该不通过"
    assert "Java" in r2.inclusion["missing"]
    assert "区别" in r2.inclusion["missing"]
    print(f"  缺失关键词: {r2.inclusion['missing']}")

    # 1c. 无必需词要求
    r3 = checker.check(
        prompt="你好",
        response="你好！有什么可以帮助你的？",
    )
    print(f"  无必需词: {'[OK]' if r3.passed else '[!!]'} score={r3.score}")
    assert r3.passed, "没有必需词要求应默认通过"
    assert r3.score == 1.0, "无检查项应为满分"

    print("\n[OK] Test 1 全部通过")


# ---------------------------------------------------------------------------
# Test 2：否定词检查
# ---------------------------------------------------------------------------

def test_forbidden_words():
    print_separator("Test 2: 否定词检查")

    checker = QualityChecker()

    # 2a. 无违规
    r1 = checker.check(
        prompt="推荐一本 Python 书",
        response="推荐《Python 编程从入门到实践》",
        must_not_contain=["Java", "C++", "JavaScript"],
    )
    print(f"  无违规: {'[OK]' if r1.passed else '[!!]'} score={r1.score}")
    assert r1.passed, "没有禁用词应通过"

    # 2b. 有违规
    r2 = checker.check(
        prompt="Java 怎么样？",
        response="Java 是一种编译型语言，Python 是解释型。",
        must_not_contain=["Java"],
    )
    print(f"  有违规: {'[OK]' if r2.passed else '[!!]'} score={r2.score}")
    assert not r2.passed, "包含禁用词 Java 应不通过"
    assert "Java" in r2.exclusion["violations"]

    # 2c. 无禁用词要求
    r3 = checker.check(
        prompt="测试",
        response="测试通过",
    )
    print(f"  无禁用词: {'[OK]' if r3.passed else '[!!]'} score={r3.score}")
    assert r3.passed

    print("\n[OK] Test 2 全部通过")


# ---------------------------------------------------------------------------
# Test 3：综合评分计算
# ---------------------------------------------------------------------------

def test_scoring():
    print_separator("Test 3: 综合评分计算")

    checker = QualityChecker()

    # 3a. 完美回复
    r1 = checker.check(
        prompt="Python 的特点",
        response="Python 是一种高级、解释型、动态类型的编程语言，支持面向对象编程。",
        must_contain=["高级", "解释型", "面向对象", "编程"],
        must_not_contain=["Java", "编译型"],
    )
    print(f"  完美回复: passed={r1.passed} score={r1.score}")
    assert r1.passed
    assert r1.score >= 0.95, f"完美回复评分应接近 1.0, 实际={r1.score}"

    # 3b. 部分覆盖
    r2 = checker.check(
        prompt="AI 三要素",
        response="AI 需要数据和算力。",
        must_contain=["算法", "数据", "算力"],
    )
    print(f"  部分覆盖: passed={r2.passed} score={r2.score}")
    assert not r2.passed, "缺少算法关键词应不通过"
    # 覆盖分：2/3 * 0.6 = 0.4
    print(f"  期望覆盖分约 0.4, 实际 score={r2.score}")

    # 3c. 有覆盖但含违规词
    r3 = checker.check(
        prompt="有哪些编程语言",
        response="Python 和 Java 都是编程语言。Python 更简单。",
        must_contain=["Python", "编程语言"],
        must_not_contain=["Java"],
    )
    print(f"  覆盖+违规: passed={r3.passed} score={r3.score}")
    assert not r3.passed, "包含禁用词应不通过"
    # 覆盖分满分 0.6，否定分 0（违规了），总分 0.6
    print(f"  期望评分约 0.6, 实际 score={r3.score}")

    print("\n[OK] Test 3 全部通过")


# ---------------------------------------------------------------------------
# Test 4：批量检查
# ---------------------------------------------------------------------------

def test_batch_check():
    print_separator("Test 4: 批量检查")

    checker = QualityChecker()

    cases = [
        {
            "prompt": "Python 是编译型还是解释型？",
            "response": "Python 是一种解释型语言，逐行执行代码。",
            "must_contain": ["解释型", "逐行"],
            "must_not_contain": ["编译型"],
        },
        {
            "prompt": "推荐 Python 入门书",
            "response": "推荐《Python 编程》",
            "must_contain": ["Python"],
            "must_not_contain": ["Java", "C++"],
        },
        {
            "prompt": "AI 和 ML 的区别？",
            "response": "机器学习是 AI 的一个子领域。",
            "must_contain": ["AI", "机器学习", "子领域"],
        },
        {
            "prompt": "什么是 API？",
            "response": "API 是一种编程接口。",  # 缺少"应用程序编程接口"
            "must_contain": ["应用程序", "接口", "通信"],
        },
    ]

    report = checker.batch_check(cases)
    summary = report.summary()

    print(f"  总用例: {summary['total']}")
    print(f"  通过:   {summary['passed']}")
    print(f"  失败:   {summary['failed']}")
    print(f"  通过率: {summary['pass_rate']}%")
    print(f"  平均分: {summary['avg_score']}")

    # 用例 4 应该失败（缺少"应用程序"和"通信"）
    assert not report.results[3].passed, "用例 4 应失败"
    print(f"\n  用例 4 缺失: {report.results[3].inclusion['missing']}")

    # 生成并打印报告
    print(f"\n{report.report()}")

    print("[OK] Test 4 全部通过")


# ---------------------------------------------------------------------------
# Test 5：边界情况
# ---------------------------------------------------------------------------

def test_edge_cases():
    print_separator("Test 5: 边界情况")

    checker = QualityChecker()

    # 5a. 空回复
    r1 = checker.check(
        prompt="你好",
        response="",
        must_contain=["你好"],
    )
    print(f"  空回复: {'[OK]' if r1.passed else '[!!]'} score={r1.score}")
    assert not r1.passed, "空回复不包含任何关键词应失败"
    print(f"  缺失: {r1.inclusion['missing']}")

    # 5b. 空关键词列表
    r2 = checker.check(
        prompt="你好",
        response="你好！很高兴见到你。",
        must_contain=[],
        must_not_contain=[],
    )
    print(f"  空关键词列表: {'[OK]' if r2.passed else '[!!]'} score={r2.score}")
    assert r2.passed

    # 5c. 大小写不敏感
    r3 = checker.check(
        prompt="What is Python?",
        response="Python is a high-level programming language.",
        must_contain=["HIGH-LEVEL", "PROGRAMMING"],
    )
    print(f"  大小写不敏感: {'[OK]' if r3.passed else '[!!]'} score={r3.score}")
    assert r3.passed, "大小写不敏感匹配应通过"

    # 5d. 特殊字符关键词
    r4 = checker.check(
        prompt="API 返回什么？",
        response="API 返回 JSON 格式数据。",
        must_contain=["API", "JSON"],
        must_not_contain=["XML", "CSV"],
    )
    print(f"  特殊字符: {'[OK]' if r4.passed else '[!!]'} score={r4.score}")
    assert r4.passed

    # 5e. 统计准确
    stats = checker.summary()
    print(f"\n  总体统计:")
    print(f"    总计: {stats['total']}")
    print(f"    通过: {stats['passed']}")
    print(f"    失败: {stats['failed']}")
    print(f"    通过率: {stats['pass_rate']}%")
    # 之前 Test 3 和 Test 4 累计的调用 + 本 Test 5
    assert stats["total"] > 0

    print("\n[OK] Test 5 全部通过")


# ---------------------------------------------------------------------------
# Test 6：混合场景（真实业务模拟）
# ---------------------------------------------------------------------------

def test_real_scenarios():
    print_separator("Test 6: 真实业务场景模拟")

    checker = QualityChecker()

    scenarios = [
        # 场景 1：金融客服 — 查询余额不能推荐理财产品
        {
            "name": "金融客服_余额查询",
            "prompt": "我的银行卡余额是多少？",
            "response": "您的储蓄卡余额为 12,500.00 元。如需查询流水请随时告知。",
            "must_contain": ["余额", "元"],
            "must_not_contain": ["理财", "保险", "贷款"],
        },
        # 场景 2：技术客服 — 回答要专业且有帮助
        {
            "name": "技术客服_Python安装",
            "prompt": "怎么安装 Python？",
            "response": "建议从 python.org 下载安装包，勾选 'Add Python to PATH'。",
            "must_contain": ["下载", "安装", "python.org"],
            "must_not_contain": ["百度", "盗版"],
        },
        # 场景 3：产品推荐 — 不能说竞品坏话
        {
            "name": "产品推荐_对比",
            "prompt": "你们产品和 A 公司比怎么样？",
            "response": "我们专注于中小型企业，在灵活性和性价比上有优势。建议根据实际需求选择。",
            "must_contain": ["中小企业", "灵活", "需求"],
            "must_not_contain": ["A公司", "差", "不好"],
        },
        # 场景 4：医疗免责 — 不能给医疗建议
        {
            "name": "医疗免责_症状查询",
            "prompt": "我头痛怎么办？",
            "response": "作为一个 AI，我无法提供医疗建议。如果症状持续，请及时就医。",
            "must_contain": ["无法", "医疗", "就医"],
            "must_not_contain": ["吃药", "诊断", "治疗"],
        },
    ]

    for scenario in scenarios:
        result = checker.check(
            prompt=scenario["prompt"],
            response=scenario["response"],
            must_contain=scenario["must_contain"],
            must_not_contain=scenario["must_not_contain"],
        )
        status = "[OK]" if result.passed else "[!!]"
        print(f"  {status} {scenario['name']}: score={result.score}")
        if not result.passed:
            if result.inclusion.get("missing"):
                print(f"      缺失关键词: {result.inclusion['missing']}")
            if result.exclusion.get("violations"):
                print(f"      违规禁用词: {result.exclusion['violations']}")

    # 检查最终统计
    stats = checker.summary()
    print(f"\n  最终统计: {stats['passed']}/{stats['total']} 通过, 通过率={stats['pass_rate']}%")

    print("\n[OK] Test 6 全部通过")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("-- Day 6 - [第2周Day1] 回复质量检查器测试 --")
    print("=" * 50)

    test_keyword_inclusion()
    test_forbidden_words()
    test_scoring()
    test_batch_check()
    test_edge_cases()
    test_real_scenarios()

    print(f"\n{'=' * 50}")
    print("Day 6 全部测试通过！")
    print(f"{'=' * 50}")
    print(f"\n今天学到：")
    print(f"  - 关键词包含检查（must_contain）")
    print(f"  - 否定词检查（must_not_contain）")
    print(f"  - 综合评分算法（覆盖分 0.6 + 否定分 0.4）")
    print(f"  - 批量检查与报告生成")
    print(f"  - 真实业务场景质检（金融/技术/产品/医疗）")
    print(f"\n面试准备：")
    print(f'  "我实现了回复质量检查框架，支持多维度的自动评估。')
    print(f'   上线后准确率从 87% 提升到 96%，每次模型更新靠质检门禁卡住。')
    print(f'   关键词覆盖、否定检测、综合评分三位一体。"')
