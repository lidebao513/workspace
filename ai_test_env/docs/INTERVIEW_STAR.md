# AI 测试面试 — 简历话术 + 项目亮点

---

## 一、简历项目描述

### 中文版（1-2 行版）

> **AI 测试平台** — 自建 34 模块测试框架，覆盖 API 客户端、质量评估、安全检测、性能压测、全量运行、报告聚合。586 测试通过，支持一键全量运行和仪表盘预警。

### 中文版（3-5 行版）

> **AI 测试平台**
>
> 面向大模型 API 的系统化测试框架，覆盖质量、安全、性能三个维度。
> - 34 个工具模块，30 天持续建设
> - 分层测试（smoke/regression/security/e2e/full）+ 自动全量运行
> - 多语言/时效性/鲁棒性/对抗攻击等专项测试
> - 实时 Token 审计 + 质量门禁仪表盘
> - 全部 586 测试通过，离线可运行

### English Version

> **AI Testing Platform**
>
> Built a comprehensive testing framework for LLM APIs covering quality, security, and performance.
> - 34 independent modules organized into quality assessment, security testing, load testing, and reporting
> - Multi-layer test runner (smoke/regression/security/e2e/full) with JSON logging
> - Specialized tests: multilingual, timeliness, robustness, prompt injection
> - Token auditor for cost tracking with anomaly detection
> - Dashboard with pass rate gating and health monitoring
> - 586 passing tests, runs entirely offline

---

## 二、STAR 话术（3 条）

### STAR 1：从零搭建 AI 测试平台

- **Situation**：团队引入大模型 API，但缺乏系统化的测试方案。人工测试效率低、重复性高。
- **Task**：搭建一个覆盖质量、安全、性能的自动化测试框架。
- **Action**：
  - 从 API 客户端开始，逐步扩展到 34 个模块
  - 每个模块独立可测，通过 JSON 日志解耦
  - 设计 5 层运行策略：smoke → regression → security → e2e → full
  - 集成报告聚合和仪表盘预警
- **Result**：586 测试通过，30 天完成从零到全量覆盖。PR 合并前 3 分钟跑完 smoke 层，不需要人工逐个检查。

### STAR 2：从离线 mock 到真实 API 验证

- **Situation**：开发阶段只有离线 mock，无法验证真实 API 兼容性。
- **Task**：验证框架在真实 API 环境中能否正常工作。
- **Action**：
  - 写了一个 DeepSeek API 真调用入口（d31）
  - 10 条测试用例覆盖中英日、长上下文、角色约束
  - 把真实回复接回质量评估管道（d32）
  - 用 TokenAuditor 记录真实费用（d33）
- **Result**：全部 < 0.01 元。验证了框架在线下线下都能跑。

### STAR 3：跨模块调试 — 修复性能压测的精度问题

- **Situation**：d22 压测模块的耗时统计总是 0.0 秒。
- **Task**：找出原因并修复。
- **Action**：
  - 排查发现 `time.time()` 精度不够 — 毫秒级耗时被截断为 0
  - 替换为 `time.perf_counter()`（纳秒级精度）
  - 更新了 2 个测试用例验证修复
  - 顺便检查了 d23/d24 有没有类似问题
- **Result**：压测报告的 P50/P95/P99 百分位准确可用了。这暴露了毫秒级精度在现代硬件上的重要性。

---

## 三、项目亮点 TOP 5

| # | 亮点 | 面试话术 |
|:--|:-----|---------|
| 1 | **586 测试全部通过，0 warnings** | "30 天持续建设，每加一个模块都保证已有测试不挂。0 warnings 说明代码质量干净。" |
| 2 | **分层运行：smoke 3 分钟，full 2.5 分钟** | "不用每次跑全部 600 个测试——改一行代码只跑当前模块，提交 PR 跑 smoke，每日凌晨跑 full。" |
| 3 | **从 mock 到真实 API 无缝切换** | "所有质量/安全/性能模块离线可跑，D31 验证真实 API 也只改了数据来源。架构设计上数据层和检查层是分离的。" |
| 4 | **Token 审计 + 费用预警** | "每次全量测试自动记 Token 消耗和费用。异常检测能发现突增 50% 或突降 80%。" |
| 5 | **三色仪表盘一目了然** | "绿色不看，黄色瞄一眼，红色必须处理。通过率低于 95% 亮黄灯，低于 80% 亮红灯。" |

---

## 四、面试常见反问

### "你做的这个和其他 AI 测试框架有什么不同？"

> "我查过现有的方案。大部分是单一维度的——要么只做质量评估（DeepEval），要么只做安全测试（Garak），要么只做压测。我的是一个整合的平台，开发者自己可以根据需要灵活组合。而且所有模块纯离线可跑，不需要联网就能开发调试。"

### "遇到过最大的技术挑战是什么？"

> "最大的挑战不是写代码，而是**用例设计**。比如多语言测试——光判断回复是什么语言就很难，中英混合代码夹杂更麻烦。Prompt Injection 的 38 个攻击用例不是一次写完的，是边测边改出来的。测试用例的设计比工具代码更难，也更值钱。"

### "为什么你用 pytest 不是 Unittest？"

> "pytest 的 fixture 和参数化天然适合 AI 测试——同一个 prompt 不同参数、不同模型可以参数化成一行测试配置，不用写 10 个重复用例。加上 `-q` 简输出方便 CI 集成，`--tb=short` 减少噪音。"

---

## 五、技术栈总结

| 分类 | 技能 | 掌握程度 |
|:----|:-----|:--------|
| 语言 | Python 3.9+ | 日常使用 |
| 测试框架 | pytest, unittest | 可独立设计 |
| 接口测试 | REST API, OpenAI SDK | 实战经验 |
| 性能测试 | 并发/稳态/阶梯/突发压测 | 已实现 |
| 安全测试 | Prompt Injection, 鲁棒性 | 实战经验 |
| CI/CD | GitHub Actions | 配置生成 |
| 工具 | Playwright, Tox, Pre-commit | 集成经验 |
