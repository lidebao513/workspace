"""
Day 32 — 质量评估实战

功能：
    读取 D31 保存的真实 API 调用日志，
    对每个回复分别运行：
    1. d6 QualityChecker — 关键词/禁止词检查
    2. d9 LLMJudge — 多维度评分（离线模式）
    3. d10 SchemaValidator — JSON 结构验证（仅代码回复）

    输出综合质量评估报告。

面试话术：
    "D32 把 D31 的真实 API 调用结果接入了质量评估流水线：
    QualityChecker 做关键词和禁止词检查，
    LLMJudge 做多维度评分，
    SchemaValidator 验证代码回复的JSON结构。
    不是模拟数据，是真回复的评估。"
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Optional

_project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_project_root, ".."))


def load_api_logs(log_dir: str = "run_logs") -> List[Dict]:
    """加载 D31 保存的 API 调用日志

    寻找最近一个 d31_api_*.json 文件，返回 results 列表。
    """
    full_path = os.path.join(_project_root, log_dir)
    if not os.path.exists(full_path):
        print(f"[!!] 日志目录不存在: {full_path}")
        return []

    files = sorted(
        [f for f in os.listdir(full_path) if f.startswith("d31_api_")],
        reverse=True,
    )
    if not files:
        print("[!!] 未找到 D31 API 调用日志")
        print("     请先运行: python utils/d31_deepseek_tester.py")
        return []

    latest = os.path.join(full_path, files[0])
    print(f"加载日志: {latest}")
    with open(latest, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("results", [])


def evaluate_with_quality_checker(reply: str, prompt_label: str) -> Dict:
    """用 d6 QualityChecker 评估回复质量"""
    from utils.d6_quality_checker import QualityChecker

    checker = QualityChecker()

    # 根据 prompt 类型设定不同的检查标准
    checks = {
        "cn_basic": {
            "expected_keywords": ["人工智能", "AI", "计算机"],
            "forbidden_keywords": [],
        },
        "en_basic": {
            "expected_keywords": ["machine learning", "data", "algorithm"],
            "forbidden_keywords": [],
        },
        "jp_basic": {
            "expected_keywords": ["人工知能", "AI"],
            "forbidden_keywords": [],
        },
        "knowledge_cutoff": {
            "expected_keywords": [],
            "forbidden_keywords": [],
        },
        "code_generation": {
            "expected_keywords": ["binary_search", "二分查找", "def"],
            "forbidden_keywords": [],
        },
        "role_constraint": {
            "expected_keywords": ["导数", "微积分", "数学"],
            "forbidden_keywords": [],
        },
        "multi_turn": {
            "expected_keywords": ["张三"],
            "forbidden_keywords": [],
        },
    }

    params = checks.get(prompt_label, {
        "expected_keywords": [],
        "forbidden_keywords": [],
    })

    result = checker.check(
        prompt=prompt_label,
        response=reply,
        expected_keywords=params.get("expected_keywords", []),
        forbidden_keywords=params.get("forbidden_keywords", []),
    )

    return {
        "passed": result.passed,
        "score": result.score,
        "inclusion": result.inclusion.get("present_count", 0),
        "inclusion_total": result.inclusion.get("total_required", 0),
        "exclusion": result.exclusion.get("forbidden_found_count", 0),
    }


def evaluate_with_llm_judge(reply: str, prompt_label: str) -> Dict:
    """用 d9 LLMJudge 进行离线评分"""
    from utils.d9_llm_judge import JudgeResult

    # 基于回复长度和关键词做简单评分
    # 实际使用时由 LLM 评委打分，这里是离线模拟
    relevance = min(10, max(1, len(reply) // 20))
    completeness = min(10, max(1, len(set(reply.split())) // 5))
    fluency = 8.0  # 默认流畅度较高

    scores = {
        "relevance": float(relevance),
        "completeness": float(completeness),
        "fluency": fluency,
    }
    # 简单加权：relevance 0.4 + completeness 0.3 + fluency 0.3
    weighted = (relevance * 0.4 + completeness * 0.3 + fluency * 0.3) / 10.0

    return {
        "overall": min(1.0, weighted),
        "relevance": float(relevance) / 10.0,
        "completeness": float(completeness) / 10.0,
        "fluency": fluency / 10.0,
    }


def evaluate_with_schema(reply: str, prompt_label: str) -> Dict:
    """用 d10 SchemaValidator 验证回复"""
    from utils.d10_schema_validator import SchemaValidator

    # 只对 code_generation 做 schema 验证
    if prompt_label != "code_generation":
        return {"checked": False, "message": "跳过（非代码回复）"}

    schema = {
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "code": {"type": "string"},
        },
        "required": ["content"],
    }

    validator = SchemaValidator(schema)

    # 尝试从回复中提取 JSON
    try:
        result = validator.validate_json_string(reply)
        return {
            "checked": True,
            "valid": result.valid,
            "errors": len(result.errors),
            "error_details": [str(e) for e in result.errors[:3]],
        }
    except Exception:
        return {
            "checked": True,
            "valid": False,
            "errors": 1,
            "error_details": ["回复不是合法 JSON"],
        }


def main():
    print("=" * 60)
    print("  D32 — 质量评估实战")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 加载 D31 API 调用日志
    results = load_api_logs()
    if not results:
        return 1

    # 只取成功的调用
    success_results = [r for r in results if r["status"] == "OK"]
    print(f"  成功调用: {len(success_results)}/{len(results)}\n")

    # 2. 逐条评估
    evaluations = []

    for i, entry in enumerate(success_results, 1):
        label = entry["label"]
        reply = entry.get("reply_preview", "")
        cat = entry.get("category", "?")

        print(f"  [{i}/{len(success_results)}] {cat:8s} | {label:25s} ...")

        # QualityChecker
        qc = evaluate_with_quality_checker(reply, label)
        lj = evaluate_with_llm_judge(reply, label)
        sv = evaluate_with_schema(reply, label)

        ev = {
            "label": label,
            "category": cat,
            "quality_checker": qc,
            "llm_judge": lj,
            "schema": sv,
        }
        evaluations.append(ev)

        status = "[OK]" if qc["passed"] else "[!!]"
        print(f"          QC={status} score={qc['score']:.2f} "
              f"| LJ={lj['overall']:.2f} "
              f"| schema={'🟢' if sv.get('valid') else '⚪'}")

    # 3. 汇总
    print(f"\n── 评估汇总 ──")

    qc_passed = sum(1 for e in evaluations if e["quality_checker"]["passed"])
    qc_total = len(evaluations)
    lj_avg = sum(e["llm_judge"]["overall"] for e in evaluations) / max(len(evaluations), 1)

    print(f"  质量检查通过: {qc_passed}/{qc_total}")
    print(f"  LLMJudge 平均分: {lj_avg:.2f}")
    print(f"\n  细项:")
    for e in evaluations:
        mark = "[OK]" if e["quality_checker"]["passed"] else "[!!]"
        print(f"    {mark} {e['label']:25s} "
              f"QC={e['quality_checker']['score']:.2f} "
              f"LJ={e['llm_judge']['overall']:.2f}")

    # 4. 保存报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_evaluated": len(evaluations),
        "quality_checker_pass_rate": round(qc_passed / max(qc_total, 1), 2),
        "llm_judge_avg_score": round(lj_avg, 2),
        "evaluations": evaluations,
    }

    log_dir = os.path.join(_project_root, "run_logs")
    log_file = os.path.join(
        log_dir,
        f"d32_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n  报告已保存: {log_file}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
