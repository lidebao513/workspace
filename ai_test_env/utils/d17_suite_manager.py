"""
Day 17 (Week 4 Day 2) — pytest 参数化 + 分层管理

实现：
1. TestSuiteManager — 将测试按层级组织（smoke/regression/security/performance）
2. @parametrized_case — 参数化装饰器，支持多轮组合和 CSV 导入
3. HTML report 集成（pytest-html）
4. 测试标签系统（@pytest.mark 映射）
5. 用例选择器（按层级 + 标签 + 模块运行）

面试话术：
    "我把 Week 1-3 的所有测试模块整合到一个 pytest 工程里，
    用自定义的 TestSuiteManager 分层管理：冒烟级（环境+连通）、
    回归级（所有功能）、安全级（注入+越狱）、性能级（并发）。
    通过 pytest.mark 打标签，可以在 CI 中灵活选择运行层级。"
"""
from typing import List, Dict, Optional, Tuple, Callable, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import os
import re


# ---------------------------------------------------------------------------
# 测试层级
# ---------------------------------------------------------------------------

class TestLevel(Enum):
    """测试层级"""
    SMOKE = "smoke"              # 冒烟 — 环境+连通性
    REGRESSION = "regression"    # 回归 — 全量功能
    SECURITY = "security"        # 安全 — 注入+越狱
    PERFORMANCE = "performance"  # 性能 — 并发+响应时间
    E2E = "e2e"                  # 端到端 — 业务场景
    ALL = "all"                  # 全部
    __test__ = False  # 防止 pytest 误收集


class TagCategory(Enum):
    """标签分类"""
    API = "api"
    QUALITY = "quality"
    SECURITY = "security"
    CONVERSATION = "conversation"
    REGRESSION = "regression"
    PERFORMANCE = "performance"
    BOUNDARY = "boundary"
    ERROR = "error"
    __test__ = False  # 防止 pytest 误收集


# ---------------------------------------------------------------------------
# 用例元信息
# ---------------------------------------------------------------------------

@dataclass
class TestCaseMeta:
    """测试用例元信息"""
    __test__ = False  # 防止 pytest 误收集
    name: str
    level: TestLevel
    tags: List[TagCategory]
    module: str                    # 所属模块
    description: str = ""
    priority: int = 3             # 1=critical, 2=high, 3=medium, 4=low
    estimated_ms: int = 500       # 预估耗时
    source: str = ""              # 来源（api_client/quality_checker...）
    ci_only: bool = False         # 仅 CI 执行

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "level": self.level.value,
            "tags": [t.value for t in self.tags],
            "module": self.module,
            "priority": self.priority,
            "source": self.source,
        }


# ---------------------------------------------------------------------------
# 测试套件管理器
# ---------------------------------------------------------------------------

class TestSuiteManager:
    """
    测试套件管理器

    功能：
    - 按层级组织所有测试用例元信息
    - 支持按层级、标签、模块过滤
    - 生成测试覆盖报告
    - 导出用例清单
    """
    __test__ = False  # 防止 pytest 误收集

    def __init__(self):
        self._cases: Dict[str, TestCaseMeta] = {}
        self._init_default_cases()

    def _init_default_cases(self):
        """初始化 Week 1-4 的用例清单"""
        builtin = [
            # === SMOKE 冒烟 ===
            TestCaseMeta("smoke_api_connect", TestLevel.SMOKE,
                        [TagCategory.API], "api_client",
                        "API 连通性测试", priority=1),
            TestCaseMeta("smoke_key_manager", TestLevel.SMOKE,
                        [TagCategory.API], "key_manager",
                        "Key 管理模块可用性", priority=1),
            TestCaseMeta("smoke_error_classify", TestLevel.SMOKE,
                        [TagCategory.ERROR], "error_classifier",
                        "错误分类模块可用性", priority=1),

            # === BOUNDARY（回归级） ===
            TestCaseMeta("boundary_max_tokens", TestLevel.REGRESSION,
                        [TagCategory.BOUNDARY, TagCategory.API], "api_client",
                        "max_tokens 边界测试", priority=2),
            TestCaseMeta("boundary_temperature", TestLevel.REGRESSION,
                        [TagCategory.BOUNDARY, TagCategory.API], "api_client",
                        "temperature 边界测试", priority=2),

            # === API ===
            TestCaseMeta("api_request_format", TestLevel.REGRESSION,
                        [TagCategory.API], "api_client",
                        "请求格式测试", priority=1),
            TestCaseMeta("api_response_baseline", TestLevel.REGRESSION,
                        [TagCategory.API], "response_validator",
                        "响应结构验证", priority=1),
            TestCaseMeta("api_truncation", TestLevel.REGRESSION,
                        [TagCategory.API], "truncation_analyzer",
                        "截断检测", priority=2),

            # === QUALITY ===
            TestCaseMeta("quality_accuracy", TestLevel.REGRESSION,
                        [TagCategory.QUALITY], "quality_checker",
                        "回复准确性检查", priority=2),
            TestCaseMeta("quality_consistency", TestLevel.REGRESSION,
                        [TagCategory.QUALITY], "consistency_checker",
                        "回复一致性测试", priority=2),
            TestCaseMeta("quality_llm_judge", TestLevel.REGRESSION,
                        [TagCategory.QUALITY], "llm_judge",
                        "LLM-as-Judge 自动评分", priority=2),

            # === CONVERSATION ===
            TestCaseMeta("conversation_context", TestLevel.REGRESSION,
                        [TagCategory.CONVERSATION], "conversation_tester",
                        "多轮对话上下文保持", priority=2),

            # === SECURITY ===
            TestCaseMeta("security_prompt_injection", TestLevel.SECURITY,
                        [TagCategory.SECURITY], "prompt_injection_tester",
                        "Prompt Injection 攻击防御", priority=1),
            TestCaseMeta("security_prompt_leak", TestLevel.SECURITY,
                        [TagCategory.SECURITY], "robustness_tester",
                        "System Prompt 泄露检测", priority=1),
            TestCaseMeta("security_jailbreak", TestLevel.SECURITY,
                        [TagCategory.SECURITY], "robustness_tester",
                        "越狱攻击防御", priority=1),

            # === REGRESSION ===
            TestCaseMeta("regression_library", TestLevel.REGRESSION,
                        [TagCategory.REGRESSION], "regression_tester",
                        "回归用例库管理", priority=2),
            TestCaseMeta("regression_ab_compare", TestLevel.REGRESSION,
                        [TagCategory.REGRESSION], "regression_tester",
                        "A/B 对比测试", priority=2),

            # === E2E ===
            TestCaseMeta("e2e_business_scenarios", TestLevel.E2E,
                        [TagCategory.REGRESSION], "e2e_tester",
                        "E2E 业务场景", priority=1),

            # === PERFORMANCE ===
            TestCaseMeta("perf_concurrent_small", TestLevel.PERFORMANCE,
                        [TagCategory.PERFORMANCE], "api_client",
                        "小并发测试 (5 threads)", priority=3),
            TestCaseMeta("perf_concurrent_medium", TestLevel.PERFORMANCE,
                        [TagCategory.PERFORMANCE], "api_client",
                        "中等并发测试 (20 threads)", priority=3),
        ]

        for case in builtin:
            self._cases[case.name] = case

    def add(self, case: TestCaseMeta):
        self._cases[case.name] = case

    def get(self, name: str) -> Optional[TestCaseMeta]:
        return self._cases.get(name)

    def filter(self, level: Optional[TestLevel] = None,
               tag: Optional[TagCategory] = None,
               module: Optional[str] = None,
               priority: Optional[int] = None) -> List[TestCaseMeta]:
        """多条件过滤"""
        results = list(self._cases.values())

        if level and level != TestLevel.ALL:
            results = [c for c in results if c.level == level]
        if tag:
            results = [c for c in results if tag in c.tags]
        if module:
            results = [c for c in results if c.module == module]
        if priority:
            results = [c for c in results if c.priority <= priority]

        return results

    def get_level_counts(self) -> Dict[str, int]:
        """各层级用例数量"""
        counts = {}
        for level in TestLevel:
            count = len(self.filter(level=level))
            if count > 0:
                counts[level.value] = count
        return counts

    def get_tag_counts(self) -> Dict[str, int]:
        """各标签用例数量"""
        counts = {}
        for tag in TagCategory:
            count = len(self.filter(tag=tag))
            if count > 0:
                counts[tag.value] = count
        return counts

    def all(self) -> List[TestCaseMeta]:
        return list(self._cases.values())

    def count(self) -> int:
        return len(self._cases)

    def export_json(self) -> str:
        """导出为 JSON 用例清单"""
        data = [c.to_dict() for c in self.all()]
        return json.dumps(data, ensure_ascii=False, indent=2)

    def generate_coverage_report(self) -> str:
        """生成覆盖率报告"""
        lines = [
            "=== Test Coverage Report ===",
            f"Total cases: {self.count()}",
            "",
            "--- By Level ---",
        ]
        for level_name, count in sorted(self.get_level_counts().items()):
            lines.append(f"  {level_name}: {count}")

        lines.append("")
        lines.append("--- By Tag ---")
        for tag_name, count in sorted(self.get_tag_counts().items()):
            lines.append(f"  {tag_name}: {count}")

        lines.append("")
        lines.append("--- Critical Cases (priority=1) ---")
        critical = self.filter(priority=1)
        for c in critical:
            lines.append(f"  [CRIT] {c.name} ({c.module})")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 参数化用例生成器
# ---------------------------------------------------------------------------

class ParametrizedCase:
    """
    参数化用例

    支持：
    - 单维度参数（一个变量多个值）
    - 多维度组合（多个变量笛卡尔积）
    - CSV 导入（从 CSV 文件生成参数组合）
    """

    def __init__(self, name: str):
        self.name = name
        self._params: Dict[str, List[Any]] = {}
        self._param_names: List[str] = []

    def add_param(self, name: str, values: List[Any]):
        """添加一个参数维度"""
        self._params[name] = values
        self._param_names.append(name)

    def combinations(self) -> List[Dict[str, Any]]:
        """生成所有参数组合"""
        if not self._param_names:
            return [{}]

        result = [{}]
        for pname in self._param_names:
            new_result = []
            for combo in result:
                for val in self._params[pname]:
                    new_combo = combo.copy()
                    new_combo[pname] = val
                    new_result.append(new_combo)
            result = new_result

        return result

    def param_names(self) -> List[str]:
        return self._param_names

    @classmethod
    def from_csv(cls, name: str, csv_text: str):
        """从 CSV 文本导入参数

        CSV 格式（首行为参数名）:
        temperature,top_p
        0,0.5
        1,1.0
        2,1.5
        """
        lines = csv_text.strip().split("\n")
        if len(lines) < 2:
            return None

        pc = cls(name)
        headers = [h.strip() for h in lines[0].split(",")]

        for i in range(len(headers)):
            values = []
            for line in lines[1:]:
                parts = [p.strip() for p in line.split(",")]
                if i < len(parts):
                    val = parts[i]
                    # 尝试转数字
                    try:
                        val = float(val) if "." in val else int(val)
                    except ValueError:
                        pass
                    values.append(val)
            pc.add_param(headers[i], values)

        return pc

    def description(self) -> str:
        total_combos = len(self.combinations())
        param_desc = " x ".join(f"{n}({len(self._params[n])})"
                                for n in self._param_names)
        return f"{self.name}: {param_desc} = {total_combos} combos"


# ---------------------------------------------------------------------------
# pytest 标签生成器
# ---------------------------------------------------------------------------

class PytestMarkerGenerator:
    """
    pytest 标签生成器

    将 TestLevel + TagCategory 映射为 pytest mark 表达式。
    可用于 CI 中的 -m 参数：
      pytest -m "smoke"       → 只跑冒烟
      pytest -m "security"   → 只跑安全
      pytest -m "regression and not perf" → 回归排除性能
    """

    @staticmethod
    def level_to_mark(level: TestLevel) -> str:
        return level.value

    @staticmethod
    def tag_to_mark(tag: TagCategory) -> str:
        return tag.value

    @staticmethod
    def marks_from_meta(meta: TestCaseMeta) -> List[str]:
        """从用例元数据生成 pytest.mark 列表"""
        marks = [meta.level.value]
        marks.extend(t.value for t in meta.tags)
        return marks

    @staticmethod
    def select_expr(levels: Optional[List[TestLevel]] = None,
                    tags: Optional[List[TagCategory]] = None) -> str:
        """
        生成 pytest -m 选择表达式

        Example:
          select_expr(levels=[SMOKE])
          → "(smoke)"

          select_expr(tags=[SECURITY, REGRESSION])
          → "(security or regression)"
        """
        parts = []
        if levels:
            level_expr = " or ".join(l.value for l in levels)
            parts.append(f"({level_expr})")

        if tags:
            tag_expr = " or ".join(t.value for t in tags)
            parts.append(f"({tag_expr})")

        return " and ".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# 报告信息（补充 pytest-html）
# ---------------------------------------------------------------------------

def generate_test_run_summary(
    total: int, passed: int, failed: int,
    duration_sec: float,
    breakdown: Optional[Dict[str, Dict]] = None,
) -> str:
    """
    生成测试运行摘要文本

    Args:
        total: 总数
        passed: 通过
        failed: 失败
        duration_sec: 耗时
        breakdown: {level: {"total": n, "passed": m}}
    """
    rate = passed / max(total, 1)
    lines = [
        f"=== Test Run Summary ===",
        f"Total: {total} | Passed: {passed} | Failed: {failed} | "
        f"Rate: {rate:.1%} | Duration: {duration_sec:.2f}s",
    ]

    if breakdown:
        lines.append("")
        lines.append("--- Breakdown ---")
        for level, stats in sorted(breakdown.items()):
            rate_l = stats["passed"] / max(stats["total"], 1)
            lines.append(
                f"  {level}: {stats['passed']}/{stats['total']} "
                f"({rate_l:.0%})"
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 模块兼容 — 适配之前各模块的 pytest 格式
# ---------------------------------------------------------------------------

class CompatRunner:
    """
    兼容运行器

    可以对 Week 1-3 的所有 test_*.py 文件按级别选择性运行。
    """

    # 模块到层级的映射
    MODULE_LEVEL_MAP: Dict[str, TestLevel] = {
        "test_params": TestLevel.SMOKE,
        "test_request_format": TestLevel.SMOKE,
        "test_response_baseline": TestLevel.REGRESSION,
        "test_key_manager": TestLevel.SMOKE,
        "test_quality": TestLevel.REGRESSION,
        "test_consistency": TestLevel.REGRESSION,
        "test_truncation": TestLevel.REGRESSION,
        "test_llm_judge": TestLevel.REGRESSION,
        "test_pipeline_assessment": TestLevel.REGRESSION,
        "test_conversation": TestLevel.REGRESSION,
        "test_prompt_injection": TestLevel.SECURITY,
        "test_robustness": TestLevel.SECURITY,
        "test_regression": TestLevel.REGRESSION,
        "test_e2e": TestLevel.E2E,
        "test_browser_checker": TestLevel.SMOKE,
    }

    # 模块到标签的映射
    MODULE_TAG_MAP: Dict[str, List[TagCategory]] = {
        "test_params": [TagCategory.API, TagCategory.BOUNDARY],
        "test_request_format": [TagCategory.API],
        "test_response_baseline": [TagCategory.API],
        "test_key_manager": [TagCategory.API],
        "test_quality": [TagCategory.QUALITY],
        "test_consistency": [TagCategory.QUALITY],
        "test_truncation": [TagCategory.API],
        "test_llm_judge": [TagCategory.QUALITY],
        "test_pipeline_assessment": [TagCategory.QUALITY],
        "test_conversation": [TagCategory.CONVERSATION],
        "test_prompt_injection": [TagCategory.SECURITY],
        "test_robustness": [TagCategory.SECURITY],
        "test_regression": [TagCategory.REGRESSION],
        "test_e2e": [TagCategory.REGRESSION],
        "test_browser_checker": [TagCategory.API],
    }

    @classmethod
    def get_modules_for_level(cls, level: TestLevel) -> List[str]:
        """获取指定层级的测试模块列表"""
        if level == TestLevel.ALL:
            return list(cls.MODULE_LEVEL_MAP.keys())

        return [name for name, lvl in cls.MODULE_LEVEL_MAP.items()
                if lvl == level]

    @classmethod
    def get_module_label(cls, module_name: str) -> str:
        """获取模块的显示标签"""
        level = cls.MODULE_LEVEL_MAP.get(module_name)
        tags = cls.MODULE_TAG_MAP.get(module_name, [])
        tag_names = [t.value for t in tags]
        return f"[{level.value}] {module_name} ({','.join(tag_names)})"
