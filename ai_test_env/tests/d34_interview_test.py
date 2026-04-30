"""
D34-D36 — 面试准备验证测试
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_interview_top20_exists():
    path = os.path.join(os.path.dirname(__file__), "..", "INTERVIEW_TOP20.md")
    assert os.path.exists(path), "INTERVIEW_TOP20.md 不存在"
    size = os.path.getsize(path)
    assert size > 5000, f"文件太小: {size} 字节"


def test_interview_scenarios_exists():
    path = os.path.join(os.path.dirname(__file__), "..", "INTERVIEW_SCENARIOS.md")
    assert os.path.exists(path), "INTERVIEW_SCENARIOS.md 不存在"
    size = os.path.getsize(path)
    assert size > 3000, f"文件太小: {size} 字节"


def test_interview_star_exists():
    path = os.path.join(os.path.dirname(__file__), "..", "INTERVIEW_STAR.md")
    assert os.path.exists(path), "INTERVIEW_STAR.md 不存在"
    size = os.path.getsize(path)
    assert size > 2000, f"文件太小: {size} 字节"


def test_top20_has_20_questions():
    path = os.path.join(os.path.dirname(__file__), "..", "INTERVIEW_TOP20.md")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # 统计问题编号（以 "### N." 格式）
    import re
    questions = re.findall(r"### \d+\.", content)
    assert len(questions) >= 20, f"题目数不足: {len(questions)}"


def test_scenarios_has_5_scenarios():
    path = os.path.join(os.path.dirname(__file__), "..", "INTERVIEW_SCENARIOS.md")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    import re
    scenarios = re.findall(r"### 场景 \d", content)
    assert len(scenarios) >= 5, f"场景不足: {len(scenarios)}"


def test_star_has_3_stars():
    path = os.path.join(os.path.dirname(__file__), "..", "INTERVIEW_STAR.md")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    stars = content.count("STAR")
    assert stars >= 3, f"STAR 叙述不足: {stars}"
