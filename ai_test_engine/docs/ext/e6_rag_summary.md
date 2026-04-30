# 补充 Day 6 — RAG 测试体系总结

> 目标：汇总 Week 1 的 RAG 测试体系，理清三层验证的关系，更新简历内容。

---

## 一、RAG 测试全链路架构

```
                    ┌────────────────────────────────────────────┐
                    │           RAG 测试全链路                     │
                    └────────────────────────────────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         │                            │                            │
         ▼                            ▼                            ▼
   ┌─────────────┐           ┌──────────────┐           ┌──────────────┐
   │  检索层测试   │           │  生成层测试   │           │ 端到端测试     │
   │ (Retrieval)  │           │ (Generation) │           │ (E2E)         │
   └──────┬──────┘           └──────┬───────┘           └──────┬───────┘
          │                         │                          │
   ┌──────┴──────┐          ┌──────┴───────┐          ┌───────┴──────┐
   │ Precision@K │          │  事实核对     │          │ 答案准确率    │
   │ Recall@K    │          │  幻觉检测     │          │ 用户满意度    │
   │ MRR         │          │  置信度评分   │          │ 降级处理      │
   │ NDCG@K      │          │  一致性检查   │          │ 鲁棒性       │
   │ 检索延迟     │          │  重复查询     │          │ 回归测试     │
   │ Embedding   │          │  空结果降级   │          │              │
   └─────────────┘          └──────────────┘          └──────────────┘
```

---

## 二、三层测试对比表

| 维度 | 检索层测试 | 生成层测试 | 端到端测试 |
|------|-----------|-----------|-----------|
| **测试对象** | Embedding + 检索算法 | Prompt + 模型生成 | 完整 RAG 流程 |
| **关键指标** | Precision@K, Recall@K, MRR, NDCG | 幻觉率, Hit Rate, 置信度 | 综合准确率, 排名 |
| **数据需求** | 标注的查询-文档相关性矩阵 | 知识库 + 标注答案 | 完整 QA 测试集 |
| **是否依赖模型** | 否（纯检索层） | 是（需模型生成） | 是（需完整流程） |
| **测试频率** | 知识库更新时 | 每次生成时 | 每次上线前 |
| **自动可回归** | 完全自动化 | 半自动（需人工复核） | 需标注数据 |
| **代表工具** | `d_ext_embedding.py`, `d_ext_retrieval_metrics.py` | `d_ext_hallucination.py` | `test_rag_e2e.py` |
| **发现的问题** | Chunk 切错, Embedding 不好, 检索漏了 | 模型编造, 忽略资料, 模糊回答 | 流程断裂, 降级失效 |

---

## 三、典型故障模式与测试策略

| 故障模式 | 现象 | 影响 | 优先级 | 测试用例 |
|---------|------|------|--------|---------|
| 检索不相关 | 答非所问 | 用户困惑 | P0 | check_semantic_pair("天气","修车") |
| 检索遗漏 | 答案不完整 | 信息缺失 | P0 | Recall@K < 0.6 |
| 排序不对 | 正确答案排后面 | 用户找不到 | P1 | NDCG@K < 0.7 |
| 幻觉编造 | 回答和资料矛盾 | 信任危机 | P0 | HallucinationRate > 0.3 |
| 检索超时 | 用户等待 > 3s | 体验差 | P1 | 95分位延迟 |
| 空结果无降级 | 直接报错 | 系统崩溃 | P0 | 降级触发器 |
| 多轮遗忘 | 前文信息丢了 | 对话断裂 | P1 | ConsistencyRate < 0.5 |
| 注入超长 | 超出窗口 | 报错/截断 | P1 | Token 计数检查 |

---

## 四、实现的功能模块清单

### 模块 (ext/)

| 模块 | 文件 | 核心功能 |
|------|------|---------|
| Embedding Tester | `d_ext_embedding.py` | 余弦相似度, 语义等级, 批量矩阵, 语义对验证 |
| Retrieval Metrics | `d_ext_retrieval_metrics.py` | Precision@K, Recall@K, MRR, NDCG@K, 批量分析 |
| Hallucination Detector | `d_ext_hallucination.py` | 事实核对, 置信度评分, 一致性检查, 综合评估 |

### 测试 (tests/)

| 测试文件 | 测试数 | 覆盖 |
|---------|-------|------|
| `test_ext_embedding.py` | 34 | 余弦相似度, EmbeddingTester, 语义对, 矩阵 |
| `test_ext_retrieval_metrics.py` | 52 | 四大指标, DCG/IDCG, 批量分析, 样本数据集 |
| `test_rag_e2e.py` | 20 | 有答案/无答案/矛盾/空检索/检索质量/多轮一致性 |

---

## 五、面试话术（完整版）

> 面试官："你做过 RAG 测试吗？怎么做的？"

回答结构（Step by Step）：

**第一步：分层测试策略**
"RAG 测试我分三层：检索层、生成层和端到端。检索层用 Precision@K 和 Recall@K 评估召回质量，NDCG 看排序是否合理，MRR 看第一个正确答案的位置。生成层用事实核对检测幻觉，具体做法是从回答中提取实体和数值断言，与知识库对照，计算 Hit Rate 和 Hallucination Rate。端到端覆盖四个核心场景：有答案、无答案、有矛盾、检索为空。"

**第二步：工具链**
"我实现了三个工具模块：Embedding Tester 做语义相似度验证，Retrieval Metrics 做检索指标计算，Hallucination Detector 做幻觉检测。三个工具组合使用，可以覆盖 RAG 的全链路测试。"

**第三步：关键发现**
"实际跑下来发现几个规律：首先是 Precision 和 Recall 的 trade-off——提高 K 值 Recall 上升但 Precision 下降，取 K=3 或 K=5 比较平衡。其次是幻觉率高的回答通常有较多的模糊词（'可能''也许'）和较少的实体数据，可以用置信度评分作为快速筛选。第三是多轮对话中的实体不一致性是很灵敏的幻觉指标——如果同一问题问两次得到不同实体，大概率有幻觉。"

---

## 六、补充第 2 周预告

完成 RAG 测试体系后，下一步是 **Agent / Tool Calling 测试**，包括：
- Tool Calling 原理与三次调用流程
- Mock Tool Calling 测试框架
- 工具选择测试（是否选对了工具）
- 参数提取测试（参数是否提取正确）
- Agent E2E 测试（完整 ReAct 流程）

---

## 七、自检清单

- [ ] 能画出 RAG 三层测试架构图
- [ ] 能说出 Precision@K vs Recall@K 的 trade-off
- [ ] 能解释 NDCG 在什么场景下比 MRR 更适用
- [ ] 能复述事实核对检测幻觉的具体步骤
- [ ] 能列出至少 5 种 RAG 故障模式及其测试策略
- [ ] 能流利回答"你做过 RAG 测试吗？"面试问题

---

## 产出物

| 文件 | 说明 | 状态 |
|------|------|------|
| `ext/d_ext_embedding.py` | Embedding + 余弦相似度 | ✅ |
| `ext/d_ext_retrieval_metrics.py` | 检索质量四大指标 | ✅ |
| `ext/d_ext_hallucination.py` | 幻觉检测 + 置信度 + 一致性 | ✅ |
| `tests/test_ext_embedding.py` | Embedding 测试 34 个 | ✅ |
| `tests/test_ext_retrieval_metrics.py` | 检索指标测试 52 个 | ✅ |
| `tests/test_rag_e2e.py` | RAG 端到端测试 20 个 | ✅ |
| `docs/ext/e1_rag_principles.md` | RAG 原理 | ✅ |
| `docs/ext/e2_embedding_similarity.md` | Embedding + 相似度 | ✅ |
| `docs/ext/e3_retrieval_metrics.md` | 检索质量指标 | ✅ |
| `docs/ext/e6_rag_summary.md` | 本文档 | ✅ |
