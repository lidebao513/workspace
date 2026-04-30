# AGENDA.md — AI 测试平台 · 日计划完整清单

> 覆盖 d1-d38（9 阶段 · 38 天）
> 总测试：627 passed, 19 skipped, 0 warnings
> 最后更新：2026-04-30

---

## 符号说明

| 标记 | 含义 |
|:----|:-----|
| 📖 | 学习文档（day{day}_study.md） |
| 🔧 | 工具模块（utils/d{day}_{name}.py） |
| 🧪 | 测试文件（tests/d{day}_test_{name}.py） |
| 🏗️ | 项目级文件 |
| ✅ | 已完成 |

---

## 第 1 周 — 基础建设

### D1 — API 客户端

- 📖 `day1_study.md`（26KB）
- 🔧 `utils/d1_api_client.py` — `AITestClient`：请求/响应/超时/错误处理
- 🧪 `tests/d1_test_client.py`（按 d1 惯例需排查实际文件）

### D2 — 参数化测试

- 📖 `day2_study.md`（27KB）
- 🧪 `tests/d2_test_params.py` — pytest parametrize 用例
- 说明：d2 是测试方法论的 day，无独立工具模块

### D3 — 错误分类器

- 📖 `day3_study.md`（31KB）
- 🔧 `utils/d3_error_classifier.py` — API 错误分类（超时/限流/无效Key等）
- 🧪 `tests/d3_test_error.py`（需排查实际文件）
- 话术：分时态（临时/持久）+ 域（通信/系统/业务）+ 严重程度

### D4 — 响应校验

- 📖 `day4_study.md`（32KB）
- 🔧 `utils/d4_response_validator.py` — 必填字段检查 + 类型验证
- 🧪 `tests/d4_test_request_format.py` — 请求格式验证

### D5 — Key 池管理器

- 📖 `day5_study.md`（44KB）
- 🔧 `utils/d5_key_manager.py` — `KeyPoolManager`：轮询/最少使用/权重调度
- 🧪 `tests/d5_test_key_manager.py` + `tests/d5_test_response_baseline.py`

---

## 第 2 周 — 质量评估

### D6 — 质量检查器

- 📖 `day6_study.md`（19KB）
- 🔧 `utils/d6_quality_checker.py` — `QualityChecker`：关键词/禁止词/冗余度/长度
- 🧪 `tests/d6_test_quality.py`

### D7 — 一致性检查器

- 📖 `day7_study.md`（20KB）
- 🔧 `utils/d7_consistency_checker.py` — 语义一致/矛盾检测
- 🧪 `tests/d7_test_consistency.py`

### D8 — 截断 & TC 测试（双模块）

- 📖 `day8_study.md`（12KB）+ `day8b_tc_study.md`（21KB）
- 🔧 `utils/d8_truncation_analyzer.py` — 截断检测（finish_reason/字符模式）
- 🔧 `utils/d8_tc_tester.py` — Tool Calling 测试
- 🧪 `tests/d8_test_truncation.py` + `tests/d8_test_tc.py`

### D8c — 格式验证

- 📖 无独立 day doc（格式检查属于 d8 质量子维度）
- 🔧 `utils/d8c_format_validator.py` — JSON/代码块/表格/Markdown 格式校验
- 🧪 `tests/d8c_test_format.py`

### D8d — 风格检查

- 📖 同上，格式检查子模块
- 🔧 `utils/d8d_style_checker.py` — 语气/人称/立场/情感倾向
- 🧪 `tests/d8d_test_style.py`

### D8e — 多语言测试

- 📖 同上，多语言子模块
- 🔧 `utils/d8e_multilingual_tester.py` — `LanguageDetector` / `MultilingualTester`
- 🧪 `tests/d8e_test_multilingual.py`

### D8f — 时效性测试

- 📖 同上，时效性子模块
- 🔧 `utils/d8f_timeliness_tester.py` — 时间感知/知识截止/过时信息
- 🧪 `tests/d8f_test_timeliness.py`

### D9 — LLM Judge

- 📖 `day9_study.md`（14KB）
- 🔧 `utils/d9_llm_judge.py` — `LLMJudge` + `JudgeResult`：多维度自动评分
- 🧪 `tests/d9_test_llm_judge.py`

### D10 — Schema 验证 + 流水线

- 📖 `day10_study.md`（16KB）
- 🔧 `utils/d10_schema_validator.py` — JSON Schema 校验
- 🔧 `utils/d10_pipeline_assessment.py` — 评分流水线
- 🧪 `tests/d10_test_schema.py` + `tests/d10_test_pipeline_assessment.py`

---

## 第 3 周 — 安全与高级测试

### D11 — 对话测试

- 📖 `day11_study.md`（17KB）
- 🔧 `utils/d11_conversation_tester.py` — `ConversationTester`：多轮上下文保持
- 🧪 `tests/d11_test_conversation.py`

### D12 — Prompt Injection（双模块）

- 📖 `day12_study.md`（16KB）
- 🔧 `utils/d12_injection_detector.py` — 单条注入检测
- 🔧 `utils/d12_prompt_injection_tester.py` — `PromptInjectionTester`：38 个攻击用例全量套件
- 🧪 `tests/d12_test_injection.py` + `tests/d12_test_prompt_injection.py`

### D13 — 鲁棒性测试

- 📖 `day13_study.md`（15KB）
- 🔧 `utils/d13_robustness_tester.py` — 空输入/超长/特殊字符/XSS
- 🧪 `tests/d13_test_robustness.py`

### D14 — 回归测试

- 📖 `day14_study.md`（14KB）
- 🔧 `utils/d14_regression_tester.py` — 功能/安全/性能回归套件
- 🧪 `tests/d14_test_regression.py`

### D15 — E2E 测试

- 📖 `day15_study.md`（13KB）
- 🔧 `utils/d15_e2e_tester.py` — 端到端链路测试
- 🧪 `tests/d15_test_e2e.py`

---

## 第 4 周 — 自动化

### D16 — 浏览器自动化

- 📖 `day16_study.md`（7KB）
- 🔧 `utils/d16_browser_checker.py` — Playwright 浏览器检查
- 🧪 `tests/d16_test_browser_checker.py`

### D17 — 分层管理

- 📖 `day17_study.md`（9KB）
- 🔧 `utils/d17_suite_manager.py` — Smoke/Regression/Security/E2E 分层
- 🧪 `tests/d17_test_suite_manager.py`

### D18 — CI/CD

- 📖 `day18_study.md`（7KB）
- 🔧 `utils/d18_ci_config_gen.py` — GitHub Actions 配置生成器
- 🧪 `tests/d18_test_ci_config_gen.py`

### D19 — 工具链集成

- 📖 `day19_study.md`（7KB）
- 🔧 `utils/d19_toolchain_integration.py` — Tox/Pre-commit 集成
- 🧪 `tests/d19_test_toolchain_integration.py`

### D20 — 数据管理

- 📖 `day20_study.md`（10KB）
- 🔧 `utils/d20_data_manager.py` — 模板填充/批量生成/脱敏
- 🧪 `tests/d20_test_data_manager.py`

---

## 第 5 周 — 性能与工程化

### D21 — CLI（run.py）

- 📖 `day21_study.md`（8KB）
- 🏗️ `run.py` — 6 个子命令（test/param/ci/quality/security/performance）
- 🧪 `tests/d21_test_run.py`

### D22 — 并发压测

- 📖 `day22_study.md`（6KB）
- 🔧 `utils/d22_load_tester.py` — `LoadTester`：稳态/阶梯/突发
- 🧪 `tests/d22_test_load_tester.py`

### D23 — 重试引擎

- 📖 `day23_study.md`（6KB）
- 🔧 `utils/d23_retry_engine.py` — 固定/线性/指数退避 + Jitter
- 🧪 `tests/d23_test_retry_engine.py`

### D24 — 熔断器

- 📖 `day24_study.md`（6KB）
- 🔧 `utils/d24_circuit_breaker.py` — 三态状态机 + 半开探测
- 🧪 `tests/d24_test_circuit_breaker.py`

### D25 — 错误体系

- 📖 `day25_study.md`（7KB）
- 🔧 `utils/d25_error_system.py` — 分级异常 + to_dict 序列化
- 🧪 `tests/d25_test_error_system.py`

---

## 第 6 周 — 实战项目

### D26 — Token 审计

- 📖 `day26_study.md`（5KB）
- 🔧 `utils/d26_token_auditor.py` — `TokenAuditor`：费用/异常/报表
- 🧪 `tests/d26_test_token_auditor.py`

### D27 — 全量运行器

- 📖 `day27_study.md`（5KB）
- 🔧 `utils/d27_full_runner.py` — 全量/分层运行 + JSON 日志
- 🧪 `tests/d27_test_full_runner.py`

### D28 — 报告聚合器

- 📖 `day28_study.md`（4KB）
- 🔧 `utils/d28_report_aggregator.py` — 模块稳定性/趋势
- 🧪 `tests/d28_test_report_aggregator.py`

### D29 — 仪表盘

- 📖 `day29_study.md`（4KB）
- 🔧 `utils/d29_dashboard.py` — 三色门禁/健康仪表盘
- 🧪 `tests/d29_test_dashboard.py`

### D30 — 综合验证

- 📖 `day30_study.md`（4KB）
- 🔧 `utils/d30_comprehensive.py` — 端到端自检/全验证
- 🧪 `tests/d30_test_comprehensive.py`

---

## Phase 1 — API 实战

### D31 — DeepSeek API 真调用

- 📖 `day31_study.md`（5KB）
- 🔧 `utils/d31_deepseek_tester.py` — 10 个预置 prompt + 安全检查 + 费用估算
- 🧪 `tests/d31_test_deepseek_tester.py`（12 tests）

### D32 — 质量评估实战

- 📖 `day32_study.md`（3KB）
- 🔧 `utils/d32_quality_eval.py` — QC+Judge+Schema 管道
- 🧪 `tests/d32_test_quality_eval.py`（9 tests）

### D33 — 审计+多语言+压测

- 📖 `day33_study.md`（3KB）
- 🔧 `utils/d33_integration.py` — 三合一
- 🧪 `tests/d33_test_integration.py`（7 tests）

---

## Phase 2 — 面试准备

### D34 — 面试 TOP 20

- 📖 `INTERVIEW_TOP20.md`（7KB）
- 🧪 `tests/d34_interview_test.py`（6 tests）

### D35 — 场景+系统设计

- 📖 `INTERVIEW_SCENARIOS.md`（5KB）

### D36 — 简历话术

- 📖 `INTERVIEW_STAR.md`（3KB）

---

## Phase 3 — 项目文档

### D37 — README

- 🏗️ `README.md`（4KB）

### D38 — 架构文档

- 🏗️ `ARCHITECTURE.md`（5KB）
- 🧪 `tests/d37_project_docs_test.py`（7 tests）

---

## 附录：文件汇总

### 📖 学习文档（34 份）

| 文件 | 大小 | 文件 | 大小 |
|:-----|:-----|:-----|:-----|
| day1_study.md | 26KB | day2_study.md | 27KB |
| day3_study.md | 31KB | day4_study.md | 32KB |
| day5_study.md | 44KB | day6_study.md | 19KB |
| day7_study.md | 20KB | day8_study.md | 12KB |
| day8b_tc_study.md | 21KB | day9_study.md | 14KB |
| day10_study.md | 16KB | day11_study.md | 17KB |
| day12_study.md | 16KB | day13_study.md | 15KB |
| day14_study.md | 14KB | day15_study.md | 13KB |
| day16_study.md | 7KB | day17_study.md | 9KB |
| day18_study.md | 7KB | day19_study.md | 7KB |
| day20_study.md | 10KB | day21_study.md | 8KB |
| day22_study.md | 6KB | day23_study.md | 6KB |
| day24_study.md | 6KB | day25_study.md | 7KB |
| day26_study.md | 5KB | day27_study.md | 5KB |
| day28_study.md | 4KB | day29_study.md | 4KB |
| day30_study.md | 4KB | day31_study.md | 5KB |
| day32_study.md | 3KB | day33_study.md | 3KB |

### 🔧 工具模块（38 个）

```
d1: api_client            d3: error_classifier         d4: response_validator
d5: key_manager           d6: quality_checker          d7: consistency_checker
d8: truncation_analyzer   d8: tc_tester                d8c: format_validator
d8d: style_checker        d8e: multilingual_tester     d8f: timeliness_tester
d9: llm_judge             d10: schema_validator        d10: pipeline_assessment
d11: conversation_tester  d12: injection_detector      d12: prompt_injection_tester
d13: robustness_tester    d14: regression_tester       d15: e2e_tester
d16: browser_checker      d17: suite_manager           d18: ci_config_gen
d19: toolchain_integrator d20: data_manager            d22: load_tester
d23: retry_engine         d24: circuit_breaker         d25: error_system
d26: token_auditor        d27: full_runner             d28: report_aggregator
d29: dashboard            d30: comprehensive           d31: deepseek_tester
d32: quality_eval         d33: integration
```

### 🧪 测试文件（40 个）

```
d2_test_params           d4_test_request_format    d5_test_key_manager
d5_test_response_baseline d6_test_quality          d7_test_consistency
d8_test_truncation       d8_test_tc               d8c_test_format
d8d_test_style           d8e_test_multilingual     d8f_test_timeliness
d9_test_llm_judge        d10_test_schema           d10_test_pipeline
d11_test_conversation    d12_test_injection        d12_test_prompt_injection
d13_test_robustness      d14_test_regression       d15_test_e2e
d16_test_browser         d17_test_suite_manager    d18_test_ci_config_gen
d19_test_toolchain       d20_test_data_manager     d21_test_run
d22_test_load_tester     d23_test_retry_engine     d24_test_circuit_breaker
d25_test_error_system    d26_test_token_auditor    d27_test_full_runner
d28_test_report_agg      d29_test_dashboard        d30_test_comprehensive
d31_test_deepseek        d32_test_quality_eval     d33_test_integration
d34_interview_test       d37_project_docs_test
```

### 🏗️ 项目级文件

```
run.py              README.md           ARCHITECTURE.md
PLAN_PHASE2.md      INTERVIEW_TOP20.md  INTERVIEW_SCENARIOS.md
INTERVIEW_STAR.md   AGENDA.md           pytest.ini
requirements.txt    ai_test_learning_plan_v3.md
```

---

## 下一步方向

d1-d38 已全部完成。如需继续扩展，参见下方方向：

| 方向 | 天数 | 起始 |
|:-----|:-----|:-----|
| LLMJudge 在线版 | 2 天 | D39 |
| 面试模拟器 | 2 天 | D54 |
| 分布式压测 | 3 天 | D41 |
| 更多模型接入 | 4 天 | D44 |
| Web 仪表盘 | 6 天 | D48 |
