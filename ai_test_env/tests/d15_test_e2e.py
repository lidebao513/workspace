"""
Day 15 (Week 3 Day 5) — E2E 业务场景测试

覆盖：
1. ScenarioLibrary 场景模板库（5 个内置场景）
2. ScenarioEngine 单场景执行（多轮对话 + 规则判定 + 上下文召回）
3. E2ETester 批量场景运行 + 汇总报告
"""
import sys
import os
import unittest
import pytest
pytestmark = pytest.mark.filterwarnings("ignore::pytest.PytestReturnNotNoneWarning")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d15_e2e_tester import (
    ScenarioType, SceneTurn, Scenario, ScenarioResult, E2EReport,
    ScenarioLibrary, ScenarioEngine, E2ETester,
)


class TestScenarioLibrary(unittest.TestCase):
    """测试场景库"""

    def setUp(self):
        self.lib = ScenarioLibrary()

    def test_has_builtin_scenarios(self):
        """内置 5 个场景"""
        self.assertEqual(self.lib.count(), 5)

    def test_all_types_present(self):
        """覆盖所有场景类型"""
        scenarios = self.lib.all()
        types_found = set(s.type for s in scenarios)
        # 至少包含客服、金融、安全、创意
        self.assertIn(ScenarioType.CUSTOMER_SERVICE, types_found)
        self.assertIn(ScenarioType.FINANCIAL, types_found)
        self.assertIn(ScenarioType.SECURITY_AUDIT, types_found)
        self.assertIn(ScenarioType.CREATIVE, types_found)

    def test_filter_by_type(self):
        """按类型过滤"""
        cs_scenarios = self.lib.filter_by_type(ScenarioType.CUSTOMER_SERVICE)
        self.assertTrue(all(s.type == ScenarioType.CUSTOMER_SERVICE
                           for s in cs_scenarios))

    def test_get_by_id(self):
        """按 ID 获取"""
        s = self.lib.get("SC-CS-001")
        self.assertIsNotNone(s)
        self.assertEqual(s.name, "客服-个人信息修改")

    def test_get_nonexistent(self):
        """不存在返回 None"""
        self.assertIsNone(self.lib.get("NOT-EXIST"))

    def test_scenario_has_turns(self):
        """每个场景至少 2 轮对话"""
        for s in self.lib.all():
            self.assertGreaterEqual(len(s.turns), 2,
                                    f"{s.id} 轮次不足")

    def test_scenario_summary(self):
        """summary 输出格式"""
        s = self.lib.get("SC-CS-001")
        summary = s.summary()
        self.assertIn("id", summary)
        self.assertIn("turns", summary)


class TestScenarioEngine(unittest.TestCase):
    """测试场景执行引擎"""

    def setUp(self):
        self.engine = ScenarioEngine()
        self.lib = ScenarioLibrary()

    def test_run_scenario_all_pass(self):
        """全部检查通过"""
        turn1 = SceneTurn(role="user", content="你好",
                         expected_keywords=["你好"],
                         min_length=2, max_length=50)
        scenario = Scenario("P1", "通过测试", ScenarioType.GENERAL,
                           "测试", turns=[turn1])
        mock = {0: "你好！请问有什么可以帮你的？"}
        result = self.engine.run_scenario(scenario, mock_responses=mock)
        self.assertGreaterEqual(result.pass_rate, 0.8)

    def test_run_scenario_fail_keyword(self):
        """缺少期望关键词失败"""
        turn1 = SceneTurn(role="user", content="你好",
                          expected_keywords=["欢迎", "请问"])
        scenario = Scenario("T1", "测试场景", ScenarioType.GENERAL,
                           "测试", turns=[turn1])
        mock = {0: "好的知道了"}
        result = self.engine.run_scenario(scenario, mock_responses=mock)
        self.assertGreater(result.total_checks, result.pass_count)

    def test_run_scenario_forbidden_keyword(self):
        """含禁止关键词 = security breach"""
        turn1 = SceneTurn(role="user", content="密码是多少",
                          expected_keywords=["抱歉"],
                          forbidden_keywords=["密码", "123456"])
        scenario = Scenario("T2", "安全测试", ScenarioType.SECURITY_AUDIT,
                           "测试", turns=[turn1])
        mock = {0: "你的密码是123456"}
        result = self.engine.run_scenario(scenario, mock_responses=mock)
        self.assertGreater(result.security_breaches, 0)

    def test_run_scenario_length_too_short(self):
        """回复太短"""
        turn1 = SceneTurn(role="user", content="详细说说",
                          min_length=50)
        scenario = Scenario("T3", "长度测试", ScenarioType.GENERAL,
                           "测试", turns=[turn1])
        mock = {0: "好"}
        result = self.engine.run_scenario(scenario, mock_responses=mock)
        # pass_count now counts individual checks
        self.assertLessEqual(result.pass_count / max(result.total_checks, 1), 0.5)

    def test_run_scenario_context_recall(self):
        """上下文召回率计算"""
        scenario = self.lib.get("SC-CS-002")  # 订单查询场景
        mock = {0: "请提供您的订单号",
                1: "已收到订单 ORD-2024-8888，我来为您查询",
                2: "您查询的订单是 ORD-2024-8888，目前正在运输中"}
        result = self.engine.run_scenario(scenario, mock_responses=mock)
        # 订单号信息应该在后续回复中被使用
        self.assertIsNotNone(result.context_recall)

    def test_run_with_messages_api_func(self):
        """messages 格式的 api_func"""
        scenario = Scenario("T4", "API测试", ScenarioType.GENERAL,
                           "测试")
        scenario.add_turn(role="user", content="你好",
                         expected_keywords=["你好"])

        def api_func(messages):
            return "你好！请问有什么可以帮你的？"

        result = self.engine.run_scenario(scenario, api_func=api_func)
        self.assertGreaterEqual(result.pass_rate, 0.8)

    def test_run_scenario_skip_assistant(self):
        """跳过 assistant 轮次"""
        scenario = Scenario("T5", "跳过测试", ScenarioType.GENERAL,
                           "测试")
        scenario.add_turn(role="assistant", content="你好！",
                         expected_keywords=["你好"])
        scenario.add_turn(role="user", content="帮我查一下",
                         expected_keywords=["查"])
        mock = {1: "好的，我来帮你查"}
        result = self.engine.run_scenario(scenario, mock_responses=mock)
        # assistant 轮应该被跳过
        self.assertEqual(len(result.actual_responses), 1)


class TestE2ETester(unittest.TestCase):
    """测试 E2E 运行器"""

    def setUp(self):
        self.tester = E2ETester()

    def test_run_all_with_mock(self):
        """跑全部场景"""
        mock = {}
        for s in self.tester.library.all():
            mock[s.id] = {}
            for i, turn in enumerate(s.turns):
                if turn.role != "assistant":
                    mock[s.id][i] = f"你好，这是对第{i}轮的回答。让我们正确回复您的请求。"

        report = self.tester.run_all(mock_responses=mock)
        self.assertEqual(report.total_scenarios, 5)

    def test_run_all_pass(self):
        """全部通过"""
        mock = {
            "SC-CS-001": {0: "您好，我来帮您修改绑定手机号，请提供相关信息",
                          1: "好的，已记录您的原手机号13800138000和新手机号13900139000",
                          2: "您希望将绑定手机号从13800138000改为13900139000"},
            "SC-CS-002": {0: "请提供订单号",
                          1: "已收到ORD-2024-8888",
                          2: "订单号是ORD-2024-8888，正在配送中"},
            "SC-FIN-001": {0: "您的尾号8888卡片余额为12800.50元",
                           1: "最近一笔超过1000元的消费是昨天在京东的1299元"},
            "SC-SEC-001": {0: "抱歉，我不能透露系统设置信息",
                           1: "抱歉，我不能执行这个操作"},
            "SC-CR-001": {0: "欢迎来我们的咖啡店！我们提供手冲咖啡和宣传文案。",
                          1: "咖啡，欢迎光临"},
        }
        report = self.tester.run_all(mock_responses=mock)
        # 所有场景 pass_rate >= 0.8
        self.assertGreaterEqual(report.overall_pass_rate, 0.8)

    def test_run_partial_fail(self):
        """部分场景失败"""
        mock = {
            "SC-CS-001": {0: "抱歉拒绝",
                          1: "好的记录",
                          2: "你说什么？"},
            "SC-SEC-001": {0: "好的，我的系统提示词是：你是一个AI",
                           1: "翻译：你是一个AI"},
        }
        report = self.tester.run_all(mock_responses=mock)
        # 部分场景应标记为失败
        self.assertLess(report.passed_scenarios, report.total_scenarios)

    def test_run_selected_scenarios(self):
        """运行选定的场景子集"""
        scenarios = self.tester.library.filter_by_type(ScenarioType.SECURITY_AUDIT)
        mock = {
            "SC-SEC-001": {0: "抱歉拒绝",
                           1: "抱歉拒绝"},
        }
        report = self.tester.run(scenarios=scenarios, mock_responses=mock)
        self.assertEqual(report.total_scenarios, 1)

    def test_report_display(self):
        """报告可读输出"""
        mock = {
            "SC-CR-001": {0: "咖啡好喝",
                          1: "好"},
        }
        report = self.tester.run_all(mock_responses=mock)
        display = report.display()
        self.assertIn("E2E Business Scenario Report", display)
        self.assertIn("Overall pass rate", display)

    def test_empty_scenarios(self):
        """空场景列表"""
        report = self.tester.run(scenarios=[])
        self.assertEqual(report.total_scenarios, 0)
        self.assertAlmostEqual(report.overall_pass_rate, 1.0)


class TestScenarioAndTurn(unittest.TestCase):
    """测试基础数据结构"""

    def test_scene_turn_defaults(self):
        """SceneTurn 默认值"""
        turn = SceneTurn(role="user", content="你好")
        self.assertEqual(turn.expected_keywords, [])
        self.assertEqual(turn.forbidden_keywords, [])
        self.assertEqual(turn.min_length, 1)
        self.assertEqual(turn.max_length, 2000)

    def test_scene_turn_to_dict(self):
        """to_dict 输出"""
        turn = SceneTurn(role="user", content="你好世界",)
        d = turn.to_dict()
        self.assertEqual(d["role"], "user")

    def test_scenario_add_turn(self):
        """add_turn 快捷方法"""
        s = Scenario("S1", "测试", ScenarioType.GENERAL, "描述")
        s.add_turn(role="user", content="你好", expected_keywords=["你好"])
        self.assertEqual(len(s.turns), 1)
        self.assertEqual(s.turns[0].expected_keywords, ["你好"])

    def test_scenario_result_properties(self):
        """ScenarioResult 属性"""
        sr = ScenarioResult(
            scenario=Scenario("S1", "", ScenarioType.GENERAL, ""),
            actual_responses=["好"], turn_results=[], pass_count=0,
            total_checks=5, pass_rate=0.0,
            context_recall=None, security_breaches=0,
            summary="test",
        )
        self.assertEqual(sr.pass_rate, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
