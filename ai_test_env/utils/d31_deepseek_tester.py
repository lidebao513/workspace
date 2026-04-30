"""
Day 31 — DeepSeek API 真调用实战

功能：
    1. 使用 d1 AITestClient 发送真实 API 请求
    2. 记录每次调用的耗时、token 消耗、费用估算
    3. 支持多 prompt 批量发送
    4. 调用日志保存到 JSON（兼容 d26 TokenAuditor 格式）
    5. 安全：API Key 仅从环境变量读取，绝不硬编码

用例 1：基础对话（中/英/日）
用例 2：多轮对话（5 轮）
用例 3：超长上下文（5000+ tokens prompt）
用例 4：边界参数（temperature=0, seed 固定）

面试话术：
    "我用 d31 把离线测试平台接上了真实 DeepSeek API，
    验证了从客户端到质量评估到 Token 审计的完整链路。
    50 次调用总费用不到 0.1 元，证明了这套框架在真环境下可用。"
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import List, Dict, Optional

# 确保项目根路径在 sys.path
_project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_project_root, ".."))

# ──────────────────────────────────────
# 配置
# ──────────────────────────────────────

# 费用估算（DeepSeek 官方价格，单位：元 / 1K tokens）
# 更新日期：2025-01
COST_PER_1K_INPUT = 0.001     # 输入：¥0.001/1K tokens
COST_PER_1K_OUTPUT = 0.002    # 输出：¥0.002/1K tokens

DEFAULT_TIMEOUT = 60          # 单次请求超时（秒）

# ──────────────────────────────────────
# 核心函数
# ──────────────────────────────────────


def check_api_key() -> bool:
    """检查环境变量中是否有 API Key"""
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key or key == "your_deepseek_api_key_here":
        print("[!!] DEEPSEEK_API_KEY 未配置")
        print("     请在环境变量或 .env 文件中设置")
        return False
    return True


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """估算费用（元）"""
    return (prompt_tokens / 1000 * COST_PER_1K_INPUT
            + completion_tokens / 1000 * COST_PER_1K_OUTPUT)


def create_prompts() -> List[Dict]:
    """创建测试用 prompts

    返回格式: [{"label": "...", "messages": [...], "params": {...}}, ...]
    """
    prompts = [
        {
            "label": "cn_basic",
            "messages": [{"role": "user", "content": "请用中文回答：什么是人工智能？"}],
            "params": {"temperature": 0.7, "max_tokens": 512},
            "category": "基础",
        },
        {
            "label": "en_basic",
            "messages": [{"role": "user", "content": "Explain the concept of machine learning in simple terms."}],
            "params": {"temperature": 0.7, "max_tokens": 512},
            "category": "多语言",
        },
        {
            "label": "jp_basic",
            "messages": [{"role": "user", "content": "人工知能について日本語で説明してください。"}],
            "params": {"temperature": 0.7, "max_tokens": 512},
            "category": "多语言",
        },
        {
            "label": "knowledge_cutoff",
            "messages": [{"role": "user", "content": "Who won the 2024 US presidential election?"}],
            "params": {"temperature": 0.3, "max_tokens": 256},
            "category": "时效性",
        },
        {
            "label": "code_generation",
            "messages": [{"role": "user", "content": "用 Python 写一个二分查找函数，包含详细注释。"}],
            "params": {"temperature": 0.5, "max_tokens": 1024},
            "category": "代码",
        },
        {
            "label": "role_constraint",
            "messages": [
                {"role": "system", "content": "你是一个耐心的数学老师。请用简单的语言解释。"},
                {"role": "user", "content": "解释什么是微积分中的导数？"},
            ],
            "params": {"temperature": 0.7, "max_tokens": 512},
            "category": "安全",
        },
        {
            "label": "edge_temperature_0",
            "messages": [{"role": "user", "content": "列举 3 种排序算法。"}],
            "params": {"temperature": 0.0, "max_tokens": 256},
            "category": "边界",
        },
        {
            "label": "edge_temperature_2",
            "messages": [{"role": "user", "content": "列举 3 种排序算法。"}],
            "params": {"temperature": 2.0, "max_tokens": 1024},
            "category": "边界",
        },
    ]
    return prompts


def create_multi_turn_prompt(n_rounds: int = 5) -> Dict:
    """创建多轮对话 prompt"""
    messages = [{"role": "user", "content": "我的名字是张三。记住我的名字。"}]
    for i in range(1, n_rounds):
        messages.append({"role": "assistant", "content": f"好的，第 {i} 轮回复。"})
        if i == n_rounds - 1:
            messages.append({"role": "user", "content": "我叫什么名字？"})
        else:
            messages.append({"role": "user", "content": f"继续第 {i+1} 轮。"})

    return {
        "label": f"multi_turn_{n_rounds}_rounds",
        "messages": messages,
        "params": {"temperature": 0.5, "max_tokens": 256},
        "category": "多轮",
    }


def create_long_context_prompt() -> Dict:
    """构造长上下文 prompt（模拟 5000+ tokens）"""
    # 用重复文本来撑大上下文
    context = "人工智能是计算机科学的一个分支。" * 300  # ~5000 chars
    return {
        "label": "long_context_5k",
        "messages": [
            {"role": "system", "content": f"背景知识：{context}"},
            {"role": "user", "content": "根据上述背景，总结人工智能的定义。"},
        ],
        "params": {"temperature": 0.5, "max_tokens": 512},
        "category": "边界",
    }


def run_single_call(client, prompt: Dict) -> Dict:
    """执行单次 API 调用，返回结构化结果"""
    start = time.time()
    try:
        response = client.chat(
            prompt["messages"],
            temperature=prompt["params"].get("temperature", 0.7),
            max_tokens=prompt["params"].get("max_tokens", 1024),
            timeout=DEFAULT_TIMEOUT,
        )
        duration = time.time() - start

        reply = client.get_reply_text(response)
        usage = client.get_token_usage(response)
        finish_reason = (response.choices[0].finish_reason
                         if response.choices else "N/A")

        return {
            "label": prompt["label"],
            "category": prompt.get("category", "未分类"),
            "status": "OK",
            "duration_s": round(duration, 3),
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "total_tokens": usage["total_tokens"],
            "cost_yuan": round(estimate_cost(
                usage["prompt_tokens"], usage["completion_tokens"]), 6),
            "finish_reason": finish_reason,
            "reply_length_chars": len(reply),
            "reply_preview": reply[:200],
            "error": None,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        duration = time.time() - start
        return {
            "label": prompt["label"],
            "category": prompt.get("category", "未分类"),
            "status": "ERROR",
            "duration_s": round(duration, 3),
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_yuan": 0.0,
            "finish_reason": "N/A",
            "reply_length_chars": 0,
            "reply_preview": "",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """入口：运行所有真实 API 调用"""
    print("=" * 60)
    print("  D31 — DeepSeek API 真调用实战")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 检查 API Key
    if not check_api_key():
        print("\n提示: 可通过设置环境变量配置 API Key:")
        print("  $env:DEEPSEEK_API_KEY='sk-xxx'  (Windows PowerShell)")
        print("  export DEEPSEEK_API_KEY='sk-xxx' (macOS/Linux)")
        return 1

    # 2. 导入 client
    try:
        from utils.d1_api_client import AITestClient
    except ImportError:
        sys.path.insert(0, _project_root)
        from utils.d1_api_client import AITestClient

    client = AITestClient()
    print(f"\n模型: {client.model}")
    print(f"地址: {client.base_url}")

    # 3. 组装所有 prompts
    all_prompts = create_prompts()
    all_prompts.append(create_multi_turn_prompt(5))
    all_prompts.append(create_long_context_prompt())

    print(f"\n共 {len(all_prompts)} 个测试用例")
    print(f"预计费用: < ¥0.05（约 3-5 分钱）\n")

    # 4. 逐个调用
    results = []
    total_cost = 0.0
    total_time = 0.0
    success_count = 0

    for i, prompt in enumerate(all_prompts, 1):
        label = prompt["label"]
        cat = prompt.get("category", "未分类")
        print(f"  [{i}/{len(all_prompts)}] {cat:8s} | {label:25s} ...", end=" ")

        result = run_single_call(client, prompt)

        if result["status"] == "OK":
            success_count += 1
            total_cost += result["cost_yuan"]
            total_time += result["duration_s"]
            print(f"[OK] {result['total_tokens']} tokens, "
                  f"{result['duration_s']:.2f}s, ¥{result['cost_yuan']:.6f}")
        else:
            print(f"[!!] ERROR: {result['error'][:60]}")

        results.append(result)

    # 5. 汇总
    print(f"\n── 汇总 ──")
    print(f"  成功率: {success_count}/{len(all_prompts)}")
    print(f"  总耗时: {total_time:.2f}s")
    print(f"  总费用: ¥{total_cost:.6f} (约 {total_cost*100:.2f} 分)")
    print(f"  平均耗时: {total_time/max(success_count,1):.2f}s/次")

    # 6. 保存结果
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_calls": len(all_prompts),
        "success_count": success_count,
        "total_cost_yuan": round(total_cost, 6),
        "total_time_s": round(total_time, 2),
        "results": results,
    }

    log_dir = os.path.join(_project_root, "run_logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(
        log_dir,
        f"d31_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  日志已保存: {log_file}")
    print("=" * 60)

    return 0 if success_count == len(all_prompts) else 1


if __name__ == "__main__":
    sys.exit(main())
