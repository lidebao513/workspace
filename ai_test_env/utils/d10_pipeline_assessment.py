"""
Week 2 统一质量评估报告生成器

功能：整合 Day 6-9 的四个工具（QualityChecker, ConsistencyChecker,
TruncationAnalyzer, LLMJudge）为统一的端到端评估流水线。
生成综合质量报告，包含各维度评分、趋势分析和改进建议。

面试话术：
    "我搭建了一套端到端的 AI 回复质量评估流水线，整合了质检查、
    一致性验证、截断监控和 LLM-as-Judge 四种评估方法。
    每个模型版本发布前跑 500 条测试用例，从四个维度评估质量变化，
    自动生成报告和门禁决策。上线后质量评估从 4 天缩短到 30 分钟。"
"""
import json
import time
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from utils.d6_quality_checker import QualityChecker, CheckResult
    from utils.d7_consistency_checker import ConsistencyChecker, ConsistencyResult
    from utils.d8_truncation_analyzer import TruncationAnalyzer, TruncationReport
    from utils.d9_llm_judge import LLMJudge, JudgeResult, BatchJudgeReport, ABCompareResult
else:
    from .d6_quality_checker import QualityChecker, CheckResult
    from .d7_consistency_checker import ConsistencyChecker, ConsistencyResult
    from .d8_truncation_analyzer import TruncationAnalyzer, TruncationReport
    from .d9_llm_judge import LLMJudge, JudgeResult, BatchJudgeReport, ABCompareResult


# ---------------------------------------------------------------------------
# 评估报告数据结构
# ---------------------------------------------------------------------------

@dataclass
class QualityReport:
    """完整质量评估报告"""
    # 基本信息
    model_name: str = ""
    test_date: str = ""
    test_suite: str = ""
    total_cases: int = 0

    # Day 6 结果：质量检查
    quality_score: float = 0.0
    quality_pass_rate: float = 0.0
    quality_details: List[Dict] = field(default_factory=list)

    # Day 7 结果：一致性检查
    consistency_score: float = 0.0
    consistency_level: str = ""
    consistency_details: List[Dict] = field(default_factory=list)

    # Day 8 结果：截断分析
    truncation_rate: float = 0.0
    truncation_level: str = ""
    max_tokens_advice: int = 0
    truncation_details: Dict = field(default_factory=dict)

    # Day 9 结果：LLM-as-Judge
    judge_avg_score: float = 0.0
    judge_details: List[Dict] = field(default_factory=list)

    # 综合
    overall_score: float = 0.0
    overall_grade: str = ""
    issues: List[Dict] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "model": self.model_name,
            "test_date": self.test_date,
            "total_cases": self.total_cases,
            "overall_score": self.overall_score,
            "overall_grade": self.overall_grade,
            "quality": {"score": self.quality_score, "pass_rate": self.quality_pass_rate},
            "consistency": {"score": self.consistency_score, "level": self.consistency_level},
            "truncation": {"rate": self.truncation_rate, "level": self.truncation_level},
            "judge": {"avg_score": self.judge_avg_score},
            "issues": len(self.issues),
            "recommendations": len(self.recommendations),
        }


@dataclass
class AssessmentPipelineConfig:
    """流水线配置"""
    quality_checker: Optional[QualityChecker] = None
    consistency_checker: Optional[ConsistencyChecker] = None
    truncation_analyzer: Optional[TruncationAnalyzer] = None
    llm_judge: Optional[LLMJudge] = None
    verbose: bool = True


# ---------------------------------------------------------------------------
# 等级计算
# ---------------------------------------------------------------------------

def compute_overall_grade(score: float) -> str:
    """综合评分等级映射"""
    if score >= 0.90:
        return "A+"
    elif score >= 0.80:
        return "A"
    elif score >= 0.70:
        return "B+"
    elif score >= 0.60:
        return "B"
    elif score >= 0.50:
        return "C"
    else:
        return "D"


def compute_overall_score(
    quality: float,
    consistency: float,
    truncation: float,
    judge: float,
) -> float:
    """
    综合评分计算（0 - 1.0）

    权重：
    - Day 6 质量检查: 0.25（关键词覆盖 + 否定检测）
    - Day 7 一致性:    0.15（对同一问题的回复稳定性）
    - Day 8 截断率:    0.10（低截断 = 高得分）
    - Day 9 LLM评分:   0.50（最重要的指标）

    truncation 需要转换：低截断率高分
        score = 1.0 - truncation_rate
    """
    # 截断分转换（越低越好）
    # 截断分转换：无数据时得 0 分，有数据时低截断率得高分
    truncation_score = max(0.0, 1.0 - min(truncation, 1.0)) if truncation > 0 else 0.0

    count = 0
    weighted_sum = 0.0

    if quality > 0:
        weighted_sum += quality * 0.25
        count += 1
    if consistency > 0:
        weighted_sum += consistency * 0.15
        count += 1
    if truncation > 0:
        weighted_sum += truncation_score * 0.10
        count += 1
    if judge > 0:
        weighted_sum += judge * 0.50
        count += 1

    if count == 0:
        return 0.0

    # 归一化：按实际参与的模块重新分配权重
    total_available_weight = 0.25 if quality > 0 else 0
    total_available_weight += 0.15 if consistency > 0 else 0
    total_available_weight += 0.10 if truncation > 0 else 0
    total_available_weight += 0.50 if judge > 0 else 0

    score = weighted_sum / total_available_weight if total_available_weight > 0 else 0.0
    return round(score, 2)


# ---------------------------------------------------------------------------
# 流水线主类
# ---------------------------------------------------------------------------

class AssessmentPipeline:
    """
    Week 2 统一质量评估流水线

    将 Day 6-9 四个工具整合为一条端到端流水线：

    1. Quality Check    (Day 6) → 关键词覆盖和否定检测
    2. Consistency      (Day 7) → 多轮回复一致性
    3. Truncation       (Day 8) → 截断率和 max_tokens 分析
    4. LLM-as-Judge     (Day 9) → 多维自动评分

    用法（离线模式）：
        pipeline = AssessmentPipeline()

        report = pipeline.run_offline(
            model_name="DeepSeek-v4",
            quality_cases=[...],      # QualityChecker 用例
            consistency_cases=[...],  # ConsistencyChecker 用例
            truncation_records=[...], # TruncationAnalyzer 记录
            judge_cases=[...],        # LLMJudge 用例
        )
        print(report.to_dict())
    """

    def __init__(self, config: Optional[AssessmentPipelineConfig] = None):
        config = config or AssessmentPipelineConfig()
        self.quality = config.quality_checker or QualityChecker()
        self.consistency = config.consistency_checker or ConsistencyChecker()
        self.truncation = config.truncation_analyzer or TruncationAnalyzer()
        self.judge = config.llm_judge or LLMJudge()
        self.verbose = config.verbose
        self._run_history: List[QualityReport] = []

    # ------------------------------------------------------------------
    # 离线全量评估
    # ------------------------------------------------------------------

    def run_offline(
        self,
        model_name: str = "unknown",
        test_suite: str = "default",
        quality_cases: Optional[List[Dict]] = None,
        consistency_cases: Optional[List[Dict]] = None,
        truncation_records: Optional[List[Dict]] = None,
        judge_cases: Optional[List[Dict]] = None,
    ) -> QualityReport:
        """
        完整离线评估：传入各工具的测试数据，输出综合报告。

        quality_cases 格式（给 QualityChecker）：
            [{"prompt": "...", "response": "...",
              "must_contain": [...], "must_not_contain": [...]}]

        consistency_cases 格式（给 ConsistencyChecker）：
            [{"prompt": "...", "responses": [..., ..., ...],
              "temperature": 0.0}]

        truncation_records 格式（给 TruncationAnalyzer）：
            [{"prompt": "...", "response_len": ..., "finish_reason": "...",
              "max_tokens": ..., "total_tokens": ...}]

        judge_cases 格式（给 LLMJudge.score_offline）：
            [{"prompt": "...", "response": "...", "judge_raw": "..."}]
        """
        report = QualityReport(
            model_name=model_name,
            test_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            test_suite=test_suite,
        )

        # 步骤 1：质量检查（Day 6）
        if quality_cases:
            self._log("Step 1/4: 质量检查...")
            batch = self.quality.batch_check(quality_cases)
            summary = batch.summary()
            report.quality_score = summary["avg_score"]
            report.quality_pass_rate = summary["pass_rate"]
            report.quality_details = [
                {"prompt": r.prompt[:30], "passed": r.passed, "score": r.score}
                for r in batch.results
            ]

            # 记录问题
            for r in batch.results:
                if not r.passed and r.score < 0.5:
                    report.issues.append({
                        "source": "quality_check",
                        "severity": "high",
                        "detail": f"低质量回复: {r.prompt[:30]}, score={r.score}",
                    })

            total = max(len(quality_cases), report.total_cases)
            report.total_cases = total

        # 步骤 2：一致性检查（Day 7）
        if consistency_cases:
            self._log("Step 2/4: 一致性检查...")
            consistency_scores = []
            for case in consistency_cases:
                r = self.consistency.analyze_responses(
                    prompt=case["prompt"],
                    responses=case["responses"],
                    temperature=case.get("temperature", 0.0),
                )
                consistency_scores.append(r.consistency_score)

            report.consistency_score = round(
                sum(consistency_scores) / len(consistency_scores), 2
            ) if consistency_scores else 0.0

            # 用最后一个结果代表等级
            report.consistency_level = (
                self.consistency.history()[-1]["level"]
                if self.consistency.history() else "未知"
            )

            report.consistency_details = [
                {"prompt": case["prompt"][:20],
                 "n_runs": len(case["responses"]),
                 "temperature": case.get("temperature", 0.0),
                 "score": s}
                for case, s in zip(consistency_cases, consistency_scores)
            ]

            # 记录低一致性
            for i, s in enumerate(consistency_scores):
                if s < 0.5:
                    report.issues.append({
                        "source": "consistency",
                        "severity": "medium",
                        "detail": f"低一致性: {consistency_cases[i]['prompt'][:20]}, score={s}",
                    })

        # 步骤 3：截断分析（Day 8）
        if truncation_records:
            self._log("Step 3/4: 截断分析...")
            self.truncation.record_batch(truncation_records)
            t_report = self.truncation.analyze()
            report.truncation_rate = t_report.truncation_rate
            report.truncation_level = t_report.level_info["label"]
            report.max_tokens_advice = t_report.recommendation["recommended"]
            report.truncation_details = t_report.to_dict()

            # 记录高截断问题
            if t_report.truncation_rate > 0.10:
                report.issues.append({
                    "source": "truncation",
                    "severity": "high" if t_report.truncation_rate > 0.20 else "medium",
                    "detail": f"截断率={t_report.truncation_rate:.1%}, "
                              f"建议调 max_tokens 到 {t_report.recommendation['recommended']}",
                })

        # 步骤 4：LLM-as-Judge 评分（Day 9）
        if judge_cases:
            self._log("Step 4/4: LLM-as-Judge 评分...")
            judge_results = []
            for case in judge_cases:
                r = self.judge.score_offline(
                    prompt=case["prompt"],
                    response=case["response"],
                    judge_raw_output=case["judge_raw"],
                )
                judge_results.append(r)

            batch = BatchJudgeReport(judge_results, self.judge.dimensions)
            report.judge_avg_score = batch.avg_score
            report.judge_details = [
                {"prompt": r.prompt[:30], "score": r.weighted_score,
                 "best_dim": max(r.scores, key=r.scores.get) if r.scores else "",
                 "worst_dim": min(r.scores, key=r.scores.get) if r.scores else ""}
                for r in judge_results
            ]

            # 记录低分
            for r in judge_results:
                if r.weighted_score < 0.5:
                    report.issues.append({
                        "source": "llm_judge",
                        "severity": "high",
                        "detail": f"低评分回复: {r.prompt[:30]}, score={r.weighted_score}",
                    })

        # 综合评分
        report.overall_score = compute_overall_score(
            quality=report.quality_score,
            consistency=report.consistency_score,
            truncation=report.truncation_rate,
            judge=report.judge_avg_score,
        )
        report.overall_grade = compute_overall_grade(report.overall_score)

        # 生成改进建议
        report.recommendations = self._generate_recommendations(report)

        self._run_history.append(report)
        return report

    # ------------------------------------------------------------------
    # 版本对比
    # ------------------------------------------------------------------

    def compare_versions(
        self,
        report_v1: QualityReport,
        report_v2: QualityReport,
    ) -> Dict:
        """
        比较两个版本的质量报告。
        用于：模型更新前 vs 更新后、优化前 vs 优化后。
        """
        deltas = {}
        deltas["overall"] = round(report_v2.overall_score - report_v1.overall_score, 2)
        deltas["quality"] = round(report_v2.quality_score - report_v1.quality_score, 2)
        deltas["consistency"] = round(report_v2.consistency_score - report_v1.consistency_score, 2)
        deltas["truncation_rate"] = round(report_v2.truncation_rate - report_v1.truncation_rate, 4)
        deltas["judge"] = round(report_v2.judge_avg_score - report_v1.judge_avg_score, 2)

        status = "PASS" if deltas["overall"] >= 0 else "WARN"

        return {
            "version_a": report_v1.model_name,
            "version_b": report_v2.model_name,
            "status": status,
            "deltas": deltas,
            "v1_grade": report_v1.overall_grade,
            "v2_grade": report_v2.overall_grade,
            "new_issues": len(report_v2.issues) - len(report_v1.issues),
            "detail": (
                f"综合评分: {deltas['overall']:+0.2f} "
                f"({report_v1.overall_score:.2f} -> {report_v2.overall_score:.2f}), "
                f"等级: {report_v1.overall_grade} -> {report_v2.overall_grade}, "
                f"状态: {status}"
            ),
        }

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _log(self, msg: str):
        if self.verbose:
            print(f"  {msg}")

    def _generate_recommendations(self, report: QualityReport) -> List[str]:
        """自动生成改进建议"""
        recs = []

        if report.quality_score < 0.7:
            recs.append("质量分偏低：检查 must_contain 关键词覆盖率是否合理，"
                        "可考虑扩大关键词列表或降低部分维度权重。")
        elif report.quality_score < 0.5:
            recs.append("质量分严重偏低：存在大量 FAIL 检查，优先排查模型"
                        "回复是否跑题或包含禁用词。")

        if report.consistency_score < 0.5:
            recs.append(f"一致性不足（{report.consistency_score:.2f}）："
                        "考虑降低 temperature 或将关键业务场景锁定到 temp<0.3。")
            if report.consistency_level in ("低", "极低"):
                recs.append("一致性极低：建议排查是否为 temperature 过高或 prompt 不稳定导致。")

        if report.truncation_rate > 0.10:
            recs.append(f"截断率偏高（{report.truncation_rate:.1%}）："
                        f"建议将 max_tokens 调至 {report.max_tokens_advice}。")
        if report.truncation_rate > 0.20:
            recs.append(f"截断率严重（{report.truncation_rate:.1%}）："
                        "立即调整 max_tokens，同时排查是否有 prompt 过长导致可用配额不足。")

        if report.judge_avg_score < 0.6:
            recs.append(f"LLM 评分偏低（{report.judge_avg_score:.2f}）："
                        "检查是否所有维度的评分都低、还是某特定维度拉低了总分。")
        if report.judge_avg_score < 0.4:
            recs.append("LLM 评分极低：存在严重的回复质量问题，建议不发布此版本。")

        if not recs:
            recs.append("所有指标在健康范围内，继续观察。")

        return recs

    def history(self) -> List[Dict]:
        return [r.to_dict() for r in self._run_history]

    def reset(self):
        self.quality.reset()
        self.consistency.reset()
        self.truncation.reset()
        self.judge.reset()
        self._run_history = []


# ---------------------------------------------------------------------------
# 报告格式化输出
# ---------------------------------------------------------------------------

def format_report_console(report: QualityReport) -> str:
    """生成控制台可读的综合评估报告"""
    lines = []
    lines.append("=" * 60)
    lines.append("  AI 回复质量综合评估报告")
    lines.append("=" * 60)
    lines.append(f"  模型:      {report.model_name}")
    lines.append(f"  测试日期:  {report.test_date}")
    lines.append(f"  测试套件:  {report.test_suite}")
    lines.append(f"  用例数:    {report.total_cases}")
    lines.append("-" * 60)
    lines.append(f"  [综合] 综合质量评分:          {report.overall_score:.2f}")
    lines.append(f"  [综合] 综合质量等级:          {report.overall_grade}")
    lines.append("-" * 60)
    lines.append(f"  [Day6] 质量检查分:            {report.quality_score:.2f}")
    lines.append(f"  [Day6] 质量检查通过率:        {report.quality_pass_rate:.1f}%")
    lines.append(f"  [Day7] 一致性评分:            {report.consistency_score:.2f}")
    lines.append(f"  [Day7] 一致性等级:            {report.consistency_level}")
    lines.append(f"  [Day8] 截断率:                {report.truncation_rate:.1%}")
    lines.append(f"  [Day8] 截断等级:              {report.truncation_level}")
    lines.append(f"  [Day9] LLM 评分均值:          {report.judge_avg_score:.2f}")
    lines.append("-" * 60)
    lines.append(f"  发现的问题: {len(report.issues)} 个")
    for issue in report.issues:
        level = "[!!]" if issue["severity"] == "high" else "[??]"
        lines.append(f"    {level} [{issue['source']}] {issue['detail'][:60]}")
    lines.append("-" * 60)
    lines.append(f"  改进建议:")
    for i, rec in enumerate(report.recommendations, 1):
        lines.append(f"    {i}. {rec}")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_version_comparison(result: Dict) -> str:
    """生成版本对比报告"""
    lines = []
    lines.append("=" * 60)
    lines.append("  版本质量对比报告")
    lines.append("=" * 60)
    lines.append(f"  版本 A: {result['version_a']}  -> 等级 {result['v1_grade']}")
    lines.append(f"  版本 B: {result['version_b']} -> 等级 {result['v2_grade']}")
    lines.append(f"  综合评分变化: {result['deltas']['overall']:+0.2f}")
    lines.append("-" * 60)
    lines.append(f"    质量检查:    {result['deltas']['quality']:+0.2f}")
    lines.append(f"    一致性:      {result['deltas']['consistency']:+0.2f}")
    lines.append(f"    截断率变化:  {result['deltas']['truncation_rate']:+0.2%}")
    lines.append(f"    LLM 评分:    {result['deltas']['judge']:+0.2f}")
    lines.append("-" * 60)
    lines.append(f"  新版本问题数变化: {result['new_issues']:+d}")
    lines.append(f"  整体状态: {'[OK] 通过' if result['status'] == 'PASS' else '[!!] 需关注'}")
    lines.append("=" * 60)
    return "\n".join(lines)
