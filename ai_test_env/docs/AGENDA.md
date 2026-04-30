# AGENDA.md — AI 测试平台 · 日计划完整清单

> 覆盖 d1-d38（9 阶段 · 38 天）
> 总测试：627 passed, 19 skipped, 0 warnings
> 最后更新：2026-04-30

---

## 符号说明

| 标记 | 含义 |
|:----|:-----|
| 📖 | 学习文档（`day{day}_study.md`，在 `docs/`） |
| 🔧 | 工具模块（`utils/d{day}_{name}.py`） |
| 🧪 | 测试文件（`tests/d{day}_test_{name}.py`） |
| 🏗️ | 项目级文件 |
| ✅ | 已完成 |

## 优先级说明

| 标签 | 含义 | 建议 |
|:----|:-----|:-----|
| 🟢 **看看就行** | 看一遍、跑一下测试即可 | 5-10 分钟 |
| 🟡 **手敲一遍** | 抄核心逻辑到白纸再检查 | 15-20 分钟 |
| 🔴 **脱稿能讲** | 必须能讲 5 分钟 | 先看 10 分钟 → 闭眼讲一遍 |

---

## 第 1 周 — 基础建设

### D1 — API 客户端 🟡 手敲

- 📖 `day1_study.md`（26KB）
- 🔧 `utils/d1_api_client.py` — `AITestClient`：请求/响应/超时/错误处理
- 🧪 `tests/d1_test_client.py`
- **手敲重点：** `chat()` 方法签名、超时处理、错误处理逻辑
- **面试话术：** "接口我封装了 AITestClient，支持超时设置和错误分类..."

### D2 — 参数化测试 🟢 看看

- 📖 `day2_study.md`（27KB）
- 🧪 `tests/d2_test_params.py` — pytest parametrize 用例
- **说明：** 纯方法论 day，无独立工具模块
- **建议：** 跑一次 pytest -k params 看输出

### D3 — 错误分类器 🟢 看看

- 📖 `day3_study.md`（31KB）
- 🔧 `utils/d3_error_classifier.py` — API 错误分类（超时/限流/无效Key等）
- 🧪 `tests/d3_test_error.py`
- **说明：** 逻辑简单，分时态 + 域 + 严重程度
- **建议：** 跑下测试知道会用即可

### D4 — 响应校验 🟢 看看

- 📖 `day4_study.md`（32KB）
- 🔧 `utils/d4_response_validator.py` — 必填字段检查 + 类型验证
- 🧪 `tests/d4_test_request_format.py`
- **说明：** 字段校验逻辑简单，知道有工具类即可

### D5 — Key 池管理器 🟡 手敲

- 📖 `day5_study.md`（44KB）
- 🔧 `utils/d5_key_manager.py` — `KeyPoolManager`：轮询/最少使用/权重调度
- 🧪 `tests/d5_test_key_manager.py` + `tests/d5_test_response_baseline.py`
- **手敲重点：** 3 种调度策略 + `get_next_key()` 逻辑
- **面试话术：** "多个 API Key 通过 KeyPoolManager 轮换，支持自动降级..."

---

## 第 2 周 — 质量评估

### D6 — 质量检查器 🔴 脱稿能讲

- 📖 `day6_study.md`（19KB）
- 🔧 `utils/d6_quality_checker.py` — `QualityChecker`：关键词/禁止词/冗余度/长度
- 🧪 `tests/d6_test_quality.py`
- **手敲重点：** `check()` 方法、4 个维度权重
- **脱稿练习：** "我评估质量从 4 个维度：关键词覆盖（是否包含要点）、禁止词检查（是否泄漏）、长度完整度（是否截断）、冗余度（是否车轱辘话）"
- **面试必问：** "你们怎么判断一个回答好不好？"

### D7 — 一致性检查器 🟡 手敲

- 📖 `day7_study.md`（20KB）
- 🔧 `utils/d7_consistency_checker.py` — 语义一致/矛盾检测
- 🧪 `tests/d7_test_consistency.py`
- **手敲重点：** 矛盾检测的核心正则/模式匹配逻辑
- **场景题素材：** 多轮对话的上下文保持

### D8 — 截断 & TC 测试（双模块）🟢 看看

- 📖 `day8_study.md`（12KB）+ `day8b_tc_study.md`（21KB）
- 🔧 `utils/d8_truncation_analyzer.py` — 截断检测（finish_reason/字符模式）
- 🔧 `utils/d8_tc_tester.py` — Tool Calling 测试
- 🧪 `tests/d8_test_truncation.py` + `tests/d8_test_tc.py`
- **说明：** 截断检测有用但简单；TC 测试需要环境，先了解

### D8c — 格式验证 🟢 看看

- 🔧 `utils/d8c_format_validator.py` — JSON/代码块/表格/Markdown 格式校验
- 🧪 `tests/d8c_test_format.py`

### D8d — 风格检查 🟢 看看

- 🔧 `utils/d8d_style_checker.py` — 语气/人称/立场/情感倾向
- 🧪 `tests/d8d_test_style.py`

### D8e — 多语言测试 🟢 看看

- 🔧 `utils/d8e_multilingual_tester.py` — `LanguageDetector` / `MultilingualTester`
- 🧪 `tests/d8e_test_multilingual.py`

### D8f — 时效性测试 🟢 看看

- 🔧 `utils/d8f_timeliness_tester.py` — 时间感知/知识截止/过时信息
- 🧪 `tests/d8f_test_timeliness.py`

### D9 — LLM Judge 🔴 脱稿能讲

- 📖 `day9_study.md`（14KB）
- 🔧 `utils/d9_llm_judge.py` — `LLMJudge` + `JudgeResult`：多维度自动评分
- 🧪 `tests/d9_test_llm_judge.py`
- **手敲重点：** `JudgeResult` 的字段（scores/weighted_score/comment）
- **脱稿练习：** "用 LLM 评 LLM 的核心是多维加权：relevance 0.4 + completeness 0.3 + fluency 0.3..."
- **面试必问：** "你叫 AI 评 AI，能信吗？" → 回答：趋势监控 + 人工复审异常值

### D10 — Schema 验证 + 流水线 🟢 看看

- 📖 `day10_study.md`（16KB）
- 🔧 `utils/d10_schema_validator.py` — JSON Schema 校验
- 🔧 `utils/d10_pipeline_assessment.py` — 评分流水线
- 🧪 `tests/d10_test_schema.py` + `tests/d10_test_pipeline_assessment.py`

---

## 第 3 周 — 安全与高级测试

### D11 — 对话测试 🟢 看看

- 📖 `day11_study.md`（17KB）
- 🔧 `utils/d11_conversation_tester.py` — `ConversationTester`：多轮上下文保持
- 🧪 `tests/d11_test_conversation.py`

### D12 — Prompt Injection 🟡 手敲

- 📖 `day12_study.md`（16KB）
- 🔧 `utils/d12_injection_detector.py` — 单条注入检测
- 🔧 `utils/d12_prompt_injection_tester.py` — `PromptInjectionTester`：38 个攻击用例全量套件
- 🧪 `tests/d12_test_injection.py` + `tests/d12_test_prompt_injection.py`
- **手敲重点：** InjectionDetector 的检测核心逻辑
- **面试话术：** "我做了 38 个攻击用例，分角色泄露、忽略指令、越权执行三类..."

### D13 — 鲁棒性测试 🟢 看看

- 📖 `day13_study.md`（15KB）
- 🔧 `utils/d13_robustness_tester.py` — 空输入/超长/特殊字符/XSS
- 🧪 `tests/d13_test_robustness.py`
- **说明：** 边界场景知道分类即可

### D14 — 回归测试 🟢 看看

- 📖 `day14_study.md`（14KB）
- 🔧 `utils/d14_regression_tester.py` — 功能/安全/性能回归套件
- 🧪 `tests/d14_test_regression.py`

### D15 — E2E 测试 🟢 看看

- 📖 `day15_study.md`（13KB）
- 🔧 `utils/d15_e2e_tester.py` — 端到端链路测试
- 🧪 `tests/d15_test_e2e.py`

---

## 第 4 周 — 自动化

### D16 — 浏览器自动化 🟢 看看

- 📖 `day16_study.md`（7KB）
- 🔧 `utils/d16_browser_checker.py` — Playwright 浏览器检查
- 🧪 `tests/d16_test_browser_checker.py`
- **说明：** 需要 Playwright 环境，暂时只看

### D17 — 分层管理 🟡 手敲

- 📖 `day17_study.md`（9KB）
- 🔧 `utils/d17_suite_manager.py` — Smoke/Regression/Security/E2E 分层
- 🧪 `tests/d17_test_suite_manager.py`
- **手敲重点：** 分层设计、RunLevel 枚举
- **面试话术：** "我分了 5 层：smoke（commit 前）、regression（每日）、security（每日）、e2e（每周）、full（全量）"

### D18 — CI/CD 🟢 看看

- 📖 `day18_study.md`（7KB）
- 🔧 `utils/d18_ci_config_gen.py` — GitHub Actions 配置生成器
- 🧪 `tests/d18_test_ci_config_gen.py`

### D19 — 工具链集成 🟢 看看

- 📖 `day19_study.md`（7KB）
- 🔧 `utils/d19_toolchain_integration.py` — Tox/Pre-commit 集成
- 🧪 `tests/d19_test_toolchain_integration.py`

### D20 — 数据管理 🟢 看看

- 📖 `day20_study.md`（10KB）
- 🔧 `utils/d20_data_manager.py` — 模板填充/批量生成/脱敏
- 🧪 `tests/d20_test_data_manager.py`

---

## 第 5 周 — 性能与工程化

### D21 — CLI（run.py）🟢 看看

- 📖 `day21_study.md`（8KB）
- 🏗️ `run.py` — 6 个子命令（test/param/ci/quality/security/performance）
- 🧪 `tests/d21_test_run.py`
- **建议：** 知道 6 个命令怎么用即可

### D22 — 并发压测 🟡 手敲

- 📖 `day22_study.md`（6KB）
- 🔧 `utils/d22_load_tester.py` — `LoadTester`：稳态/阶梯/突发
- 🧪 `tests/d22_test_load_tester.py`
- **手敲重点：** 三种压测模式、百分位统计（P50/P95/P99）
- **面试话术：** "关注 P50/P95/P99，不是平均值——平均值掩盖长尾"

### D23 — 重试引擎 🔴 脱稿能讲

- 📖 `day23_study.md`（6KB）
- 🔧 `utils/d23_retry_engine.py` — 固定/线性/指数退避 + Jitter
- 🧪 `tests/d23_test_retry_engine.py`
- **手敲重点：** 三种策略、Decorrelated Jitter 公式
- **脱稿练习：** "指数退避 + Jitter 是最实用的——每次重试间隔翻倍，加上随机偏移防止惊群效应..."

### D24 — 熔断器 🔴 脱稿能讲

- 📖 `day24_study.md`（6KB）
- 🔧 `utils/d24_circuit_breaker.py` — 三态状态机 + 半开探测
- 🧪 `tests/d24_test_circuit_breaker.py`
- **手敲重点：** 三态状态机（Closed → Open → Half-Open）
- **脱稿练习：** "三态状态机：Closed 正常运行 → Open 断开 30 秒 → Half-Open 试一个请求，成功就恢复..."
- **面试必问：** "重试和熔断有什么区别？" → 重试是短层（秒级），熔断是长层（分钟级）

### D25 — 错误体系 🟢 看看

- 📖 `day25_study.md`（7KB）
- 🔧 `utils/d25_error_system.py` — 分级异常 + to_dict 序列化
- 🧪 `tests/d25_test_error_system.py`

---

## 第 6 周 — 实战项目

### D26 — Token 审计 🟡 手敲

- 📖 `day26_study.md`（5KB）
- 🔧 `utils/d26_token_auditor.py` — `TokenAuditor`：费用/异常/报表
- 🧪 `tests/d26_test_token_auditor.py`
- **手敲重点：** `record_call()`、异常检测逻辑
- **面试话术：** "每天记录调用量和费用，检测突增/突降/持续增长三种异常"

### D27 — 全量运行器 🔴 脱稿能讲

- 📖 `day27_study.md`（5KB）
- 🔧 `utils/d27_full_runner.py` — 全量/分层运行 + JSON 日志
- 🧪 `tests/d27_test_full_runner.py`
- **手敲重点：** RunLevel 枚举、各层运行时间
- **脱稿练习：** "smoke 15 秒 → regression 30 秒 → security 10 秒 → e2e 15 秒 → full 2.5 分钟"
- **面试必问：** "你们怎么确保测试不拖慢开发？"

### D28 — 报告聚合器 🟢 看看

- 📖 `day28_study.md`（4KB）
- 🔧 `utils/d28_report_aggregator.py` — 模块稳定性/趋势
- 🧪 `tests/d28_test_report_aggregator.py`

### D29 — 仪表盘 🟢 看看

- 📖 `day29_study.md`（4KB）
- 🔧 `utils/d29_dashboard.py` — 三色门禁/健康仪表盘
- 🧪 `tests/d29_test_dashboard.py`

### D30 — 综合验证 🟢 看看

- 📖 `day30_study.md`（4KB）
- 🔧 `utils/d30_comprehensive.py` — 端到端自检/全验证
- 🧪 `tests/d30_test_comprehensive.py`

---

## Phase 1 — API 实战

### D31 — DeepSeek API 真调用 🟢 看看

- 📖 `day31_study.md`（5KB）
- 🔧 `utils/d31_deepseek_tester.py` — 10 个预置 prompt + 安全检查 + 费用估算
- 🧪 `tests/d31_test_deepseek_tester.py`（12 tests）
- **说明：** 需要 API Key 才能跑真调用，了解管道设计即可
- **建议：** 有兴趣时配 Key 跑一次 `python utils/d31_deepseek_tester.py`

### D32 — 质量评估实战 🟢 看看

- 📖 `day32_study.md`（3KB）
- 🔧 `utils/d32_quality_eval.py` — QC+Judge+Schema 管道
- 🧪 `tests/d32_test_quality_eval.py`（9 tests）

### D33 — 审计+多语言+压测 🟢 看看

- 📖 `day33_study.md`（3KB）
- 🔧 `utils/d33_integration.py` — 三合一
- 🧪 `tests/d33_test_integration.py`（7 tests）

---

## Phase 2 — 面试准备

### D34 — 面试 TOP 20 🔴 脱稿能讲

- 📖 `docs/INTERVIEW_TOP20.md`（7KB）
- 🧪 `tests/d34_interview_test.py`（6 tests）
- **建议：** 每天练 3 题，一题 5 分钟闭眼讲
- **重点：** d6（质量）、d9（Judge）、d23（重试）、d24（熔断）、d12（安全）

### D35 — 场景+系统设计 🟡 手敲

- 📖 `docs/INTERVIEW_SCENARIOS.md`（5KB）
- **建议：** 模拟面试场景问自己，"如果...怎么办"

### D36 — 简历话术 🟡 手敲

- 📖 `docs/INTERVIEW_STAR.md`（3KB）
- **建议：** 写自己版本的 STAR 故事

---

## Phase 3 — 项目文档

### D37 — README 🟢 看看

- 🏗️ `docs/README.md` → `README.md`（根目录副本）

### D38 — 架构文档 🟢 看看

- 🏗️ `docs/ARCHITECTURE.md`（5KB）
- 🧪 `tests/d37_project_docs_test.py`（7 tests）

---

## 学习路线建议

### 🎯 面试冲刺路线（~7 天）

按优先级排序：

| 排序 | Day | 优先级 | 时间 |
|:----|:----|:-------|:-----|
| 1 | D6 | 🔴 脱稿 | 15min |
| 2 | D9 | 🔴 脱稿 | 15min |
| 3 | D23-D24 | 🔴 脱稿 | 20min |
| 4 | D27 | 🔴 脱稿 | 15min |
| 5 | D5 D7 D12 | 🟡 手敲 | 30min |
| 6 | D22 D26 | 🟡 手敲 | 20min |
| 7 | D34-D36 | 🔴 话术 | 30min |

总时：约 7 天 × 每天 1-2 小时

### 🧠 深度掌握路线（~14 天）

从上往下按日顺序：

1. 🟡 D1 → 🟡 D5 → 🔴 D6 → 🟡 D7 → 🔴 D9
2. 🟡 D12 → 🟡 D17 → 🟡 D22 → 🔴 D23 → 🔴 D24
3. 🟡 D26 → 🔴 D27 → 🟢 其他
4. D34-D36 面试准备

---

## 附录：文件汇总 （略，见 docs/ 目录）
