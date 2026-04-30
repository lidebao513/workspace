"""
D30 — 综合端到端测试
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d30_comprehensive import check_imports


def test_check_imports_returns_dict():
    result = check_imports()
    assert isinstance(result, dict)
    assert len(result) >= 30, f"只有 {len(result)} 个模块"


def test_check_imports_week6_all_pass():
    """Week 6 (d26-d30) 导入必须全部通过"""
    result = check_imports()
    week6 = [k for k in result if any(k.startswith(f"d{d}") for d in ["26", "27", "28", "29", "30"])]
    failed = [(k, v) for k, v in result.items() if k in week6 and not v["ok"]]
    assert len(failed) == 0, f"Week 6 导入失败的模块: {failed}"


def test_check_imports_week5_all_pass():
    """Week 5 (d21-d25) 导入必须全部通过（核心模块）"""
    result = check_imports()
    week5 = [k for k in result if any(k.startswith(f"d{d}") for d in ["21", "22", "23", "24", "25"])]
    failed = [(k, v) for k, v in result.items() if k in week5 and not v["ok"]]
    assert len(failed) == 0, f"Week 5 导入失败的模块: {failed}"


def test_check_imports_returns_keys_are_strings():
    result = check_imports()
    for k, v in result.items():
        assert isinstance(k, str)
        assert "ok" in v
        assert "msg" in v
