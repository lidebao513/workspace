# 补充 Day 6 — RAG 测试体系总结

## 学习目标

1. 理解 RAG 测试的三层验证架构（检索层、生成层、端到端）
2. 掌握各层的核心测试指标和方法
3. 熟悉 RAG 的典型故障模式和测试策略
4. 能设计完整的 RAG 测试方案

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

## 七、面试题

**Q: RAG 测试为什么需要三层验证？**
A: RAG 系统的质量取决于检索和生成两个环节，任何一个环节出问题都会导致最终回答质量下降。检索层测召回质量，生成层测幻觉率，端到端测整体效果。三层验证可以定位问题出在哪个环节，便于针对性优化。

**Q: 如何检测 RAG 系统中的幻觉？**
A: 检测幻觉主要通过事实核对：从回答中提取实体和数值断言，与知识库对照，计算 Hit Rate 和 Hallucination Rate。此外，还可以通过检查回答中的模糊词比例、多轮对话中的实体一致性来辅助检测。

**Q: 什么是降级测试？为什么重要？**
A: 降级测试验证系统在异常情况下的行为，比如检索失败、空结果、超时等。RAG 系统必须有降级兜底机制，否则会直接报错影响用户体验。降级测试确保系统在异常情况下仍能优雅处理。

**Q: 如何设计 RAG 系统的回归测试？**
A: 构建标注测试集，覆盖核心场景（有答案、无答案、有矛盾、检索为空）。每次知识库更新或模型更新后，自动运行回归测试，监控各项指标是否退化。重点关注 Precision@K、Recall@K、幻觉率等关键指标。

## 八、代码示例

### RAG 全链路测试框架

```python
from typing import List, Dict, Tuple
from enum import Enum

class TestResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"

class RAGTestFramework:
    """RAG 全链路测试框架"""
    
    def __init__(self, retrieval_metrics, embedding_tester, hallucination_detector):
        self.retrieval_metrics = retrieval_metrics
        self.embedding_tester = embedding_tester
        self.hallucination_detector = hallucination_detector
    
    def test_retrieval_layer(self, queries: List[Dict], k: int = 3) -> Dict:
        """测试检索层"""
        results = self.retrieval_metrics.analyze_queries(queries, k)
        
        # 检查指标是否达标
        checks = {
            'precision_ok': results['precision_at_k'] >= 0.7,
            'recall_ok': results['recall_at_k'] >= 0.6,
            'ndcg_ok': results['ndcg_at_k'] >= 0.7
        }
        
        return {
            'metrics': results,
            'checks': checks,
            'passed': all(checks.values())
        }
    
    def test_generation_layer(self, qa_pairs: List[Tuple[str, str, str]]) -> Dict:
        """测试生成层"""
        total = len(qa_pairs)
        passed = 0
        hallucinations = 0
        
        for query, context, answer in qa_pairs:
            # 事实核对
            result = self.hallucination_detector.check_facts(answer, context)
            
            if result['hallucination_rate'] < 0.3:
                passed += 1
            else:
                hallucinations += 1
        
        return {
            'total': total,
            'passed': passed,
            'hallucinations': hallucinations,
            'hallucination_rate': hallucinations / total,
            'accuracy': passed / total
        }
    
    def test_e2e_scenario(self, scenario: Dict) -> Dict:
        """测试端到端场景"""
        scenario_name = scenario['name']
        test_cases = scenario['test_cases']
        results = []
        
        for case in test_cases:
            result = {
                'case': case['description'],
                'expected': case['expected'],
                'actual': None,
                'passed': False
            }
            
            try:
                # 模拟 RAG 流程
                query = case['query']
                context = case.get('context', "")
                
                # 评估回答质量
                if case['expected'] == 'has_answer':
                    result['passed'] = len(context) > 0
                elif case['expected'] == 'no_answer':
                    result['passed'] = len(context) == 0
                elif case['expected'] == 'no_hallucination':
                    result['passed'] = True  # 简化处理
                
                result['actual'] = "success" if result['passed'] else "failed"
            except Exception as e:
                result['actual'] = str(e)
            
            results.append(result)
        
        passed_count = sum(1 for r in results if r['passed'])
        
        return {
            'scenario': scenario_name,
            'total': len(results),
            'passed': passed_count,
            'failed': len(results) - passed_count,
            'details': results
        }
    
    def run_full_suite(self, retrieval_queries, generation_pairs, e2e_scenarios) -> Dict:
        """运行完整测试套件"""
        print("=== 开始 RAG 全链路测试 ===")
        
        # 检索层测试
        print("\n1. 检索层测试")
        retrieval_result = self.test_retrieval_layer(retrieval_queries)
        print(f"   Precision@3: {retrieval_result['metrics']['precision_at_k']:.4f}")
        print(f"   Recall@3: {retrieval_result['metrics']['recall_at_k']:.4f}")
        print(f"   NDCG@3: {retrieval_result['metrics']['ndcg_at_k']:.4f}")
        print(f"   检查结果: {'通过' if retrieval_result['passed'] else '未通过'}")
        
        # 生成层测试
        print("\n2. 生成层测试")
        generation_result = self.test_generation_layer(generation_pairs)
        print(f"   准确率: {generation_result['accuracy']:.4f}")
        print(f"   幻觉率: {generation_result['hallucination_rate']:.4f}")
        
        # 端到端测试
        print("\n3. 端到端测试")
        e2e_results = []
        for scenario in e2e_scenarios:
            result = self.test_e2e_scenario(scenario)
            e2e_results.append(result)
            print(f"   {scenario['name']}: {result['passed']}/{result['total']} 通过")
        
        # 汇总报告
        overall_passed = retrieval_result['passed'] and generation_result['accuracy'] >= 0.8
        print(f"\n=== 测试完成 ===")
        print(f"整体结果: {'通过' if overall_passed else '未通过'}")
        
        return {
            'retrieval': retrieval_result,
            'generation': generation_result,
            'e2e': e2e_results,
            'overall_passed': overall_passed
        }

# 简化的幻觉检测器（用于示例）
class MockHallucinationDetector:
    def check_facts(self, answer: str, context: str) -> Dict:
        # 简化实现：检查回答是否包含上下文中的关键词
        context_keywords = set(context.lower().split()[:10])
        answer_keywords = set(answer.lower().split())
        
        overlap = len(context_keywords & answer_keywords)
        hallucination_rate = 0.0 if overlap > 0 else 0.5
        
        return {
            'hallucination_rate': hallucination_rate,
            'hit_rate': overlap / len(context_keywords) if context_keywords else 1.0
        }

# 使用示例
if __name__ == "__main__":
    from e3_retrieval_metrics import RetrievalMetrics
    
    # 初始化测试框架
    rag_tester = RAGTestFramework(
        retrieval_metrics=RetrievalMetrics(),
        embedding_tester=None,  # 可传入实际的 EmbeddingTester
        hallucination_detector=MockHallucinationDetector()
    )
    
    # 测试数据
    retrieval_queries = RetrievalMetrics.get_sample_queries()
    
    generation_pairs = [
        ("AI测试需要哪些技能", "AI测试工程师需要掌握Python、pytest、API测试", 
         "AI测试工程师需要掌握Python、pytest和API测试技能"),
        ("什么是RAG", "RAG是检索增强生成", "RAG是一种通过检索外部知识库来增强大模型回答的技术")
    ]
    
    e2e_scenarios = [
        {
            'name': '有答案场景',
            'test_cases': [
                {'description': '正常查询', 'query': 'AI测试技能', 'context': 'Python测试', 'expected': 'has_answer'}
            ]
        },
        {
            'name': '无答案场景',
            'test_cases': [
                {'description': '知识库无相关内容', 'query': '未知问题', 'context': '', 'expected': 'no_answer'}
            ]
        }
    ]
    
    # 运行测试
    report = rag_tester.run_full_suite(retrieval_queries, generation_pairs, e2e_scenarios)
```

## 九、练习题

1. **基础题：** 扩展 `MockHallucinationDetector`，添加更多事实核对逻辑。

2. **进阶题：** 设计一个完整的 RAG 端到端测试场景，覆盖所有典型故障模式。

3. **挑战题：** 实现一个测试报告生成器，将测试结果输出为 Markdown 格式的报告。

## 十、自检清单

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
