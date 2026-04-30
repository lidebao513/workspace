"""
Retrieval Metrics — 检索质量评估四大指标

功能：
1. Precision@K：前 K 个结果中相关文档的比例
2. Recall@K：所有相关文档中被召回的覆盖比例
3. MRR (Mean Reciprocal Rank)：第一个正确答案的排名倒数
4. NDCG@K (Normalized Discounted Cumulative Gain)：位置加权的累积增益

用法：
    from ext.retrieval_metrics import RetrievalMetrics
    rm = RetrievalMetrics()
    rm.precision_at_k(relevant_in_top_k, k)
    rm.recall_at_k(relevant_in_top_k, total_relevant, k)
"""

import math
from typing import List, Dict, Optional, Tuple


class RetrievalMetrics:
    """检索质量评估指标计算器。

    所有指标均支持批量计算和单次计算。
    """

    # 等级标签
    RELEVANCE_LABELS = {0: "不相关", 1: "弱相关", 2: "相关", 3: "强相关"}

    @staticmethod
    def precision_at_k(relevant_in_top_k: int, k: int) -> float:
        """计算 Precision@K。

        Precision@K = 前 K 个结果中相关文档数 / K

        Args:
            relevant_in_top_k: 前 K 个结果中相关文档的数量
            k: 截断位置

        Returns:
            Precision@K 值 [0.0, 1.0]
        """
        if k <= 0:
            raise ValueError("K 必须大于 0")
        return relevant_in_top_k / k

    @staticmethod
    def recall_at_k(relevant_in_top_k: int, total_relevant: int, k: int) -> float:
        """计算 Recall@K。

        Recall@K = 前 K 个结果中相关文档数 / 总相关文档数

        Args:
            relevant_in_top_k: 前 K 个结果中相关文档的数量
            total_relevant: 知识库中总相关文档数
            k: 截断位置（仅用于校验）

        Returns:
            Recall@K 值 [0.0, 1.0]（total_relevant=0 时返回 1.0）
        """
        if k <= 0:
            raise ValueError("K 必须大于 0")
        if total_relevant == 0:
            return 1.0  # 没有相关文档时，认为完美覆盖
        if total_relevant < 0:
            raise ValueError("total_relevant 不能为负数")
        return relevant_in_top_k / total_relevant

    @staticmethod
    def reciprocal_rank_at_k(rank_of_first_relevant: Optional[int], k: int) -> float:
        """计算单个查询的 Reciprocal Rank @ K。

        RR@K = 1 / rank_of_first_relevant  (如果 rank <= K)
        RR@K = 0  (如果前 K 个中没有相关结果)

        Args:
            rank_of_first_relevant: 第一个相关结果的排名（1-based），
                                    没有则传 None
            k: 截断位置

        Returns:
            RR@K 值 [0.0, 1.0]
        """
        if k <= 0:
            raise ValueError("K 必须大于 0")
        if rank_of_first_relevant is None:
            return 0.0
        if rank_of_first_relevant <= 0:
            raise ValueError("排名必须从 1 开始")
        if rank_of_first_relevant > k:
            return 0.0
        return 1.0 / rank_of_first_relevant

    @staticmethod
    def mrr_at_k(ranks: List[Optional[int]], k: int) -> float:
        """计算 MRR@K (Mean Reciprocal Rank)。

        MRR@K = (1/N) * sum(RR@K for each query)

        Args:
            ranks: 每个查询的第一个相关结果排名（1-based），
                   没有相关结果传 None
            k: 截断位置

        Returns:
            MRR@K 值 [0.0, 1.0]
        """
        if not ranks:
            return 0.0
        rr_sum = sum(
            RetrievalMetrics.reciprocal_rank_at_k(r, k) for r in ranks
        )
        return rr_sum / len(ranks)

    @staticmethod
    def dcg_at_k(relevance_scores: List[float], k: int) -> float:
        """计算 DCG@K (Discounted Cumulative Gain)。

        DCG@K = sum_{i=1}^{k} (2^{rel_i} - 1) / log2(i+1)

        Args:
            relevance_scores: 前 K 个结果的相关性得分列表
            k: 截断位置

        Returns:
            DCG@K 值
        """
        if k <= 0:
            raise ValueError("K 必须大于 0")
        if not relevance_scores:
            return 0.0

        k = min(k, len(relevance_scores))
        if k == 0:
            return 0.0

        dcg = 0.0
        for i in range(k):
            rel = relevance_scores[i]
            gain = (2 ** rel - 1) / math.log2(i + 2)  # i+2 因为 log2(1) = 0
            dcg += gain
        return dcg

    @staticmethod
    def ideal_dcg_at_k(relevance_scores: List[float], k: int) -> float:
        """计算 IDCG@K (Ideal DCG)。

        对评分降序排列后计算 DCG，即理论最优值。

        Returns:
            IDCG@K 值
        """
        if not relevance_scores:
            return 0.0
        sorted_scores = sorted(relevance_scores, reverse=True)
        return RetrievalMetrics.dcg_at_k(sorted_scores, k)

    @staticmethod
    def ndcg_at_k(relevance_scores: List[float], k: int) -> float:
        """计算 NDCG@K (Normalized DCG)。

        NDCG@K = DCG@K / IDCG@K

        Returns:
            NDCG@K 值 [0.0, 1.0]
        """
        if k <= 0:
            raise ValueError("K 必须大于 0")
        if not relevance_scores:
            return 0.0

        dcg = RetrievalMetrics.dcg_at_k(relevance_scores, k)
        idcg = RetrievalMetrics.ideal_dcg_at_k(relevance_scores, k)

        if idcg == 0.0:
            return 1.0  # 没有增益时为完美
        return dcg / idcg

    # --- 批量查询分析 ---

    @staticmethod
    def analyze_queries(
        query_results: List[Dict],
        k: int,
    ) -> Dict:
        """对一组查询批量计算所有指标。

        Args:
            query_results: 查询结果列表，每个元素：
                {
                    "query": str,               # 查询语句（可选，仅用于标识）
                    "relevance_scores": [int],   # 每个检索结果的相关性得分 [0-3]
                    "total_relevant": int,        # 知识库中总相关文档数
                }
            k: 截断位置

        Returns:
            {
                "k": int,
                "num_queries": int,
                "precision_at_k": float,     # 所有查询均值
                "recall_at_k": float,
                "mrr_at_k": float,
                "ndcg_at_k": float,
                "per_query": [               # 每个查询的详细结果
                    {
                        "query": str,
                        "precision": float,
                        "recall": float,
                        "reciprocal_rank": float,
                        "ndcg": float,
                    }
                ]
            }
        """
        if not query_results:
            return {
                "k": k,
                "num_queries": 0,
                "precision_at_k": 0.0,
                "recall_at_k": 0.0,
                "mrr_at_k": 0.0,
                "ndcg_at_k": 0.0,
                "per_query": [],
            }

        per_query = []
        all_ranks = []
        all_precisions = []
        all_recalls = []
        all_ndcgs = []

        for qr in query_results:
            scores = qr["relevance_scores"][:k]
            total_rel = qr["total_relevant"]

            # Precision@K
            relevant_count = sum(1 for s in scores if s >= 1)
            prec = RetrievalMetrics.precision_at_k(relevant_count, k)

            # Recall@K
            rec = RetrievalMetrics.recall_at_k(relevant_count, total_rel, k)

            # RR@K
            first_rel_idx = None
            for i, s in enumerate(scores):
                if s >= 1:
                    first_rel_idx = i + 1  # 1-based
                    break
            rr = RetrievalMetrics.reciprocal_rank_at_k(first_rel_idx, k)

            # NDCG@K
            ndcg = RetrievalMetrics.ndcg_at_k(scores, k)

            per_query.append({
                "query": qr.get("query", f"Query-{len(per_query)}"),
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "reciprocal_rank": round(rr, 4),
                "ndcg": round(ndcg, 4),
            })

            all_ranks.append(first_rel_idx)
            all_precisions.append(prec)
            all_recalls.append(rec)
            all_ndcgs.append(ndcg)

        return {
            "k": k,
            "num_queries": len(query_results),
            "precision_at_k": round(sum(all_precisions) / len(all_precisions), 4),
            "recall_at_k": round(sum(all_recalls) / len(all_recalls), 4),
            "mrr_at_k": round(RetrievalMetrics.mrr_at_k(all_ranks, k), 4),
            "ndcg_at_k": round(sum(all_ndcgs) / len(all_ndcgs), 4),
            "per_query": per_query,
        }

    # --- 预置测试集 ---

    @staticmethod
    def get_sample_queries() -> List[Dict]:
        """获取预置的检索测试集。

        模拟一个关于"AI 测试"知识库的 5 个查询，
        每个查询有标注的相关文档数和检索结果评分。
        """
        return [
            {
                "query": "AI测试需要哪些技能",
                "relevance_scores": [3, 2, 1, 0, 0],  # 前3相关
                "total_relevant": 4,
            },
            {
                "query": "RAG系统怎么测试",
                "relevance_scores": [3, 3, 2, 0, 0],  # 前3相关
                "total_relevant": 5,
            },
            {
                "query": "什么是Prompt Injection",
                "relevance_scores": [3, 0, 0, 0, 0],  # 仅第1相关
                "total_relevant": 3,
            },
            {
                "query": "Python测试框架对比",
                "relevance_scores": [0, 0, 0, 0, 0],  # 全不相关
                "total_relevant": 2,
            },
            {
                "query": "Embedding向量维度是多少",
                "relevance_scores": [3, 2, 3, 0, 0],  # 前3相关
                "total_relevant": 3,
            },
        ]
