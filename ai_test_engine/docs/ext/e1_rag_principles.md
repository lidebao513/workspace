# 补充 Day 1 — RAG 原理与架构理解

## 学习目标

1. 理解 RAG 的核心概念和工作原理
2. 掌握 RAG 四大步骤（Embedding、Retrieval、Augment、Generate）
3. 理解三个关键决策点（Chunk 策略、检索方式、重排序）
4. 掌握 RAG 的典型故障模式和测试方法

> 目标：掌握 RAG 系统的工作原理、关键组件和典型故障模式，为后续测试打下理论基础。

---

## 一、什么是 RAG？

RAG（Retrieval-Augmented Generation，检索增强生成）是一种通过 **外部知识库检索** 来增强大模型回答质量的技术架构。

### 核心问题

大模型的训练数据有截止日期（例如 DeepSeek 的训练数据截至 2025 年 5 月）。对于这之后发生的事情、公司内部文档、或者专业知识库里的内容，模型不知道。

RAG 的解决思路：**不指望模型记住所有知识，而是在模型回答时，先从外部知识库里找出相关片段，作为"参考材料"一起发给模型。**

### 类比：开卷考试

| 传统 LLM（闭卷） | RAG（开卷） |
|---|---|
| 模型全靠训练时记住的知识 | 模型收到问题后先去查资料 |
| 知识过时了也没办法 | 知识库更新 = 回答同步更新 |
| 不知道的事就硬编（幻觉） | 查不到就坦白说不知道 |
| 公司内部数据没法融入训练 | 内部文档直接当知识库用 |

---

## 二、RAG 四大步骤

```
  用户提问
     │
     ▼
  ┌──────────────┐
  │ ① Query      │  用户输入 -> 向量化
  │    Embedding  │  用 Embedding 模型把文本转成向量
  └──────┬───────┘
         │ 768/1024/1536 维向量
         ▼
  ┌──────────────┐
  │ ② 检索      │  向量库中搜索最相似的 Top-K 片段
  │    Retrieval │  可选：关键词检索 / 混合检索
  └──────┬───────┘
         │ 相关文档片段
         ▼
  ┌──────────────┐
  │ ③ 注入      │  把检索结果拼到 Prompt 的上下文里
  │    Augment   │  "参考以下资料：\n{chunk1}\n{chunk2}"
  └──────┬───────┘
         │ 增强后的 Prompt
         ▼
  ┌──────────────┐
  │ ④ 生成      │  大模型基于"资料+问题"生成回答
  │    Generate  │  输出最终答案
  └──────────────┘
```

### 步骤详解

#### ① Query Embedding

```python
# 用户提问
query = "2026年4月的AI测试岗位有哪些技能要求？"

# 调用 Embedding 模型转成向量
# openai.embeddings.create(input=query, model="text-embedding-3-small")
# 返回一个 1536 维的浮点数向量：[0.023, -0.015, 0.087, ...]
```

Embedding 模型的作用：把"语义"变成"坐标"。语义相近的句子，在向量空间中距离近。

#### ② 检索（Retrieval）

三种检索方式：

| 方式 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| 向量检索 | 计算查询向量 vs 文档向量的余弦相似度 | 语义匹配好 | 对精确关键词匹配弱 |
| 关键词检索 | BM25 / TF-IDF 精确匹配 | 精确关键词好用 | 语义理解差 |
| 混合检索 | 两者结合，加权排序 | 综合最优 | 调参复杂 |

核心指标：Top-K 召回率 —— 前 K 个结果里包含了多少个真正相关的片段。

#### ③ 注入（Augment）

```python
# 检索结果
retrieved_chunks = [
    "AI测试工程师需要掌握Python、pytest、API测试...",
    "DeepSeek API 提供 chat/completions 接口..."
]

# 注入到 Prompt
augmented_prompt = f"""
请基于以下参考资料回答问题：

参考资料：
{chr(10).join(f'- {c}' for c in retrieved_chunks)}

问题：2026年4月的AI测试岗位有哪些技能要求？
"""
```

注意：注入的内容不能超过模型的上下文窗口（context window）。

#### ④ 生成（Generate）

大模型接收增强后的 Prompt，生成最终回复。这一步和普通 LLM 调用没有区别，区别在于 Prompt 里多了检索回来的资料。

---

## 三、三个关键决策点

### 3.1 Chunk 策略

知识库文档需要切成片段再存入向量库。切法直接影响检索质量。

| 策略 | 做法 | 适合场景 | 风险 |
|------|------|----------|------|
| 固定大小 | 按 Token 数切割（如每段 256 token） | 通用 | 截断语义 |
| 语义切分 | 按自然段落/句子切分 | 文章型文档 | 长度不均匀 |
| 递归切分 | 从大到小递归，直到不超过最大长度 | 混合长度文档 | 实现复杂 |

推荐：语义切分 + 固定大小兜底。

### 3.2 检索方式

参见上表。混合检索通常是工业界的最佳实践。

### 3.3 重排序（Re-ranking）

检索出来的 Top-K 结果，用更精细的模型重新排序，把真正相关的排前面。

重排序和 Embedding 的区别：
- Embedding：一次算好存下来，速度快
- Re-ranking：查询时实时算，精度高但慢

---

## 四、典型故障模式（测试重点）

### 4.1 故障一览表

| 故障 | 表现 | 根因 | 测试方法 |
|------|------|------|----------|
| 检索不相关 | 回答引用的资料和问题无关 | Chunk 切错/Embedding 不好 | 检验检索结果的 Precision@K |
| 遗漏关键信息 | 回答不完整，漏了重要内容 | Top-K 不够/检索算法漏了 | 检验 Recall@K |
| 检索超时 | 查询耗时 > 5 秒 | 向量库规模大/索引失效 | 压测检索延迟 |
| 注入超长 | 超出上下文窗口报错 | 检索结果太多 | 检查注入 Token 数 |
| 模型忽略资料 | 答案和检索资料矛盾 | Prompt 设计不好 | E2E 一致性检查 |
| 降级失效 | 检索失败直接报错 | 没有做降级兜底 | Mock 检索失败测试 |

### 4.2 测试的三层验证

RAG 测试必须分层验证，不能只测端到端：

```
RAG 测试 → 三个层次
├── 检索层（Retrieval）
│   ├── 精确率 Precision@K — 检索结果里多少是相关的
│   ├── 召回率 Recall@K — 所有相关文档有多少被找到了
│   ├── MRR — 第一个正确答案排第几
│   ├── NDCG@K — 排名加权的累积增益
│   └── 检索延迟 — 95 分位耗时
│
├── 生成层（Generation）
│   ├── 幻觉率 — 回答与资料的矛盾比例
│   ├── 忠实度 — 回答是否严格基于资料
│   ├── 完整性 — 是否覆盖了资料中的关键信息
│   └── 降级测试 — 检索失败/空结果时的行为
│
└── 端到端层（E2E）
    ├── 答案准确率 — 与标注答案的匹配度
    ├── 用户满意度 — A/B 测试/评分
    ├── 鲁棒性 — 输入干扰/同义改写后的稳定性
    └── 回归 — 知识库更新后是否退化
```

### 4.3 面试话术

> "RAG 测试的关键是多层验证——检索层测召回率，生成层测幻觉率，端到端测用户满意度。三个层次任何一个出问题，用户得到的回答都不对。我在实际项目中会先构建标注数据集，然后用 Precision@K、Recall@K、MRR、NDCG 四个指标评估检索质量，再通过事实核对和重复查询来检测幻觉率，最后用 E2E 场景覆盖关键业务路径。"

---

## 五、RAG vs 传统 LLM 测试对比

| 维度 | 普通 LLM 测试 | RAG 测试 |
|------|-------------|----------|
| 测试目标 | 模型本身的回复质量 | 检索 + 生成的整体质量 |
| 数据准备 | 通用测试集 | 需要标注的检索数据集 |
| 关键指标 | 评分/一致性/安全 | Precision@K + 幻觉率 |
| 知识时效 | 训练数据截止 | 取决于知识库 |
| 故障模式 | 模型编造 | 检索不准 → 答案偏移 |
| 回归测试 | 模型版本更新 | 知识库更新 + 模型更新 |

---

## 六、面试题

**Q: RAG 相比传统 LLM 有什么优势？**
A: RAG 的核心优势在于知识的时效性和可更新性。传统 LLM 的知识截止于训练数据，而 RAG 通过检索外部知识库获取最新信息。此外，RAG 可以使用内部文档作为知识库，避免敏感数据泄露；当模型产生幻觉时，可以追溯到具体的参考资料；知识库更新后，回答会自动同步更新，无需重新训练模型。

**Q: 如何设计 RAG 的测试策略？**
A: RAG 测试需要分层验证：检索层测 Precision@K、Recall@K、MRR、NDCG 等指标；生成层测幻觉率、忠实度、完整性；端到端测答案准确率、用户满意度和降级处理。这三个层次任何一个出问题，最终回答都会有问题。

**Q: Chunk 切分策略对 RAG 效果有什么影响？**
A: Chunk 切分直接影响检索质量。固定大小切分简单但可能截断语义；语义切分能保持段落完整性但长度不均匀；递归切分适合混合长度文档但实现复杂。通常推荐语义切分加固定大小兜底的策略。

**Q: 混合检索为什么是工业界的最佳实践？**
A: 混合检索结合了向量检索和关键词检索的优点。向量检索擅长语义匹配，关键词检索擅长精确匹配。两者加权排序后，既能理解用户意图，又能准确匹配关键信息，是综合效果最优的方案。

## 七、代码示例

### RAG 流程简化实现

```python
from typing import List, Dict
import numpy as np

class SimpleRAG:
    """简化版 RAG 系统"""
    
    def __init__(self):
        self.document_chunks = []  # 存储文档片段
        self.chunk_vectors = []    # 存储对应的向量
    
    def add_document(self, text: str, chunk_size: int = 256):
        """添加文档并切分成片段"""
        tokens = text.split()
        for i in range(0, len(tokens), chunk_size):
            chunk = " ".join(tokens[i:i+chunk_size])
            self.document_chunks.append(chunk)
            # 模拟向量化（实际中调用 Embedding API）
            self.chunk_vectors.append(self._mock_embed(chunk))
    
    def _mock_embed(self, text: str) -> List[float]:
        """模拟 Embedding 向量化"""
        # 简单哈希生成固定长度向量
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [(hash_val >> (i * 8)) % 256 / 256 for i in range(32)]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        return dot / (norm1 * norm2) if norm1 and norm2 else 0.0
    
    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        """检索相关文档片段"""
        query_vec = self._mock_embed(query)
        
        # 计算相似度并排序
        similarities = [
            (i, self._cosine_similarity(query_vec, vec))
            for i, vec in enumerate(self.chunk_vectors)
        ]
        
        # 按相似度降序排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # 返回 Top-K 结果
        return [self.document_chunks[i] for i, _ in similarities[:top_k]]
    
    def generate(self, query: str, top_k: int = 3) -> str:
        """生成增强后的回答"""
        chunks = self.retrieve(query, top_k)
        
        if not chunks:
            return "抱歉，我没有找到相关资料来回答这个问题。"
        
        # 构建增强 Prompt
        context = "\n".join(f"- {chunk}" for chunk in chunks)
        augmented_prompt = f"""请基于以下参考资料回答问题：
        
参考资料：
{context}

问题：{query}
"""
        
        # 模拟生成回答（实际中调用 LLM）
        return f"根据参考资料，关于 '{query}' 的回答如下：\n\n资料显示：{chunks[0][:100]}..."

# 使用示例
if __name__ == "__main__":
    rag = SimpleRAG()
    
    # 添加知识库文档
    rag.add_document("""AI测试工程师需要掌握Python、pytest、API测试等技能。
    还需要了解LLM的基本原理，以及如何评估模型输出质量。
    熟悉CI/CD流程和性能测试也是加分项。""")
    
    # 查询
    query = "AI测试岗位需要什么技能？"
    result = rag.generate(query)
    print(result)
```

## 八、练习题

1. **基础题：** 为 `SimpleRAG` 类添加一个方法，计算检索结果的 Precision@K（假设已知哪些文档是相关的）。

2. **进阶题：** 实现一个函数，比较不同 Chunk 大小（如 128、256、512）对检索结果的影响。

3. **挑战题：** 设计一个完整的 RAG 测试用例，覆盖检索不相关、遗漏关键信息、检索超时三种故障模式。

## 九、自检清单

- [ ] 能口述 RAG 四个步骤及每个步骤的作用
- [ ] 理解 Embedding 向量与余弦相似度的关系
- [ ] 能区分三种 Chunk 策略和各自的适用场景
- [ ] 能说出三种检索方式的优缺点
- [ ] 能列出至少 4 种 RAG 故障模式
- [ ] 能解释 RAG 测试为什么需要三层验证
- [ ] 准备好面试话术（可以分段讲，不用全背）

---

## 产出物

- [x] 本文档：RAG 原理学习材料
- [ ] （下一步）Day 2: Embedding 调用与余弦相似度代码
