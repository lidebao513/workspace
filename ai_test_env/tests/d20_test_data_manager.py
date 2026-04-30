"""
Day 20 (Week 4 Day 5) — 测试数据管理 单元测试

覆盖：
1. DataProfile 配置校验和归一化
2. PromptDataFactory 生成、多样性、种子一致性
3. ResponseDataFactory 响应比例分布、类型标记
4. DataMasker 邮箱/手机/身份证/API Key/IP 脱敏
5. DataVersionTracker 版本管理、diff、历史
"""
import sys
import os
import unittest
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d20_data_manager import (
    DataProfile, PromptDataFactory, ResponseDataFactory,
    DataMasker, DataVersionTracker, DatasetEntry,
)


class TestDataProfile(unittest.TestCase):
    """数据配置"""

    def test_default_profile(self):
        """默认配置"""
        p = DataProfile(name="test")
        self.assertEqual(p.count, 100)
        self.assertEqual(p.version, "1.0.0")

    def test_validate_valid(self):
        """有效配置"""
        p = DataProfile(name="test", count=10)
        errors = p.validate()
        self.assertEqual(len(errors), 0)

    def test_validate_invalid_count(self):
        """无效 count"""
        p = DataProfile(name="test", count=0)
        errors = p.validate()
        self.assertTrue(any("count" in e for e in errors))

    def test_validate_ratio_sum(self):
        """比例和不为 1"""
        p = DataProfile(name="test", count=10,
                       response_type_ratios={"valid": 0.5, "truncated": 0.5})
        errors = p.validate()
        self.assertEqual(len(errors), 0)

    def test_validate_bad_ratio_sum(self):
        """比例和偏离 1"""
        p = DataProfile(name="test", count=10,
                       response_type_ratios={"valid": 0.3})
        errors = p.validate()
        self.assertTrue(any("ratios sum" in e for e in errors))

    def test_adjust_ratios(self):
        """归一化"""
        p = DataProfile(name="test", count=10,
                       response_type_ratios={"a": 2, "b": 2, "c": 1})
        p.adjust_ratios()
        total = sum(p.response_type_ratios.values())
        self.assertAlmostEqual(total, 1.0)


class TestPromptDataFactory(unittest.TestCase):
    """Prompt 生成"""

    def setUp(self):
        self.factory = PromptDataFactory(seed=42)

    def test_generate_count(self):
        """生成数量正确"""
        profile = DataProfile(name="test", count=10)
        prompts = self.factory.generate_prompts(profile)
        self.assertEqual(len(prompts), 10)

    def test_generate_structure(self):
        """生成结构正确"""
        profile = DataProfile(name="test", count=5)
        prompts = self.factory.generate_prompts(profile)
        for p in prompts:
            self.assertIn("id", p)
            self.assertIn("text", p)
            self.assertIn("category", p)
            self.assertIn("tags", p)

    def test_seed_consistency(self):
        """相同种子生成相同结果"""
        profile = DataProfile(name="test", count=10, seed=42)
        prompts1 = PromptDataFactory(seed=42).generate_prompts(profile)
        prompts2 = PromptDataFactory(seed=42).generate_prompts(profile)
        for p1, p2 in zip(prompts1, prompts2):
            self.assertEqual(p1["text"], p2["text"])

    def test_different_seed(self):
        """不同 profile seed 生成不同结果"""
        p1 = DataProfile(name="test", count=10, seed=42)
        p2 = DataProfile(name="test", count=10, seed=99)
        prompts1 = PromptDataFactory().generate_prompts(p1)
        prompts2 = PromptDataFactory().generate_prompts(p2)
        texts1 = [p["text"] for p in prompts1]
        texts2 = [p["text"] for p in prompts2]
        # 大概率不同（种子不同）
        self.assertNotEqual(texts1, texts2)

    def test_category_cycle(self):
        """类别循环"""
        profile = DataProfile(name="test", count=6,
                            categories=["qa", "summary"])
        prompts = self.factory.generate_prompts(profile)
        self.assertEqual(prompts[0]["category"], "qa")
        self.assertEqual(prompts[1]["category"], "summary")
        self.assertEqual(prompts[2]["category"], "qa")

    def test_all_texts_non_empty(self):
        """所有文本非空"""
        profile = DataProfile(name="test", count=50)
        prompts = self.factory.generate_prompts(profile)
        self.assertTrue(all(p["text"] for p in prompts))

    def test_texts_are_strings(self):
        """所有文本为字符串"""
        profile = DataProfile(name="test", count=20)
        prompts = self.factory.generate_prompts(profile)
        self.assertTrue(all(isinstance(p["text"], str) for p in prompts))

    def test_id_format(self):
        """ID 格式正确"""
        profile = DataProfile(name="test", count=5)
        prompts = self.factory.generate_prompts(profile)
        for p in prompts:
            self.assertRegex(p["id"], r"prompt_[\d_]+_\d{4}")


class TestResponseDataFactory(unittest.TestCase):
    """Response 生成"""

    def setUp(self):
        self.factory = ResponseDataFactory(seed=42)

    def test_generate_count(self):
        """生成数量正确"""
        profile = DataProfile(name="test", count=20)
        responses = self.factory.generate_responses(profile)
        self.assertEqual(len(responses), 20)

    def test_generate_structure(self):
        """生成结构正确"""
        profile = DataProfile(name="test", count=5)
        responses = self.factory.generate_responses(profile)
        for r in responses:
            self.assertIn("id", r)
            self.assertIn("text", r)
            self.assertIn("type", r)
            self.assertIn("finish_reason", r)

    def test_proportional_types(self):
        """类型比例分布"""
        profile = DataProfile(name="test", count=100,
                            response_type_ratios={
                                "valid": 0.40,
                                "truncated": 0.20,
                                "rejected": 0.20,
                                "empty": 0.10,
                                "error": 0.10,
                            })
        responses = self.factory.generate_responses(profile)
        type_counts = {}
        for r in responses:
            type_counts[r["type"]] = type_counts.get(r["type"], 0) + 1
        # 所有类型都出现
        for t in ["valid", "truncated", "rejected", "empty", "error"]:
            self.assertGreater(type_counts.get(t, 0), 0)

    def test_valid_response_has_text(self):
        """有效回复有文本"""
        profile = DataProfile(name="test", count=50)
        responses = self.factory.generate_responses(profile)
        valid = [r for r in responses if r["type"] == "valid"]
        if valid:
            self.assertTrue(all(len(r["text"]) > 20 for r in valid))

    def test_empty_response(self):
        """空回复"""
        profile = DataProfile(name="test", count=30,
                            response_type_ratios={"empty": 1.0})
        responses = self.factory.generate_responses(profile)
        self.assertTrue(all(r["text"] == "" for r in responses))

    def test_prompt_correlation(self):
        """与 prompt 关联"""
        profile = DataProfile(name="test", count=5)
        factory = PromptDataFactory()
        prompts = factory.generate_prompts(profile)
        responses = self.factory.generate_responses(profile, prompts=prompts)
        for i, r in enumerate(responses):
            self.assertIn(prompts[i]["id"], r["id"])

    def test_seed_determinism(self):
        """种子确定性"""
        profile = DataProfile(name="test", count=10)
        r1 = ResponseDataFactory(seed=42).generate_responses(profile)
        r2 = ResponseDataFactory(seed=42).generate_responses(profile)
        for a, b in zip(r1, r2):
            self.assertEqual(a["text"], b["text"])

    def test_ratio_exact_type(self):
        """单一类型"""
        for rtype in ["valid", "truncated", "rejected", "empty", "error"]:
            profile = DataProfile(name="test", count=5,
                                response_type_ratios={rtype: 1.0})
            responses = self.factory.generate_responses(profile)
            self.assertTrue(all(r["type"] == rtype for r in responses),
                          f"Failed for type: {rtype}")


class TestDataMasker(unittest.TestCase):
    """脱敏工具"""

    def test_mask_email(self):
        """邮箱脱敏"""
        result = DataMasker.mask_email("user@example.com")
        self.assertIn("@example.com", result)
        self.assertNotIn("user@", result)

    def test_mask_email_multiple(self):
        """多个邮箱"""
        text = "Contact: foo@bar.com and baz@qux.com"
        result = DataMasker.mask_email(text)
        self.assertNotIn("foo@", result)
        self.assertNotIn("baz@", result)

    def test_mask_phone(self):
        """手机号脱敏"""
        result = DataMasker.mask_phone("13812345678")
        self.assertIn("138****5678", result)

    def test_mask_id_card(self):
        """身份证脱敏"""
        result = DataMasker.mask_id_card("110101199001011234")
        self.assertIn("110101********1234", result)

    def test_mask_api_key(self):
        """API Key 脱敏"""
        result = DataMasker.mask_api_key("sk-abcdefghijklmnopqrst")
        self.assertIn("sk-****************qrst", result)

    def test_mask_api_key_short(self):
        """短 API Key 脱敏（20+字符才被识别）"""
        result = DataMasker.mask_api_key("sk-abc")
        # sk- 后不足20字符，regex 不匹配
        self.assertEqual(result, "sk-abc")

    def test_mask_ip(self):
        """IP 脱敏"""
        result = DataMasker.mask_ip("192.168.1.1")
        self.assertIn("192.168.*.*", result)

    def test_mask_all(self):
        """全部脱敏"""
        text = "user@test.com 13812345678 sk-abcdefghijklmnopqrstuvwxyz 192.168.1.1"
        result = DataMasker.mask_all(text)
        self.assertNotIn("user@", result)
        self.assertNotIn("12345678", result)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", result)

    def test_has_sensitive_data(self):
        """敏感数据检测"""
        result = DataMasker.has_sensitive_data("email: foo@bar.com")
        self.assertTrue(result["email"])
        self.assertFalse(result["phone"])

    def test_no_sensitive(self):
        """无敏感数据"""
        result = DataMasker.has_sensitive_data("hello world")
        self.assertTrue(not any(result.values()))

    def test_phone_partial(self):
        """部分脱敏不匹配"""
        result = DataMasker.has_sensitive_data("phone: 12345678901")
        self.assertFalse(result["phone"])


class TestDataVersionTracker(unittest.TestCase):
    """版本追踪"""

    def setUp(self):
        self.tracker = DataVersionTracker("test_dataset")

    def test_initial_version(self):
        """初始版本"""
        self.assertEqual(self.tracker.current_version, "0.0.1")

    def test_add_entries(self):
        """添加条目"""
        entries = [DatasetEntry(id=f"e{i}", text=f"text{i}") for i in range(5)]
        version = self.tracker.add_entries(entries, "Initial import")
        self.assertEqual(version, "0.0.2")
        self.assertEqual(len(self.tracker.entries), 5)

    def test_version_bump(self):
        """版本递增"""
        entries = [DatasetEntry(id="e1", text="hello")]
        v1 = self.tracker.add_entries(entries)
        v2 = self.tracker.update_entries(entries, "Update")
        self.assertNotEqual(v1, v2)

    def test_update_entries_records_added(self):
        """更新记录新增"""
        t = DataVersionTracker("test")
        t.add_entries([DatasetEntry(id="e1", text="a")], "init")
        t.update_entries(
            [DatasetEntry(id="e1", text="a"),
             DatasetEntry(id="e2", text="b")],
            "add one"
        )
        latest = t.history[-1]
        self.assertIn("Added", " ".join(latest.changes))

    def test_update_entries_records_modified(self):
        """更新记录修改"""
        t = DataVersionTracker("test")
        t.add_entries([DatasetEntry(id="e1", text="a")], "init")
        t.update_entries([DatasetEntry(id="e1", text="b")], "modify")
        latest = t.history[-1]
        combined = " ".join(latest.changes)
        self.assertIn("Modified", combined)

    def test_get_diff(self):
        """版本间 diff"""
        t = DataVersionTracker("test")
        v1 = t.add_entries([DatasetEntry(id="e1", text="a")], "v1")
        v2 = t.update_entries(
            [DatasetEntry(id="e1", text="b"),
             DatasetEntry(id="e2", text="c")],
            "v2"
        )
        diff = t.get_diff(v1, v2)
        self.assertIn("modified", diff)
        self.assertIn("added", diff)

    def test_get_version_history(self):
        """版本历史"""
        t = DataVersionTracker("test")
        t.add_entries([DatasetEntry(id="e1", text="a")], "init")
        t.update_entries([DatasetEntry(id="e1", text="b")], "update")
        history = t.get_version_history()
        self.assertEqual(len(history), 2)

    def test_entry_checksum(self):
        """条目校验和"""
        entry = DatasetEntry(id="e1", text="hello world")
        cs = entry.checksum()
        self.assertEqual(len(cs), 32)  # MD5 hex length
        self.assertIsInstance(cs, str)

    def test_history_has_timestamps(self):
        """历史含时间戳"""
        t = DataVersionTracker("test")
        t.add_entries([DatasetEntry(id="e1", text="a")], "init")
        entry = t.history[0]
        self.assertIn("timestamp", entry.__dict__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
