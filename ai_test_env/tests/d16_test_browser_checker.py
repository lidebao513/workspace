"""
Day 16 (Week 4 Day 1) — Playwright 浏览器自动化 单元测试

覆盖：
1. BrowserManager 安装检测 + launch + 降级
2. MockBrowser / MockElement 模拟浏览器
3. PageInspector 各种检查类型
4. AIAppPageChecker 默认检查 + Chat 交互
"""
import sys
import os
import unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.d16_browser_checker import (
    BrowserManager, BrowserStatus, MockBrowser, MockElement,
    PageCheckItem, PageCheckResult, PageCheckType, PageCheckReport,
    PageInspector, AIAppPageChecker,
)


class TestBrowserManager(unittest.TestCase):
    """浏览器管理器"""

    def setUp(self):
        self.bm = BrowserManager()

    def test_check_installation(self):
        """检测 Playwright 安装状态"""
        status = self.bm._check_installation()
        self.assertIn(status, [BrowserStatus.INSTALLED, BrowserStatus.NOT_INSTALLED])

    def test_is_available(self):
        """is_available 返回 bool"""
        self.assertIsInstance(self.bm.is_available(), bool)

    def test_launch_mock_when_not_installed(self):
        """未安装时降级为 MockBrowser"""
        browser = self.bm.launch()
        self.assertIsInstance(browser, MockBrowser)

    def test_mock_browser_attributes(self):
        """MockBrowser 属性"""
        mb = MockBrowser(headless=False, browser_type="firefox")
        self.assertFalse(mb.headless)
        self.assertEqual(mb.browser_type, "firefox")

    def test_mock_browser_goto(self):
        """MockBrowser.goto 记录调用"""
        mb = MockBrowser()
        mb.goto("https://example.com")
        self.assertIn("goto", [c["action"] for c in mb.get_calls()])

    def test_mock_browser_screenshot(self):
        """MockBrowser.screenshot 返回字节"""
        mb = MockBrowser()
        data = mb.screenshot()
        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 0)

    def test_mock_element_properties(self):
        """MockElement 默认可见且启用"""
        el = MockElement("#test")
        self.assertTrue(el.is_visible())
        self.assertTrue(el.is_enabled())
        self.assertIn("test", el.text_content())

    def test_browser_status_report(self):
        """status_report 输出格式"""
        report = self.bm.status_report()
        self.assertIn("install_status", report)
        self.assertIn("browser_alive", report)


class TestPageCheckModel(unittest.TestCase):
    """页面检查模型"""

    def test_page_check_item_defaults(self):
        """PageCheckItem 默认值"""
        item = PageCheckItem(PageCheckType.LOAD)
        self.assertTrue(item.enabled)
        self.assertEqual(item.min_count, 0)
        self.assertEqual(item.max_count, 999)

    def test_page_check_result(self):
        """PageCheckResult 基础"""
        item = PageCheckItem(PageCheckType.VISIBILITY, "#btn")
        result = PageCheckResult(item=item, passed=True, actual_value=True)
        self.assertTrue(result.passed)

    def test_page_check_report_display(self):
        """检查报告可读"""
        item = PageCheckItem(PageCheckType.LOAD, description="Page Load")
        result = PageCheckResult(item=item, passed=True)
        report = PageCheckReport(
            url="https://example.com", results=[result],
            total_checks=1, passed=1, failed=0, pass_rate=1.0,
            timestamp="2024-01-01", summary="[OK] Pass",
        )
        display = report.display()
        self.assertIn("Page Inspection Report", display)
        self.assertIn("100%", display)


class TestPageInspector(unittest.TestCase):
    """页面巡检器"""

    def setUp(self):
        self.page = MockBrowser()
        self.inspector = PageInspector(self.page)

    def test_load_check(self):
        """页面加载检查"""
        item = PageCheckItem(PageCheckType.LOAD, description="https://example.com")
        result = self.inspector._execute_check(item)
        self.assertTrue(result.passed)

    def test_visibility_check_found(self):
        """可见性 — 模拟元素总是可见"""
        item = PageCheckItem(PageCheckType.VISIBILITY, "#btn")
        result = self.inspector._execute_check(item)
        self.assertTrue(result.passed)

    def test_text_content_check(self):
        """文本内容检查"""
        item = PageCheckItem(PageCheckType.TEXT_CONTENT, "#title",
                            expected_text="mock")
        result = self.inspector._execute_check(item)
        self.assertTrue(result.passed)

    def test_text_content_mismatch(self):
        """文本内容不匹配"""
        item = PageCheckItem(PageCheckType.TEXT_CONTENT, "#title",
                            expected_text="NOT_IN_MOCK")
        result = self.inspector._execute_check(item)
        self.assertFalse(result.passed)

    def test_element_count_check(self):
        """元素数量检查"""
        item = PageCheckItem(PageCheckType.ELEMENT_COUNT, ".item",
                            min_count=0, max_count=5)
        result = self.inspector._execute_check(item)
        self.assertTrue(result.passed)

    def test_element_count_exceed(self):
        """元素数量超出上限"""
        item = PageCheckItem(PageCheckType.ELEMENT_COUNT, ".item",
                            min_count=10, max_count=20)
        result = self.inspector._execute_check(item)
        self.assertFalse(result.passed)

    def test_screenshot_check(self):
        """截图检查"""
        item = PageCheckItem(PageCheckType.SCREENSHOT, "test_screenshot.png")
        result = self.inspector._execute_check(item)
        self.assertTrue(result.passed)

    def test_link_check(self):
        """链接检查"""
        item = PageCheckItem(PageCheckType.LINK_CHECK, min_count=0)
        result = self.inspector._execute_check(item)
        self.assertTrue(result.passed)

    def test_error_check_pass(self):
        """无错误"""
        item = PageCheckItem(PageCheckType.ERROR_CHECK)
        result = self.inspector._execute_check(item)
        self.assertTrue(result.passed)

    def test_inspect_all_checks(self):
        """执行完整巡检"""
        checks = [
            PageCheckItem(PageCheckType.LOAD, description="https://example.com"),
            PageCheckItem(PageCheckType.VISIBILITY, "#chat-input"),
            PageCheckItem(PageCheckType.TEXT_CONTENT, "#title"),
            PageCheckItem(PageCheckType.SCREENSHOT),
            PageCheckItem(PageCheckType.ERROR_CHECK),
        ]
        report = self.inspector.inspect("https://example.com", checks)
        self.assertGreaterEqual(report.pass_rate, 0.8)

    def test_inspect_screenshot(self):
        """带截图的巡检"""
        checks = [
            PageCheckItem(PageCheckType.LOAD, description="https://example.com"),
        ]
        report = self.inspector.inspect("https://example.com", checks,
                                       screenshot_path="test_screenshot.png")
        self.assertIn("Page Inspection Report", report.display())

    def test_unknown_check_type(self):
        """未知检查类型"""
        item = PageCheckItem("unknown_type", description="unknown")
        result = self.inspector._execute_check(item)
        self.assertFalse(result.passed)
        self.assertIn("Unknown check type", result.error_message)

    def test_elapsed_ms_recorded(self):
        """检查耗时字段存在"""
        item = PageCheckItem(PageCheckType.LOAD, description="https://example.com")
        result = self.inspector._execute_check(item)
        self.assertIsNotNone(result.elapsed_ms)


class TestAIAppPageChecker(unittest.TestCase):
    """高层 AI 页面巡检"""

    def setUp(self):
        self.page = MockBrowser()
        self.checker = AIAppPageChecker()

    def test_default_checks_count(self):
        """默认检查项数量"""
        checks = self.checker.create_default_checks()
        self.assertEqual(len(checks), 5)

    def test_check_page(self):
        """页面巡检"""
        report = self.checker.check_page(self.page, "https://chat.example.com")
        self.assertIsInstance(report, PageCheckReport)
        self.assertGreater(report.passed, 0)

    def test_check_chat_ui(self):
        """完整的 Chat 交互巡检"""
        results = self.checker.check_chat_ui(self.page,
                                            "https://chat.example.com",
                                            message="What is AI?")
        self.assertIn("load", results)

    def test_custom_checks(self):
        """自定义检查项"""
        custom = [
            PageCheckItem(PageCheckType.LOAD, description="https://example.com"),
        ]
        report = self.checker.check_page(self.page, "https://example.com",
                                        checks=custom)
        self.assertEqual(report.total_checks, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
