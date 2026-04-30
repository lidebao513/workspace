"""
D31 — DeepSeek API 真调用测试
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d31_deepseek_tester import (
    check_api_key, estimate_cost, create_prompts,
    create_multi_turn_prompt, create_long_context_prompt,
    COST_PER_1K_INPUT, COST_PER_1K_OUTPUT,
)


def test_check_api_key_not_set():
    """没有 API Key 时返回 False"""
    # 临时清除环境变量
    old_key = os.environ.pop("DEEPSEEK_API_KEY", None)
    try:
        result = check_api_key()
        assert not result
    finally:
        if old_key is not None:
            os.environ["DEEPSEEK_API_KEY"] = old_key


def test_check_api_key_placeholder():
    """占位符 key 返回 False"""
    old_key = os.environ.pop("DEEPSEEK_API_KEY", None)
    os.environ["DEEPSEEK_API_KEY"] = "your_deepseek_api_key_here"
    try:
        result = check_api_key()
        assert not result
    finally:
        if old_key:
            os.environ["DEEPSEEK_API_KEY"] = old_key
        else:
            del os.environ["DEEPSEEK_API_KEY"]


def test_estimate_cost_zero():
    cost = estimate_cost(0, 0)
    assert cost == 0.0


def test_estimate_cost_formula():
    """验证费用公式"""
    cost = estimate_cost(1000, 500)
    expected = (1000 / 1000 * COST_PER_1K_INPUT
                + 500 / 1000 * COST_PER_1K_OUTPUT)
    assert abs(cost - expected) < 0.00001


def test_estimate_cost_example():
    """典型值：500 input + 200 output ≈ ¥0.0009"""
    cost = estimate_cost(500, 200)
    expected = 0.5 * 0.001 + 0.2 * 0.002
    assert abs(cost - expected) < 0.00001


def test_create_prompts_has_basic():
    prompts = create_prompts()
    labels = [p["label"] for p in prompts]
    assert "cn_basic" in labels
    assert "en_basic" in labels
    assert "jp_basic" in labels


def test_create_prompts_has_edge():
    prompts = create_prompts()
    labels = [p["label"] for p in prompts]
    assert "edge_temperature_0" in labels
    assert "edge_temperature_2" in labels


def test_create_prompts_all_have_params():
    prompts = create_prompts()
    for p in prompts:
        assert "messages" in p
        assert "params" in p
        assert "temperature" in p["params"]
        assert "max_tokens" in p["params"]


def test_create_multi_turn():
    result = create_multi_turn_prompt(3)
    assert result["label"] == "multi_turn_3_rounds"
    assert len(result["messages"]) >= 4  # user + assistant + user + ...
    assert isinstance(result["messages"], list)


def test_create_multi_turn_default():
    result = create_multi_turn_prompt()
    assert "5" in result["label"]


def test_create_long_context():
    result = create_long_context_prompt()
    assert result["label"] == "long_context_5k"
    # 系统消息应该包含大量文本
    sys_content = result["messages"][0]["content"]
    assert len(sys_content) > 2000


def test_main_returns_1_without_key():
    """没有 API Key 时 main 返回 1"""
    old_key = os.environ.pop("DEEPSEEK_API_KEY", None)
    try:
        import utils.d31_deepseek_tester as mod
        rc = mod.main()
        assert rc == 1
    finally:
        if old_key:
            os.environ["DEEPSEEK_API_KEY"] = old_key


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])

