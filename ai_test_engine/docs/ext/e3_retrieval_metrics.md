# 补充 Day 3 — 检索质量评估指标

## 学习目标

1. 理解四大检索质量指标（Precision@K、Recall@K、MRR、NDCG@K）的原理
2. 掌握各指标的计算公式和适用场景
3. 学会构建标注测试集进行检索质量评估
4. 理解为什么需要多指标组合评估

> 目标：掌握 Precision@K、Recall@K、MRR、NDCG@K 四大检索质量指标，能构建标注测试集并自动评估。

---

## 一、为什么需要检索质量指标？

RAG 系统的质量首先取决于**检索质量**。如果检索出来的文档不对，模型再聪明也答不好。

四大指标各自回答一个问题：

| 指标 | 回答的问题 | 关注维度 |
|------|-----------|----------|
| Precision@K | 检出来的东西里，有多少是相关的？ | 准确率 |
| Recall@K | 所有相关的东西，检出来了多少？ | 覆盖率 |
| MRR@K | 第一个正确答案排第几？ | 排名 |
| NDCG@K | 相关文档是否排在了正确的位置？ | 排序质量 |

这四个指标必须一起看。只看 Precision 不看 Recall，可能只检索了一条相关文档但丢了九条。

---

## 二、四大指标详解

### 2.1 Precision@K

**公式**：
```
Precision@K = (前 K 个结果中相关文档数) / K
```

**直观理解**：用户看了前 K 条结果，有多少是想要的。

**示例**（K=3）：
```
检索结果排名：[相关, 相关, 不相关, 相关, 不相关]
                ↑     ↑     ↑
                前3个里有2个相关 → Precision@3 = 2/3 = 0.667
```

**边界情况**：
- 全相关 → 1.0
- 全不相关 → 0.0
- K 越大，Precision 通常会下降（更多不相关结果混进来）

### 2.2 Recall@K

**公式**：
```
Recall@K = (前 K 个结果中相关文档数) / (知识库中总相关文档数)
```

**直观理解**：所有相关的文档里，检索系统找回了多少。

**示例**（K=3，库中有 5 条相关文档）：
```
检索结果排名：[相关, 相关, 不相关]
前3个里有2个相关，库中共5条 → Recall@3 = 2/5 = 0.4
```

**边界情况**：
- 没有相关文档时 → 约定返回 1.0（没有要召回的，算完美）
- 相关数超过库中总数 → 可能 > 1.0（数据异常，但计算合理）

### 2.3 MRR@K (Mean Reciprocal Rank)

**公式**：
```
RR@K = 1 / rank_of_first_relevant  （如果 rank <= K）
RR@K = 0                             （前 K 个没有相关结果）

MRR@K = (1/N) × sum(RR@K for all queries)
```

**直观理解**：用户最快在第几条结果找到想要的。排名越靠前越好。

**示例**（K=5）：
```
查询A：第一个相关在第 1 位 → RR=1/1=1.0
查询B：第一个相关在第 3 位 → RR=1/3=0.333
查询C：前5个都不相关       → RR=0/5=0.0

MRR@5 = (1.0 + 0.333 + 0.0) / 3 = 0.444
```

**适用场景**："查找类"任务（用户只关心第一个正确答案的位置）。

### 2.4 NDCG@K (Normalized Discounted Cumulative Gain)

**公式**：
```
DCG@K  = sum_{i=1}^{k} (2^{rel_i} - 1) / log2(i+1)
IDCG@K = 将评分按降序排列后计算的 DCG
NDCG@K = DCG@K / IDCG@K
```

**直观理解**：相关度高的文档排前面多给分，排后面少给分。

**示例**（K=3）：
```
相关性评分：[3, 1, 2]  （强相关=3，弱相关=1）

DCG@3 = (2^3-1)/log2(2) + (2^1-1)/log2(3) + (2^2-1)/log2(4)
     = 7/1 + 1/1.585 + 3/2
     = 7 + 0.631 + 1.5 = 9.131

IDCG@3（排序后 [3, 2, 1]）:
     = 7/1 + 3/1.585 + 1/2 = 7 + 1.893 + 0.5 = 9.393

NDCG@3 = 9.131 / 9.393 = 0.972
```

排序不好时 NDCG 会显著下降。这是四个指标里唯一考虑**排序顺序**的。

---

## 三、四指标对比速查

| 特性 | Precision@K | Recall@K | MRR@K | NDCG@K |
|------|-------------|----------|-------|--------|
| 考虑排名 | 否 | 否 | 是（只关心第1个） | 是（关心全部位置） |
| 需要总分档数 | 否 | 是 | 否 | 否 |
| 多级相关性 | 二值化 | 二值化 | 二值化 | 支持三级 |
| 取值范围 | [0, 1] | [0, 1+] | [0, 1] | [0, 1] |
| 核心价值 | 准确率 | 覆盖率 | 最快找到 | 排序质量 |

---

## 四、构建测试集的方法论

### 标注数据集

```python
query_results = [
    {
        "query": "AI测试需要哪些技能",
        "relevance_scores": [3, 2, 1, 0, 0],   # 检索结果的标注
        "total_relevant": 4,                     # 库中共有 4 条相关
    },
    ...
]
```

相关性等级：
- **0** = 不相关
- **1** = 弱相关（沾边但不直接）
- **2** = 相关（回答了问题的一部分）
- **3** = 强相关（直接回答了问题）

### 预置测试集

`RetrievalMetrics.get_sample_queries()` 提供 5 条预置查查询：

| 查询 | 检索结果 | 库中相关数 | Precision@3 | Recall@3 | NDCG@3 |
|------|---------|-----------|-------------|---------|--------|
| AI测试需要哪些技能 | [3,2,1,0,0] | 4 | 1.0 | 0.75 | ~0.91 |
| RAG系统怎么测试 | [3,3,2,0,0] | 5 | 1.0 | 0.60 | ~0.96 |
| 什么是Prompt Injection | [3,0,0,0,0] | 3 | 0.33 | 0.33 | ~0.58 |
| Python测试框架对比 | [0,0,0,0,0] | 2 | 0.0 | 0.0 | 0.0 |
| Embedding向量维度 | [3,2,3,0,0] | 3 | 1.0 | 1.0 | ~0.96 |

### 面试话术

> "评估检索质量我用四个指标：Precision@K 和 Recall@K 衡量准确率和覆盖率，MRR 看用户能否快速找到第一个答案，NDCG 评估排序是否合理。这四个指标必须组合使用——比如只看 Precision，你可能只检了一条相关结果就以为自己完美了，但忽略了没召回的其他 9 条。我的做法是先构建一个 50-100 条查询的标注测试集，然后定期回归，监控模型更新或知识库变更是否导致检索退化。"

---

## 五、面试题

**Q: Precision@K 和 Recall@K 有什么区别？为什么需要同时关注？**
A: Precision@K 衡量的是前 K 个结果中有多少是相关的（准确率），Recall@K 衡量的是所有相关文档中有多少被检索到了（覆盖率）。只看 Precision 可能只检了一条相关文档就以为完美了，但忽略了没召回的其他文档；只看 Recall 可能召回了很多不相关的结果。必须两者结合才能全面评估检索质量。

**Q: MRR 和 NDCG 有什么区别？分别适用于什么场景？**
A: MRR 只关心第一个相关结果的位置，适用于"查找类"任务；NDCG 考虑所有结果的排序质量，支持多级相关性评分，适用于需要综合排序质量的场景。MRR 简单直观但忽略了其他结果的排序，NDCG 更全面但计算复杂。

**Q: 为什么 NDCG 需要归一化？**
A: NDCG 将实际排序的 DCG 除以理想排序的 IDCG，这样可以消除查询间的差异，使得不同查询的 NDCG 可以比较。归一化后，NDCG 的取值范围在 [0, 1] 之间，1 表示完美排序。

**Q: 如何选择合适的 K 值？**
A: K 值的选择取决于具体场景。如果用户只关心第一个结果，K=1 或 K=3 合适；如果需要展示多个结果，K=5 或 K=10 更合适。通常需要在 Precision 和 Recall 之间做权衡，K 越大，Recall 越高但 Precision 越低。

## 六、代码示例

### 检索质量指标计算工具

```python
from typing import List, Dict
import math

class RetrievalMetrics:
    """检索质量指标计算工具"""
    
    @staticmethod
    def precision_at_k(relevance_scores: List[int], k: int) -> float:
        """计算 Precision@K"""
        if k <= 0:
            return 0.0
        top_k = relevance_scores[:k]
        relevant_count = sum(1 for score in top_k if score > 0)
        return relevant_count / k if k > 0 else 0.0
    
    @staticmethod
    def recall_at_k(relevance_scores: List[int], k: int, total_relevant: int) -> float:
        """计算 Recall@K"""
        if total_relevant == 0:
            return 1.0  # 没有要召回的，算完美
        top_k = relevance_scores[:k]
        relevant_found = sum(1 for score in top_k if score > 0)
        return relevant_found / total_relevant
    
    @staticmethod
    def mrr_at_k(relevance_scores: List[int], k: int) -> float:
        """计算 MRR@K (Mean Reciprocal Rank)"""
        for i, score in enumerate(relevance_scores[:k], 1):
            if score > 0:
                return 1.0 / i
        return 0.0
    
    @staticmethod
    def dcg_at_k(relevance_scores: List[int], k: int) -> float:
        """计算 DCG@K (Discounted Cumulative Gain)"""
        dcg = 0.0
        for i, score in enumerate(relevance_scores[:k], 1):
            if i == 1:
                dcg += score  # log2(1+1) = 1
            else:
                dcg += score / math.log2(i + 1)
        return dcg
    
    @staticmethod
    def ndcg_at_k(relevance_scores: List[int], k: int) -> float:
        """计算 NDCG@K (Normalized DCG)"""
        dcg = RetrievalMetrics.dcg_at_k(relevance_scores, k)
        # 理想排序：按相关性降序排列
        ideal_scores = sorted(relevance_scores, reverse=True)
        idcg = RetrievalMetrics.dcg_at_k(ideal_scores, k)
        return dcg / idcg if idcg > 0 else 0.0
    
    @staticmethod
    def analyze_queries(query_results: List[Dict], k: int = 5) -> Dict:
        """批量分析一组查询的检索质量"""
        results = {
            'precision_at_k': [],
            'recall_at_k': [],
            'mrr_at_k': [],
            'ndcg_at_k': []
        }
        
        for query in query_results:
            scores = query['relevance_scores']
            total_rel = query['total_relevant']
            
            results['precision_at_k'].append(RetrievalMetrics.precision_at_k(scores, k))
            results['recall_at_k'].append(RetrievalMetrics.recall_at_k(scores, k, total_rel))
            results['mrr_at_k'].append(RetrievalMetrics.mrr_at_k(scores, k))
            results['ndcg_at_k'].append(RetrievalMetrics.ndcg_at_k(scores, k))
        
        # 计算平均值
        return {
            'k': k,
            'query_count': len(query_results),
            'precision_at_k': sum(results['precision_at_k']) / len(results['precision_at_k']),
            'recall_at_k': sum(results['recall_at_k']) / len(results['recall_at_k']),
            'mrr_at_k': sum(results['mrr_at_k']) / len(results['mrr_at_k']),
            'ndcg_at_k': sum(results['ndcg_at_k']) / len(results['ndcg_at_k']),
            'detailed': results
        }
    
    @staticmethod
    def get_sample_queries() -> List[Dict]:
        """获取预置的示例查询数据"""
        return [
            {
                "query": "AI测试需要哪些技能",
                "relevance_scores": [3, 2, 1, 0, 0],
                "total_relevant": 4
            },
            {
                "query": "RAG系统怎么测试",
                "relevance_scores": [3, 3, 2, 0, 0],
                "total_relevant": 5
            },
            {
                "query": "什么是Prompt Injection",
                "relevance_scores": [3, 0, 0, 0, 0],
                "total_relevant": 3
            },
            {
                "query": "Python测试框架对比",
                "relevance_scores": [0, 0, 0, 0, 0],
                "total_relevant": 2
            },
            {
                "query": "Embedding向量维度",
                "relevance_scores": [3, 2, 3, 0, 0],
                "total_relevant": 3
            }
        ]

# 使用示例
if __name__ == "__main__":
    # 获取示例数据
    queries = RetrievalMetrics.get_sample_queries()
    
    # 批量分析
    results = RetrievalMetrics.analyze_queries(queries, k=3)
    
    print("检索质量分析报告:")
    print(f"查询数量: {results['query_count']}")
    print(f"Precision@3: {results['precision_at_k']:.4f}")
    print(f"Recall@3: {results['recall_at_k']:.4f}")
    print(f"MRR@3: {results['mrr_at_k']:.4f}")
    print(f"NDCG@3: {results['ndcg_at_k']:.4f}")
    
    # 单个查询分析
    query = queries[0]
    print(f"\n单个查询分析: {query['query']}")
    print(f"Precision@5: {RetrievalMetrics.precision_at_k(query['relevance_scores'], 5):.4f}")
    print(f"Recall@5: {RetrievalMetrics.recall_at_k(query['relevance_scores'], 5, query['total_relevant']):.4f}")
    print(f"MRR@5: {RetrievalMetrics.mrr_at_k(query['relevance_scores'], 5):.4f}")
    print(f"NDCG@5: {RetrievalMetrics.ndcg_at_k(query['relevance_scores'], 5):.4f}")
```

## 七、练习题

1. **基础题：** 使用 `RetrievalMetrics` 计算示例数据在 K=1、K=3、K=5 时的各项指标，并比较结果差异。

2. **进阶题：** 添加一个新的查询数据到示例中，并分析其对整体指标的影响。

3. **挑战题：** 实现一个函数，根据给定的指标阈值（如 Precision@3 >= 0.8）筛选出需要优化的查询。

## 八、自检清单

- [ ] 能手写 Precision@K 和 Recall@K 公式
- [ ] 能解释 MRR 什么时候用、什么时候不能用
- [ ] 能说出 NDCG 比前三个指标多考虑了哪个维度
- [ ] 能构造一个标注测试集（含多级相关性评分）
- [ ] 能解释为什么只看单一指标有盲区
- [ ] 能用 `analyze_queries` 批量评估一组查询

---

## 产出物

| 文件 | 说明 |
|------|------|
| `ext/retrieval_metrics.py` | Precision@K / Recall@K / MRR / NDCG@K + 批量分析 |
| `tests/test_ext_retrieval_metrics.py` | 52 个测试全部 PASS |
| `docs/ext/e3_retrieval_metrics.md` | 本文档 |
