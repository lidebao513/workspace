"""
Day 11 (Week 3 Day 1) — 多轮对话上下文测试

测试 ConversationTester、ConversationManager 的各核心功能。
所有测试基于离线模式（不调用 API），确保独立可验证。
"""
import sys
import os
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d11_conversation_tester import (
    Turn, Conversation, ContextTestResult,
    ConversationTester, ConversationManager,
    detect_key_info,
)


class TestTurnAndConversation(unittest.TestCase):
    """测试基础数据结构"""

    def test_turn_creation(self):
        """Turn 数据结构正确"""
        t = Turn(role="user", content="你好", tokens=10, latency_ms=1.2)
        self.assertEqual(t.role, "user")
        self.assertEqual(t.content, "你好")
        self.assertEqual(t.tokens, 10)
        self.assertEqual(t.latency_ms, 1.2)

    def test_conversation_add_turn(self):
        """Conversation 添加轮次"""
        conv = Conversation()
        self.assertEqual(conv.length, 0)
        conv.add_turn("user", "你好", tokens=10)
        conv.add_turn("assistant", "你好！", tokens=20)
        self.assertEqual(conv.length, 2)
        self.assertEqual(conv.total_tokens, 30)
        self.assertEqual(conv.total_latency_ms, 0.0)

    def test_conversation_summary(self):
        """Conversation.summary() 输出格式正确"""
        conv = Conversation()
        conv.add_turn("user", "你好", tokens=10, latency_ms=100)
        conv.add_turn("assistant", "好的", tokens=20, latency_ms=200)
        summary = conv.summary()
        self.assertEqual(summary["total_turns"], 2)
        self.assertEqual(summary["total_tokens"], 30)
        self.assertAlmostEqual(summary["avg_tokens_per_turn"], 15.0)
        self.assertAlmostEqual(summary["avg_latency_per_turn"], 150.0)

    def test_conversation_to_messages(self):
        """Conversation.to_messages() 输出 API 格式"""
        conv = Conversation()
        conv.add_turn("user", "你好")
        conv.add_turn("assistant", "好的")
        msgs = conv.to_messages()
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "user")
        self.assertEqual(msgs[0]["content"], "你好")
        self.assertEqual(msgs[1]["role"], "assistant")
        self.assertEqual(msgs[1]["content"], "好的")


class TestConversationTesterBuildScript(unittest.TestCase):
    """测试对话脚本构造"""

    def setUp(self):
        self.tester = ConversationTester()

    def test_build_script_has_all_phases(self):
        """build_conversation_script 包含注入->干扰->验证三阶段"""
        script = self.tester.build_conversation_script(
            key_info={"name": "张三", "phone": "13800138000"},
            context_turns_before=2,
            context_turns_after=3,
            verification_delays=[1, 3, 5],
        )
        # 提取 tag
        tags = [msg.get("_tag") for msg in script]
        # 检查是否包含各阶段
        self.assertIn("greeting", tags, "应包含寒暄阶段")
        self.assertIn("info_injection", tags, "应包含信息注入阶段")
        self.assertIn("distractor", tags, "应包含干扰阶段")
        self.assertIn("verification", tags, "应包含验证阶段")

    def test_build_script_message_count(self):
        """脚本消息数为 (寒暄 + 注入 + 干扰 + 验证) * 2（user + assistant）"""
        script = self.tester.build_conversation_script(
            key_info={"name": "张三"},
            context_turns_before=2,
            context_turns_after=2,
            verification_delays=[1],
        )
        # 寒暄 2 * 2 = 4, 注入 1 * 2 = 2, 干扰 2 * 2 = 4, 验证 1 * 1 = 1（assistant留空）
        expected = 4 + 2 + 4 + 1  # = 11
        self.assertEqual(len(script), expected,
                         f"期望 {expected} 条消息，实际 {len(script)}")

    def test_verification_questions_match_keys(self):
        """验证问题覆盖所有注入的关键信息键"""
        key_info = {"name": "张三", "phone": "13800138000", "email": "a@b.com"}
        script = self.tester.build_conversation_script(
            key_info=key_info,
            context_turns_before=1,
            context_turns_after=1,
        )
        verification_qs = [
            msg["content"] for msg in script
            if msg.get("_tag") == "verification"
        ]
        # 应该正好有 3 个验证问题
        self.assertEqual(len(verification_qs), 3,
                         f"期望 3 个验证问题，实际 {len(verification_qs)}")
        # 每个 key 的标签都应出现在问题中
        self.assertTrue(
            any("名字" in q for q in verification_qs),
            "验证问题应包含名字"
        )
        self.assertTrue(
            any("手机号" in q for q in verification_qs),
            "验证问题应包含手机号"
        )
        self.assertTrue(
            any("邮箱" in q for q in verification_qs),
            "验证问题应包含邮箱"
        )


class TestConversationTesterAnalyze(unittest.TestCase):
    """测试上下文分析"""

    def setUp(self):
        self.tester = ConversationTester()

    def test_analyze_full_recall(self):
        """全部信息正确召回 → recall_rate = 1.0"""
        conv = Conversation()
        conv.add_turn("user", "我叫张三", tokens=10)
        conv.add_turn("assistant", "好的张三", tokens=20)
        conv.add_turn("user", "我刚才说的名字是什么？", tokens=15)

        result = self.tester.analyze_context(
            key_info={"name": "张三"},
            recall_responses={"name": "张三"},
            conversation=conv,
            verification_turn=3,
        )
        self.assertEqual(result.recall_rate, 1.0)
        self.assertEqual(result.turns_until_forget, -1)
        self.assertIn("全部", result.conclusion)

    def test_analyze_partial_recall(self):
        """部分信息召回 → 0 < recall_rate < 1.0"""
        conv = Conversation()
        conv.add_turn("user", "我叫张三，手机13800", tokens=15)
        conv.add_turn("assistant", "好的", tokens=10)
        conv.add_turn("user", "我的信息是什么？", tokens=10)

        result = self.tester.analyze_context(
            key_info={"name": "张三", "phone": "13800"},
            recall_responses={"name": "张三", "phone": ""},
            conversation=conv,
            verification_turn=3,
        )
        self.assertAlmostEqual(result.recall_rate, 0.5)
        self.assertEqual(result.turns_until_forget, 3)

    def test_analyze_zero_recall(self):
        """全部遗忘 → recall_rate = 0.0"""
        result = self.tester.analyze_context(
            key_info={"name": "张三", "card_last4": "8888"},
            recall_responses={"name": "", "card_last4": ""},
            verification_turn=5,
        )
        self.assertAlmostEqual(result.recall_rate, 0.0)
        self.assertEqual(result.turns_until_forget, 5)
        self.assertIn("严重遗忘", result.conclusion)

    def test_analyze_empty_key_info(self):
        """无关键信息 → recall_rate = 1.0（无意义）"""
        result = self.tester.analyze_context(
            key_info={},
            recall_responses={},
        )
        self.assertEqual(result.recall_rate, 1.0)
        self.assertEqual(result.conclusion, "无关键信息注入")

    def test_analyze_contain_match(self):
        """模型回复包含期望值（非精确匹配）→ 仍算召回"""
        result = self.tester.analyze_context(
            key_info={"name": "张三"},
            recall_responses={"name": "您说的是张三，对吧？"},
            verification_turn=3,
        )
        self.assertEqual(result.recall_rate, 1.0)

    def test_analyze_history_tracked(self):
        """analyze_context 的调用历史会被记录"""
        self.tester.analyze_context(
            key_info={"name": "李四"},
            recall_responses={"name": "李四"},
        )
        self.tester.analyze_context(
            key_info={"phone": "13900"},
            recall_responses={"phone": ""},
        )
        history = self.tester.history()
        self.assertEqual(len(history), 2)
        self.assertAlmostEqual(history[0]["recall_rate"], 1.0)
        self.assertAlmostEqual(history[1]["recall_rate"], 0.0)


class TestConversationManager(unittest.TestCase):
    """测试会话管理器"""

    def setUp(self):
        self.manager = ConversationManager()

    def test_create_conversation(self):
        """创建会话并计数"""
        conv = self.manager.create_conversation()
        self.assertIsNotNone(conv)
        self.assertEqual(self.manager.count(), 1)

    def test_latest_conversation(self):
        """latest() 返回最新会话"""
        _ = self.manager.create_conversation()
        conv2 = self.manager.create_conversation()
        self.assertIs(self.manager.latest(), conv2)

    def test_summary_all(self):
        """summary_all() 输出格式"""
        conv = self.manager.create_conversation()
        conv.add_turn("user", "你好", tokens=10)
        conv.add_turn("assistant", "好的", tokens=20)
        summaries = self.manager.summary_all()
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["total_turns"], 2)

    def test_token_trend(self):
        """token_trend() 分析 Token 趋势"""
        conv = self.manager.create_conversation()
        conv.add_turn("user", "你好", tokens=10)
        conv.add_turn("assistant", "好的你好啊", tokens=20)
        conv.add_turn("user", "还有什么问题", tokens=15)
        trends = self.manager.token_trend()
        self.assertEqual(len(trends), 1)
        trend_points = trends[0]["trend"]
        self.assertEqual(len(trend_points), 3)
        # 累计 Token 应递增
        self.assertLess(trend_points[0]["cumulative_tokens"],
                        trend_points[-1]["cumulative_tokens"])

    def test_export_messages(self):
        """export_messages 转为 API messages 格式"""
        conv = self.manager.create_conversation()
        conv.add_turn("user", "你好")
        conv.add_turn("assistant", "好的")
        msgs = self.manager.export_messages(conv)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0], {"role": "user", "content": "你好"})

    def test_reset(self):
        """reset() 清空所有会话"""
        self.manager.create_conversation()
        self.manager.create_conversation()
        self.assertEqual(self.manager.count(), 2)
        self.manager.reset()
        self.assertEqual(self.manager.count(), 0)


class TestDetectKeyInfo(unittest.TestCase):
    """测试辅助函数"""

    def test_detect_exact_match(self):
        """精确匹配到关键信息"""
        result = detect_key_info("我叫张三，手机13800", {"name": "张三", "phone": "13800"})
        self.assertEqual(result["name"], "张三")
        self.assertEqual(result["phone"], "13800")

    def test_detect_partial_match(self):
        """部分匹配"""
        result = detect_key_info("我叫张三", {"name": "张三", "phone": "13800"})
        self.assertEqual(result["name"], "张三")
        self.assertEqual(result["phone"], "")

    def test_detect_no_match(self):
        """无匹配"""
        result = detect_key_info("我不认识你", {"name": "张三"})
        self.assertEqual(result["name"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
