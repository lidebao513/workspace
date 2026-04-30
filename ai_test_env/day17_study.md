# Day 17 — pytest 参数化 + 分层管理

## 一、今日目标

> 学会用 TestSuiteManager 将 Week 1-4 的所有测试分层管理，并用参数化用例生成器创建组合测试。

- 理解测试分层（Smoke / Regression / Security / Performance / E2E）
- 掌握 TestSuiteManager 的过滤和报告能力
- 学会 ParametrizedCase 的单维/多维/CSV 参数化
- 理解 CompatRunner 对已有测试模块的兼容映射

---

## 二、核心设计

### 测试层级定义

| 层级 | 含义 | 包含模块 | CI 频率 |
|------|------|---------|---------|
| smoke | 冒烟测试 | key_manager, api_client, request_format | 每次提交 |
| regression | 回归测试 | quality, consistency, truncation, llm_judge | 每天 |
| security | 安全测试 | prompt_injection, robustness | 每天 |
| e2e | 端到端 | e2e_tester | 每周 |
| performance | 性能测试 | api_client (并发) | 每周 |

### 层间选择表达式

```bash
# 只跑冒烟
pytest -m "smoke"

# 跑安全和回归
pytest -m "security or regression"

# 跑冒烟但不跑浏览器
pytest -m "smoke and not browser"
```

### TestSuiteManager 结构
```
TestSuiteManager (20+ 内置用例)
  ├── filter(level, tag, module, priority)
  ├── get_level_counts() / get_tag_counts()
  ├── export_json() → 用例清单 JSON
  └── generate_coverage_report() → 覆盖率报告
```

### ParametrizedCase 参数化
```
单维度：temperature [0, 0.5, 1, 2] → 4 组合
多维度：temperature × top_p = 2 × 2 = 4 组合
CSV 导入：每列独立收集 → 做笛卡尔积
```

---

## 三、运行验证

```
37 passed in 0.05s
```

## 四、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/suite_manager.py` | 分层管理 + 参数化 | [OK] 已创建 |
| `tests/test_suite_manager.py` | 37 个测试 | [OK] 37/37 PASS |
| `day17_study.md` | 本篇文档 | [OK] 已完成 |
