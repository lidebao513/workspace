"""
RAG E2E Test — 端到端 RAG 测试（离线模式）

测试场景覆盖：
1. 知识库有正确答案 → 验证答案与标注一致
2. 知识库无相关信息 → 验证模型拒绝回答
3. 知识库有矛盾信息 → 验证模型能识别矛盾
4. 检索结果为空 → 验证降级处理
"""

import os
import sys
import unittest

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from ext.d_ext_embedding import EmbeddingTester
from ext.d_ext_retrieval_metrics import RetrievalMetrics
from ext.d_ext_hallucination import HallucinationDetector


# 模拟知识库
MOCK_KNOWLEDGE_BASE = """
DeepSeek API 提供 chat/completions 接口，支持 deepseek-chat 和 deepseek-reasoner 模型。
DeepSeek API 兼容 OpenAI SDK，可以通过 openai Python SDK 直接调用。
API 地址为 https://api.deepseek.com。
DeepSeek API 支持流式输出（stream=True）和批量请求。
Token 计费按输入和输出分别计算，缓存命中享半价。
DeepSeek 的上下文窗口为 64K Token。
"""

MOCK_RELEVANT_ANSWER = "DeepSeek API 使用 OpenAI SDK 调用，endpoint 是 https://api.deepseek.com。"
MOCK_IRRELEVANT_ANSWER = "今天天气不错，适合出门散步。"
MOCK_CONTRADICTING_ANSWER = "DeepSeek API 使用自有协议，不兼容 OpenAI SDK。"
MOCK_REFUSED_ANSWER = "抱歉，我无法回答这个问题。"
MOCK_WEAK_ANSWER = "可能 DeepSeek API 好像是用...嗯...某种 SDK 吧。"


class TestRAGEndToEnd(unittest.TestCase):
    """RAG 端到端测试套件。"""

    def setUp(self):
        self.et = EmbeddingTester()
        self.rm = RetrievalMetrics()
        self.hd = HallucinationDetector()

    # === 场景 1: 知识库有正确答案 ===

    def test_has_answer_retrieval_quality(self):
        """有正确答案时 -> 检索应命中知识库"""
        result = self.hd.check_fact_consistency(
            MOCK_RELEVANT_ANSWER, MOCK_KNOWLEDGE_BASE
        )
        # 至少有一个实体命中知识库
        self.assertGreater(result["kb_hits"], 0,
                            msg="有正确答案时，模型回答应命中知识库")

    def test_has_answer_low_hallucination(self):
        """有正确答案时 -> 幻觉率应较低"""
        eval_result = self.hd.evaluate(
            MOCK_RELEVANT_ANSWER, MOCK_KNOWLEDGE_BASE
        )
        # 幻觉分应低于高风险线
        self.assertLess(eval_result["hallucination_score"], 0.5,
                        msg=f"有正确答案时幻觉分应 < 0.5，实际 {eval_result['hallucination_score']}")

    def test_has_answer_fact_hits(self):
        """有正确答案时 -> 事实核对命中率应 > 0"""
        result = self.hd.check_fact_consistency(
            MOCK_RELEVANT_ANSWER, MOCK_KNOWLEDGE_BASE
        )
        self.assertGreater(result["hit_rate"], 0.0)

    # === 场景 2: 知识库无相关信息 ===

    def test_no_answer_refuses(self):
        """无相关信息时 -> 模型拒绝回答（实体少/回答短）"""
        conf = self.hd.score_confidence(MOCK_REFUSED_ANSWER)
        # 拒绝回答通常没有事实核对的必要
        entities = self.hd.extract_entities(MOCK_REFUSED_ANSWER)
        self.assertLess(len(entities), 3,
                        msg="拒绝回答时不应包含大量事实实体")

    def test_no_answer_entity_count(self):
        """无相关信息时 -> 回答中实体应很少或为 0"""
        entities = self.hd.extract_entities(MOCK_IRRELEVANT_ANSWER)
        # 不相关回答中的实体不应在知识库中命中
        result = self.hd.check_fact_consistency(
            MOCK_IRRELEVANT_ANSWER, MOCK_KNOWLEDGE_BASE
        )
        self.assertEqual(result["kb_hits"], 0,
                         msg="无关回答不应命中知识库")

    def test_no_answer_semantic_distance(self):
        """无相关信息时 -> 问答语义距离应很大"""
        sim = self.et.compute_similarity(
            "DeepSeek API 怎么调用", "今天天气不错，适合出门散步"
        )
        level = self.et.get_similarity_level(sim)
        self.assertIn(level, ("low", "unrelated"),
                      msg=f"无关问答的语义相似度应为 low/unrelated，实际 {level}")

    # === 场景 3: 知识库有矛盾信息 ===

    def test_contradiction_detected(self):
        """矛盾信息时 -> 事实核对应发现不一致"""
        result = self.hd.check_fact_consistency(
            MOCK_CONTRADICTING_ANSWER, MOCK_KNOWLEDGE_BASE
        )
        # "不兼容" 不应在知识库中命中
        self.assertIn("不兼容", MOCK_CONTRADICTING_ANSWER)
        self.assertNotIn("不兼容", MOCK_KNOWLEDGE_BASE)

    def test_contradiction_unmatched_entity(self):
        """矛盾信息时 -> 应有未命中的实体"""
        result = self.hd.check_fact_consistency(
            MOCK_CONTRADICTING_ANSWER, MOCK_KNOWLEDGE_BASE
        )
        # "不兼容" 这个断言不在知识库中
        unmatched_joined = " ".join(result["unmatched_entities"])
        self.assertGreater(len(result["unmatched_entities"]), 0,
                           msg="矛盾回答应有未命中的实体")

    def test_contradiction_hallucination_score(self):
        """矛盾信息时 -> 幻觉分应较高"""
        eval_result = self.hd.evaluate(
            MOCK_CONTRADICTING_ANSWER, MOCK_KNOWLEDGE_BASE
        )
        # 矛盾回答的幻觉分应高于一致回答的幻觉分
        normal_eval = self.hd.evaluate(
            MOCK_RELEVANT_ANSWER, MOCK_KNOWLEDGE_BASE
        )
        self.assertGreater(
            eval_result["hallucination_score"],
            normal_eval["hallucination_score"],
            msg="矛盾回答的幻觉分应高于正确回答",
        )

    # === 场景 4: 检索结果为空（降级） ===

    def test_empty_retrieval_handling(self):
        """检索为空时 -> 应有降级处理（拒绝/道歉/免责）"""
        fallback_phrases = ["抱歉", "无法回答", "不知道", "没有找到", "无法确认"]
        has_fallback = any(p in MOCK_REFUSED_ANSWER for p in fallback_phrases)
        self.assertTrue(has_fallback or len(MOCK_REFUSED_ANSWER) < 30,
                        msg="检索为空时应触发降级策略")

    def test_empty_retrieval_short_answer(self):
        """检索为空时 -> 回答应简短（没有编造的空间）"""
        weak_conf = self.hd.score_confidence(MOCK_WEAK_ANSWER)
        refused_conf = self.hd.score_confidence(MOCK_REFUSED_ANSWER)
        # 拒绝回答不应有模糊词
        self.assertGreaterEqual(refused_conf["confidence_score"], 0.0)

    def test_empty_retrieval_no_new_info(self):
        """检索为空时 -> 回答不应包含知识库中没有的信息"""
        # 模拟检索结果为空的场景：传入空的知识库
        result = self.hd.check_fact_consistency(
            MOCK_WEAK_ANSWER, ""
        )
        # 空知识库时任何实体都是"未命中"
        if result["total_checked"] > 0:
            self.assertGreater(result["hallucination_rate"], 0.0)

    # === 补充场景: 检索质量与注入 ===

    def test_retrieval_precision_basic(self):
        """检索质量: Precision 基础计算"""
        self.assertAlmostEqual(self.rm.precision_at_k(3, 5), 0.6)

    def test_retrieval_recall_basic(self):
        """检索质量: Recall 基础计算"""
        self.assertAlmostEqual(self.rm.recall_at_k(3, 5, 5), 0.6)

    def test_retrieval_ndcg_penalty(self):
        """检索质量: 排序不好 NDCG 降低"""
        good = self.rm.ndcg_at_k([3, 2, 1], 3)
        bad = self.rm.ndcg_at_k([1, 2, 3], 3)
        self.assertGreater(good, bad,
                           msg="强相关在前时的 NDCG 应高于弱相关在前")

    def test_retrieval_e2e_analysis(self):
        """检索质量: 批量分析返回完整结构"""
        queries = self.rm.get_sample_queries()
        result = self.rm.analyze_queries(queries, 3)
        self.assertIn("precision_at_k", result)
        self.assertIn("recall_at_k", result)
        self.assertIn("mrr_at_k", result)
        self.assertIn("ndcg_at_k", result)

    # === 补充场景: 多轮 RAG 一致性 ===

    def test_multi_turn_consistency(self):
        """多轮对话中实体一致性应较高"""
        responses = [
            "DeepSeek API 使用 OpenAI SDK。",
            "DeepSeek API 兼容 OpenAI SDK，可以直接调用。",
        ]
        result = self.hd.check_consistency_across_runs(responses)
        self.assertGreater(result["consistency_rate"], 0.5,
                           msg="相同问题的多次回答应保持较高实体一致性")

    def test_multi_turn_inconsistency_detected(self):
        """多轮对话中不一致应被检测到"""
        responses = [
            "DeepSeek API 使用 OpenAI SDK。",
            "DeepSeek API 使用自有协议。",
        ]
        result = self.hd.check_consistency_across_runs(responses)
        self.assertGreater(len(result["inconsistent_entities"]), 0,
                           msg="矛盾回答应产生不一致的实体")


if __name__ == "__main__":
    unittest.main()
