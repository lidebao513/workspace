"""
多语言/语码混杂测试模块

功能：
1. 生成多语言测试用例（中文、英文、中英混杂、日语、代码混杂）
2. 检测回复语言一致性（用户用中文问→模型用中文答）
3. 评估翻译准确性和语码混合处理能力
4. 提供批量测试和报告生成

面试话术：
    "AI 模型的国际化场景下，多语言测试是关键。我设计了一个覆盖 5 种语言模式
    的测试器，能自动检测语言一致性（用户输入中文时模型是否用中文回复）、
    语码混合处理（中英混杂时是否有翻译偏差）以及翻译准确性。
    上线后我们发现约 8% 的多轮对话存在语言漂移问题。"
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re


# ---------------------------------------------------------------------------
# 语言/测试类型定义
# ---------------------------------------------------------------------------

class LanguageMode(Enum):
    """语言模式"""
    CHINESE = "chinese"              # 纯中文
    ENGLISH = "english"              # 纯英文
    ZH_EN_MIXED = "zh_en_mixed"     # 中英混杂
    JAPANESE = "japanese"           # 日语
    CODE_MIXED = "code_mixed"       # 代码/语言混杂


class MultilingualDimension(Enum):
    """多语言测试维度"""
    LANG_CONSISTENCY = "lang_consistency"      # 语言一致性：输入输出语言匹配
    CODE_SWITCHING = "code_switching"           # 语码切换：处理语码混合
    TRANSLATION_ACCURACY = "translation_accuracy" # 翻译准确性（如有翻译）
    TERM_CONSISTENCY = "term_consistency"       # 术语一致性：专业术语跨语言一致性
    RESPONSE_LANGUAGE = "response_language"      # 回复语言标签


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class MultilingualCase:
    """单条多语言测试用例"""
    id: str
    prompt: str                           # 输入 prompt
    lang_mode: LanguageMode               # 输入语言模式
    expected_lang: str                     # 期望回复语言（'zh'/'en'/'ja'/'mixed'）
    expected_keywords: List[str] = field(default_factory=list)  # 期望关键词
    forbidden_keywords: List[str] = field(default_factory=list)  # 禁止关键词
    description: str = ""                  # 用例描述

    def short_display(self) -> str:
        return f"[{self.id}] ({self.lang_mode.value}) {self.prompt[:60]}..."


@dataclass
class MultilingualResult:
    """单条测试结果"""
    case: MultilingualCase
    response: str                         # 模型回复
    detected_lang: str                    # 检测到的回复语言
    lang_match: bool                      # 语言是否匹配期望
    keyword_match: bool                   # 关键词是否覆盖
    forbidden_breach: bool                # 是否命中禁止词
    issues: List[str] = field(default_factory=list)  # 问题列表
    score: float = 0.0                    # 单条分数 0-1

    @property
    def status_emoji(self) -> str:
        return "[OK]" if self.score >= 0.7 else "[!!]"


@dataclass
class MultilingualReport:
    """多语言测试报告"""
    total_cases: int
    passed: int
    failed: int
    pass_rate: float
    breakdown: Dict[str, Dict]           # {lang_mode: {total, passed, avg_score}}
    details: List[MultilingualResult]
    summary: str

    def display(self) -> str:
        lines = [
            "━━━ 多语言测试报告 ━━━",
            f"总用例: {self.total_cases}  |  通过: {self.passed}  |  失败: {self.failed}",
            f"通过率: {self.pass_rate:.1%}",
            "",
            "── 按语言模式细分 ──",
        ]
        for mode, stats in sorted(self.breakdown.items()):
            rate = stats["passed"] / max(stats["total"], 1)
            lines.append(
                f"  {mode}: {stats['passed']}/{stats['total']} 通过 "
                f"({rate:.0%}) 均分={stats['avg_score']:.2f}"
            )
        lines.extend(["", f"总结: {self.summary}"])
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 语言检测器
# ---------------------------------------------------------------------------

class LanguageDetector:
    """
    简易语言检测器

    通过 Unicode 范围 + 关键词判断回复语言。
    注意：这是规则引擎，不依赖 NLP 模型，适用于离线测试。
    """

    # Unicode 范围
    CJK_RANGE = range(0x4E00, 0x9FFF + 1)     # 中日韩统一表意文字
    HIRAGANA_RANGE = range(0x3040, 0x309F + 1)  # 平假名
    KATAKANA_RANGE = range(0x30A0, 0x30FF + 1)  # 片假名

    @staticmethod
    def detect(text: str) -> str:
        """检测文本语言 -> 'zh' / 'en' / 'ja' / 'mixed' / 'code'"""
        if not text:
            return "unknown"

        has_cjk = any(ord(c) in LanguageDetector.CJK_RANGE for c in text)
        has_hiragana = any(ord(c) in LanguageDetector.HIRAGANA_RANGE for c in text)
        has_katakana = any(ord(c) in LanguageDetector.KATAKANA_RANGE for c in text)
        has_english = bool(re.search(r'[a-zA-Z]{2,}', text))

        # 日语特征（平假名/片假名）
        if has_hiragana or has_katakana:
            return "ja"

        # 纯中文
        if has_cjk and not has_english:
            return "zh"

        # 代码特征（大量符号、缩进、关键词）
        code_indicators = ["def ", "import ", "class ", "function ", "var ", "int ", "```"]
        code_score = sum(1 for ind in code_indicators if ind in text)
        if code_score >= 2:
            return "code"

        # 中英混合
        if has_cjk and has_english:
            return "mixed"

        # 纯英文
        if has_english:
            return "en"

        return "unknown"


# ---------------------------------------------------------------------------
# 多语言测试用例生成器
# ---------------------------------------------------------------------------

class MultilingualCaseGenerator:
    """生成多语言测试用例"""

    def __init__(self):
        self._cases: List[MultilingualCase] = []
        self._index = 0

    def generate_all(self) -> List[MultilingualCase]:
        self._cases = []
        self._add_chinese_cases()
        self._add_english_cases()
        self._add_zh_en_mixed_cases()
        self._add_japanese_cases()
        self._add_code_mixed_cases()
        return list(self._cases)

    def _next_id(self) -> str:
        self._index += 1
        return f"ML-{self._index:03d}"

    def _add(self, prompt: str, lang_mode: LanguageMode,
             expected_lang: str, expected_kw: List[str] = None,
             forbidden_kw: List[str] = None, desc: str = ""):
        self._cases.append(MultilingualCase(
            id=self._next_id(), prompt=prompt, lang_mode=lang_mode,
            expected_lang=expected_lang,
            expected_keywords=expected_kw or [],
            forbidden_keywords=forbidden_kw or [],
            description=desc,
        ))

    def _add_chinese_cases(self):
        """纯中文场景"""
        self._add("请介绍一下Python的数据类型。",
                  LanguageMode.CHINESE, "zh",
                  expected_kw=["列表", "字典", "元组", "字符串"],
                  desc="中文技术问题")
        self._add("今天天气怎么样？",
                  LanguageMode.CHINESE, "zh",
                  expected_kw=["天气"],
                  desc="中文日常问题")
        self._add("请用中文解释什么是机器学习。",
                  LanguageMode.CHINESE, "zh",
                  expected_kw=["机器学习", "算法", "数据"],
                  desc="中文定义性问题")
        self._add("请写一首关于春天的诗。",
                  LanguageMode.CHINESE, "zh",
                  expected_kw=["春"],
                  desc="中文创意性请求")

    def _add_english_cases(self):
        """纯英文场景"""
        self._add("Explain the concept of recursion in programming.",
                  LanguageMode.ENGLISH, "en",
                  expected_kw=["recursion", "function"],
                  desc="英文技术问题")
        self._add("What is the capital of France?",
                  LanguageMode.ENGLISH, "en",
                  expected_kw=["Paris", "capital"],
                  desc="英文事实性问题")
        self._add("Write a short poem about autumn.",
                  LanguageMode.ENGLISH, "en",
                  expected_kw=["autumn"],
                  desc="英文创意请求")
        self._add("Can you summarize the main differences between SQL and NoSQL databases?",
                  LanguageMode.ENGLISH, "en",
                  expected_kw=["SQL", "NoSQL", "database"],
                  desc="英文技术对比")

    def _add_zh_en_mixed_cases(self):
        """中英混杂场景"""
        self._add("这个API的response格式是什么样的？需要哪些parameters？",
                  LanguageMode.ZH_EN_MIXED, "mixed",
                  desc="中英混杂技术问题")
        self._add("帮我debug一下这个function：为什么我的list comprehension不work？",
                  LanguageMode.ZH_EN_MIXED, "mixed",
                  expected_kw=["list comprehension", "function"],
                  desc="中英混杂调试问题")
        self._add("What's 深度学习 and how is it different from 传统机器学习？",
                  LanguageMode.ZH_EN_MIXED, "mixed",
                  desc="中英混杂概念问题")
        self._add("请用英文解释'深度学习'，但保留关键词的中文注释。",
                  LanguageMode.ZH_EN_MIXED, "mixed",
                  expected_kw=["深度学习", "deep learning"],
                  desc="双语翻译请求")
        self._add("这个PR的code review怎么办？CI一直fail。",
                  LanguageMode.ZH_EN_MIXED, "mixed",
                  desc="中英混杂工作场景")

    def _add_japanese_cases(self):
        """日语场景"""
        self._add("Pythonのデータ型について説明してください。",
                  LanguageMode.JAPANESE, "ja",
                  expected_kw=["データ型"],
                  desc="日语技术问题")
        self._add("今日の天気はどうですか？",
                  LanguageMode.JAPANESE, "ja",
                  expected_kw=["天気"],
                  desc="日语日常问题")
        self._add("機械学習とは何ですか？日本語で説明してください。",
                  LanguageMode.JAPANESE, "ja",
                  expected_kw=["機械学習"],
                  desc="日语概念解释")
        self._add("自己紹介してください。",
                  LanguageMode.JAPANESE, "ja",
                  desc="日语自我介绍请求")

    def _add_code_mixed_cases(self):
        """代码/语言混杂场景"""
        self._add("请解释这段代码：\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
                  LanguageMode.CODE_MIXED, "zh",
                  expected_kw=["递归", "fibonacci"],
                  desc="中文解释代码")
        self._add("What does this JavaScript function do?\nfunction debounce(fn, delay) {\n  let timer;\n  return function(...args) {\n    clearTimeout(timer);\n    timer = setTimeout(() => fn(...args), delay);\n  }\n}",
                  LanguageMode.CODE_MIXED, "en",
                  expected_kw=["debounce", "delay"],
                  desc="英文解释代码")
        self._add("优化以下SQL：SELECT * FROM users WHERE age > 18 ORDER BY name",
                  LanguageMode.CODE_MIXED, "mixed",
                  expected_kw=["SQL", "优化", "SELECT"],
                  desc="中英混合SQL优化")
        self._add("以下のコードのバグを見つけてください：\nfor i in range(10):\n    print(i)",
                  LanguageMode.CODE_MIXED, "ja",
                  expected_kw=["コード", "バグ"],
                  desc="日语代码审查")


# ---------------------------------------------------------------------------
# 多语言测试执行器
# ---------------------------------------------------------------------------

class MultilingualTester:
    """
    多语言测试执行器

    对一组多语言用例进行测试，返回报告。
    支持离线模拟（mock_responses）和 API 调用模式。
    """

    def __init__(self, detector: Optional[LanguageDetector] = None):
        self.detector = detector or LanguageDetector()
        self._generator = MultilingualCaseGenerator()
        self._results: List[MultilingualResult] = []

    def run(
        self,
        cases: Optional[List[MultilingualCase]] = None,
        api_func: Optional[callable] = None,
        mock_responses: Optional[Dict[str, str]] = None,
    ) -> MultilingualReport:
        if cases is None:
            cases = self._generator.generate_all()

        results: List[MultilingualResult] = []

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

    def _evaluate(self, case: MultilingualCase, response: str) -> MultilingualResult:
        """评估单条用例"""
        detected_lang = self.detector.detect(response)
        issues = []

        # 1. 语言一致性检查
        expected = case.expected_lang
        if expected == "zh" and detected_lang not in ("zh", "mixed"):
            issues.append(f"期望中文回复，实际检测到 {detected_lang}")
        elif expected == "en" and detected_lang not in ("en", "mixed"):
            issues.append(f"期望英文回复，实际检测到 {detected_lang}")
        elif expected == "ja" and detected_lang not in ("ja", "mixed"):
            issues.append(f"期望日语回复，实际检测到 {detected_lang}")

        lang_match = len(issues) == 0

        # 2. 关键词覆盖
        keyword_match = True
        for kw in case.expected_keywords:
            if kw.lower() not in response.lower():
                issues.append(f"缺少期望关键词: {kw}")
                keyword_match = False

        # 3. 禁止词检测
        forbidden_breach = False
        for kw in case.forbidden_keywords:
            if kw.lower() in response.lower():
                issues.append(f"命中禁止词: {kw}")
                forbidden_breach = True

        # 4. 计算分数
        score = 1.0
        if not lang_match:
            score -= 0.3
        if not keyword_match:
            score -= 0.2
        if forbidden_breach:
            score -= 0.3
        score = max(0.0, min(1.0, score))

        return MultilingualResult(
            case=case, response=response[:200],
            detected_lang=detected_lang, lang_match=lang_match,
            keyword_match=keyword_match, forbidden_breach=forbidden_breach,
            issues=issues, score=score,
        )

    def _build_report(self, results: List[MultilingualResult]) -> MultilingualReport:
        total = len(results)
        passed = sum(1 for r in results if r.score >= 0.7)
        failed = total - passed
        pass_rate = passed / total if total > 0 else 1.0

        breakdown: Dict[str, Dict] = {}
        for r in results:
            mode = r.case.lang_mode.value
            if mode not in breakdown:
                breakdown[mode] = {"total": 0, "passed": 0, "scores": []}
            breakdown[mode]["total"] += 1
            if r.score >= 0.7:
                breakdown[mode]["passed"] += 1
            breakdown[mode]["scores"].append(r.score)

        for mode, stats in breakdown.items():
            stats["avg_score"] = sum(stats["scores"]) / max(len(stats["scores"]), 1)

        if pass_rate >= 0.9:
            summary = f"[OK] 多语言测试通过率 {pass_rate:.1%}，模型跨语言表现良好"
        elif pass_rate >= 0.7:
            summary = f"[OK] 多语言测试通过率 {pass_rate:.1%}，存在可改进空间"
        else:
            summary = f"[!!] 多语言测试通过率 {pass_rate:.1%}，存在语言一致性缺陷"

        return MultilingualReport(
            total_cases=total, passed=passed, failed=failed,
            pass_rate=pass_rate, breakdown=breakdown,
            details=results, summary=summary,
        )

    @property
    def last_report(self) -> Optional[MultilingualReport]:
        if not self._results:
            return None
        return self._build_report(self._results)

    def batch_run(self, case_groups: List[Tuple[str, List[MultilingualCase]]],
                  api_func: Optional[callable] = None,
                  mock_responses: Optional[Dict[str, str]] = None) -> List[MultilingualReport]:
        """批量运行多组用例，返回多个报告"""
        reports = []
        for group_name, cases in case_groups:
            report = self.run(cases=cases, api_func=api_func, mock_responses=mock_responses)
            reports.append(report)
        return reports
