"""
Hallucination Detector — 幻觉检测与答案质量评估

功能：
1. 事实核对：提取模型回答中的关键实体，与知识库对照
2. 置信度评分：对回答的可信度打分，低分提示潜在幻觉
3. 重复查询一致性：对同一问题多次提问，不一致 = 潜在幻觉
4. 输出 Hit Rate（命中率）和 Hallucination Rate（幻觉率）

用法：
    from ext.d_ext_hallucination import HallucinationDetector
    hd = HallucinationDetector()
    result = hd.check_fact_consistency("上海的天气25度", "上海今天气温25度")
"""

import re
from typing import List, Dict, Optional, Tuple, Set


# 简单的实体提取规则（实际项目可用 NER 模型）
_ENTITY_PATTERNS = {
    "日期": r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?|\d{1,2}月\d{1,2}日|今天|明天|后天|昨天",
    "数字": r"\d+\.?\d*(?:%|万|亿|摄氏度|度|米|公里|小时|分钟|元)?",
    "地名": r"[A-Za-z\u4e00-\u9fff]{2,}(?:省|市|区|县|镇|乡|路|街|道|村|山|河|湖|海|岛)",
    "专有名词": r"[A-Za-z\u4e00-\u9fff]{2,}(?:API|SDK|模型|框架|协议|系统|平台|引擎|算法|协议|标准)",
}

# 确认性/模糊性词语检测
_CONFIRMATION_WORDS = [
    "肯定", "确定", "一定", "必然", "绝对", "毫无疑问", "明确",
    "保证", "确认", "确实", "的确是",
]
_HEDGE_WORDS = [
    "可能", "也许", "大概", "似乎", "好像", "按理说", "一般",
    "通常", "推测", "猜测", "不太确定", "有可能", "不一定",
    "应该是", "我觉得", "我认为",
]


class HallucinationDetector:
    """幻觉检测器。

    支持三种检测模式：
    - check_fact_consistency: 事实核对
    - score_confidence: 置信度评分
    - check_consistency_across_runs: 多次回答一致性检查
    """

    def __init__(self, nlp_func: Optional[callable] = None):
        """
        Args:
            nlp_func: 可选，外部 NER 实体提取函数。
                      接收字符串返回 List[str]。
                      不传则使用基于正则的简单提取。
        """
        self._nlp_func = nlp_func

    # === 实体提取 ===

    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """从文本中提取实体。

        Returns:
            [{"text": str, "type": str}, ...]
        """
        entities = []
        seen = set()

        for etype, pattern in _ENTITY_PATTERNS.items():
            for match in re.finditer(pattern, text):
                entity_text = match.group()
                if entity_text not in seen:
                    seen.add(entity_text)
                    entities.append({
                        "text": entity_text,
                        "type": etype,
                    })

        # 如果有外部 NER 函数，合并结果
        if self._nlp_func:
            external_entities = self._nlp_func(text)
            for ent in external_entities:
                if ent not in seen:
                    seen.add(ent)
                    entities.append({
                        "text": ent,
                        "type": "external",
                    })

        # 按出现顺序排序
        entities.sort(key=lambda e: text.index(e["text"]) if e["text"] in text else 0)
        return entities

    def extract_numeric_claims(self, text: str) -> List[str]:
        """提取文本中的数值型断言。

        Returns:
            ["25度", "30%", ...]
        """
        pattern = r"\d+\.?\d*(?:%|万|亿|摄氏度|度|米|公里|小时|分钟|元|个|条|件|次)"
        return list(set(re.findall(pattern, text)))

    # === 事实核对 ===

    def check_fact_consistency(
        self,
        response: str,
        knowledge_base: str,
    ) -> Dict:
        """核对模型回答与知识库的一致性。

        步骤：
        1. 从回答中提取实体和数字断言
        2. 在知识库中查找这些内容
        3. 计算命中率和幻觉率

        Returns:
            {
                "response_entities": [str],
                "kb_hits": int,
                "total_checked": int,
                "hit_rate": float,         # 命中率
                "hallucination_rate": float,  # 幻觉率
                "unmatched_entities": [str],  # 未命中的实体
                "details": str,
            }
        """
        entities = self.extract_entities(response)
        numeric_claims = self.extract_numeric_claims(response)

        # 合并实体文本列表
        entity_texts = [e["text"] for e in entities] + numeric_claims
        total_checked = len(set(entity_texts))

        if total_checked == 0:
            return {
                "response_entities": [],
                "kb_hits": 0,
                "total_checked": 0,
                "hit_rate": 1.0,  # 无实体可核对，默认无幻觉
                "hallucination_rate": 0.0,
                "unmatched_entities": [],
                "details": "回答中没有可核对的实体，无法检测幻觉。",
            }

        hits = 0
        unmatched = []

        for entity in set(entity_texts):
            if entity and entity in knowledge_base:
                hits += 1
            else:
                unmatched.append(entity)

        hit_rate = hits / total_checked
        hallucination_rate = len(unmatched) / total_checked

        detail_parts = []
        detail_parts.append(f"回答中有 {total_checked} 个实体/数值")
        detail_parts.append(f"知识库命中 {hits} 个，命中率={hit_rate:.2%}")
        if unmatched:
            detail_parts.append(f"未命中: {', '.join(unmatched[:5])}")
        if hits == total_checked:
            detail_parts.append("结论：未发现明显幻觉")

        return {
            "response_entities": list(set(entity_texts)),
            "kb_hits": hits,
            "total_checked": total_checked,
            "hit_rate": round(hit_rate, 4),
            "hallucination_rate": round(hallucination_rate, 4),
            "unmatched_entities": unmatched,
            "details": " | ".join(detail_parts),
        }

    # === 置信度评分 ===

    def score_confidence(self, text: str) -> Dict:
        """评估回答的置信度。

        基于：
        1. 模糊性词语比例（"可能"、"大概"）
        2. 确认性词语比例（"肯定"、"确定"）
        3. 缺失具体数据（只有定性没有定量）

        Returns:
            {
                "confidence_score": float,  # 0.0 ~ 1.0
                "hedge_ratio": float,
                "confirmation_ratio": float,
                "has_specific_data": bool,
                "flags": [str],
                "details": str,
            }
        """
        if not text or not text.strip():
            return {
                "confidence_score": 0.0,
                "hedge_ratio": 0.0,
                "confirmation_ratio": 0.0,
                "has_specific_data": False,
                "flags": ["回答为空"],
                "details": "空回答，置信度最低。",
            }

        words = text.split()
        total_words = len(words)
        if total_words == 0:
            total_words = 1

        # 统计模糊词
        hedge_count = sum(1 for w in words if w in _HEDGE_WORDS)
        # 检查模糊词是否出现在文本中（而不是分词精确匹配）
        hedge_count = 0
        for w in _HEDGE_WORDS:
            hedge_count += len(re.findall(re.escape(w), text))

        confirmation_count = 0
        for w in _CONFIRMATION_WORDS:
            confirmation_count += len(re.findall(re.escape(w), text))

        # 检查是否有具体数据
        has_data = bool(re.search(r"\d+\.?\d*%?", text))

        # 有数字型引用（如"2024年"、"85%"）
        has_reference = bool(re.search(r"\d{4}年|\d+%|\d+\.\d+", text))

        # 综合评分
        hedge_ratio = hedge_count / max(total_words, 1)
        confirmation_ratio = confirmation_count / max(total_words, 1)

        score = 0.5  # 基础分

        # 模糊词越多分越低
        score -= hedge_ratio * 2.0
        # 确认词越多分越高
        score += confirmation_ratio * 1.0
        # 有具体数据加分
        if has_data:
            score += 0.15
        if has_reference:
            score += 0.15
        # 句子太短（<5词）减分
        if total_words < 5:
            score -= 0.2

        score = max(0.0, min(1.0, score))

        # 标记问题
        flags = []
        if hedge_ratio > 0.1:
            flags.append(f"模糊词过多 ({hedge_count}处)")
        if not has_data:
            flags.append("缺乏具体数据")
        if total_words < 10:
            flags.append("回答过短")

        return {
            "confidence_score": round(score, 4),
            "hedge_ratio": round(hedge_ratio, 4),
            "confirmation_ratio": round(confirmation_ratio, 4),
            "has_specific_data": has_data,
            "flags": flags,
            "details": f"置信度评分 {score:.2f}（模糊词比率 {hedge_ratio:.2%}，确认词比率 {confirmation_ratio:.2%}）",
        }

    # === 多次回答一致性 ===

    def check_consistency_across_runs(
        self,
        responses: List[str],
    ) -> Dict:
        """检查多次回答的一致性。

        对同一问题多次提问，比较回答中的关键实体和数值。

        Args:
            responses: 同一问题的多次回答列表

        Returns:
            {
                "num_runs": int,
                "consistent_entities": [str],
                "inconsistent_entities": [str],
                "consistency_rate": float,  # 完全一致率
                "entity_overlap": float,     # 实体重叠率
                "details": str,
            }
        """
        if len(responses) < 2:
            return {
                "num_runs": len(responses),
                "consistent_entities": [],
                "inconsistent_entities": [],
                "consistency_rate": 1.0,
                "entity_overlap": 1.0,
                "details": "需要至少 2 次回答才能检查一致性。",
            }

        # 提取每次回答的实体
        all_entity_sets: List[Set[str]] = []
        for resp in responses:
            entities = self.extract_entities(resp)
            numeric_claims = self.extract_numeric_claims(resp)
            combined = set(e["text"] for e in entities) | set(numeric_claims)
            all_entity_sets.append(combined)

        # 计算所有实体
        all_entities = set()
        for es in all_entity_sets:
            all_entities |= es

        if not all_entities:
            return {
                "num_runs": len(responses),
                "consistent_entities": [],
                "inconsistent_entities": [],
                "consistency_rate": 1.0,
                "entity_overlap": 1.0,
                "details": "回答中未提取到实体，无法检查一致性。",
            }

        # 一致性检查：每个实体是否在所有回答中出现
        consistent = set()
        inconsistent = set()

        for entity in all_entities:
            present_in = sum(1 for es in all_entity_sets if entity in es)
            if present_in == len(responses):
                consistent.add(entity)
            else:
                inconsistent.add(entity)

        # 如果每个回答都没有实体，约定为完全一致
        total_entities = len(all_entities)
        consistency_rate = len(consistent) / total_entities if total_entities > 0 else 1.0

        # 实体重叠率（Jaccard 相似度）
        if len(all_entity_sets) >= 2:
            base = all_entity_sets[0]
            for es in all_entity_sets[1:]:
                if base:
                    overlap = len(base & es) / len(base | es)
                else:
                    overlap = 0.0
                base = base | es
            entity_overlap = overlap
        else:
            entity_overlap = 0.0

        return {
            "num_runs": len(responses),
            "consistent_entities": sorted(list(consistent)),
            "inconsistent_entities": sorted(list(inconsistent)),
            "consistency_rate": round(consistency_rate, 4),
            "entity_overlap": round(entity_overlap, 4),
            "details": (
                f"共 {len(responses)} 次回答，"
                f"提取到 {total_entities} 个实体，"
                f"一致 {len(consistent)} 个，"
                f"不一致 {len(inconsistent)} 个，"
                f"一致率={consistency_rate:.2%}"
            ),
        }

    # === 综合评估 ===

    def evaluate(
        self,
        response: str,
        knowledge_base: str,
        previous_responses: Optional[List[str]] = None,
    ) -> Dict:
        """综合评估回答质量。

        结合事实核对 + 置信度 + 一致性（如果有多次回答）。

        Returns:
            {
                "hallucination_score": float,  # 0~1, 越低越好
                "fact_check": Dict,
                "confidence": Dict,
                "consistency": Optional[Dict],
                "overall_verdict": str,
            }
        """
        fact = self.check_fact_consistency(response, knowledge_base)
        conf = self.score_confidence(response)

        consistency = None
        if previous_responses and len(previous_responses) >= 1:
            consistency = self.check_consistency_across_runs(
                [response] + previous_responses
            )

        # 综合幻觉评分 (0=无幻觉, 1=严重幻觉)
        hallucination_score = 0.0

        # 事实核对部分
        if fact["total_checked"] > 0:
            hallucination_score += fact["hallucination_rate"] * 0.5

        # 置信度部分
        hallucination_score += (1.0 - conf["confidence_score"]) * 0.3

        # 一致性部分
        if consistency and consistency["num_runs"] >= 2:
            hallucination_score += (1.0 - consistency["consistency_rate"]) * 0.2

        hallucination_score = min(1.0, hallucination_score)

        # 最终结论
        if hallucination_score < 0.2:
            verdict = "低风险（无明显幻觉）"
        elif hallucination_score < 0.5:
            verdict = "中风险（建议人工复核）"
        else:
            verdict = "高风险（疑似幻觉）"

        return {
            "hallucination_score": round(hallucination_score, 4),
            "fact_check": fact,
            "confidence": conf,
            "consistency": consistency,
            "overall_verdict": verdict,
        }


# 辅助函数
def extract_entities_simple(text: str) -> List[str]:
    """简单的实体提取工具函数（供外部调用）。"""
    detector = HallucinationDetector()
    return [e["text"] for e in detector.extract_entities(text)]
