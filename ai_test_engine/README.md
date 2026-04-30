# AI Test Engine

AI 模型接口测试引擎。35 天系统化学习成果，覆盖 API 连接性、参数边界、异常处理、质量评估、安全测试、性能压测等 AI 测试全链路。

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY
python -m pytest tests/ -v
```

## Project Structure

```
ai_test_engine/
├── config/settings.py     # 全局配置（Key/Model/Timeout）
├── core/
│   ├── client.py          # AIEngineClient API 封装
│   ├── error_handler.py   # 分级错误体系 + 分类器
│   └── key_manager.py     # Key 轮换 + 降级
├── tests/
│   ├── smoke/             # 冒烟测试（连通性/边界/错误）
│   ├── quality/           # 质量评估（评分/一致性/Judge）
│   ├── security/          # 安全测试（注入/健壮性/回归）
│   └── performance/       # 性能测试（压测/熔断器/Token审计）
├── reports/               # 测试报告输出
├── .env.example
└── requirements.txt
```

## Features

- **API 客户端封装** — OpenAI SDK 封装，支持同步/流式
- **Key 管理** — 多 Key 轮换 + 模型降级 + 失败计数
- **错误分级** — FATAL/ERROR/WARN/INFO 四级体系 + 告警规则
- **冒烟测试** — 61 个用例覆盖参数边界/错误分类/消息格式
- **质量评估** — 5 维评分 + LLM-as-Judge + 一致性检查 + Token 优化
- **安全测试** — 9 类注入攻击 + 6 种健壮性扰动的测试
- **性能测试** — 并发压测 P95/P99 + 三态熔断器 + Token 审计
- **CI/CD** — GitHub Actions workflow + 4 级门禁策略

## Configuration

| 参数 | 默认值 | 说明 |
|------|--------|------|
| DEEPSEEK_API_KEY | (必填) | API Key |
| API_BASE | https://api.deepseek.com | API 地址 |
| MODEL_NAME | deepseek-chat | 模型名 |
| MAX_RETRIES | 3 | 最大重试次数 |
| TIMEOUT | 30.0 | 请求超时(秒) |
| MAX_TOKENS | 1024 | 最大生成 Token |
| TEMPERATURE | 0.7 | 随机度(0-2) |

## 面试话术

> "我搭建了一个完整的 AI 测试引擎，覆盖从 API 连通性到生产级错误体系的 8 个维度。核心设计是分层架构——基础层（客户端/配置/错误处理）、测试层（冒烟/质量/安全/性能）、报告层（集成报告/告警）。共 350+ 测试用例，CI 集成 GitHub Actions。"
