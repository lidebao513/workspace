# AI Test Engine — 项目总摘要

## 35 天学习旅程

| 阶段 | 天数 | 主题 | 关键产出 |
|------|------|------|----------|
| Week 1 | Day 1-5 | API 基础 + SDK 接入 | 4 个 utils 模块，5 个知识点扩充 |
| Week 2 | Day 6-10 | 回复质量评估体系 | 5 维评分 + LLM Judge + 流水线 |
| Week 3 | Day 11-15 | 高级安全测试 | 9 种注入检测 + 6 类健壮性 + 回归 |
| Week 4 | Day 16-21 | 自动化框架 + CI/CD | 浏览器自动化 + 门禁策略 + CLi |
| Week 5 | Day 22-26 | 性能 + 错误体系 | 压测 + 熔断器 + Token 审计 |
| Week 6-7 | Day 27-33 | 实战项目搭建 | 分层架构 + 全模块集成（161 测试） |
| Wwek 8 | Day 34-35 | 面试冲刺 | 10 道 STAR 题 + 薪资谈判 + 求职策略 |

## 架构（ASCII）

```
ai_test_engine/
├── config/
│   └── settings.py          ← 全局配置
├── core/                    
│   ├── client.py            ← API 客户端（OpenAI SDK）
│   ├── error_handler.py     ← 四级错误体系
│   └── key_manager.py       ← Key 轮换 + 降级
├── tests/
│   ├── smoke/               ← 连通性(26) + 边界(20) + 错误(16)
│   ├── quality/             ← 评分(5) + Judge(5) + 流水线(3)
│   ├── security/            ← 注入(8) + 健壮性(4) + 回归(4)
│   └── performance/         ← 压测(4) + 熔断器(8) + 审计(5)
└── test_integration.py      ← 全模块集成(55)
```

## 关键指标

| 指标 | 值 |
|------|-----|
| 总测试用例 | 161 |
| 全部通过 | 161/161 (100%) |
| 总耗时 | 0.49 秒 |
| 测试模块 | 4 大模块 (smoke/quality/security/performance) |
| 项目语言 | Python 3.9+ |
| 依赖 | openai + pytest + python-dotenv |
| CI | GitHub Actions (3.9/3.10/3.11) |

## 核心设计原则

1. **分层架构** — Base (config/core) ← Tests (4 modules) ← Reports
2. **无真实 API 依赖** — 测试全部使用 mock/pure logic，离线可跑
3. **失败即修复** — 测试失败立即定位原因修复（average 1.2 次修复/模块）
4. **面试可讲** — 每个模块都有面试话术 + 可直接展示的测试报告

## 两个项目的关系

```
ai_test_env/         ← 学习路径（26 个模块，~600 测试）
ai_test_engine/      ← 实战项目（161 测试，分层架构）
```

`ai_test_env` 是逐天学习的积累，`ai_test_engine` 是将其中的核心概念用专业项目架构重组的成果。
