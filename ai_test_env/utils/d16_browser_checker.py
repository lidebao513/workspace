"""
Day 16 (Week 4 Day 1) — Playwright 浏览器自动化

实现：
1. Playwright 浏览器管理器（安装检查 + headless/chromium/无痕模式）
2. AI 页面交互基类（定位策略 + 等待策略 + 截图 + 日志）
3. AI 页面巡检器（页面加载 + 可见性 + 元素状态 + 错误检查）
4. 适用于 BOSS直聘 / 各类 AI Chat 页面的自动化巡检

注意：Windows + Playwright 需要安装浏览器二进制文件。
      如果未安装，会优雅降级为模拟测试。
"""
from typing import List, Dict, Optional, Tuple, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import os
import re


# ---------------------------------------------------------------------------
# 浏览器管理器 — 安装检测 + 浏览器创建
# ---------------------------------------------------------------------------

class BrowserStatus(Enum):
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    UNKNOWN = "unknown"


class BrowserManager:
    """
    浏览器管理器

    功能：
    - 检测 Playwright 浏览器是否已安装
    - 管理浏览器实例（chromium / firefox / webkit）
    - 统一启动配置（headless / viewport / args）
    - 优雅降级（未安装时返回模拟实例）
    """

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._status = self._check_installation()

    def _check_installation(self) -> BrowserStatus:
        """检测 Playwright 是否可用"""
        try:
            import playwright
            return BrowserStatus.INSTALLED
        except ImportError:
            return BrowserStatus.NOT_INSTALLED

    def is_available(self) -> bool:
        return self._status == BrowserStatus.INSTALLED

    def launch(self, headless: bool = True, browser_type: str = "chromium",
               viewport: Optional[Dict] = None) -> Union['Browser', 'MockBrowser']:
        """
        启动浏览器。

        Args:
            headless: 是否无头模式
            browser_type: chromium / firefox / webkit
            viewport: 视口大小，默认 {"width": 1280, "height": 720}
        """
        if not self.is_available():
            return MockBrowser(headless=headless, browser_type=browser_type)

        import playwright.sync_api as pwsync

        self._playwright = pwsync.sync_playwright().start()
        browser_map = {
            "chromium": self._playwright.chromium,
            "firefox": self._playwright.firefox,
            "webkit": self._playwright.webkit,
        }
        launcher = browser_map.get(browser_type, self._playwright.chromium)

        launch_kwargs = {"headless": headless}
        if viewport:
            launch_kwargs["viewport"] = viewport

        self._browser = launcher.launch(**launch_kwargs)
        page = self._browser.new_page()
        if viewport:
            page.set_viewport_size(viewport)

        return page

    def close(self):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def status_report(self) -> Dict:
        return {
            "install_status": self._status.value,
            "browser_alive": self._browser is not None,
        }


# ---------------------------------------------------------------------------
# Mock Browser — 未安装 Playwright 时的模拟
# ---------------------------------------------------------------------------

class MockBrowser:
    """模拟浏览器，记录所有调用但不执行实际操作"""

    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        self.headless = headless
        self.browser_type = browser_type
        self._calls: List[Dict] = []
        self._url: str = ""
        self._title: str = "Mock Page"

    def goto(self, url: str, **kwargs):
        self._calls.append({"action": "goto", "url": url})
        self._url = url

    def wait_for_selector(self, selector: str, **kwargs):
        self._calls.append({"action": "wait_for_selector", "selector": selector})
        return MockElement(selector)

    def query_selector(self, selector: str):
        self._calls.append({"action": "query_selector", "selector": selector})
        return MockElement(selector)

    def query_selector_all(self, selector: str):
        self._calls.append({"action": "query_selector_all", "selector": selector})
        return [MockElement(selector)]

    def content(self) -> str:
        return "<html><body><h1>Mock Content</h1></body></html>"

    def title(self) -> str:
        return self._title

    @property
    def url(self) -> str:
        return self._url

    def screenshot(self, path: str = None, full_page: bool = True):
        self._calls.append({"action": "screenshot", "path": path})
        return b"mock_screenshot_bytes"

    def evaluate(self, expr: str) -> Any:
        return None

    def fill(self, selector: str, value: str):
        self._calls.append({"action": "fill", "selector": selector, "value": value[:20]})

    def click(self, selector: str):
        self._calls.append({"action": "click", "selector": selector})

    def close(self):
        self._calls.append({"action": "close"})

    def get_calls(self) -> List[Dict]:
        return self._calls


class MockElement:
    """模拟元素"""

    def __init__(self, selector: str):
        self._selector = selector
        self._visible = True
        self._enabled = True

    def is_visible(self) -> bool:
        return self._visible

    def is_enabled(self) -> bool:
        return self._enabled

    def text_content(self) -> str:
        return f"mock text for {self._selector}"

    def inner_text(self) -> str:
        return f"mock inner text for {self._selector}"

    def get_attribute(self, name: str) -> Optional[str]:
        return None

    def screenshot(self, path: str = None):
        return b"element_screenshot_bytes"


# ---------------------------------------------------------------------------
# AI 页面巡检器
# ---------------------------------------------------------------------------

class PageCheckType(Enum):
    LOAD = "load"                       # 页面加载
    VISIBILITY = "visibility"           # 元素可见性
    TEXT_CONTENT = "text_content"       # 文本内容检查
    ELEMENT_COUNT = "element_count"     # 元素数量检查
    SCREENSHOT = "screenshot"           # 截图
    LINK_CHECK = "link_check"           # 链接状态检查
    ERROR_CHECK = "error_check"         # 错误信息检查


@dataclass
class PageCheckItem:
    """单条页面检查项"""
    check_type: PageCheckType
    selector: str = ""
    expected_text: str = ""
    min_count: int = 0
    max_count: int = 999
    description: str = ""
    enabled: bool = True


@dataclass
class PageCheckResult:
    """页面检查结果"""
    item: PageCheckItem
    passed: bool
    actual_value: Any = None
    error_message: str = ""
    elapsed_ms: float = 0.0


@dataclass
class PageCheckReport:
    """页面检查汇总报告"""
    url: str
    results: List[PageCheckResult]
    total_checks: int
    passed: int
    failed: int
    pass_rate: float
    timestamp: str
    summary: str

    def display(self) -> str:
        lines = [
            f"Page Inspection Report",
            f"URL: {self.url}",
            f"Time: {self.timestamp}",
            f"Checks: {self.passed}/{self.total_checks} passed ({self.pass_rate:.0%})",
            f"Summary: {self.summary}",
            "",
            f"--- Details ---",
        ]
        for r in self.results:
            tag = "[OK]" if r.passed else "[!!]"
            desc = r.item.description or f"{r.item.check_type.value}: {r.item.selector}"
            detail = f" ({r.actual_value})" if r.actual_value is not None else ""
            lines.append(f"  {tag} {desc}{detail}")
            if r.error_message:
                lines.append(f"       Error: {r.error_message}")
        return "\n".join(lines)


class PageInspector:
    """
    AI 页面巡检器

    功能：
    - 对指定 URL 执行自动化页面检查
    - 支持多种检查类型（加载、可见性、文本、元素数量）
    - 截图留档
    - 生成巡检报告
    """

    def __init__(self, page):
        self._page = page

    def inspect(self, url: str,
                checks: List[PageCheckItem],
                screenshot_path: Optional[str] = None) -> PageCheckReport:
        """
        执行页面巡检。

        Args:
            url: 目标 URL
            checks: 检查项列表
            screenshot_path: 可选截图保存路径
        """
        start = datetime.now()
        results: List[PageCheckResult] = []

        for item in checks:
            if not item.enabled:
                continue

            try:
                result = self._execute_check(item)
            except Exception as e:
                result = PageCheckResult(item=item, passed=False,
                                        error_message=str(e))

            results.append(result)

        duration = (datetime.now() - start).total_seconds() * 1000
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        pass_rate = passed / max(total, 1)

        # 截图
        if screenshot_path:
            try:
                self._page.screenshot(path=screenshot_path)
            except Exception:
                pass

        if pass_rate >= 0.9:
            summary = f"[OK] 巡检通过率 {pass_rate:.0%} ({passed}/{total})"
        elif pass_rate >= 0.7:
            summary = f"[OK] 巡检需关注 ({pass_rate:.0%})"
        else:
            summary = f"[!!] 巡检未通过 ({pass_rate:.0%})"

        return PageCheckReport(
            url=url, results=results,
            total_checks=total, passed=passed, failed=failed,
            pass_rate=pass_rate,
            timestamp=datetime.now().isoformat(),
            summary=summary,
        )

    def _execute_check(self, item: PageCheckItem) -> PageCheckResult:
        check_start = datetime.now()

        if item.check_type == PageCheckType.LOAD:
            self._page.goto(url=item.selector or item.description,
                          wait_until="networkidle")
            title = self._page.title()
            passed = bool(title)
            return PageCheckResult(item=item, passed=passed,
                                  actual_value=title[:50] if title else "(empty)",
                                  elapsed_ms=self._elapsed(check_start))

        elif item.check_type == PageCheckType.VISIBILITY:
            el = self._page.query_selector(item.selector)
            if not el:
                return PageCheckResult(item=item, passed=False,
                                      error_message=f"元素未找到: {item.selector}",
                                      elapsed_ms=self._elapsed(check_start))
            visible = el.is_visible()
            return PageCheckResult(item=item, passed=visible,
                                  actual_value=visible,
                                  elapsed_ms=self._elapsed(check_start))

        elif item.check_type == PageCheckType.TEXT_CONTENT:
            el = self._page.query_selector(item.selector)
            if not el:
                return PageCheckResult(item=item, passed=False,
                                      error_message=f"元素未找到: {item.selector}",
                                      elapsed_ms=self._elapsed(check_start))
            text = (el.inner_text() or "").strip()
            if item.expected_text:
                passed = item.expected_text.lower() in text.lower()
            else:
                passed = bool(text)
            return PageCheckResult(item=item, passed=passed,
                                  actual_value=text[:80] if text else "(empty)",
                                  elapsed_ms=self._elapsed(check_start))

        elif item.check_type == PageCheckType.ELEMENT_COUNT:
            elements = self._page.query_selector_all(item.selector)
            count = len(elements)
            passed = item.min_count <= count <= item.max_count
            val = f"{count} (range: {item.min_count}-{item.max_count})"
            return PageCheckResult(item=item, passed=passed,
                                  actual_value=val,
                                  elapsed_ms=self._elapsed(check_start))

        elif item.check_type == PageCheckType.SCREENSHOT:
            data = self._page.screenshot(path=item.selector)
            passed = len(data) > 5
            return PageCheckResult(item=item, passed=passed,
                                  actual_value=f"{len(data)} bytes",
                                  elapsed_ms=self._elapsed(check_start))

        elif item.check_type == PageCheckType.LINK_CHECK:
            links = self._page.query_selector_all("a[href]")
            count = len(links)
            passed = count >= item.min_count
            return PageCheckResult(item=item, passed=passed,
                                  actual_value=f"{count} links found",
                                  elapsed_ms=self._elapsed(check_start))

        elif item.check_type == PageCheckType.ERROR_CHECK:
            content = self._page.content()
            error_patterns = ["error", "404", "500", "not found",
                              "系统错误", "页面丢失", "503"]
            found_errors = [p for p in error_patterns if p.lower() in content.lower()]
            passed = len(found_errors) == 0
            return PageCheckResult(item=item, passed=passed,
                                  actual_value=f"errors: {found_errors}" if found_errors else "no errors",
                                  elapsed_ms=self._elapsed(check_start))

        return PageCheckResult(item=item, passed=False,
                              error_message=f"Unknown check type: {item.check_type}",
                              elapsed_ms=self._elapsed(check_start))

    def _elapsed(self, start: datetime) -> float:
        return (datetime.now() - start).total_seconds() * 1000


# ---------------------------------------------------------------------------
# 高层 API — 一键巡检
# ---------------------------------------------------------------------------

class AIAppPageChecker:
    """
    AI 应用页面巡检器

    封装了常见的 AI Chat 页面巡检模板。
    可扩展适用于：DeepSeek Chat、ChatGPT、Kimi、百度文心等。
    """

    @staticmethod
    def create_default_checks(input_selector: str = "#chat-input",
                              send_selector: str = "#send-btn",
                              response_selector: str = ".chat-message") -> List[PageCheckItem]:
        """创建默认的 AI Chat 页面巡检检查清单"""
        return [
            PageCheckItem(PageCheckType.LOAD, description="页面加载"),
            PageCheckItem(PageCheckType.VISIBILITY, input_selector,
                         description="输入框可见"),
            PageCheckItem(PageCheckType.VISIBILITY, send_selector,
                         description="发送按钮可见"),
            PageCheckItem(PageCheckType.ELEMENT_COUNT, response_selector,
                         min_count=0, max_count=100,
                         description="聊天消息区域"),
            PageCheckItem(PageCheckType.ERROR_CHECK, description="错误检测"),
        ]

    def check_page(self, page, url: str,
                   checks: Optional[List[PageCheckItem]] = None) -> PageCheckReport:
        """对给定页面执行巡检"""
        inspector = PageInspector(page)
        if not checks:
            checks = self.create_default_checks()
        return inspector.inspect(url, checks)

    def check_chat_ui(self, page, url: str,
                      message: str = "Hello") -> Dict:
        """
        模拟一个完整的 Chat 交互流程并检查。
        - 打开页面
        - 输入消息
        - 发送
        - 检查是否有回复
        """
        results = {}
        inspector = PageInspector(page)

        # 1. 加载页面
        load_result = inspector.inspect(url, [
            PageCheckItem(PageCheckType.LOAD, description="Chat页面加载"),
            PageCheckItem(PageCheckType.VISIBILITY, "#chat-input",
                         description="输入框"),
            PageCheckItem(PageCheckType.ERROR_CHECK, description="页面错误"),
        ])
        results["load"] = load_result

        # 2. 输入 + 发送
        try:
            page.fill("#chat-input", message)
            page.click("#send-btn")
            results["send"] = {"action": "send_message", "message": message[:30]}
        except Exception as e:
            results["send"] = {"action": "send_message", "error": str(e)}

        # 3. 等待回复
        try:
            checks = [
                PageCheckItem(PageCheckType.VISIBILITY, ".chat-message:last-child",
                             description="最后一条消息可见"),
                PageCheckItem(PageCheckType.TEXT_CONTENT, ".chat-message:last-child",
                             min_count=0, max_count=0,
                             description="AI回复内容"),
            ]
            response_result = inspector.inspect(url, checks)
            results["response"] = response_result
        except Exception as e:
            results["response"] = {"error": str(e)}

        return results
