"""
Prompt 回归测试体系

功能：
1. 回归用例集管理（增删改查、分类、版本标记）
2. 自动 A/B 对比（旧版本 vs 新版本的 Prompt 表现差异）
3. 通过率门禁（设定阈值，判定是否达标）

面试话术：
    "回归测试是 Prompt 版本管理的核心环节。
    我们每次修改 System Prompt 或调整参数后，
    都会跑一套回归用例集——包含 50+ 条基准用例。
    每条用例标注了期望行为，自动化对比新旧版本的回复。

    有一次我们改了一个词，90% 的用例都过了，
    但有 3 条关键安全用例的期望行为变了。
    如果没有回归测试，这个改动可能直接上线。"
"""
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json


# ---------------------------------------------------------------------------
# 用例类型
# ---------------------------------------------------------------------------

class CaseCategory(Enum):
    """测试用例分类"""
    FUNCTIONAL = "functional"          # 功能正确性
    SECURITY = "security"              # 安全边界
    QUALITY = "quality"                # 回复质量
    EDGE_CASE = "edge_case"            # 边界输入
    BUSINESS = "business"              # 业务场景


class Verdict(Enum):
    """测试判定"""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class RegressionCase:
    """单条回归测试用例"""
    id: str                            # 用例编号 e.g. REG-001
    category: CaseCategory             # 用例分类
    prompt: str                        # 输入 prompt
    expected_behavior: str             # 期望行为描述
    tags: List[str] = field(default_factory=list)  # 标签 e.g. ["security", "critical"]
    expected_keywords: List[str] = field(default_factory=list)  # 回复中应含关键词
    forbidden_keywords: List[str] = field(default_factory=list) # 回复中不应含关键词
    min_length: int = 0                # 最小回复长度
    max_length: int = 99999            # 最大回复长度
    created_at: str = ""               # 创建时间
    version: str = "v1"                # 版本标记

    def display(self) -> str:
        return f"[{self.id}] ({self.category.value}) {self.prompt[:50]}..."

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "category": self.category.value,
            "prompt": self.prompt, "expected": self.expected_behavior,
            "tags": self.tags, "version": self.version,
        }


@dataclass
class RegressionResult:
    """单条测试结果"""
    case: RegressionCase
    actual_response: str               # 模型实际回复
    passed: bool                       # 是否通过
    failures: List[str] = field(default_factory=list)  # 失败原因列表
    response_length: int = 0           # 回复长度
    runtime_ms: float = 0.0            # 耗时

    @property
    def tag(self) -> str:
        return "[OK]" if self.passed else "[!!]"


@dataclass
class RegressionReport:
    """回归测试报告"""
    total: int
    passed: int
    failed: int
    pass_rate: float                   # 通过率
    breakdown: Dict[str, Dict]         # 按分类细分
    failures_detail: List[RegressionResult]  # 失败用例详情
    summary: str                       # 总结
    version: str = ""                  # 测试版本
    timestamp: str = ""                # 测试时间

    def display(self) -> str:
        lines = [
            f"--- Regression Test Report ---",
            f"Version: {self.version or 'N/A'}",
            f"Timestamp: {self.timestamp or 'N/A'}",
            f"Total: {self.total}  |  Passed: {self.passed}  |  Failed: {self.failed}",
            f"Pass rate: {self.pass_rate:.1%}",
            "",
            "--- Breakdown By Category ---",
        ]
        for cat, stats in sorted(self.breakdown.items()):
            rate = stats["passed"] / max(stats["total"], 1)
            lines.append(f"  {cat}: {stats['passed']}/{stats['total']} ({rate:.0%})")
        if self.failures_detail:
            lines.append("")
            lines.append("--- Failed Cases ---")
            for r in self.failures_detail[:5]:
                lines.append(f"  [{r.case.id}] {r.case.prompt[:40]:40s} -> {r.failures}")
        lines.append("")
        lines.append(f"Summary: {self.summary}")
        return "\n".join(lines)


@dataclass
class ABTestResult:
    """A/B 对比结果"""
    case_id: str
    prompt: str
    expected: str
    a_response: str                    # 旧版本回复
    b_response: str                    # 新版本回复
    a_passed: bool                     # 旧版本是否通过
    b_passed: bool                     # 新版本是否通过
    changed: bool                      # 结果是否变化（新版本 old_pass -> new_fail 或反之）
    regression: bool                   # 是否退化（old_pass -> new_fail）


@dataclass
class ABTestReport:
    """A/B 对比报告"""
    total: int
    a_pass_rate: float                 # 旧版本通过率
    b_pass_rate: float                 # 新版本通过率
    regressions: int                   # 退化的用例数
    improvements: int                  # 改善的用例数
    unchanged: int                     # 不变的用例数
    details: List[ABTestResult]        # 详细对比
    summary: str                       # 总结

    def display(self) -> str:
        lines = [
            "--- A/B Regression Comparison ---",
            f"Total cases: {self.total}",
            f"  Version A pass rate: {self.a_pass_rate:.1%}",
            f"  Version B pass rate: {self.b_pass_rate:.1%}",
            f"  Regressions: {self.regressions}  |  Improvements: {self.improvements}",
            f"  Unchanged: {self.unchanged}",
            "",
        ]
        if self.regressions > 0:
            lines.append("--- Regressions (OLD pass -> NEW fail) ---")
            for d in self.details:
                if d.regression:
                    lines.append(f"  [{d.case_id}] {d.prompt[:40]}")
        lines.append("")
        lines.append(f"Summary: {self.summary}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 回归用例库
# ---------------------------------------------------------------------------

class RegressionLibrary:
    """
    回归测试用例库

    功能：
    1. 添加/更新/删除用例
    2. 按分类/标签/版本过滤
    3. 导出/导入 JSON
    4. 版本快照
    """

    def __init__(self):
        self._cases: Dict[str, RegressionCase] = {}
        self._index = 0

    # ---- 增删改查 ----

    def add(self, case: RegressionCase) -> str:
        if not case.id:
            self._index += 1
            case.id = f"REG-{self._index:03d}"
        if not case.created_at:
            case.created_at = datetime.now().isoformat()
        self._cases[case.id] = case
        return case.id

    def add_batch(self, cases: List[RegressionCase]) -> List[str]:
        return [self.add(c) for c in cases]

    def get(self, case_id: str) -> Optional[RegressionCase]:
        return self._cases.get(case_id)

    def remove(self, case_id: str) -> bool:
        return self._cases.pop(case_id, None) is not None

    def update(self, case_id: str, **kwargs) -> bool:
        case = self._cases.get(case_id)
        if not case:
            return False
        for key, value in kwargs.items():
            if hasattr(case, key):
                setattr(case, key, value)
        return True

    def all(self) -> List[RegressionCase]:
        return list(self._cases.values())

    def count(self) -> int:
        return len(self._cases)

    def filter(
        self,
        category: Optional[CaseCategory] = None,
        tag: Optional[str] = None,
        version: Optional[str] = None,
    ) -> List[RegressionCase]:
        results = self.all()
        if category:
            results = [c for c in results if c.category == category]
        if tag:
            results = [c for c in results if tag in c.tags]
        if version:
            results = [c for c in results if c.version == version]
        return results

    def categories(self) -> Dict[str, int]:
        """返回各类别的用例数"""
        counts = {}
        for c in self._cases.values():
            cat = c.category.value
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    # ---- 导入导出 ----

    def export_json(self) -> str:
        data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "count": self.count(),
            "cases": [c.to_dict() for c in self.all()],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def import_json(self, json_str: str) -> int:
        data = json.loads(json_str)
        count = 0
        for item in data.get("cases", []):
            case = RegressionCase(
                id=item.get("id", ""),
                category=CaseCategory(item.get("category", "functional")),
                prompt=item.get("prompt", ""),
                expected_behavior=item.get("expected", ""),
                tags=item.get("tags", []),
                version=item.get("version", "v1"),
            )
            self._cases[case.id] = case
            count += 1
        return count

    def clear(self):
        self._cases.clear()
        self._index = 0


# ---------------------------------------------------------------------------
# 回归测试执行器
# ---------------------------------------------------------------------------

class RegressionTester:
    """
    回归测试执行器

    对一组回归用例执行测试，基于规则判定通过/失败：
    - expected_keywords: 必须包含的关键词
    - forbidden_keywords: 不能包含的关键词
    - min_length / max_length: 长度范围
    """

    def __init__(self, library: Optional[RegressionLibrary] = None):
        self.library = library or RegressionLibrary()

    def run(
        self,
        cases: Optional[List[RegressionCase]] = None,
        api_func: Optional[Callable] = None,
        mock_responses: Optional[Dict[str, str]] = None,
    ) -> RegressionReport:
        if cases is None:
            cases = self.library.all()

        if not cases:
            return self._empty_report()

        results: List[RegressionResult] = []
        for case in cases:
            if mock_responses and case.id in mock_responses:
                response = mock_responses[case.id]
            elif api_func:
                response = api_func(case.prompt)
            else:
                continue

            result = self._judge(case, response)
            results.append(result)

        return self._build_report(results)

    def _judge(self, case: RegressionCase, response: str) -> RegressionResult:
        """基于规则判定一条用例的通过/失败"""
        failures = []
        response_lower = response.lower()

        # 1. 检查 must_contain 关键词
        for kw in case.expected_keywords:
            if kw.lower() not in response_lower:
                failures.append(f"缺少期望关键词: {kw}")

        # 2. 检查 forbidden 关键词
        for kw in case.forbidden_keywords:
            if kw.lower() in response_lower:
                failures.append(f"含禁止关键词: {kw}")

        # 3. 检查长度
        resp_len = len(response)
        if resp_len < case.min_length:
            failures.append(f"回复过短: {resp_len} < {case.min_length}")
        if resp_len > case.max_length:
            failures.append(f"回复过长: {resp_len} > {case.max_length}")

        passed = len(failures) == 0
        return RegressionResult(
            case=case, actual_response=response[:200],
            passed=passed, failures=failures,
            response_length=resp_len,
        )

    def _empty_report(self) -> RegressionReport:
        return RegressionReport(
            total=0, passed=0, failed=0,
            pass_rate=1.0, breakdown={},
            failures_detail=[], summary="无测试用例",
        )

    def _build_report(self, results: List[RegressionResult]) -> RegressionReport:
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        # 按分类细分
        breakdown: Dict[str, Dict] = {}
        for r in results:
            cat = r.case.category.value
            if cat not in breakdown:
                breakdown[cat] = {"total": 0, "passed": 0, "failed": 0}
            breakdown[cat]["total"] += 1
            if r.passed:
                breakdown[cat]["passed"] += 1
            else:
                breakdown[cat]["failed"] += 1

        pass_rate = passed / total if total > 0 else 1.0
        failures_detail = [r for r in results if not r.passed]

        if pass_rate >= 0.95:
            summary = f"[OK] 通过率 {pass_rate:.1%}，回归测试通过"
        elif pass_rate >= 0.80:
            summary = f"[OK] 通过率 {pass_rate:.1%}，需要关注失败用例"
        else:
            summary = f"[!!] 通过率 {pass_rate:.1%}，回归测试未通过"

        return RegressionReport(
            total=total, passed=passed, failed=failed,
            pass_rate=pass_rate, breakdown=breakdown,
            failures_detail=failures_detail, summary=summary,
            version="v1",
            timestamp=datetime.now().isoformat(),
        )

    # ---- A/B 对比 ----

    def ab_compare(
        self,
        cases: List[RegressionCase],
        api_a: Callable,          # 旧版本模型调用函数
        api_b: Callable,          # 新版本模型调用函数
    ) -> ABTestReport:
        """
        A/B 对比测试：同一组用例分别在旧版和新版模型上跑。
        """
        details: List[ABTestResult] = []
        regressions = 0
        improvements = 0
        unchanged = 0

        for case in cases:
            resp_a = api_a(case.prompt)
            resp_b = api_b(case.prompt)

            result_a = self._judge(case, resp_a)
            result_b = self._judge(case, resp_b)

            changed = result_a.passed != result_b.passed
            is_regression = result_a.passed and not result_b.passed
            is_improvement = not result_a.passed and result_b.passed

            if is_regression:
                regressions += 1
            elif is_improvement:
                improvements += 1
            else:
                unchanged += 1

            details.append(ABTestResult(
                case_id=case.id, prompt=case.prompt,
                expected=case.expected_behavior,
                a_response=resp_a[:150], b_response=resp_b[:150],
                a_passed=result_a.passed, b_passed=result_b.passed,
                changed=changed, regression=is_regression,
            ))

        a_pass_rate = sum(1 for d in details if d.a_passed) / max(len(details), 1)
        b_pass_rate = sum(1 for d in details if d.b_passed) / max(len(details), 1)

        if regressions == 0 and b_pass_rate >= a_pass_rate:
            summary = f"[OK] 新版本无退化，通过率 {b_pass_rate:.1%}（旧版 {a_pass_rate:.1%}）"
        elif regressions > 0:
            summary = f"[!!] 发现 {regressions} 个退化，新版本 {b_pass_rate:.1%} vs 旧版 {a_pass_rate:.1%}"
        else:
            summary = f"[OK] 新版本 {b_pass_rate:.1%} vs 旧版 {a_pass_rate:.1%}"

        return ABTestReport(
            total=len(details),
            a_pass_rate=a_pass_rate,
            b_pass_rate=b_pass_rate,
            regressions=regressions,
            improvements=improvements,
            unchanged=unchanged,
            details=details,
            summary=summary,
        )

    # ---- 门禁检查 ----

    def gating_check(
        self,
        report: RegressionReport,
        threshold: float = 0.95,
    ) -> Tuple[bool, str]:
        """
        门禁检查：测试报告是否通过门禁阈值。

        Returns:
            (是否通过, 门禁结果信息)
        """
        if report.total == 0:
            return True, "[OK] 无测试用例，跳过门禁"

        if report.pass_rate >= threshold:
            return True, f"[OK] 通过率 {report.pass_rate:.1%} >= {threshold:.0%}，门禁通过"
        else:
            failed_ids = [r.case.id for r in report.failures_detail]
            return False, (
                f"[!!] 通过率 {report.pass_rate:.1%} < {threshold:.0%}，门禁拦截\n"
                f"     失败用例: {', '.join(failed_ids[:10])}"
            )
