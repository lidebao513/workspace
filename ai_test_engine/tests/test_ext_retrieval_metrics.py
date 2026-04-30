"""Test RetrievalMetrics — Precision@K / Recall@K / MRR / NDCG@K。"""

import math
import os
import sys
import unittest

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from ext.d_ext_retrieval_metrics import RetrievalMetrics


class TestPrecisionAtK(unittest.TestCase):
    """测试 Precision@K。"""

    def test_all_relevant(self):
        """前 K 个全相关"""
        self.assertAlmostEqual(RetrievalMetrics.precision_at_k(5, 5), 1.0)

    def test_half_relevant(self):
        """一半相关"""
        self.assertAlmostEqual(RetrievalMetrics.precision_at_k(3, 6), 0.5)

    def test_none_relevant(self):
        """全不相关"""
        self.assertAlmostEqual(RetrievalMetrics.precision_at_k(0, 5), 0.0)

    def test_k_equals_1(self):
        """K=1"""
        self.assertAlmostEqual(RetrievalMetrics.precision_at_k(1, 1), 1.0)
        self.assertAlmostEqual(RetrievalMetrics.precision_at_k(0, 1), 0.0)

    def test_k_invalid(self):
        """K <= 0 -> 抛 ValueError"""
        with self.assertRaises(ValueError):
            RetrievalMetrics.precision_at_k(0, 0)
        with self.assertRaises(ValueError):
            RetrievalMetrics.precision_at_k(0, -1)


class TestRecallAtK(unittest.TestCase):
    """测试 Recall@K。"""

    def test_full_coverage(self):
        """覆盖所有相关文档"""
        self.assertAlmostEqual(RetrievalMetrics.recall_at_k(3, 3, 5), 1.0)

    def test_half_coverage(self):
        """覆盖一半"""
        self.assertAlmostEqual(RetrievalMetrics.recall_at_k(2, 4, 5), 0.5)

    def test_no_coverage(self):
        """未被覆盖"""
        self.assertAlmostEqual(RetrievalMetrics.recall_at_k(0, 5, 5), 0.0)

    def test_no_relevant_docs(self):
        """没有相关文档 -> 返回 1.0"""
        self.assertAlmostEqual(RetrievalMetrics.recall_at_k(0, 0, 5), 1.0)

    def test_relevant_exceeds_total(self):
        """相关数超过总数（数据异常但计算合理）"""
        self.assertGreater(RetrievalMetrics.recall_at_k(5, 3, 5), 1.0)

    def test_k_invalid(self):
        """K <= 0 -> 抛 ValueError"""
        with self.assertRaises(ValueError):
            RetrievalMetrics.recall_at_k(0, 5, 0)

    def test_negative_total(self):
        """total_relevant 为负 -> ValueError"""
        with self.assertRaises(ValueError):
            RetrievalMetrics.recall_at_k(0, -1, 5)


class TestReciprocalRank(unittest.TestCase):
    """测试 RR@K。"""

    def test_first_pos(self):
        """第一个结果就相关"""
        self.assertAlmostEqual(RetrievalMetrics.reciprocal_rank_at_k(1, 5), 1.0)

    def test_third_pos(self):
        """第三个结果相关"""
        expected = 1.0 / 3.0
        self.assertAlmostEqual(RetrievalMetrics.reciprocal_rank_at_k(3, 5), expected)

    def test_beyond_k(self):
        """第一个相关结果在 K 之后"""
        self.assertAlmostEqual(RetrievalMetrics.reciprocal_rank_at_k(6, 5), 0.0)

    def test_none(self):
        """没有相关结果"""
        self.assertAlmostEqual(RetrievalMetrics.reciprocal_rank_at_k(None, 5), 0.0)

    def test_invalid_rank(self):
        """排名 < 1 -> ValueError"""
        with self.assertRaises(ValueError):
            RetrievalMetrics.reciprocal_rank_at_k(0, 5)

    def test_k_invalid(self):
        """K <= 0 -> ValueError"""
        with self.assertRaises(ValueError):
            RetrievalMetrics.reciprocal_rank_at_k(1, 0)


class TestMRR(unittest.TestCase):
    """测试 MRR@K。"""

    def test_all_first(self):
        """所有查询的第一个结果都相关"""
        ranks = [1, 1, 1]
        self.assertAlmostEqual(RetrievalMetrics.mrr_at_k(ranks, 5), 1.0)

    def test_mixed(self):
        """混合情况"""
        ranks = [1, 3, None]
        # RR1=1.0, RR2=1/3, RR3=0.0
        expected = (1.0 + 1/3 + 0.0) / 3
        self.assertAlmostEqual(RetrievalMetrics.mrr_at_k(ranks, 5), expected)

    def test_all_none(self):
        """全无相关结果"""
        self.assertAlmostEqual(RetrievalMetrics.mrr_at_k([None, None], 5), 0.0)

    def test_single_query(self):
        """单个查询"""
        self.assertAlmostEqual(RetrievalMetrics.mrr_at_k([1], 5), 1.0)
        self.assertAlmostEqual(RetrievalMetrics.mrr_at_k([None], 5), 0.0)

    def test_empty(self):
        """空列表"""
        self.assertAlmostEqual(RetrievalMetrics.mrr_at_k([], 5), 0.0)

    def test_beyond_k(self):
        """部分结果在 K 之后"""
        ranks = [1, 10]
        expected = (1.0 + 0.0) / 2
        self.assertAlmostEqual(RetrievalMetrics.mrr_at_k(ranks, 5), expected)


class TestDCG(unittest.TestCase):
    """测试 DCG@K。"""

    def test_perfect(self):
        """全满分"""
        dcg = RetrievalMetrics.dcg_at_k([3, 3, 3], 3)
        expected = (7.0 / math.log2(2)) + (7.0 / math.log2(3)) + (7.0 / math.log2(4))
        self.assertAlmostEqual(dcg, expected)

    def test_zero(self):
        """全 0 分"""
        dcg = RetrievalMetrics.dcg_at_k([0, 0, 0], 3)
        # (2^0-1)/log2... = 0/log2... = 0
        self.assertAlmostEqual(dcg, 0.0)

    def test_mixed(self):
        """混合评分"""
        dcg = RetrievalMetrics.dcg_at_k([3, 1, 0], 3)
        expected = (7.0 / math.log2(2)) + (1.0 / math.log2(3)) + (0.0 / math.log2(4))
        self.assertAlmostEqual(dcg, expected)

    def test_empty(self):
        """空列表"""
        self.assertAlmostEqual(RetrievalMetrics.dcg_at_k([], 3), 0.0)

    def test_partial_k(self):
        """K 超过结果长度"""
        dcg3 = RetrievalMetrics.dcg_at_k([3, 1], 3)
        dcg2 = RetrievalMetrics.dcg_at_k([3, 1], 2)
        self.assertAlmostEqual(dcg3, dcg2)


class TestIDCG(unittest.TestCase):
    """测试 IDCG@K。"""

    def test_ideal_is_max(self):
        """IDCG >= DCG"""
        scores = [3, 1, 2, 0]
        dcg = RetrievalMetrics.dcg_at_k(scores, 4)
        idcg = RetrievalMetrics.ideal_dcg_at_k(scores, 4)
        self.assertGreaterEqual(idcg, dcg)

    def test_perfect_already(self):
        """已是完美排序"""
        scores = [3, 3, 3]
        self.assertAlmostEqual(
            RetrievalMetrics.dcg_at_k(scores, 3),
            RetrievalMetrics.ideal_dcg_at_k(scores, 3),
        )

    def test_empty(self):
        """空列表"""
        self.assertAlmostEqual(RetrievalMetrics.ideal_dcg_at_k([], 3), 0.0)

    def test_unsorted_ideal(self):
        """乱序时的 IDCG 计算"""
        scores = [0, 3, 1, 2]
        idcg = RetrievalMetrics.ideal_dcg_at_k(scores, 4)
        # 排序后 [3, 2, 1, 0]
        dcg_sorted = RetrievalMetrics.dcg_at_k([3, 2, 1, 0], 4)
        self.assertAlmostEqual(idcg, dcg_sorted)


class TestNDCG(unittest.TestCase):
    """测试 NDCG@K。"""

    def test_perfect(self):
        """完美排序 -> NDCG = 1.0"""
        self.assertAlmostEqual(RetrievalMetrics.ndcg_at_k([3, 3, 3], 3), 1.0)

    def test_worst(self):
        """全 0 -> 没有增益，视作完美"""
        ndcg = RetrievalMetrics.ndcg_at_k([0, 0, 0], 3)
        self.assertAlmostEqual(ndcg, 1.0)  # DCG=IDCG=0，约定返回1

    def test_some_value(self):
        """部分正确 -> NDCG 在 0~1 之间"""
        # [1, 3, 1] 排序后为 [3, 1, 1]，所以 NDCG < 1.0
        ndcg = RetrievalMetrics.ndcg_at_k([1, 3, 1], 3)
        self.assertGreater(ndcg, 0.0)
        self.assertLess(ndcg, 1.0)

    def test_empty(self):
        """空 -> 0.0"""
        self.assertAlmostEqual(RetrievalMetrics.ndcg_at_k([], 3), 0.0)

    def test_bad_order_penalty(self):
        """排序惩罚：弱相关在前不如强相关在前"""
        sorted_ndcg = RetrievalMetrics.ndcg_at_k([3, 2, 1], 3)
        unsorted_ndcg = RetrievalMetrics.ndcg_at_k([1, 2, 3], 3)
        self.assertGreater(sorted_ndcg, unsorted_ndcg)


class TestAnalyzeQueries(unittest.TestCase):
    """测试批量查询分析。"""

    def test_empty(self):
        """空查询列表"""
        result = RetrievalMetrics.analyze_queries([], 5)
        self.assertEqual(result["num_queries"], 0)

    def test_sample_set_k3(self):
        """预置测试集 K=3"""
        queries = RetrievalMetrics.get_sample_queries()
        result = RetrievalMetrics.analyze_queries(queries, 3)
        self.assertEqual(result["num_queries"], 5)
        self.assertEqual(result["k"], 3)
        self.assertGreater(result["precision_at_k"], 0.0)
        self.assertGreaterEqual(result["mrr_at_k"], 0.0)
        self.assertLessEqual(result["ndcg_at_k"], 1.0)

    def test_sample_set_k5(self):
        """预置测试集 K=5"""
        queries = RetrievalMetrics.get_sample_queries()
        result = RetrievalMetrics.analyze_queries(queries, 5)
        self.assertEqual(result["k"], 5)
        per_query = result["per_query"]
        self.assertEqual(len(per_query), 5)

    def test_single_query_scores(self):
        """单查询的详细分数"""
        queries = [
            {
                "query": "test",
                "relevance_scores": [3, 0, 0],
                "total_relevant": 2,
            }
        ]
        result = RetrievalMetrics.analyze_queries(queries, 3)
        pq = result["per_query"][0]
        self.assertAlmostEqual(pq["precision"], round(1.0/3.0, 4))  # 1/3 相关
        self.assertAlmostEqual(pq["recall"], 0.5)     # 1/2 被召回
        self.assertAlmostEqual(pq["reciprocal_rank"], 1.0)  # 第1就相关

    def test_no_relevant(self):
        """查询完全无相关结果"""
        queries = [
            {
                "query": "none",
                "relevance_scores": [0, 0, 0],
                "total_relevant": 3,
            }
        ]
        result = RetrievalMetrics.analyze_queries(queries, 3)
        pq = result["per_query"][0]
        self.assertAlmostEqual(pq["precision"], 0.0)
        self.assertAlmostEqual(pq["recall"], 0.0)
        self.assertAlmostEqual(pq["reciprocal_rank"], 0.0)

    def test_perfect_retrieval(self):
        """完美检索"""
        queries = [
            {
                "query": "perfect",
                "relevance_scores": [3, 3, 3],
                "total_relevant": 3,
            }
        ]
        result = RetrievalMetrics.analyze_queries(queries, 3)
        pq = result["per_query"][0]
        self.assertAlmostEqual(pq["precision"], 1.0)
        self.assertAlmostEqual(pq["recall"], 1.0)
        self.assertAlmostEqual(pq["ndcg"], 1.0)

    def test_query_labels(self):
        """自定义查询标签"""
        queries = RetrievalMetrics.get_sample_queries()
        labels = [q["query"] for q in queries]
        self.assertIn("AI测试需要哪些技能", labels)
        self.assertIn("RAG系统怎么测试", labels)

    def test_mrr_in_analyze(self):
        """批量分析中的 MRR 计算"""
        queries = RetrievalMetrics.get_sample_queries()
        result = RetrievalMetrics.analyze_queries(queries, 5)
        # Query 3 (Python测试框架对比) 全部不相关 -> RR=0
        # 所以 MRR < 1.0
        self.assertLess(result["mrr_at_k"], 1.0)
        self.assertGreater(result["mrr_at_k"], 0.0)

    def test_different_k_values(self):
        """不同 K 值的对比"""
        queries = RetrievalMetrics.get_sample_queries()
        r3 = RetrievalMetrics.analyze_queries(queries, 3)
        r5 = RetrievalMetrics.analyze_queries(queries, 5)
        # K=5 通常表现不差于 K=3（更多结果有更多潜力）
        self.assertGreaterEqual(r5["recall_at_k"], r3["recall_at_k"])


class TestSampleQueries(unittest.TestCase):
    """测试预置测试集的结构完整性。"""

    def test_all_have_keys(self):
        """所有查询都有 required key"""
        for q in RetrievalMetrics.get_sample_queries():
            for key in ("query", "relevance_scores", "total_relevant"):
                self.assertIn(key, q)

    def test_scores_length(self):
        """评分列表长度一致"""
        for q in RetrievalMetrics.get_sample_queries():
            self.assertEqual(len(q["relevance_scores"]), 5)

    def test_score_range(self):
        """评分在有效范围内"""
        for q in RetrievalMetrics.get_sample_queries():
            for s in q["relevance_scores"]:
                self.assertGreaterEqual(s, 0)
                self.assertLessEqual(s, 3)

    def test_non_negative_total(self):
        """相关总数非负"""
        for q in RetrievalMetrics.get_sample_queries():
            self.assertGreaterEqual(q["total_relevant"], 0)

    def test_num_queries(self):
        """5 个查询"""
        self.assertEqual(len(RetrievalMetrics.get_sample_queries()), 5)


if __name__ == "__main__":
    unittest.main()
