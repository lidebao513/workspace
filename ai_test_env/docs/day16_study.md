# Day 16 — Playwright 浏览器自动化

## 学习目标

1. **理解 Playwright**：掌握 Playwright 在 AI 测试中的定位和用途
2. **掌握降级模式**：理解 MockBrowser 的适配器模式设计思想
3. **掌握检查类型**：熟练运用 7 种检查类型（LOAD/VISIBILITY/TEXT_CONTENT 等）
4. **构建巡检系统**：能够构建 AI Chat 页面的自动化巡检流水线
5. **集成告警机制**：实现异常检测和告警通知的完整闭环

---

## 一、今日目标

> 学会用 Playwright + 自定义巡检器对 AI 页面进行自动化检查，包括页面加载、元素状态、错误检测和截图留档。

- 理解 Playwright 在 AI 测试中的用途
- 掌握浏览器管理器（安装检测 + 降级策略）
- 学会 PageInspector 多种检查类型
- 能构建 AI Chat 页面自动化巡检

---

## 二、前置知识讲解

### 2.1 什么是 Playwright？

**一句话定义：** Playwright 是微软开源的浏览器自动化框架，核心功能是控制真实的 Chromium/Firefox/WebKit 浏览器执行操作。

**类比：** 就像一个机器人帮你操作浏览器——你可以命令它"打开这个网页"、"找到那个按钮"、"点击它"、"看看页面变成了什么"。

**对比 Selenium：**
| 维度 | Selenium | Playwright |
|------|----------|-----------|
| 浏览器支持 | 3 种 | 3 种（同内核） |
| 自动等待 | 需显式 wait | 内置自动等待 |
| API 风格 | 较老 | 现代 async/await |
| 安装 | webdriver | `playwright install` |
| 截图 | 支持 | 支持（更稳定） |

**面试话术：**
> "在 AI 产品测试中，Playwright 主要是用来做 AI 页面的自动化巡检。我们公司的 QA 团队用它每天早上自动打开 AI Chat 页面，检查输入框是否可见、发送按钮是否可用、页面有没有报错，截图留档。一旦检测到异常，自动在钉钉群里告警。这样我们能在用户投诉之前发现页面问题。"

---

### 2.2 为什么要降级模拟？

现实场景：你的测试环境没有安装 Playwright 浏览器二进制（`playwright install` 会下载 200MB+ 的浏览器），或者 CI 环境没有 GPU。

**降级策略：**
```
BrowserManager.launch()
  ├── Playwright 已安装 → 返回真实 Browser Page
  └── Playwright 未安装 → 返回 MockBrowser（模拟调用）
```

MockBrowser 记录所有调用但不执行真实操作，让代码在无浏览器环境下也能跑通测试。

### 2.3 检查类型一览

| 类型 | 含义 | 适合检测 |
|------|------|---------|
| LOAD | 页面加载 | 页面是否能打开 |
| VISIBILITY | 元素可见 | 输入框/按钮是否显示 |
| TEXT_CONTENT | 文本内容 | 标题/提示是否正常 |
| ELEMENT_COUNT | 元素数量 | 列表项是否过多/过少 |
| SCREENSHOT | 截图留档 | 视觉证据 |
| LINK_CHECK | 链接检查 | 页面超链接 |
| ERROR_CHECK | 错误检测 | 404/500/错误提示 |

---

## 三、代码设计

### 3.1 模块结构
```
BrowserManager               ← 浏览器管理
├── install check + launch
└── MockBrowser (降级)

PageInspector                ← 巡检引擎
├── 7 种检查类型
├── inspect() → Report
└── 耗时记录 + 截图

AIAppPageChecker             ← 高层封装
├── create_default_checks()
├── check_page()
└── check_chat_ui()
```

### 3.2 MockBrowser 设计模式
对于没有安装 Playwright 的环境，MockBrowser 替代真实 Page 对象。它实现了和 playwright Page 相同的接口（goto/query_selector/screenshot 等），但所有操作只是记录调用日志。

这是**适配器模式**的一个变种——对外暴露相同 API，对内返回模拟数据。

---

## 四、运行验证

```
test_browser_checker.py::TestBrowserManager::test_browser_status_report PASSED
test_browser_checker.py::TestBrowserManager::test_check_installation PASSED
test_browser_checker.py::TestBrowserManager::test_is_available PASSED
test_browser_checker.py::TestBrowserManager::test_launch_mock_when_not_installed PASSED
test_browser_checker.py::TestBrowserManager::test_mock_browser_attributes PASSED
test_browser_checker.py::TestBrowserManager::test_mock_browser_goto PASSED
test_browser_checker.py::TestBrowserManager::test_mock_browser_screenshot PASSED
test_browser_checker.py::TestBrowserManager::test_mock_element_properties PASSED
test_browser_checker.py::TestPageCheckModel::test_page_check_item_defaults PASSED
test_browser_checker.py::TestPageCheckModel::test_page_check_report_display PASSED
test_browser_checker.py::TestPageCheckModel::test_page_check_result PASSED
test_browser_checker.py::TestPageInspector::test_elapsed_ms_recorded PASSED
test_browser_checker.py::TestPageInspector::test_element_count_check PASSED
test_browser_checker.py::TestPageInspector::test_element_count_exceed PASSED
test_browser_checker.py::TestPageInspector::test_error_check_pass PASSED
test_browser_checker.py::TestPageInspector::test_inspect_all_checks PASSED
test_browser_checker.py::TestPageInspector::test_inspect_screenshot PASSED
test_browser_checker.py::TestPageInspector::test_link_check PASSED
test_browser_checker.py::TestPageInspector::test_load_check PASSED
test_browser_checker.py::TestPageInspector::test_screenshot_check PASSED
test_browser_checker.py::TestPageInspector::test_text_content_check PASSED
test_browser_checker.py::TestPageInspector::test_text_content_mismatch PASSED
test_browser_checker.py::TestPageInspector::test_unknown_check_type PASSED
test_browser_checker.py::TestPageInspector::test_visibility_check_found PASSED
test_browser_checker.py::TestAIAppPageChecker::test_check_chat_ui PASSED
test_browser_checker.py::TestAIAppPageChecker::test_check_page PASSED
test_browser_checker.py::TestAIAppPageChecker::test_custom_checks PASSED
test_browser_checker.py::TestAIAppPageChecker::test_default_checks_count PASSED

28 passed in 0.04s
```

## 五、工作中怎么用

### AI Chat 页面巡检脚本
```python
from utils.browser_checker import BrowserManager, AIAppPageChecker

manager = BrowserManager()
page = manager.launch(headless=True)
checker = AIAppPageChecker()

report = checker.check_page(page, "https://chat.deepseek.com")
print(report.display())

# 输出：
# Page Inspection Report
# URL: https://chat.deepseek.com
# Checks: 5/5 passed (100%)
#   [OK] 页面加载
#   [OK] 输入框可见
#   [OK] 发送按钮可见
#   [OK] 聊天消息区域
#   [OK] 错误检测

manager.close()
```

### 巡检集成到 CI
```
┌─────────┐    ┌─────────────┐    ┌──────────┐
│ 每日 8:00│───>│ Playwright  │───>│ 截图留档  │
│ Cron Trig│    │ 自动巡检     │    │          │
└─────────┘    └──────┬──────┘    └──────────┘
                      │
                      v
               ┌──────────────┐
               │ 检测到异常？  │──Yes──> 钉钉告警
               └──────────────┘
                      │ No
                      v
                  报告存档
```

## 六、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/browser_checker.py` | Playwright 浏览器自动化 + 巡检器 | [OK] 已创建 |
| `tests/test_browser_checker.py` | 28 个单元测试 | [OK] 28/28 PASS |
| `day16_study.md` | 本篇学习文档 | [OK] 已完成 |

---

## 面试题

### 面试题 1：Playwright 在 AI 测试中有哪些应用场景？

**答案：**

Playwright 在 AI 测试中主要有以下应用场景：

**1. 页面功能巡检**
- 检查 AI Chat 页面的核心元素（输入框、发送按钮、消息区域）是否可见和可用
- 验证页面加载时间和错误状态
- 监控页面可用性和用户体验

**2. UI 自动化测试**
- 自动执行登录、发送消息、接收回复等操作
- 验证多轮对话流程的正确性
- 测试边界条件下的 UI 响应

**3. 截图对比测试**
- 定期截图留档，记录页面状态
- 用于视觉回归测试，发现 UI 变化
- 生成测试报告的视觉证据

**4. 集成到 CI/CD**
- 每日定时执行页面巡检
- 检测到异常时自动告警
- 与监控平台集成实现持续监控

**5. 浏览器兼容性测试**
- 在 Chromium/Firefox/WebKit 三种浏览器上测试
- 确保 AI 产品在各浏览器上表现一致

### 面试题 2：如何设计一个可靠的浏览器自动化测试框架？

**答案：**

设计可靠的浏览器自动化测试框架需要考虑以下方面：

**1. 降级策略**
- Playwright 未安装时使用 MockBrowser 降级
- 保证测试在无浏览器环境也能运行
- 对外提供一致的 API 接口

**2. 错误处理机制**
- 捕获页面加载超时、元素未找到等异常
- 实现重试逻辑提高稳定性
- 详细的错误日志便于问题定位

**3. 页面检查类型**
- LOAD：页面加载状态检查
- VISIBILITY：元素可见性检查
- TEXT_CONTENT：文本内容匹配
- ELEMENT_COUNT：元素数量验证
- SCREENSHOT：截图留档
- LINK_CHECK：链接有效性检查
- ERROR_CHECK：错误状态检测

**4. 等待策略**
- 使用自动等待机制减少不稳定性
- 配置合理的超时时间
- 支持显式等待特定条件

**5. 报告与告警**
- 生成结构化的检查报告
- 支持截图附件
- 异常时触发告警通知

---

## 代码示例

### 浏览器管理器与页面巡检器实现

```python
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class CheckType(Enum):
    LOAD = "load"
    VISIBILITY = "visibility"
    TEXT_CONTENT = "text_content"
    ELEMENT_COUNT = "element_count"
    SCREENSHOT = "screenshot"
    LINK_CHECK = "link_check"
    ERROR_CHECK = "error_check"

class CheckStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"

@dataclass
class PageCheckItem:
    check_type: CheckType
    selector: str = ""
    expected_value: str = ""
    threshold: int = 0
    status: CheckStatus = CheckStatus.SKIP
    message: str = ""
    screenshot_path: str = ""

@dataclass
class PageCheckReport:
    url: str
    timestamp: str
    checks: List[PageCheckItem] = field(default_factory=list)
    passed_count: int = 0
    failed_count: int = 0
    total_count: int = 0
    pass_rate: float = 0.0

class MockBrowser:
    """降级浏览器模拟器"""
    
    def __init__(self):
        self.calls = []
    
    def goto(self, url: str):
        self.calls.append(f"goto:{url}")
        return {"url": url, "status": "loaded"}
    
    def query_selector(self, selector: str):
        self.calls.append(f"query_selector:{selector}")
        return {
            "visible": True,
            "text": "mock element",
            "count": 1
        }
    
    def screenshot(self, path: str = ""):
        self.calls.append(f"screenshot:{path}")
        return f"screenshot_saved_at_{path}"
    
    def evaluate(self, script: str):
        self.calls.append(f"evaluate:{script[:20]}")
        return {"error": None}

class BrowserManager:
    """浏览器管理器"""
    
    def __init__(self):
        self.playwright_available = self._check_playwright()
        self.browser = None
    
    def _check_playwright(self) -> bool:
        try:
            from playwright.sync_api import sync_playwright
            return True
        except ImportError:
            return False
    
    def launch(self, headless: bool = True):
        if self.playwright_available:
            from playwright.sync_api import sync_playwright
            p = sync_playwright().start()
            browser = p.chromium.launch(headless=headless)
            self.browser = browser
            return browser.new_page()
        else:
            return MockBrowser()
    
    def close(self):
        if self.browser and hasattr(self.browser, 'close'):
            self.browser.close()

class PageInspector:
    """页面巡检引擎"""
    
    def __init__(self):
        self.checks = []
    
    def add_check(self, check: PageCheckItem):
        self.checks.append(check)
    
    def inspect(self, page) -> PageCheckReport:
        results = []
        passed = 0
        failed = 0
        
        for check in self.checks:
            result = self._execute_check(page, check)
            results.append(result)
            if result.status == CheckStatus.PASS:
                passed += 1
            elif result.status == CheckStatus.FAIL:
                failed += 1
        
        total = len(results)
        return PageCheckReport(
            url=getattr(page, 'url', lambda: 'unknown')(),
            timestamp=datetime.now().isoformat(),
            checks=results,
            passed_count=passed,
            failed_count=failed,
            total_count=total,
            pass_rate=passed / total if total > 0 else 0.0
        )
    
    def _execute_check(self, page, check: PageCheckItem) -> PageCheckItem:
        result = PageCheckItem(
            check_type=check.check_type,
            selector=check.selector,
            expected_value=check.expected_value,
            threshold=check.threshold
        )
        
        try:
            if check.check_type == CheckType.LOAD:
                page.goto(check.selector)
                result.status = CheckStatus.PASS
                result.message = "Page loaded successfully"
            
            elif check.check_type == CheckType.VISIBILITY:
                element = page.query_selector(check.selector)
                if element and element.get("visible"):
                    result.status = CheckStatus.PASS
                    result.message = "Element is visible"
                else:
                    result.status = CheckStatus.FAIL
                    result.message = "Element not visible"
            
            elif check.check_type == CheckType.TEXT_CONTENT:
                element = page.query_selector(check.selector)
                if element and check.expected_value in element.get("text", ""):
                    result.status = CheckStatus.PASS
                    result.message = "Text content matches"
                else:
                    result.status = CheckStatus.FAIL
                    result.message = "Text content mismatch"
            
            elif check.check_type == CheckType.ELEMENT_COUNT:
                element = page.query_selector(check.selector)
                count = element.get("count", 0) if element else 0
                if count >= check.threshold:
                    result.status = CheckStatus.PASS
                    result.message = f"Element count: {count}"
                else:
                    result.status = CheckStatus.FAIL
                    result.message = f"Element count {count} < {check.threshold}"
            
            elif check.check_type == CheckType.SCREENSHOT:
                path = page.screenshot(check.selector or "screenshot.png")
                result.status = CheckStatus.PASS
                result.message = f"Screenshot saved: {path}"
                result.screenshot_path = str(path)
            
            elif check.check_type == CheckType.ERROR_CHECK:
                errors = page.evaluate("() => window.errors || []")
                if not errors:
                    result.status = CheckStatus.PASS
                    result.message = "No errors detected"
                else:
                    result.status = CheckStatus.FAIL
                    result.message = f"Errors found: {errors}"
            
        except Exception as e:
            result.status = CheckStatus.FAIL
            result.message = f"Check failed: {str(e)}"
        
        return result

# 使用示例
manager = BrowserManager()
page = manager.launch(headless=True)

inspector = PageInspector()
inspector.add_check(PageCheckItem(CheckType.LOAD, selector="https://example.com"))
inspector.add_check(PageCheckItem(CheckType.VISIBILITY, selector="#input-box"))
inspector.add_check(PageCheckItem(CheckType.TEXT_CONTENT, selector="h1", expected_value="Welcome"))
inspector.add_check(PageCheckItem(CheckType.SCREENSHOT, selector="screenshot.png"))
inspector.add_check(PageCheckItem(CheckType.ERROR_CHECK))

report = inspector.inspect(page)
print(f"Checks: {report.passed_count}/{report.total_count} passed ({report.pass_rate:.0%})")

for check in report.checks:
    status_icon = "✓" if check.status == CheckStatus.PASS else "✗"
    print(f"  [{status_icon}] {check.check_type.value}: {check.message}")

manager.close()
```

---

## 练习题

### 练习题 1：实现元素对比检查器

**要求：**
扩展 PageInspector，支持元素属性对比检查。

**步骤：**
1. 添加新的检查类型 ATTRIBUTE_COMPARE
2. 实现元素属性（disabled、placeholder、class 等）对比
3. 支持正则表达式匹配
4. 测试对比功能

### 练习题 2：实现页面性能监控

**要求：**
实现页面性能指标收集器。

**步骤：**
1. 收集页面加载时间、TTFB 等指标
2. 实现资源加载时间统计（JS/CSS/图片）
3. 生成性能报告
4. 设置性能阈值，超出时告警

### 练习题 3：实现分布式巡检调度器

**要求：**
实现一个支持多节点并行巡检的调度器。

**步骤：**
1. 设计巡检任务分发机制
2. 支持多浏览器并行执行
3. 收集并汇总各节点巡检结果
4. 生成统一的巡检报告

---
