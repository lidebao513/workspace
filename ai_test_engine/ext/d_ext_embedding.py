"""
Embedding Tester — 调用 Embedding 模型生成向量 + 余弦相似度计算

功能：
1. 使用 OpenAI SDK 调用 Embedding API 生成文本向量
2. 计算两个文本向量之间的余弦相似度
3. 批量计算文本间的相似度矩阵
4. 判断语义相似度等级（高/中/低）

用法（离线模式，不需要真实 API）：
    from ext.embedding_tester import EmbeddingTester
    et = EmbeddingTester()
    sim = et.compute_similarity("上海的天气", "上海今天气温")
"""

import math
import json
from typing import List, Optional


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算两个向量的余弦相似度。

    公式: cos(A,B) = (A·B) / (|A| * |B|)

    取值范围: [-1, 1]
    - 1: 完全相同方向
    - 0: 正交（不相关）
    - -1: 完全相反
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"向量维度不一致: {len(vec1)} vs {len(vec2)}")
    if not vec1 or all(v == 0.0 for v in vec1):
        return 0.0

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return dot / (norm1 * norm2)


# 预置的测试用 Embedding（模拟真实向量，已做 L2 归一化）
# 真实场景中通过 openai.embeddings.create() 获取
_MOCK_EMBEDDINGS = {
    "上海的天气怎么样": [0.175962, -0.047862, 0.39134, 0.1281, -0.219601, 0.439201, -0.094316, 0.063346, 0.278724, -0.125285, 0.329401, -0.173147, 0.078831, 0.235085, -0.063346, 0.125285, -0.1098, 0.204116, 0.047862, -0.094316, 0.282947, -0.157662, 0.1098, 0.219601],
    "上海今天气温": [0.18809, -0.040203, 0.409205, 0.124915, -0.213935, 0.442228, -0.087584, 0.055996, 0.274239, -0.117736, 0.327364, -0.167989, 0.08902, 0.245523, -0.055996, 0.119172, -0.103378, 0.199577, 0.040203, -0.087584, 0.279982, -0.152195, 0.103378, 0.213935],
    "怎么修汽车": [-0.148641, 0.39549, -0.059722, 0.221634, 0.103518, -0.118116, 0.310553, -0.07432, 0.192437, 0.41407, -0.103518, 0.059722, -0.120771, 0.045123, 0.368947, -0.163239, 0.088919, -0.207035, 0.262775, 0.118116, -0.045123, 0.165894, -0.266757, 0.07432],
    "电脑和计算机有什么区别": [-0.129316, 0.352321, -0.044865, 0.234881, 0.11744, -0.102925, 0.323291, -0.08841, 0.17682, 0.397186, -0.11744, 0.073895, -0.134595, 0.056741, 0.381351, -0.17682, 0.102925, -0.220366, 0.249396, 0.129316, -0.05938, 0.17682, -0.279746, 0.08841],
    "计算机和电脑的区别": [-0.124387, 0.366401, -0.037857, 0.24607, 0.112219, -0.097346, 0.323136, -0.082474, 0.17306, 0.39885, -0.112219, 0.083826, -0.129795, 0.050025, 0.382625, -0.17306, 0.097346, -0.217677, 0.247422, 0.124387, -0.052729, 0.17306, -0.278519, 0.082474],
    "Python 列表和元组的区别": [0.049371, 0.214686, -0.269531, 0.157446, 0.233014, -0.301253, 0.175388, 0.021119, 0.344466, 0.308442, 0.028695, 0.218988, -0.289082, 0.16292, 0.250077, -0.03979, -0.04639, -0.053816, 0.132175, -0.006404, -0.201293, 0.387434, -0.165269, 0.021848],
    "今天天气怎么样": [0.165171, -0.05459, 0.379333, 0.132977, -0.22536, 0.426925, -0.099382, 0.068588, 0.28275, -0.130177, 0.333141, -0.177769, 0.072787, 0.22816, -0.068588, 0.130177, -0.11478, 0.208563, 0.053191, -0.099382, 0.286949, -0.162371, 0.11478, 0.22536],
    "如何做酱牛肉": [0.25, 0.25, -0.25, -0.25, 0.25, -0.25, 0.25, -0.25, 0.0, 0.0, 0.0, 0.0, 0.25, 0.25, -0.25, -0.25, 0.0, 0.0, 0.0, 0.0, 0.25, 0.25, -0.25, -0.25],
}

# 相似度等级阈值
SIMILARITY_THRESHOLDS = {
    "high": 0.85,     # 高相似度（同义/近义）
    "medium": 0.60,   # 中相似度（相关话题）
    "low": 0.30,      # 低相似度（弱相关）
    # < 0.30 为不相关
}


class EmbeddingTester:
    """Embedding 测试工具。

    可以传入真实 Embedding API 函数（在线模式），
    或使用预置的 Mock 数据（离线模式）。
    """

    def __init__(self, embed_func: Optional[callable] = None):
        """
        Args:
            embed_func: 可选，嵌入函数。接收字符串返回 List[float]。
                        不传则使用预置的 Mock 数据。
        """
        self._embed_func = embed_func
        self._embeddings = dict(_MOCK_EMBEDDINGS) if embed_func is None else {}

    def get_embedding(self, text: str) -> List[float]:
        """获取文本的向量表示。

        在线模式：调用传入的 embed_func
        离线模式：从预置数据中查找；找不到则抛出 KeyError
        """
        if self._embed_func:
            return self._embed_func(text)

        if text in self._embeddings:
            return self._embeddings[text]

        # 尝试模糊匹配（忽略空格、大小写）
        for key in self._embeddings:
            if key.replace(" ", "") == text.replace(" ", "") or key == text:
                return self._embeddings[key]

        raise KeyError(f"未找到 '{text}' 的预置 Embedding。可用文本: {list(self._embeddings.keys())}")

    def compute_similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的余弦相似度。

        Returns:
            余弦相似度值 [-1, 1]
        """
        vec1 = self.get_embedding(text1)
        vec2 = self.get_embedding(text2)
        return cosine_similarity(vec1, vec2)

    def get_similarity_level(self, score: float) -> str:
        """根据相似度得分返回等级。

        Returns:
            "high" | "medium" | "low" | "unrelated"
        """
        if score >= SIMILARITY_THRESHOLDS["high"]:
            return "high"
        elif score >= SIMILARITY_THRESHOLDS["medium"]:
            return "medium"
        elif score >= SIMILARITY_THRESHOLDS["low"]:
            return "low"
        else:
            return "unrelated"

    def batch_similarity_matrix(self, texts: List[str]) -> List[List[float]]:
        """计算文本列表间的相似度矩阵。

        Returns:
            N x N 的相似度矩阵（floats）
        """
        n = len(texts)
        # 先一次性获取所有向量
        embeddings = []
        for t in texts:
            try:
                embeddings.append(self.get_embedding(t))
            except KeyError:
                embeddings.append(None)

        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 1.0
                elif embeddings[i] is not None and embeddings[j] is not None:
                    matrix[i][j] = cosine_similarity(embeddings[i], embeddings[j])
                else:
                    matrix[i][j] = 0.0
        return matrix

    def check_semantic_pair(self, text1: str, text2: str, expected: str) -> dict:
        """验证一组语义对，返回诊断信息。

        Args:
            text1: 第一段文本
            text2: 第二段文本
            expected: 期望的语义关系。
                "high" — 较高相似度（同义/近义），接受 high
                "medium" — 中度相关，接受 medium
                "low" — 低相关或不相关，接受 low 或 unrelated

        Returns:
            {
                "text1": str,
                "text2": str,
                "similarity": float,
                "level": str,
                "expected": str,
                "pass": bool,
                "detail": str
            }
        """
        # 宽松匹配：期望 "low" 时，实际为 "unrelated" 也算通过
        _accepted = {expected}
        if expected == "low":
            _accepted.add("unrelated")
        sim = self.compute_similarity(text1, text2)
        level = self.get_similarity_level(sim)
        passed = level in _accepted

        detail_parts = []
        if passed:
            detail_parts.append(f"通过: 等级 '{level}' 符合预期 '{expected}'")
        else:
            detail_parts.append(f"未通过: 等级 '{level}' 不等于预期 '{expected}'")

        detail_parts.append(f"相似度={sim:.4f}")
        detail_parts.append(f"阈值区间: {SIMILARITY_THRESHOLDS}")

        return {
            "text1": text1,
            "text2": text2,
            "similarity": round(sim, 4),
            "level": level,
            "expected": expected,
            "pass": passed,
            "detail": " | ".join(detail_parts),
        }

    def list_available_texts(self) -> List[str]:
        """列出所有可用的预置文本。"""
        return list(self._embeddings.keys())

    def register_mock(self, text: str, vector: List[float]) -> None:
        """注册自定义的 Mock Embedding。"""
        self._embeddings[text] = vector
