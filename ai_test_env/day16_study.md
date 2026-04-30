# Day 16 — Playwright 浏览器自动化

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
