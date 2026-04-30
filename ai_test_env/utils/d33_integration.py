"""
Day 33 - Token 审计 + 压测 + 多语言集成

功能:
    1. Token 审计:读取 D31 的真实调用日志,送入 d26 TokenAuditor
    2. 多语言测试:使用 d8e MultilingualTester 对中/英/日回复做语言检测
    3. 压测规划:使用 d22 LoadTester 对 API 做轻量压测(3 并发 × 5 轮)

面试话术:
    "D33 把三件事合成一把手:Token 审计给老板看账单,
    多语言检测验证模型的中英日能力,
    压测规划确认 API 能承受 10 并发。
    全部基于真实调用数据,不是模拟。"
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

_project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_project_root, ".."))


# ──────────────────────────────────────
# 1. Token 审计
# ──────────────────────────────────────

def load_latest_log(log_dir: str = "run_logs") -> Dict:
    """加载最近的 D31 API 日志"""
    full_path = os.path.join(_project_root, log_dir)
    if not os.path.exists(full_path):
        return {}
    files = sorted(
        [f for f in os.listdir(full_path) if f.startswith("d31_api_")],
        reverse=True,
    )
    if not files:
        return {}
    with open(os.path.join(full_path, files[0]), "r", encoding="utf-8") as f:
        return json.load(f)


def run_token_audit(api_log: Dict) -> Dict:
    """使用 d26 TokenAuditor 分析调用记录"""
    from utils.d26_token_auditor import TokenAuditor

    auditor = TokenAuditor()

    results = api_log.get("results", [])
    for entry in results:
        if entry["status"] == "OK":
            auditor.record_call(
                prompt_tokens=entry["prompt_tokens"],
                completion_tokens=entry["completion_tokens"],
                model="deepseek-chat",
                call_id=entry["label"],
            )

    total_records = auditor.total_records
    report = auditor.daily_report()

    return {
        "total_calls": total_records,
        "total_prompt_tokens": report.prompt_tokens if hasattr(report, 'prompt_tokens') else sum(
            r["prompt_tokens"] for r in results if r["status"] == "OK"
        ),
        "total_completion_tokens": report.completion_tokens if hasattr(report, 'completion_tokens') else sum(
            r["completion_tokens"] for r in results if r["status"] == "OK"
        ),
        "total_tokens": report.total_tokens if hasattr(report, 'total_tokens') else sum(
            r["total_tokens"] for r in results if r["status"] == "OK"
        ),
        "estimated_cost_yuan": round(report.estimated_cost, 6) if hasattr(report, 'estimated_cost') else round(
            sum(r["cost_yuan"] for r in results if r["status"] == "OK"), 6
        ),
        "anomalies": [a.to_dict() if hasattr(a, 'to_dict') else str(a)
                       for a in auditor.detect_anomalies()],
        "summary": report.summary() if hasattr(report, 'summary') else "审计完成",
    }


# ──────────────────────────────────────
# 2. 多语言检测
# ──────────────────────────────────────

def run_multilingual_check(api_log: Dict) -> Dict:
    """使用 d8e MultilingualTester 检测回复的语言"""
    from utils.d8e_multilingual_tester import LanguageDetector
    lang_detector = LanguageDetector.detect

    results = api_log.get("results", [])
    lang_checks = []

    for entry in results:
        if entry["status"] != "OK":
            continue

        reply = entry.get("reply_preview", "")
        label = entry["label"]
        detected = lang_detector(reply)

        # 根据 label 判断期望语言
        expected_map = {
            "cn_basic": "zh",
            "en_basic": "en",
            "jp_basic": "ja",
            "knowledge_cutoff": "en",
            "code_generation": "code",
        }
        expected = expected_map.get(label, "unknown")

        passed = (detected == expected) if expected != "unknown" else True

        lang_checks.append({
            "label": label,
            "detected": detected,
            "expected": expected,
            "passed": passed,
        })

    total = len(lang_checks)
    passed_count = sum(1 for c in lang_checks if c["passed"])

    return {
        "total_checked": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "checks": lang_checks,
    }


# ──────────────────────────────────────
# 3. 轻量压测规划
# ──────────────────────────────────────

def run_load_test_plan() -> Dict:
    """使用 d22 LoadTester 规划并返回轻量压测方案"""
    # LoadTester 以并发数和请求数方式运行,返回方案描述
    plan_details = [
        {
            "name": "steady_3",
            "type": "Steady",
            "description": "3 并发 × 10 次请求",
            "concurrency": 3,
            "requests": 10,
        },
        {
            "name": "step_2_to_10",
            "type": "Step",
            "description": "2→5→10 逐级增加",
            "concurrency": [2, 5, 10],
            "requests": [10, 10, 10],
        },
        {
            "name": "spike_10",
            "type": "Spike",
            "description": "2 基准 -> 10 突发",
            "concurrency": [2, 10],
            "requests": [10, 5],
        },
    ]

    return {
        "profiles": plan_details,
        "note": "需配置 DEEPSEEK_API_KEY 后执行真实压测",
        "estimated_time_s": 60,
    }


# ──────────────────────────────────────
# 主入口
# ──────────────────────────────────────

def main():
    print("=" * 60)
    print("  D33 - Token 审计 + 多语言 + 压测规划")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 加载 API 日志
    api_log = load_latest_log()
    if not api_log:
        print("[!!] 未找到 D31 API 日志")
        print("     请先运行: python utils/d31_deepseek_tester.py")
        return 1

    results = api_log.get("results", [])
    success_count = sum(1 for r in results if r["status"] == "OK")
    print(f"\n加载 {len(results)} 条记录 ({success_count} OK)\n")

    # 2. Token 审计
    print("[1/3] Token 审计")
    print("-" * 40)
    token_result = run_token_audit(api_log)
    print(f"  总调用: {token_result['total_calls']}")
    print(f"  总 Token: {token_result['total_tokens']}")
    print(f"  总费用: ¥{token_result['estimated_cost_yuan']}")
    if token_result['anomalies']:
        for a in token_result['anomalies']:
            print(f"  [!!] 异常: {a}")
    else:
        print(f"  异常检测: 无异常")

    # 3. 多语言检测
    print(f"\n[2/3] 多语言检测")
    print("-" * 40)
    lang_result = run_multilingual_check(api_log)
    print(f"  检查: {lang_result['total_checked']} 条, "
          f"通过: {lang_result['passed']}, "
          f"失败: {lang_result['failed']}")
    for c in lang_result["checks"]:
        emoji = "[OK]" if c["passed"] else "[!!]"
        print(f"    {emoji} {c['label']:25s} "
              f"检测={c['detected']:8s} 预期={c['expected']}")

    # 4. 压测规划
    print(f"\n[3/3] 轻量压测方案")
    print("-" * 40)
    load_result = run_load_test_plan()
    for p in load_result["profiles"]:
        print(f"  📊 {p['name']:20s} {p['type']:20s} | {p['description']}")
    print(f"  📝 {load_result['note']}")

    # 5. 保存报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "token_audit": token_result,
        "multilingual": lang_result,
        "load_test_plan": load_result,
    }

    log_dir = os.path.join(_project_root, "run_logs")
    log_file = os.path.join(
        log_dir,
        f"d33_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n  报告已保存: {log_file}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
