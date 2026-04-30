"""Test EmbeddingTester — 余弦相似度 + 语义等级分类。"""

import math
import os
import sys
import unittest

# 确保项目根目录在 sys.path 中（pytest 不会自动添加）
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from ext.d_ext_embedding import (
    EmbeddingTester,
    cosine_similarity,
    SIMILARITY_THRESHOLDS,
)


class TestCosineSimilarity(unittest.TestCase):
    """测试余弦相似度基础计算。"""

    def test_identical_vectors(self):
        """相同向量 -> 相似度 = 1.0"""
        v = [1.0, 2.0, 3.0, 4.0]
        self.assertAlmostEqual(cosine_similarity(v, v), 1.0)

    def test_opposite_vectors(self):
        """相反向量 -> 相似度 = -1.0"""
        v1 = [1.0, 2.0, 3.0]
        v2 = [-1.0, -2.0, -3.0]
        self.assertAlmostEqual(cosine_similarity(v1, v2), -1.0)

    def test_orthogonal_vectors(self):
        """正交向量 -> 相似度 = 0.0"""
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(v1, v2), 0.0)

    def test_partial_similarity(self):
        """部分相似 -> 相似度在 0 和 1 之间"""
        v1 = [1.0, 2.0, 3.0]
        v2 = [1.0, 2.0, 1.0]
        sim = cosine_similarity(v1, v2)
        self.assertGreater(sim, 0.0)
        self.assertLess(sim, 1.0)

    def test_dimension_mismatch(self):
        """维度不同 -> 抛 ValueError"""
        with self.assertRaises(ValueError):
            cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])

    def test_zero_vector(self):
        """零向量 -> 相似度 = 0.0"""
        v1 = [0.0, 0.0, 0.0]
        v2 = [1.0, 2.0, 3.0]
        self.assertAlmostEqual(cosine_similarity(v1, v2), 0.0)

    def test_empty_vector(self):
        """空向量 -> 相似度 = 0.0"""
        self.assertAlmostEqual(cosine_similarity([], []), 0.0)

    def test_unit_vector(self):
        """单位向量计算"""
        v1 = [1.0, 0.0]
        v2 = [0.7071, 0.7071]
        expected = 0.7071  # cos(45度)
        sim = cosine_similarity(v1, v2)
        self.assertAlmostEqual(sim, expected, places=4)

    def test_single_element_vectors(self):
        """单元素向量"""
        self.assertAlmostEqual(cosine_similarity([2.0], [2.0]), 1.0)
        self.assertAlmostEqual(cosine_similarity([2.0], [-2.0]), -1.0)


class TestEmbeddingTester(unittest.TestCase):
    """测试 EmbeddingTester（离线模式）。"""

    def setUp(self):
        self.et = EmbeddingTester()

    def test_get_embedding_known_text(self):
        """获取已知文本的向量"""
        vec = self.et.get_embedding("上海的天气怎么样")
        self.assertIsInstance(vec, list)
        self.assertGreater(len(vec), 0)
        # 向量经过 L2 归一化，模长应为 1
        norm = math.sqrt(sum(v * v for v in vec))
        self.assertAlmostEqual(norm, 1.0, places=5)

    def test_get_embedding_unknown_text(self):
        """获取未知文本 -> KeyError"""
        with self.assertRaises(KeyError):
            self.et.get_embedding("完全不存在的文本内容")

    def test_get_embedding_fuzzy_match(self):
        """模糊匹配：忽略空格"""
        vec1 = self.et.get_embedding("上海的天气怎么样")
        vec2 = self.et.get_embedding("上海的天气怎么样 ")  # 末尾空格
        self.assertEqual(vec1, vec2)

    def test_list_available_texts(self):
        """列出可用文本"""
        texts = self.et.list_available_texts()
        self.assertIn("上海的天气怎么样", texts)
        self.assertIn("怎么修汽车", texts)
        self.assertGreaterEqual(len(texts), 5)

    def test_register_mock(self):
        """注册自定义 Mock Embedding"""
        self.et.register_mock("测试文本", [0.5, 0.5])
        vec = self.et.get_embedding("测试文本")
        self.assertEqual(vec, [0.5, 0.5])

    def test_online_mode(self):
        """在线模式（提供 embed_func）"""
        def fake_embed(text):
            return [float(len(text)), 0.0]

        et = EmbeddingTester(embed_func=fake_embed)
        vec = et.get_embedding("hello")
        self.assertEqual(vec, [5.0, 0.0])

    def test_online_similarity(self):
        """在线模式的相似度计算"""
        def fake_embed(text):
            return [float(len(text)), 0.0]

        et = EmbeddingTester(embed_func=fake_embed)
        sim = et.compute_similarity("hi", "hi")
        self.assertAlmostEqual(sim, 1.0)
        sim2 = et.compute_similarity("hi", "hello")
        self.assertAlmostEqual(sim2, 1.0)


class TestSemanticSimilarityPairs(unittest.TestCase):
    """测试语义相似度对（关键业务场景）。"""

    def setUp(self):
        self.et = EmbeddingTester()

    def test_weather_related(self):
        """天气相关句子 -> 高相似度"""
        sim = self.et.compute_similarity("上海的天气怎么样", "上海今天气温")
        self.assertGreater(sim, SIMILARITY_THRESHOLDS["high"])

    def test_weather_unrelated(self):
        """天气 vs 修车 -> 不相关"""
        sim = self.et.compute_similarity("上海的天气怎么样", "怎么修汽车")
        self.assertLess(sim, SIMILARITY_THRESHOLDS["low"])

    def test_synonym_high_similarity(self):
        """同义词替换 -> 高相似度（电脑 vs 计算机）"""
        sim = self.et.compute_similarity("电脑和计算机有什么区别", "计算机和电脑的区别")
        self.assertGreater(sim, SIMILARITY_THRESHOLDS["high"])

    def test_weather_variants(self):
        """天气不同表达 -> 中高相似度"""
        sim = self.et.compute_similarity("上海的天气怎么样", "今天天气怎么样")
        self.assertGreater(sim, SIMILARITY_THRESHOLDS["medium"])

    def test_tech_vs_cooking(self):
        """完全不同领域 -> 不相关"""
        sim = self.et.compute_similarity("电脑和计算机有什么区别", "如何做酱牛肉")
        self.assertLess(sim, SIMILARITY_THRESHOLDS["low"])


class TestCheckSemanticPair(unittest.TestCase):
    """测试语义对验证函数。"""

    def setUp(self):
        self.et = EmbeddingTester()

    def test_check_pass_high(self):
        """预期 high 且实际 high -> pass=True"""
        result = self.et.check_semantic_pair("上海的天气怎么样", "上海今天气温", "high")
        self.assertTrue(result["pass"])
        self.assertEqual(result["level"], "high")

    def test_check_fail_high(self):
        """预期 high 但实际 low -> pass=False"""
        result = self.et.check_semantic_pair("上海的天气怎么样", "怎么修汽车", "high")
        self.assertFalse(result["pass"])

    def test_check_pass_low(self):
        """预期 low 且实际 low -> pass=True"""
        result = self.et.check_semantic_pair("上海的天气怎么样", "怎么修汽车", "low")
        self.assertTrue(result["pass"])

    def test_check_result_structure(self):
        """验证返回结果的完整结构"""
        result = self.et.check_semantic_pair("上海的天气怎么样", "上海今天气温", "high")
        expected_keys = {"text1", "text2", "similarity", "level", "expected", "pass", "detail"}
        self.assertEqual(set(result.keys()), expected_keys)


class TestBatchSimilarityMatrix(unittest.TestCase):
    """测试批量相似度矩阵。"""

    def setUp(self):
        self.et = EmbeddingTester()

    def test_matrix_single_text(self):
        """单个文本 -> 1x1 矩阵"""
        matrix = self.et.batch_similarity_matrix(["上海的天气怎么样"])
        self.assertEqual(len(matrix), 1)
        self.assertEqual(len(matrix[0]), 1)
        self.assertAlmostEqual(matrix[0][0], 1.0)

    def test_matrix_two_texts(self):
        """两个文本 -> 2x2 矩阵"""
        matrix = self.et.batch_similarity_matrix(["上海的天气怎么样", "上海今天气温"])
        self.assertEqual(len(matrix), 2)
        self.assertEqual(len(matrix[0]), 2)
        self.assertAlmostEqual(matrix[0][0], 1.0)
        self.assertAlmostEqual(matrix[1][1], 1.0)
        self.assertAlmostEqual(matrix[0][1], matrix[1][0])  # 对称

    def test_matrix_diagonal_is_one(self):
        """对角线全为 1.0"""
        texts = ["上海的天气怎么样", "怎么修汽车", "电脑和计算机有什么区别"]
        matrix = self.et.batch_similarity_matrix(texts)
        for i in range(len(texts)):
            self.assertAlmostEqual(matrix[i][i], 1.0)

    def test_matrix_symmetry(self):
        """矩阵对称性"""
        texts = ["上海的天气怎么样", "怎么修汽车", "电脑和计算机有什么区别"]
        matrix = self.et.batch_similarity_matrix(texts)
        for i in range(len(texts)):
            for j in range(len(texts)):
                self.assertAlmostEqual(matrix[i][j], matrix[j][i])


class TestGetSimilarityLevel(unittest.TestCase):
    """测试相似度等级分类。"""

    def setUp(self):
        self.et = EmbeddingTester()

    def test_high_level(self):
        """高相似度范围"""
        self.assertEqual(self.et.get_similarity_level(0.90), "high")
        self.assertEqual(self.et.get_similarity_level(1.00), "high")
        self.assertEqual(self.et.get_similarity_level(0.85), "high")

    def test_medium_level(self):
        """中相似度范围"""
        self.assertEqual(self.et.get_similarity_level(0.75), "medium")
        self.assertEqual(self.et.get_similarity_level(0.60), "medium")

    def test_low_level(self):
        """低相似度范围"""
        self.assertEqual(self.et.get_similarity_level(0.45), "low")
        self.assertEqual(self.et.get_similarity_level(0.30), "low")

    def test_unrelated_level(self):
        """不相关"""
        self.assertEqual(self.et.get_similarity_level(0.20), "unrelated")
        self.assertEqual(self.et.get_similarity_level(0.00), "unrelated")
        self.assertEqual(self.et.get_similarity_level(-0.5), "unrelated")

    def test_boundary_values(self):
        """边界值"""
        self.assertEqual(self.et.get_similarity_level(0.85), "high")
        self.assertEqual(self.et.get_similarity_level(0.84), "medium")
        self.assertEqual(self.et.get_similarity_level(0.60), "medium")
        self.assertEqual(self.et.get_similarity_level(0.59), "low")
        self.assertEqual(self.et.get_similarity_level(0.30), "low")
        self.assertEqual(self.et.get_similarity_level(0.29), "unrelated")


if __name__ == "__main__":
    unittest.main()
