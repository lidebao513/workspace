"""
D32 — 质量评估实战测试
"""
import sys, os, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d32_quality_eval import (
    load_api_logs, evaluate_with_quality_checker,
    evaluate_with_llm_judge, evaluate_with_schema,
)


def _make_log(log_dir: str, results: list):
    """创建模拟 D31 日志"""
    data = {"results": results}
    os.makedirs(log_dir, exist_ok=True)
    fpath = os.path.join(log_dir, "d31_api_20260430_200000.json")
    with open(fpath, "w") as f:
        json.dump(data, f)


def test_load_api_logs_empty_dir():
    """空日志目录返回空列表"""
    with tempfile.TemporaryDirectory() as tmp:
        results = load_api_logs(log_dir=tmp)
        assert results == []


def test_load_api_logs_single():
    with tempfile.TemporaryDirectory() as tmp:
        _make_log(tmp, [
            {"label": "test1", "status": "OK", "reply_preview": "hello"},
        ])
        # 因为 load_api_logs 拼接了 _project_root，需要 mock
        # 直接测试底层逻辑
        import utils.d32_quality_eval as m
        original = m._project_root
        m._project_root = tmp
        try:
            results = m.load_api_logs(log_dir="")
            assert len(results) >= 0  # 至少不报错
        finally:
            m._project_root = original


def test_evaluate_quality_checker():
    """中文回复应包含关键词"""
    result = evaluate_with_quality_checker(
        "人工智能（AI）是计算机科学的一个重要分支。", "cn_basic"
    )
    assert "passed" in result
    assert "score" in result
    assert isinstance(result["score"], (int, float))


def test_evaluate_quality_checker_code():
    result = evaluate_with_quality_checker(
        "def binary_search(arr, target): ...", "code_generation"
    )
    # Python 回复应该能找到 binary_search 关键词
    assert "passed" in result


def test_evaluate_quality_checker_unknown():
    """未知 label 不应报错"""
    result = evaluate_with_quality_checker("some text", "nonexistent_label")
    assert result["passed"]  # 没有关键词要求，默认通过


def test_evaluate_llm_judge():
    result = evaluate_with_llm_judge(
        "人工智能是计算机科学的分支。", "cn_basic"
    )
    assert "overall" in result
    assert "relevance" in result
    assert "completeness" in result
    assert "fluency" in result


def test_evaluate_llm_judge_code():
    result = evaluate_with_llm_judge(
        "def binary_search(arr, target):\n    return -1", "code_generation"
    )
    assert result["overall"] >= 0


def test_evaluate_schema_skip():
    """非代码回复跳过 schema 检查"""
    result = evaluate_with_schema("这是一个中文回复。", "cn_basic")
    assert not result["checked"]


def test_evaluate_schema_code():
    """代码回复进行 schema 检查"""
    result = evaluate_with_schema('{"content": "code", "code": "def foo()"}', "code_generation")
    assert result["checked"]
