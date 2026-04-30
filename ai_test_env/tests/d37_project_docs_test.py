"""
D37-D38 — 项目文档验证测试
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_readme_exists():
    path = os.path.join(os.path.dirname(__file__), "..", "README.md")
    assert os.path.exists(path), "README.md 不存在"
    size = os.path.getsize(path)
    assert size > 3000, f"README 太小: {size} 字节"


def test_readme_has_modules_table():
    path = os.path.join(os.path.dirname(__file__), "..", "README.md")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "| d1 |" in content, "缺少模块表"
    assert "| d30 |" in content or "| d33 |" in content, "缺少后期模块"


def test_readme_has_quick_start():
    path = os.path.join(os.path.dirname(__file__), "..", "README.md")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "快速开始" in content or "quick start" in content.lower()


def test_architecture_exists():
    path = os.path.join(os.path.dirname(__file__), "..", "ARCHITECTURE.md")
    assert os.path.exists(path), "ARCHITECTURE.md 不存在"
    size = os.path.getsize(path)
    assert size > 3000, f"ARCHITECTURE 太小: {size} 字节"


def test_architecture_has_layers():
    path = os.path.join(os.path.dirname(__file__), "..", "ARCHITECTURE.md")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "工具层" in content or "Tool" in content
    assert "汇报层" in content or "Reporting" in content


def test_architecture_has_dep_graph():
    path = os.path.join(os.path.dirname(__file__), "..", "ARCHITECTURE.md")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "依赖" in content or "d27" in content


def test_plan_v3_exists():
    path = os.path.join(os.path.dirname(__file__), "..", "ai_test_learning_plan_v3.md")
    assert os.path.exists(path), "学习计划不存在"
