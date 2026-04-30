"""
D33 — Token 审计 + 多语言 + 压测集成测试
"""
import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d33_integration import (
    load_latest_log, run_token_audit, run_multilingual_check, run_load_test_plan,
)


def _make_d31_log(log_dir: str):
    """创建模拟 D31 日志"""
    data = {
        "results": [
            {"label": "cn_basic", "status": "OK", "prompt_tokens": 50,
             "completion_tokens": 100, "total_tokens": 150,
             "cost_yuan": 0.00025, "reply_preview": "人工智能是计算机科学的分支"},
            {"label": "en_basic", "status": "OK", "prompt_tokens": 40,
             "completion_tokens": 80, "total_tokens": 120,
             "cost_yuan": 0.00020, "reply_preview": "Machine learning is a subset of AI"},
            {"label": "code_generation", "status": "OK", "prompt_tokens": 60,
             "completion_tokens": 200, "total_tokens": 260,
             "cost_yuan": 0.00046, "reply_preview": "def binary_search(arr, target):"},
            {"label": "failed_call", "status": "ERROR", "prompt_tokens": 0,
             "completion_tokens": 0, "total_tokens": 0,
             "cost_yuan": 0, "reply_preview": ""},
        ]
    }
    os.makedirs(log_dir, exist_ok=True)
    fpath = os.path.join(log_dir, "d31_api_20260430_200000.json")
    with open(fpath, "w") as f:
        json.dump(data, f)


def test_load_latest_log():
    with tempfile.TemporaryDirectory() as tmp:
        _make_d31_log(tmp)
        import utils.d33_integration as m
        original = m._project_root
        m._project_root = tmp
        try:
            result = m.load_latest_log(log_dir="")
            assert len(result.get("results", [])) == 4
        finally:
            m._project_root = original


def test_load_latest_log_not_found():
    with tempfile.TemporaryDirectory() as tmp:
        import utils.d33_integration as m
        original = m._project_root
        m._project_root = tmp
        try:
            result = m.load_latest_log(log_dir="")
            assert result == {}
        finally:
            m._project_root = original


def test_run_token_audit():
    with tempfile.TemporaryDirectory() as tmp:
        _make_d31_log(tmp)
        import utils.d33_integration as m
        original = m._project_root
        m._project_root = tmp
        try:
            log = m.load_latest_log(log_dir="")
            result = run_token_audit(log)
            assert result["total_calls"] == 3  # 只算 OK
            assert result["total_tokens"] > 0
            assert result["estimated_cost_yuan"] > 0
        finally:
            m._project_root = original


def test_run_token_audit_empty():
    result = run_token_audit({"results": []})
    assert result["total_calls"] == 0
    assert result["estimated_cost_yuan"] == 0


def test_run_multilingual_check():
    with tempfile.TemporaryDirectory() as tmp:
        _make_d31_log(tmp)
        import utils.d33_integration as m
        original = m._project_root
        m._project_root = tmp
        try:
            log = m.load_latest_log(log_dir="")
            result = run_multilingual_check(log)
            assert result["total_checked"] == 3  # 只算 OK
            assert result["passed"] >= 1
        finally:
            m._project_root = original


def test_run_multilingual_check_empty():
    result = run_multilingual_check({"results": []})
    assert result["total_checked"] == 0


def test_run_load_test_plan():
    result = run_load_test_plan()
    assert len(result["profiles"]) == 3
    assert "note" in result
    assert "estimated_time_s" in result
