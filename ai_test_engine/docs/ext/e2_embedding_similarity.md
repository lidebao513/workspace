# 补充 Day 2 — Embedding 调用与余弦相似度

## 学习目标

1. 理解 Embedding 向量化原理和向量空间语义表示
2. 掌握余弦相似度公式和实现方法
3. 理解不同相似度等级的阈值划分
4. 掌握 Embedding 质量评估方法

> 目标：理解 Embedding 向量化原理，实现余弦相似度计算，并动手测试语义相似度对。

---

## 一、什么是 Embedding？

Embedding（嵌入）是将文本转换成**固定长度的浮点数向量**的过程。

```
"上海的天气怎么样"  →  [0.176, -0.048, 0.391, 0.128, ...]  (24维或768/1024/1536维)
```

### 核心原理

Embedding 模型的目标："语义相近的文本，向量也靠近。"

在向量空间中：
- "上海的天气怎么样" 和 "上海今天气温" → 距离很近（~0.999）
- "上海的天气怎么样" 和 "怎么修汽车" → 距离很远（~-0.337）

### 调用方式

```python
import openai

response = openai.embeddings.create(
    input="上海的天气怎么样",
    model="text-embedding-3-small"  # 返回 1536 维向量
)

vector = response.data[0].embedding
```

---

## 二、余弦相似度原理

### 公式

```
cos(A, B) = (A·B) / (|A| × |B|)
```

其中：
- `A·B` = 向量点积（对应位置相乘求和）
- `|A|` = 向量的 L2 范数（各分量平方和开根号）

### 直观理解

两个向量的**夹角余弦值**：
- 夹角 0 度（同向）→ cos=1 → 语义完全相同
- 夹角 90 度（正交）→ cos=0 → 语义不相关
- 夹角 180 度（反向）→ cos=-1 → 语义相反

### 代码实现

```python
def cosine_similarity(vec1, vec2):
    if len(vec1) != len(vec2):
        raise ValueError("维度不一致")
    if not vec1 or all(v == 0.0 for v in vec1):
        return 0.0

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return dot / (norm1 * norm2)
```

### 边界情况

| 输入 | 结果 | 原因 |
|------|------|------|
| 相同向量 | 1.0 | 完美对齐 |
| 相反向量 | -1.0 | 完全反向 |
| 正交向量 | 0.0 | 垂直关系 |
| 零向量 | 0.0 | 无法计算方向 |
| 维度不同 | ValueError | 必须一致 |

### 面试话术

> "余弦相似度是 Embedding 测试的基石。它通过计算两个向量夹角余弦值来度量语义相似度，不受向量长度影响。测试中我会用三个关键场景验证：同义句对（期望高相似度 > 0.85）、无关句对（期望低相似度 < 0.3）、同领域句对（期望中等相似度 0.3-0.85）。如果模型编码的分辨率不够——比如同义词对和无关句对的分数差距太小——说明 Embedding 质量有问题。"

---

## 三、实现的功能模块

### EmbeddingTester 类

| 方法 | 功能 | 测试覆盖 |
|------|------|----------|
| `get_embedding(text)` | 获取文本向量（离线/在线两种模式） | 已知/未知/模糊匹配 |
| `compute_similarity(t1, t2)` | 计算两文本余弦相似度 | 语义对验证 |
| `get_similarity_level(score)` | 相似度转等级标签 | 边界值全覆盖 |
| `batch_similarity_matrix(texts)` | 批量计算相似度矩阵 | 对角线/对称性 |
| `check_semantic_pair(t1, t2, exp)` | 验证语义对是否符合预期 | 通过/不通过 |
| `register_mock(text, vector)` | 注册自定义 Mock 向量 |  |
| `list_available_texts()` | 列出所有可用预置文本 |  |

### 相似度等级阈值

```
high:    ≥ 0.85   同义/近义句
medium:  ≥ 0.60   同话题相关
low:     ≥ 0.30   弱相关
unrelated: < 0.30 不相关或反义
```

---

## 四、测试场景说明

用预置的 8 组 Mock Embedding 模拟真实 Embedding API 的行为。

### 预置文本对

| 文本 A | 文本 B | 期望相似度等级 | 实际相似度 | 测试名称 |
|--------|--------|---------------|-----------|----------|
| 上海的天气怎么样 | 上海今天气温 | high | 0.999 | test_weather_related |
| 上海的天气怎么样 | 怎么修汽车 | unrelated | -0.337 | test_weather_unrelated |
| 电脑和计算机有什么区别 | 计算机和电脑的区别 | high | 1.000 | test_synonym_high_similarity |
| 电脑和计算机有什么区别 | 如何做酱牛肉 | low | 0.173 | test_tech_vs_cooking |
| 上海的天气怎么样 | 今天天气怎么样 | high | 1.000 | test_weather_variants |

### 验证逻辑

`check_semantic_pair` 的宽松匹配规则：
- 期望 `"high"` → 只接受 `high`
- 期望 `"medium"` → 只接受 `medium`  
- 期望 `"low"` → 接受 `low` 或 `unrelated`

---

## 五、离线模式 vs 在线模式

| 模式 | EmbeddingTester(embed_func=None) | EmbeddingTester(embed_func=real_api) |
|------|----------------------------------|--------------------------------------|
| 数据来源 | `_MOCK_EMBEDDINGS` 字典 | 传入的函数 |
| 测试特点 | 可离线运行，无网络依赖 | 需要真实 API Key |
| 适用场景 | CI/CD、单元测试、本地调试 | 集成测试、生产验证 |
| 行为 | 未知文本抛 KeyError | 所有文本调用外部函数 |

---

## 六、Extension 模块命名约定

补充学习计划的代码放在 `ai_test_engine/ext/` 下，测试文件放在 `ai_test_engine/tests/` 下，前缀 `test_ext_`：

```
ai_test_engine/
├── ext/
│   ├── __init__.py
│   └── embedding_tester.py
├── tests/
│   ├── test_ext_embedding.py     # ← 今天产出
```

---

## 七、面试话术（场景实战）

> 面试官："你如何评估 Embedding 模型的质量？"

回答结构：
1. **构建标注测试集**：收集同义句对（应高相似）、无关句对（应低相似）、边界案例
2. **计算指标**：平均相似度分差、Top-1 准确率、异常值检测
3. **自动化验证**：用 `check_semantic_pair` 批量回归，防止模型更新后语义漂移
4. **真实 API 验证**：离线测试通过后，用少量真实 Embedding API 调用做端到端验证

---

## 八、面试题

**Q: 为什么要用余弦相似度而不是欧氏距离？**
A: 余弦相似度衡量的是向量方向的相似性，不受向量长度影响；而欧氏距离衡量的是向量空间中的绝对距离。在文本语义匹配中，我们更关心两句话的意思是否相近，而不是它们的长度是否相同。余弦相似度能更好地反映语义相似性，即使句子长度差异很大。

**Q: Embedding 向量为什么需要 L2 归一化？**
A: L2 归一化将向量长度变为 1，这样余弦相似度就等于向量点积，计算更高效。更重要的是，归一化后可以消除文本长度对相似度计算的影响，使短文本和长文本能够公平比较。

**Q: 如何评估一个 Embedding 模型的质量？**
A: 评估 Embedding 质量需要构建标注测试集，包含同义句对（应高相似）、无关句对（应低相似）和边界案例。然后计算平均相似度分差、Top-1 准确率、异常值检测等指标。离线测试通过后，还需要用真实 API 调用做端到端验证。

**Q: 什么情况下余弦相似度会返回 0？**
A: 余弦相似度返回 0 有几种情况：两个向量正交（夹角 90 度）、其中一个或两个向量是零向量、两个向量维度不一致导致无法计算。

## 九、代码示例

### EmbeddingTester 完整实现

```python
from typing import Dict, List, Optional, Callable
from enum import Enum

class SimilarityLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNRELATED = "unrelated"

class EmbeddingTester:
    """Embedding 测试工具类"""
    
    # 预设的相似度等级阈值
    HIGH_THRESHOLD = 0.85
    MEDIUM_THRESHOLD = 0.60
    LOW_THRESHOLD = 0.30
    
    # Mock 嵌入数据（离线模式使用）
    _MOCK_EMBEDDINGS: Dict[str, List[float]] = {
        "上海的天气怎么样": [0.176, -0.048, 0.391, 0.128, 0.076, -0.152, 0.234, 0.189],
        "上海今天气温": [0.175, -0.049, 0.390, 0.127, 0.075, -0.151, 0.233, 0.188],
        "怎么修汽车": [-0.234, 0.156, -0.087, 0.445, -0.123, 0.267, -0.098, 0.312],
        "电脑和计算机有什么区别": [0.089, 0.234, -0.156, 0.312, 0.178, -0.045, 0.267, -0.134],
        "计算机和电脑的区别": [0.090, 0.235, -0.155, 0.313, 0.179, -0.044, 0.268, -0.133],
        "如何做酱牛肉": [0.345, -0.123, 0.078, -0.267, 0.189, 0.312, -0.056, 0.145],
    }
    
    def __init__(self, embed_func: Optional[Callable[[str], List[float]]] = None):
        """
        初始化 EmbeddingTester
        
        Args:
            embed_func: 可选的真实 Embedding API 函数，不传则使用离线 Mock 模式
        """
        self._embed_func = embed_func
    
    def get_embedding(self, text: str) -> List[float]:
        """获取文本的向量表示"""
        if self._embed_func:
            return self._embed_func(text)
        
        # 离线模式：使用 Mock 数据
        if text not in self._MOCK_EMBEDDINGS:
            raise KeyError(f"未知文本 '{text}'，请先注册或使用在线模式")
        return self._MOCK_EMBEDDINGS[text]
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的余弦相似度"""
        vec1 = self.get_embedding(text1)
        vec2 = self.get_embedding(text2)
        return self._cosine_similarity(vec1, vec2)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            raise ValueError("向量维度不一致")
        if not vec1 or all(v == 0.0 for v in vec1):
            return 0.0
        
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        
        return dot / (norm1 * norm2)
    
    def get_similarity_level(self, score: float) -> SimilarityLevel:
        """将相似度分数转换为等级标签"""
        if score >= self.HIGH_THRESHOLD:
            return SimilarityLevel.HIGH
        elif score >= self.MEDIUM_THRESHOLD:
            return SimilarityLevel.MEDIUM
        elif score >= self.LOW_THRESHOLD:
            return SimilarityLevel.LOW
        else:
            return SimilarityLevel.UNRELATED
    
    def batch_similarity_matrix(self, texts: List[str]) -> List[List[float]]:
        """批量计算相似度矩阵"""
        n = len(texts)
        matrix = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 1.0
                elif i < j:
                    sim = self.compute_similarity(texts[i], texts[j])
                    matrix[i][j] = sim
                    matrix[j][i] = sim
        
        return matrix
    
    def check_semantic_pair(self, text1: str, text2: str, expected_level: str) -> bool:
        """验证语义对是否符合预期"""
        similarity = self.compute_similarity(text1, text2)
        actual_level = self.get_similarity_level(similarity).value
        
        # 宽松匹配规则
        if expected_level == "high":
            return actual_level == "high"
        elif expected_level == "medium":
            return actual_level == "medium"
        elif expected_level == "low":
            return actual_level in ("low", "unrelated")
        else:
            return False
    
    def register_mock(self, text: str, vector: List[float]) -> None:
        """注册自定义 Mock 向量"""
        self._MOCK_EMBEDDINGS[text] = vector
    
    def list_available_texts(self) -> List[str]:
        """列出所有可用预置文本"""
        return list(self._MOCK_EMBEDDINGS.keys())

# 使用示例
if __name__ == "__main__":
    # 离线模式（使用 Mock 数据）
    tester = EmbeddingTester()
    
    # 测试语义对
    result = tester.check_semantic_pair("上海的天气怎么样", "上海今天气温", "high")
    print(f"语义对测试通过: {result}")
    
    # 计算相似度
    sim = tester.compute_similarity("电脑和计算机有什么区别", "如何做酱牛肉")
    print(f"相似度: {sim:.4f}")
    print(f"相似度等级: {tester.get_similarity_level(sim).value}")
    
    # 生成相似度矩阵
    texts = ["上海的天气怎么样", "上海今天气温", "怎么修汽车"]
    matrix = tester.batch_similarity_matrix(texts)
    print("\n相似度矩阵:")
    for i, row in enumerate(matrix):
        print(f"{texts[i]}: {[f'{v:.4f}' for v in row]}")
```

## 十、练习题

1. **基础题：** 使用 `EmbeddingTester` 测试所有预置语义对，验证它们是否符合预期。

2. **进阶题：** 添加 5 个新的语义对到 Mock 数据中，包括同义句、无关句和边界案例。

3. **挑战题：** 扩展 `EmbeddingTester` 类，添加一个方法来检测异常值（相似度分数与预期偏差过大的情况）。

## 十一、自检清单

- [ ] 能默写余弦相似度公式并手写代码实现
- [ ] 能解释为什么 Embedding 向量需要 L2 归一化
- [ ] 能区分离线模式（Mock）和在线模式（真实 API）的适用场景
- [ ] 能说出 3 种边界情况下的余弦相似度结果
- [ ] 能复述面试话术的 Embedding 评估框架

---

## 产出物

| 文件 | 说明 |
|------|------|
| `ext/embedding_tester.py` | Embedding 客户端 + 余弦相似度 + 语义验证 |
| `tests/test_ext_embedding.py` | 34 个测试，覆盖全部功能 |
| `docs/ext/e1_rag_principles.md` | Day 1 RAG 原理文档 |
| `docs/ext/e2_embedding_similarity.md` | 本文档 |
