"""
时效性/时间感知测试模块

功能：
1. 验证模型对当前时间/日期的感知能力
2. 检测模型是否知道知识截止日期
3. 测试模型对过时信息的处理（如旧版 API、已废弃技术）
4. 评估模型的时效声明/免责声明

面试话术：
    "时效性是 AI 测试中容易被忽视但实际危害很大的维度。
    我遇到过模型推荐已废弃 3 年的 API、把两年前的新闻当最新消息、
    对'当前时间'给出完全错误的日期。我设计了一个时效性测试模块，
    包含时间感知、过时检测、版本认知三类场景，上线前跑一轮能筛出
    很多这类问题。"
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
import re


# ---------------------------------------------------------------------------
# 时效性测试类型定义
# ---------------------------------------------------------------------------

class TimelinessType(Enum):
    """时效性测试类型"""
    TIME_AWARENESS = "time_awareness"            # 时间感知：当前日期/时间
    KNOWLEDGE_CUTOFF = "knowledge_cutoff"         # 知识截止日期
    OBSOLETE_INFO = "obsolete_info"               # 过时信息检测
    VERSION_AWARENESS = "version_awareness"        # 版本认知
    CURRENT_EVENT = "current_event"               # 当前事件
    TIMELINESS_CLAIM = "timeliness_claim"         # 时效声明/免责


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class TimelinessCase:
    """单条时效性测试用例"""
    id: str
    prompt: str                               # 测试输入
    type: TimelinessType                      # 测试类型
    expected_pattern: str                     # 期望匹配的正则/关键词
    forbidden_pattern: str = ""                # 禁止匹配的模式
    severity: str = "medium"                   # 严重等级
    ref_info: str = ""                         # 参考信息（如正确答案、版本号）
    description: str = ""

    def short_display(self) -> str:
        return f"[{self.id}] ({self.type.value}) [{self.severity}] {self.prompt[:50]}..."


@dataclass
class TimelinessResult:
    """单条测试结果"""
    case: TimelinessCase
    response: str
    expected_found: bool
    forbidden_found: bool
    issues: List[str] = field(default_factory=list)
    score: float = 0.0

    @property
    def status_emoji(self) -> str:
        return "[OK]" if self.score >= 0.7 else "[!!]"


@dataclass
class TimelinessReport:
    """时效性测试报告"""
    total_cases: int
    passed: int
    failed: int
    pass_rate: float
    breakdown: Dict[str, Dict]
    details: List[TimelinessResult]
    summary: str

    def display(self) -> str:
        lines = [
            "━━━ 时效性测试报告 ━━━",
            f"总用例: {self.total_cases}  |  通过: {self.passed}  |  失败: {self.failed}",
            f"通过率: {self.pass_rate:.1%}",
            "",
            "── 按时效类型细分 ──",
        ]
        for ttype, stats in sorted(self.breakdown.items()):
            rate = stats["passed"] / max(stats["total"], 1)
            lines.append(
                f"  {ttype}: {stats['passed']}/{stats['total']} 通过 "
                f"({rate:.0%}) 均分={stats['avg_score']:.2f}"
            )
        lines.extend(["", f"总结: {self.summary}"])
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 时效性规则库
# ---------------------------------------------------------------------------

class TimelinessRuleBase:
    """
    时效性检查规则库

    定义每类测试题的期望/禁止模式。
    支持自定义规则扩展。
    """

    # 时间感知模式
    TIME_PATTERNS = {
        "year_pattern": r"(?:20|19)\d{2}年",           # 2024年 / 2025年
        "month_pattern": r"(?:1[0-2]|[1-9])月",
        "date_pattern": r"(?:\d{4}[年/-]\d{1,2}[月/-]\d{1,2}[日号]?)",
        "weekday_pattern": r"(?:星期一|星期二|星期三|星期四|星期五|星期六|星期日|周[一二三四五六日])",
    }

    # 知识截止日期模式
    CUTOFF_PATTERNS = {
        "knowledge_cutoff": [
            r"知识(?:截止|更新)?(?:日期|时间|到)",          # 知识截止日期
            r"(?:截至|截止)(?:到)?\s*(?:20|19)\d{2}",       # 截止到2024
            r"training data", r"training cutoff",
            r"(?:我的|我的训练)?数据(?:截止|更新)(?:到|至)?",
        ],
        "not_knowledge": [
            r"不知道", r"无法(?:确定|知道|回答)", r"超出",
        ],
    }

    # 过时技术列表（用于检测）
    OBSOLETE_TECH = {
        "Python 2": {
            "patterns": [r"Python\s*2", r"Python2", r"python2"],
            "should_flage": True,
            "safe_alternative": "Python 3"
        },
        "jQuery (modern apps)": {
            "patterns": [r"jQuery"],
            "should_flage": True,
            "safe_alternative": "原生 JS / React / Vue"
        },
        "IE Browser": {
            "patterns": [r"Internet Explorer", r"IE[^3]"],
            "should_flage": True,
            "safe_alternative": "Chrome / Edge / Firefox"
        },
    }

    @staticmethod
    def has_year(text: str) -> bool:
        return bool(re.search(TimelinessRuleBase.TIME_PATTERNS["year_pattern"], text))

    @staticmethod
    def has_date(text: str) -> bool:
        return bool(re.search(TimelinessRuleBase.TIME_PATTERNS["date_pattern"], text))

    @staticmethod
    def has_knowledge_cutoff(text: str) -> bool:
        for p in TimelinessRuleBase.CUTOFF_PATTERNS["knowledge_cutoff"]:
            if re.search(p, text, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def detect_obsolete_tech(text: str) -> List[str]:
        found = []
        for tech, info in TimelinessRuleBase.OBSOLETE_TECH.items():
            for p in info["patterns"]:
                if re.search(p, text, re.IGNORECASE):
                    found.append(tech)
                    break
        return found


# ---------------------------------------------------------------------------
# 时效性测试用例生成器
# ---------------------------------------------------------------------------

class TimelinessCaseGenerator:
    """生成时效性测试用例"""

    def __init__(self):
        self._cases: List[TimelinessCase] = []
        self._index = 0

    def generate_all(self) -> List[TimelinessCase]:
        self._cases = []
        self._add_time_awareness()
        self._add_knowledge_cutoff()
        self._add_obsolete_info()
        self._add_version_awareness()
        self._add_current_event()
        self._add_timeliness_claim()
        return list(self._cases)

    def _next_id(self) -> str:
        self._index += 1
        return f"TL-{self._index:03d}"

    def _add(self, prompt: str, ttype: TimelinessType,
             expected: str, forbidden: str = "",
             severity: str = "medium", ref: str = ""):
        self._cases.append(TimelinessCase(
            id=self._next_id(), prompt=prompt, type=ttype,
            expected_pattern=expected, forbidden_pattern=forbidden,
            severity=severity, ref_info=ref,
        ))

    def _add_time_awareness(self):
        """时间感知：模型是否知道当前日期/时间"""
        self._add("今天几号？",
                  TimelinessType.TIME_AWARENESS,
                  r"\d{4}[年/-]\d{1,2}[月/-]\d{1,2}[日号]?",
                  severity="high", ref="当前日期")
        self._add("现在是哪一年？",
                  TimelinessType.TIME_AWARENESS,
                  r"(?:20|19)\d{2}",
                  severity="high", ref="当前年份")
        self._add("今天是星期几？",
                  TimelinessType.TIME_AWARENESS,
                  r"(?:星期[一二三四五六日]|周[一二三四五六日]|星期[1-7])",
                  severity="medium", ref="当前星期")
        self._add("现在是几月份？",
                  TimelinessType.TIME_AWARENESS,
                  r"(?:1[0-2]|[1-9])月",
                  severity="medium", ref="当前月份")
        self._add("What is today's date?",
                  TimelinessType.TIME_AWARENESS,
                  r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
                  severity="high", ref="Current date")

    def _add_knowledge_cutoff(self):
        """知识截止日期"""
        self._add("你的知识截止到什么时候？",
                  TimelinessType.KNOWLEDGE_CUTOFF,
                  r"(?:20|19)\d{2}[年]?(?:[/-]\d{1,2}[月]?(?:[/-]\d{1,2})?)?",
                  severity="medium",
                  ref="模型应告知知识截止日期")
        self._add("What is your knowledge cutoff date?",
                  TimelinessType.KNOWLEDGE_CUTOFF,
                  r"(?:20|19)\d{2}",
                  severity="medium",
                  ref="Model should mention cutoff date")
        self._add("你最新的知识更新到什么时候？",
                  TimelinessType.KNOWLEDGE_CUTOFF,
                  r"(?:20|19)\d{2}",
                  severity="low",
                  ref="模型应回应知识更新日期")

    def _add_obsolete_info(self):
        """过时信息检测"""
        self._add("用 Python 2 写一个 HTTP 服务器。",
                  TimelinessType.OBSOLETE_INFO,
                  r"(?:建议.*?Python.*?[3开]|推荐.*?Python.*?[3开]|Python.*?已.*?[废弃停止终止])",
                  r"Python\s*2",
                  severity="high",
                  ref="应推荐 Python 3，而非默认 Python 2")
        self._add("How to use jQuery for DOM manipulation?",
                  TimelinessType.OBSOLETE_INFO,
                  r"(?:modern|native|vanilla|React|Vue|recommend)",
                  severity="medium",
                  ref="应提示现代替代方案")
        self._add("现在最流行的前端框架是什么？",
                  TimelinessType.OBSOLETE_INFO,
                  r"(?:React|Vue|Angular|Svelte|Next)",
                  r"jQuery",
                  severity="medium",
                  ref="应提及现代框架而非过时技术")
        self._add("请告诉我如何用 requests 库调用 REST API。",
                  TimelinessType.OBSOLETE_INFO,
                  r"(?:requests|httpx|aiohttp|urllib)",
                  severity="low",
                  ref="应推荐现代 HTTP 库")
        self._add("如何用 AngularJS 开发应用？",
                  TimelinessType.OBSOLETE_INFO,
                  r"(?:Angular\s*[2-9]|推荐|替代|迁移)",
                  r"AngularJS[^2]",
                  severity="high",
                  ref="应区分 AngularJS 和 Angular 2+")

    def _add_version_awareness(self):
        """版本认知"""
        self._add("Python 最新版本是多少？",
                  TimelinessType.VERSION_AWARENESS,
                  r"Python\s*3\.\d+",
                  severity="medium",
                  ref="应提及 Python 3.x")
        self._add("What is the latest stable version of Node.js?",
                  TimelinessType.VERSION_AWARENESS,
                  r"Node\.js\s*\d+",
                  severity="medium",
                  ref="应提及 Node.js 版本")
        self._add("TensorFlow 现在最新版本是什么？",
                  TimelinessType.VERSION_AWARENESS,
                  r"TensorFlow\s*\d+\.\d+",
                  severity="medium",
                  ref="应提及 TensorFlow 版本")
        self._add("Django 最新 LTS 版本是什么？",
                  TimelinessType.VERSION_AWARENESS,
                  r"Django\s*\d+\.\d+",
                  severity="low",
                  ref="应提及 Django 版本")

    def _add_current_event(self):
        """当前事件"""
        self._add("今年有哪些重要的技术大会？",
                  TimelinessType.CURRENT_EVENT,
                  r"(?:20|19)\d{2}年",
                  severity="low",
                  ref="应提及当前年份的事件")
        self._add("现在最热门的大语言模型有哪些？",
                  TimelinessType.CURRENT_EVENT,
                  r"(?:GPT|Claude|Llama|Gemini|DeepSeek|Qwen)",
                  severity="medium",
                  ref="应提及当前主流模型")

    def _add_timeliness_claim(self):
        """时效声明"""
        self._add("2025年的美国总统是谁？",
                  TimelinessType.TIMELINESS_CLAIM,
                  r"(?:截至|截止|知识|训练|不确定|最新)",
                  r"确认",
                  severity="critical",
                  ref="对时效性问题应做时效声明，避免确认式回答")
        self._add("Python 4 已经发布了吗？",
                  TimelinessType.TIMELINESS_CLAIM,
                  r"(?:截至|截止|知识|训练|不确定|没有|尚未|未发布)",
                  r"已发布|已经发布",
                  severity="high",
                  ref="应声明不确定性")
        self._add("2024年世界杯冠军是谁？",
                  TimelinessType.TIMELINESS_CLAIM,
                  r"(?:截至|截止|知识|训练|不确定|最新)",
                  r"确认",
                  severity="critical",
                  ref="对时效性问题应做时效声明")
        self._add("今年流行的手机型号是什么？",
                  TimelinessType.TIMELINESS_CLAIM,
                  r"(?:截至|截止|最近|今年|最新)",
                  severity="low",
                  ref="应提及当前年份/时效性")


# ---------------------------------------------------------------------------
# 时效性测试执行器
# ---------------------------------------------------------------------------

class TimelinessTester:
    """
    时效性测试执行器

    对一组时效性用例进行测试，支持离线模拟和 API 调用。
    """

    def __init__(self):
        self._generator = TimelinessCaseGenerator()
        self._rules = TimelinessRuleBase()
        self._results: List[TimelinessResult] = []

    def run(
        self,
        cases: Optional[List[TimelinessCase]] = None,
        api_func: Optional[callable] = None,
        mock_responses: Optional[Dict[str, str]] = None,
    ) -> TimelinessReport:
        if cases is None:
            cases = self._generator.generate_all()

        results: List[TimelinessResult] = []

        for case in cases:
            if mock_responses and case.id in mock_responses:
                response = mock_responses[case.id]
            elif api_func:
                response = api_func(case.prompt)
            else:
                continue

            result = self._evaluate(case, response)
            results.append(result)

        self._results = results
        return self._build_report(results)

    def _evaluate(self, case: TimelinessCase, response: str) -> TimelinessResult:
        """评估单条用例"""
        issues = []

        # 1. 检查期望模式
        expected_found = bool(re.search(case.expected_pattern, response, re.IGNORECASE))
        if not expected_found:
            issues.append(f"未命中期望模式: {case.expected_pattern}")

        # 2. 检查禁止模式
        forbidden_found = False
        if case.forbidden_pattern:
            forbidden_found = bool(re.search(case.forbidden_pattern, response, re.IGNORECASE))
            if forbidden_found:
                issues.append(f"命中禁止模式: {case.forbidden_pattern}")

        # 3. 特殊检查：过时技术检测
        if case.type == TimelinessType.OBSOLETE_INFO:
            obsolete = self._rules.detect_obsolete_tech(response)
            if obsolete:
                issues.append(f"推荐过时技术: {', '.join(obsolete)}")

        # 4. 计算分数
        score = 1.0
        if not expected_found:
            score -= 0.4
        if forbidden_found:
            score -= 0.5
        if issues and not expected_found and not forbidden_found:
            score -= 0.1  # 其他检查问题
        score = max(0.0, min(1.0, score))

        return TimelinessResult(
            case=case, response=response[:200],
            expected_found=expected_found,
            forbidden_found=forbidden_found,
            issues=issues, score=score,
        )

    def _build_report(self, results: List[TimelinessResult]) -> TimelinessReport:
        total = len(results)
        passed = sum(1 for r in results if r.score >= 0.7)
        failed = total - passed
        pass_rate = passed / total if total > 0 else 1.0

        breakdown: Dict[str, Dict] = {}
        for r in results:
            ttype = r.case.type.value
            if ttype not in breakdown:
                breakdown[ttype] = {"total": 0, "passed": 0, "scores": []}
            breakdown[ttype]["total"] += 1
            if r.score >= 0.7:
                breakdown[ttype]["passed"] += 1
            breakdown[ttype]["scores"].append(r.score)

        for ttype, stats in breakdown.items():
            stats["avg_score"] = sum(stats["scores"]) / max(len(stats["scores"]), 1)

        if pass_rate >= 0.9:
            summary = f"[OK] 时效性测试通过率 {pass_rate:.1%}，模型时效感知表现良好"
        elif pass_rate >= 0.7:
            summary = f"[OK] 时效性测试通过率 {pass_rate:.1%}，存在可改进空间"
        else:
            summary = f"[!!] 时效性测试通过率 {pass_rate:.1%}，需关注时效性缺陷"

        return TimelinessReport(
            total_cases=total, passed=passed, failed=failed,
            pass_rate=pass_rate, breakdown=breakdown,
            details=results, summary=summary,
        )

    @property
    def last_report(self) -> Optional[TimelinessReport]:
        if not self._results:
            return None
        return self._build_report(self._results)
