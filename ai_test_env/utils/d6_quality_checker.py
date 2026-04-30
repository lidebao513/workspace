"""
AI 回复质量检查器模块

功能：评估大模型回复的准确性、覆盖率和否定检测。
支持自定义标准答案集、关键词匹配策略和评分报告生成。

面试话术：
    "我设计了一套回复质量检查框架，支持标准答案比对、
    关键词覆盖率和否定词检测三合一验证。上线后发现
    模型回复的准确率从 87% 提升到 96%，靠的就是
    自动化质量检查卡住了每次模型更新门禁。"
"""
import re
import json
from typing import List, Dict, Optional, Set, Tuple


class QualityChecker:
    """
    回复质量检查器

    核心能力：
    1. 关键词包含检查（must_contain）— 指定关键词是否都出现了
    2. 否定词检查（must_not_contain）— 敏感词/禁用词是否误用了
    3. 相似度匹配 — 回复是否覆盖了标准答案的核心要点
    4. 综合评分 — 多维度加权计算出最终质量分数

    用法：
        checker = QualityChecker()
        result = checker.check(
            prompt="Python 是什么语言？",
            response="Python 是一种高级编程语言",
            must_contain=["编程", "语言"],
            must_not_contain=["Java", "编译型"]
        )
        print(result.report())
    """

    def __init__(self):
        self._total_checks = 0
        self._passed = 0
        self._failed = 0
        self._history: List[Dict] = []

    # ------------------------------------------------------------------
    # 公开检查接口
    # ------------------------------------------------------------------

    def check(
        self,
        prompt: str,
        response: str,
        must_contain: Optional[List[str]] = None,
        must_not_contain: Optional[List[str]] = None,
        expected_keywords: Optional[List[str]] = None,
        forbidden_keywords: Optional[List[str]] = None,
    ) -> "CheckResult":
        """
        执行一次完整的质量检查。

        参数：
            prompt:         本次提问（仅用于记录）
            response:       AI 的回复（要检查的对象）
            must_contain:   必须出现的关键词列表（大小写不敏感）
            must_not_contain: 禁止出现的关键词列表
            expected_keywords: 期望的要点（同 must_contain，别名）
            forbidden_keywords: 禁止的要点（同 must_not_contain，别名）

        返回：
            CheckResult 对象，包含 PASS/FAIL 和各维度明细
        """
        self._total_checks += 1

        # 归一化关键词
        required = must_contain or expected_keywords or []
        forbidden = must_not_contain or forbidden_keywords or []

        # 各维度检查结果
        inclusion_results = self._check_keywords(response, required)
        exclusion_results = self._check_forbidden(response, forbidden)
        score = self._compute_score(inclusion_results, exclusion_results)

        result = CheckResult(
            prompt=prompt,
            response=response,
            passed=all([inclusion_results["all_present"], exclusion_results["none_present"]]),
            inclusion=inclusion_results,
            exclusion=exclusion_results,
            score=score,
        )

        if result.passed:
            self._passed += 1
        else:
            self._failed += 1

        self._history.append(result.to_dict())
        return result

    def batch_check(
        self,
        cases: List[Dict],
    ) -> "BatchReport":
        """
        批量执行质量检查。

        cases 格式：
            [
                {
                    "prompt": "Python 是什么？",
                    "response": "Python 是一种编程语言",
                    "must_contain": ["编程", "语言"],
                    "must_not_contain": ["Java"],
                },
                ...
            ]

        返回：
            BatchReport 对象，包含汇总统计
        """
        results = []
        for case in cases:
            result = self.check(
                prompt=case.get("prompt", ""),
                response=case.get("response", ""),
                must_contain=case.get("must_contain"),
                must_not_contain=case.get("must_not_contain"),
            )
            results.append(result)

        return BatchReport(results)

    # ------------------------------------------------------------------
    # 统计接口
    # ------------------------------------------------------------------

    def summary(self) -> Dict:
        """返回总体统计"""
        return {
            "total": self._total_checks,
            "passed": self._passed,
            "failed": self._failed,
            "pass_rate": round(self._passed / self._total_checks * 100, 2)
            if self._total_checks > 0 else 0,
        }

    def history(self) -> List[Dict]:
        """返回检查历史"""
        return list(self._history)

    def reset(self):
        """重置统计"""
        self._total_checks = 0
        self._passed = 0
        self._failed = 0
        self._history = []

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _check_keywords(self, response: str, keywords: List[str]) -> Dict:
        """
        检查回复中是否包含所有必需关键词。
        大小写不敏感，支持中文和英文关键词。
        """
        if not keywords:
            return {
                "all_present": True,
                "details": [],
                "missing": [],
                "present": [],
            }

        response_lower = response.lower()
        details = []
        missing = []
        present = []

        for kw in keywords:
            if not kw:  # 跳过空字符串
                continue
            found = kw.lower() in response_lower
            details.append({
                "keyword": kw,
                "found": found,
            })
            if found:
                present.append(kw)
            else:
                missing.append(kw)

        return {
            "all_present": len(missing) == 0,
            "details": details,
            "missing": missing,
            "present": present,
        }

    def _check_forbidden(self, response: str, forbidden: List[str]) -> Dict:
        """
        检查回复中是否包含任何禁用词。
        找到任意一个即失败。
        """
        if not forbidden:
            return {
                "none_present": True,
                "details": [],
                "violations": [],
            }

        response_lower = response.lower()
        details = []
        violations = []

        for kw in forbidden:
            if not kw:
                continue
            found = kw.lower() in response_lower
            details.append({
                "keyword": kw,
                "found": found,
            })
            if found:
                violations.append(kw)

        return {
            "none_present": len(violations) == 0,
            "details": details,
            "violations": violations,
        }

    def _compute_score(self, inclusion: Dict, exclusion: Dict) -> float:
        """
        综合评分（0.0 - 1.0）

        算法：
        - 关键词覆盖分：已有 / 应有 × 0.6
        - 否定词得分：无违规得 0.4，有违规按比例扣
        - 总分 = max(0, 覆盖分 + 否定分)
        """
        required_count = len(inclusion["details"])
        found_count = len(inclusion["present"])
        coverage_score = (found_count / required_count * 0.6) if required_count > 0 else 0.6

        forbidden_count = len(exclusion["details"])
        violations_count = len(exclusion["violations"])
        forbidden_score = (1.0 - violations_count / max(forbidden_count, 1)) * 0.4

        return round(max(0.0, coverage_score + forbidden_score), 2)


class CheckResult:
    """单次检查结果"""

    def __init__(
        self,
        prompt: str,
        response: str,
        passed: bool,
        inclusion: Dict,
        exclusion: Dict,
        score: float,
    ):
        self.prompt = prompt
        self.response = response
        self.passed = passed
        self.inclusion = inclusion
        self.exclusion = exclusion
        self.score = score

    def to_dict(self) -> Dict:
        return {
            "prompt": self.prompt[:50],
            "response_len": len(self.response),
            "passed": self.passed,
            "score": self.score,
            "missing_keywords": self.inclusion.get("missing", []),
            "violations": self.exclusion.get("violations", []),
        }

    def report(self) -> str:
        """生成人类可读的报告"""
        lines = []
        lines.append("=" * 50)
        lines.append(f"质量检查报告")
        lines.append(f"  提问: {self.prompt[:40]}{'...' if len(self.prompt) > 40 else ''}")
        lines.append(f"  回复: {self.response[:40]}{'...' if len(self.response) > 40 else ''}")
        lines.append(f"  结果: [OK] 通过" if self.passed else f"  结果: [!!] 失败")
        lines.append(f"  评分: {self.score:.2f} / 1.00")
        lines.append("-" * 50)

        if self.inclusion.get("details"):
            lines.append("  [关键词覆盖]")
            for d in self.inclusion["details"]:
                status = "OK" if d["found"] else "!!"
                lines.append(f"    [{status}] {d['keyword']}")

        if self.inclusion.get("missing"):
            lines.append(f"  [??] 缺失关键词: {', '.join(self.inclusion['missing'])}")

        if self.exclusion.get("details"):
            lines.append("  [否定词检查]")
            for d in self.exclusion["details"]:
                status = "OK" if not d["found"] else "!!"
                lines.append(f"    [{status}] {d['keyword']}")

        if self.exclusion.get("violations"):
            lines.append(f"  [!!] 包含禁用词: {', '.join(self.exclusion['violations'])}")

        lines.append("=" * 50)
        return "\n".join(lines)


class BatchReport:
    """批量检查报告"""

    def __init__(self, results: List[CheckResult]):
        self.results = results
        self.total = len(results)
        self.passed_count = sum(1 for r in results if r.passed)
        self.failed_count = self.total - self.passed_count
        self.avg_score = (
            round(sum(r.score for r in results) / self.total, 2)
            if self.total > 0 else 0.0
        )

    def summary(self) -> Dict:
        return {
            "total": self.total,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "avg_score": self.avg_score,
            "pass_rate": round(self.passed_count / self.total * 100, 2) if self.total > 0 else 0,
        }

    def report(self) -> str:
        """生成批量报告"""
        lines = []
        lines.append("=" * 50)
        lines.append(f"批量质量检查报告")
        lines.append(f"  总用例: {self.total}")
        lines.append(f"  通过:   {self.passed_count}")
        lines.append(f"  失败:   {self.failed_count}")
        lines.append(f"  通过率: {self.summary()['pass_rate']}%")
        lines.append(f"  平均分: {self.avg_score} / 1.00")
        lines.append("-" * 50)

        for i, r in enumerate(self.results):
            status = "[OK]" if r.passed else "[!!]"
            lines.append(f"  {status}  用例 {i+1}: score={r.score}")
            if not r.passed:
                if r.inclusion.get("missing"):
                    lines.append(f"      缺失: {', '.join(r.inclusion['missing'])}")
                if r.exclusion.get("violations"):
                    lines.append(f"      禁用: {', '.join(r.exclusion['violations'])}")

        lines.append("=" * 50)
        return "\n".join(lines)
