"""
语气/风格一致性检查器

功能：验证 AI 回复是否符合系统提示词（System Prompt）指定的语气和风格要求。
覆盖正式/非正式、专业/通俗、礼貌/直接、正面/中立等多种风格维度的检查。

面试话术：
    "大模型的语气一致性是产品质量的关键——回复内容正确但语气不对，
    用户会感觉'这不是我们要的 AI'。我设计了一个风格一致性检查器，
    能自动验证回复在礼貌度、专业度和情感倾向等维度上是否与
    System Prompt 设定的风格一致。"
"""

import re
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ──────────────────────────────────────────────
# 1. 风格维度定义
# ──────────────────────────────────────────────


class PolitenessLevel(Enum):
    """礼貌程度"""
    VERY_POLITE = "very_polite"       # 非常礼貌（请/谢谢/麻烦）
    POLITE = "polite"                 # 礼貌
    NEUTRAL = "neutral"               # 中性
    DIRECT = "direct"                 # 直接（不带修饰）
    BLUNT = "blunt"                   # 生硬


class FormalityLevel(Enum):
    """正式程度"""
    FORMAL = "formal"                 # 正式（书面语/敬语）
    SEMI_FORMAL = "semi_formal"       # 半正式
    CASUAL = "casual"                 # 非正式（口语化）
    SLANG = "slang"                   # 俚语/网络用语


class ToneType(Enum):
    """语气类型"""
    PROFESSIONAL = "professional"     # 专业
    FRIENDLY = "friendly"             # 友好
    EMPATHETIC = "empathetic"         # 共情
    ENCOURAGING = "encouraging"       # 鼓励
    NEUTRAL = "neutral"               # 中立
    HUMOROUS = "humorous"             # 幽默
    ASSERTIVE = "assertive"           # 坚定
    CAREFUL = "careful"              # 谨慎
    WARM = "warm"                     # 温暖


@dataclass
class StyleProfile:
    """
    风格配置——定义期望的风格。
    可以定义多个维度的期望值。
    """
    label: str                                       # 风格名称（如"客服专业"）
    required_tone: Optional[ToneType] = None         # 期望语气
    required_formality: Optional[FormalityLevel] = None  # 期望正式程度
    required_politeness: Optional[PolitenessLevel] = None  # 期望礼貌程度

    # 关键词规则
    must_contain_polite: bool = False                # 必须包含礼貌用语
    must_not_contain_jargon: bool = False            # 禁止专业术语
    must_not_contain_negative: bool = False          # 禁止负面词汇
    must_contain_actionable: bool = False            # 必须包含可操作建议

    # 语气指标
    enthusiasm_level: Optional[int] = None           # 热情度 1-5
    confidence_level: Optional[int] = None           # 自信度 1-5

    def to_description(self) -> str:
        """生成人类可读的风格描述"""
        parts = [f"Style: {self.label}"]
        if self.required_tone:
            parts.append(f"  Tone: {self.required_tone.value}")
        if self.required_formality:
            parts.append(f"  Formality: {self.required_formality.value}")
        if self.required_politeness:
            parts.append(f"  Politeness: {self.required_politeness.value}")
        return "\n".join(parts)


# ──────────────────────────────────────────────
# 2. 风格检查器
# ──────────────────────────────────────────────


class StyleChecker:
    """
    语气/风格一致性检查器

    分析回复文本在多个风格维度上的表现，与期望的 StyleProfile 对比，
    生成一致性报告。
    """

    # ── 礼貌用语表 ──
    POLITE_WORDS: Set[str] = {
        "请", "谢谢", "感谢", "麻烦", "抱歉", "对不起", "不好意思",
        "请问", "您好", "你好", "欢迎", "很荣幸", "不客气",
        "劳烦", "辛苦", "拜托",
    }

    # ── 专业术语标识 ──
    PROFESSIONAL_JARGON: Set[str] = {
        "框架", "架构", "接口", "协议", "算法", "模型", "数据",
        "流程", "机制", "策略", "体系", "组件", "模块",
        "部署", "集成", "迭代", "优化", "重构",
    }

    # ── 负面词汇 ──
    NEGATIVE_WORDS: Set[str] = {
        "不好", "不行", "不能", "不对", "错误", "失败",
        "糟糕", "差劲", "没用", "垃圾", "差",
    }

    # ── 共情用语 ──
    EMPATHETIC_PHRASES: Set[str] = {
        "理解你的", "我明白", "确实不容易", "我理解",
        "感同身受", "这是正常的", "别担心", "放松",
    }

    # ── 鼓励用语 ──
    ENCOURAGING_WORDS: Set[str] = {
        "加油", "可以的", "没问题", "一定能", "做得很好",
        "继续", "进步", "不错的", "很棒",
    }

    # ── 幽默/轻松标记 ──
    HUMOR_INDICATORS: Set[str] = {
        "哈哈", "嘿嘿", ":)",
    }

    def __init__(self):
        self._check_history: List[Dict] = []

    def check(self, text: str, profile: StyleProfile) -> "StyleCheckResult":
        """
        对回复执行风格一致性检查。
        """
        violations: List[str] = []
        observations: List[str] = []
        dimension_scores: Dict[str, float] = {}

        # 1. 礼貌度检查
        politeness_score, politeness_issues = self._check_politeness(text, profile)
        dimension_scores["politeness"] = politeness_score
        violations.extend(politeness_issues)

        # 2. 正式度检查
        formality_score, formality_obs = self._check_formality(text, profile)
        dimension_scores["formality"] = formality_score
        observations.extend(formality_obs)

        # 3. 语气检查
        tone_score, tone_issues = self._check_tone(text, profile)
        dimension_scores["tone"] = tone_score
        violations.extend(tone_issues)

        # 4. 专业度检查
        professional_score, professional_obs = self._check_professionalism(text, profile)
        dimension_scores["professionalism"] = professional_score
        observations.extend(professional_obs)

        # 5. 情感态度检查
        sentiment_score, sentiment_obs = self._check_sentiment(text, profile)
        dimension_scores["sentiment"] = sentiment_score
        observations.extend(sentiment_obs)

        # 综合分
        composite = round(sum(dimension_scores.values()) / len(dimension_scores), 2)

        result = StyleCheckResult(
            text=text,
            profile=profile,
            composite_score=composite,
            dimension_scores=dimension_scores,
            passed=composite >= 0.7,
            violations=violations,
            observations=observations,
        )

        self._check_history.append({
            "profile": profile.label,
            "composite": composite,
            "passed": result.passed,
        })
        return result

    def _check_politeness(self, text: str, profile: StyleProfile) -> Tuple[float, List[str]]:
        """检查礼貌度"""
        issues: List[str] = []
        text_lower = text.lower()

        polite_found = sum(1 for w in self.POLITE_WORDS if w in text_lower)

        if profile.required_politeness:
            if profile.required_politeness in (PolitenessLevel.POLITE, PolitenessLevel.VERY_POLITE):
                if polite_found < 1:
                    issues.append(f"期望礼貌语气，但未发现礼貌用语")
                    return 0.3, issues
                elif polite_found >= 3:
                    return 1.0, issues
                else:
                    return 0.6, issues

            if profile.required_politeness == PolitenessLevel.DIRECT:
                if polite_found > 2:
                    issues.append("期望直接语气，但包含过多礼貌用语")
                    return 0.5, issues
                return 1.0, issues

        return 0.8 if polite_found >= 1 else 0.6, issues

    def _check_formality(self, text: str, profile: StyleProfile) -> Tuple[float, List[str]]:
        """检查正式度"""
        observations: List[str] = []
        text_lower = text.lower()

        # 检查正式度标记
        has_colon_ending = text.strip().endswith("。" if "。" in text else ".")
        has_trailing_ellipsis = "..." in text or "……" in text
        has_colloquial = any(w in text_lower for w in ["哈", "呗", "啦", "呀", "嘛"])

        if profile.required_formality == FormalityLevel.FORMAL:
            if has_colloquial:
                observations.append("正式语气中包含了口语化词汇")
                return 0.5, observations
            return 0.9, observations

        if profile.required_formality == FormalityLevel.CASUAL:
            if not has_colloquial and has_colon_ending:
                observations.append("期望非正式语气，但回复偏正式")
                return 0.6, observations
            return 0.9, observations

        return 0.8, observations

    def _check_tone(self, text: str, profile: StyleProfile) -> Tuple[float, List[str]]:
        """检查语气"""
        issues: List[str] = []
        text_lower = text.lower()

        if not profile.required_tone:
            return 0.8, issues

        tone = profile.required_tone

        if tone == ToneType.EMPATHETIC:
            empathetic_found = any(p in text_lower for p in self.EMPATHETIC_PHRASES)
            if not empathetic_found:
                issues.append("期望共情语气，但未检测到共情表达")
                return 0.3, issues
            return 0.9, issues

        if tone == ToneType.ENCOURAGING:
            encouraging_found = any(w in text_lower for w in self.ENCOURAGING_WORDS)
            if not encouraging_found:
                issues.append("期望鼓励语气，但未检测到鼓励用语")
                return 0.3, issues
            return 0.9, issues

        if tone == ToneType.HUMOROUS:
            humor_found = any(w in text_lower for w in self.HUMOR_INDICATORS)
            if not humor_found:
                issues.append("期望幽默语气，但未检测到幽默标记")
                return 0.4, issues
            return 0.9, issues

        if tone == ToneType.NEUTRAL:
            # 中性语气不应过强
            if any(w in text_lower for w in self.ENCOURAGING_WORDS):
                issues.append("期望中性语气，但检测到鼓励用语")
                return 0.6, issues
            return 0.9, issues

        return 0.8, issues

    def _check_professionalism(self, text: str, profile: StyleProfile) -> Tuple[float, List[str]]:
        """检查专业度"""
        observations: List[str] = []
        text_lower = text.lower()

        jargon_count = sum(1 for w in self.PROFESSIONAL_JARGON if w in text_lower)

        if profile.must_not_contain_jargon:
            if jargon_count > 0:
                observations.append(f"禁止专业术语，发现 {jargon_count} 个")
                return 0.3, observations

        if profile.must_contain_actionable:
            # 检测是否有可操作建议（包含步骤/建议/指南等词）
            actionable_indicators = ["步骤", "建议", "可以", "试着", "方法", "方式"]
            has_actionable = any(w in text_lower for w in actionable_indicators)
            if not has_actionable:
                observations.append("期望包含可操作建议，但未检测到")
                return 0.4, observations

        return 0.8, observations

    def _check_sentiment(self, text: str, profile: StyleProfile) -> Tuple[float, List[str]]:
        """检查情感态度"""
        observations: List[str] = []
        text_lower = text.lower()

        negative_found = sum(1 for w in self.NEGATIVE_WORDS if w in text_lower)

        if profile.must_not_contain_negative:
            if negative_found > 0:
                observations.append(f"禁止负面词汇，发现 {negative_found} 处")
                return 0.2, observations

        if profile.must_contain_polite:
            polite_found = sum(1 for w in self.POLITE_WORDS if w in text_lower)
            if polite_found == 0:
                observations.append("期望包含礼貌用语，但未发现")
                return 0.4, observations

        return 0.8, observations

    def reset(self) -> None:
        self._check_history = []


@dataclass
class StyleCheckResult:
    """风格检查结果"""
    text: str
    profile: StyleProfile
    composite_score: float
    dimension_scores: Dict[str, float]
    passed: bool
    violations: List[str] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)

    def report(self) -> str:
        """生成可读报告"""
        status = "[OK]" if self.passed else "[!!]"
        lines = [
            f"  {status} Style: {self.profile.label}",
            f"       Tone: {self.profile.required_tone.value if self.profile.required_tone else 'N/A'}",
            f"       Composite Score: {self.composite_score:.2f}",
            f"       Passed: {self.passed}",
        ]

        if self.dimension_scores:
            lines.append("       Dimension Scores:")
            for dim, score in self.dimension_scores.items():
                bar = "█" * int(score * 10)
                lines.append(f"         {dim:20s}: {score:.2f}  {bar}")

        if self.violations:
            for v in self.violations:
                lines.append(f"       [!!] VIOLATION: {v}")

        if self.observations:
            for o in self.observations:
                lines.append(f"       [??] Note: {o}")

        return "\n".join(lines)


# ──────────────────────────────────────────────
# 3. 内置风格配置
# ──────────────────────────────────────────────


class StyleProfiles:
    """预置的常用风格配置"""

    @staticmethod
    def customer_service_professional() -> StyleProfile:
        """客服专业风"""
        return StyleProfile(
            label="客服专业风",
            required_tone=ToneType.EMPATHETIC,
            required_formality=FormalityLevel.SEMI_FORMAL,
            required_politeness=PolitenessLevel.POLITE,
            must_contain_polite=True,
            must_not_contain_jargon=True,
            must_contain_actionable=True,
            must_not_contain_negative=True,
            confidence_level=4,
        )

    @staticmethod
    def tech_doc_formal() -> StyleProfile:
        """技术文档正式风"""
        return StyleProfile(
            label="技术文档正式风",
            required_tone=ToneType.NEUTRAL,
            required_formality=FormalityLevel.FORMAL,
            required_politeness=PolitenessLevel.NEUTRAL,
            must_not_contain_jargon=False,
            confidence_level=5,
        )

    @staticmethod
    def friendly_chat() -> StyleProfile:
        """友好聊天风"""
        return StyleProfile(
            label="友好聊天风",
            required_tone=ToneType.FRIENDLY,
            required_formality=FormalityLevel.CASUAL,
            required_politeness=PolitenessLevel.NEUTRAL,
        )

    @staticmethod
    def encouraging_coach() -> StyleProfile:
        """鼓励教练风"""
        return StyleProfile(
            label="鼓励教练风",
            required_tone=ToneType.ENCOURAGING,
            required_formality=FormalityLevel.CASUAL,
            required_politeness=PolitenessLevel.NEUTRAL,
            must_contain_actionable=True,
            must_not_contain_negative=True,
            enthusiasm_level=5,
        )

    @staticmethod
    def cautious_harmless() -> StyleProfile:
        """谨慎安全风"""
        return StyleProfile(
            label="谨慎安全风",
            required_tone=ToneType.CAREFUL,
            required_formality=FormalityLevel.FORMAL,
            required_politeness=PolitenessLevel.VERY_POLITE,
            must_not_contain_jargon=False,
            must_not_contain_negative=True,
            confidence_level=3,  # 谨慎 = 低自信度
        )


# ──────────────────────────────────────────────
# 4. 批量风格检查
# ──────────────────────────────────────────────


class BatchStyleChecker:
    """
    批量风格一致性检查器。
    """

    def __init__(self):
        self.checker = StyleChecker()
        self.results: List[StyleCheckResult] = []

    def check(self, texts: List[str], profile: StyleProfile) -> List[StyleCheckResult]:
        """批量检查"""
        self.results = [self.checker.check(t, profile) for t in texts]
        return self.results

    def summary(self) -> str:
        """生成批量汇总"""
        if not self.results:
            return "No results to summarize."

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        avg_score = round(sum(r.composite_score for r in self.results) / total, 2)

        # 各维度平均分
        dims = {}
        for r in self.results:
            for dim, score in r.dimension_scores.items():
                if dim not in dims:
                    dims[dim] = []
                dims[dim].append(score)

        lines = [
            f"{'=' * 50}",
            f"  Batch Style Consistency Summary",
            f"{'=' * 50}",
            f"  Total:     {total}",
            f"  Passed:    {passed}",
            f"  Failed:    {total - passed}",
            f"  Pass Rate: {passed/total:.1%}" if total > 0 else "  Pass Rate: N/A",
            f"  Avg Score: {avg_score}",
            f"{'=' * 50}",
        ]

        if dims:
            lines.append("")
            lines.append("  Average Dimension Scores:")
            for dim, scores in sorted(dims.items()):
                avg = round(sum(scores) / len(scores), 2)
                bar = "█" * int(avg * 10)
                lines.append(f"    {dim:20s}: {avg:.2f}  {bar}")

        return "\n".join(lines)
