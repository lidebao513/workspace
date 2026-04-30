# Day 19 — 开源工具整合（Tox + Coverage + Sanity）

## 一、今日目标

> 学会整合 AI 测试项目的工程基础设施：Tox 多环境测试、Coverage 覆盖率门禁、Code Sanity 静态检查。

- 理解 Tox 如何管理多 Python 版本测试环境
- 掌握 Coverage 模块级阈值检查
- 学会 Code Sanity 硬编码泄露 / TODO 遗存检查
- 学会生成项目健康报告

---

## 二、核心设计

### Tox 配置

```
[tox]
envlist = py39, py310, py311
skip_missing_interpreters = True

[testenv]
deps = pytest, pytest-cov, pytest-html, openai, python-dotenv
commands = pytest tests/ --cov=utils --cov-report=xml

[coverage:run]
source = ai_test_env
omit = */tests/*, */__pycache__/*, */.tox/*

[coverage:report]
exclude_lines = pragma: no cover
```

### 覆盖率模块阈值

| 模块 | 目标 | 当前(mock) |
|------|------|-----------|
| api_client | >= 90% | 94% |
| key_manager | >= 90% | 95% |
| response_validator | >= 90% | 92% |
| quality_checker | >= 85% | 88% |
| prompt_injection_tester | >= 85% | 86% |
| e2e_tester | >= 75% | 78% |
| browser_checker | >= 75% | 76% |

### Code Sanity 检查项

| 检查项 | 检测内容 | 严重性 |
|--------|---------|--------|
| HARDCODED_KEY | `sk-xxx`, `ghp_xxx` 等硬编码密钥 | [!!] 高危 |
| TODO_REMAINING | TODO / FIXME 注释残留 | [!] 中危 |
| FILE_TOO_LARGE | 超过 500 行的文件 | [??] 低危 |
| TRAILING_NEWLINE | 文件末尾缺少换行符 | [??] 低危 |

### 健康评分公式

```
Score = min(Coverage × 50 + max(30 - issues × 3, 0) + CI_exists × 10, 100)
```

---

## 三、运行验证

```
29 passed in 0.13s
```

## 四、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/toolchain_integration.py` | Tox / Coverage / Sanity 集成 | [OK] |
| `tests/test_toolchain_integration.py` | 29 个测试 | [OK] 29/29 PASS |
| `day19_study.md` | 本篇文档 | [OK] 已完成 |

---

## 五、面试话术

**Tox 相关：**
"我们使用 Tox 管理多 Python 版本的测试环境。tox.ini 定义了 py39/py310/py311 三个环境，skip_missing_interpreters 确保 CI 中缺失的版本不报错。每个环境下跑 pytest-cov 生成覆盖率 XML。"

**Coverage 相关：**
"核心模块的覆盖率门禁我设置了 85%-90%，边缘模块 75%-80%。CI 中如果覆盖率低于阈值，门禁检查会直接失败。"

**Sanity 相关：**
"我们有一个 CodeSanityChecker 在每次 PR 时运行。它能检测到 sk-xxx 格式的硬编码 API Key——这是上线前的最后一道防线。"
