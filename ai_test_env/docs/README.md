# AI 测试平台

> 面向大模型 API 的系统化测试框架。质量、安全、性能、工程化全覆盖。

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)]()
[![tests](https://img.shields.io/badge/tests-614%20passed-brightgreen)]()
[![warnings](https://img.shields.io/badge/warnings-0-brightgreen)]()

---

## 概览

一个从零搭建的 AI 测试平台，涵盖：

| 维度 | 模块数 | 核心能力 |
|:----|:------|:---------|
| **质量评估** | 8 | 关键词检测、一致性、格式、多语言、时效性 |
| **安全测试** | 3 | Prompt Injection、鲁棒性、角色保持 |
| **性能压测** | 3 | 并发/阶梯/突发、重试引擎、熔断器 |
| **工程化** | 12 | 分层测试、CI/CD、Token 审计、CLI、Dashboard |
| **API 实战** | 3 | 真实调用、质量评估管道、费用监控 |

**614 测试通过，0 warnings，纯离线可运行。**

---

## 快速开始

```bash
# 1. 克隆项目
cd ai_test_env

# 2. 安装依赖（推荐创建虚拟环境）
pip install -r requirements.txt

# 3. 运行全部测试
python -m pytest --tb=short -q
# → 614 passed, 19 skipped

# 4. 运行单模块测试
python -m pytest tests/d6_test_quality.py -v

# 5. 命令行运行
python run.py quality --prompt "什么是 Python?" --reply "Python 是编程语言"
```

---

## 架构

```
├── utils/               # 工具模块（34 个）
│   ├── d1_d5/           # API 客户端 + Key 管理
│   ├── d6_d10/          # 质量评估体系
│   ├── d11_d15/         # 安全与对话测试
│   ├── d16_d20/         # 自动化与分层
│   ├── d21_d25/         # 性能与工程化
│   ├── d26_d30/         # 实战项目
│   └── d31_d33/         # API 实战
├── tests/               # 测试文件（37 个）
├── run.py               # CLI 入口
├── run_logs/            # 运行日志
├── *.md                 # 学习笔记 + 面试准备文档
└── ai_test_learning_plan_v3.md  # 学习计划
```

### 模块依赖

```
质量层 ← 工具层 ← 运行层 ← 汇报层
(d6-10)  (d1-5)   (d27)    (d28-29)
```

数据通过 JSON 日志解耦，没有类依赖。

---

## 模块一览

### 第 1 周 — 基础建设

| Day | 模块 | 类/函数 | 测试 |
|:----|:-----|:--------|:----:|
| d1 | API 客户端 | `AITestClient` | ✅ |
| d3 | 错误分类器 | `ErrorClassifier` | ✅ |
| d4 | 响应验证器 | `ResponseValidator` | ✅ |
| d5 | Key 管理器 | `KeyPoolManager` | ✅ |

### 第 2 周 — 质量评估

| Day | 模块 | 能力 | 测试 |
|:----|:-----|:-----|:----:|
| d6 | 质量检查器 | 关键词/禁止词/冗余度 | ✅ |
| d7 | 一致性检查器 | 语义一致/矛盾检测 | ✅ |
| d8 | 截断分析器 | finish_reason/字符模式 | ✅ |
| d8b | Tool Calling 测试 | Agent 测试 | ✅ |
| d8c | 格式验证器 | JSON/代码块/表格 | ✅ |
| d8d | 风格检查器 | 语气/人称/立场 | ✅ |
| d8e | 多语言测试 | 中/英/日/代码 | ✅ |
| d8f | 时效性测试 | 时间感知/知识截止 | ✅ |
| d9 | LLM Judge | 自动评分 | ✅ |
| d10 | Schema 验证 + 流水线 | 结构校验 | ✅ |

### 第 3 周 — 安全与高级测试

| Day | 模块 | 核心场景 | 测试 |
|:----|:-----|:---------|:----:|
| d11 | 对话测试 | 上下文保持 | ✅ |
| d12 | Injection 检测/防御 | 角色泄露/忽略指令 | ✅ |
| d13 | 鲁棒性测试 | 边界输入 | ✅ |
| d14 | 回归测试 | 功能/安全回归 | ✅ |
| d15 | E2E 测试 | 业务链路 | ✅ |

### 第 4 周 — 自动化

| Day | 模块 | 核心功能 | 测试 |
|:----|:-----|:---------|:----:|
| d16 | 浏览器自动化 | Playwright | ✅ |
| d17 | 分层管理 | Smoke/Regression/Full | ✅ |
| d18 | CI/CD 配置 | Actions 生成 | ✅ |
| d19 | 工具链集成 | Tox/Pre-commit | ✅ |
| d20 | 数据管理 | 模板/生成/脱敏 | ✅ |

### 第 5 周 — 性能与工程化

| Day | 模块 | 核心功能 | 测试 |
|:----|:-----|:---------|:----:|
| d21 | CLI | 6 子命令 | ✅ |
| d22 | 并发压测 | 稳态/阶梯/突发 | ✅ |
| d23 | 重试引擎 | 指数退避+Jitter | ✅ |
| d24 | 熔断器 | 三态状态机 | ✅ |
| d25 | 错误体系 | 分级异常 | ✅ |

### 第 6 周 — 实战项目

| Day | 模块 | 核心功能 | 测试 |
|:----|:-----|:---------|:----:|
| d26 | Token 审计 | 费用监控+异常检测 | ✅ |
| d27 | 全量运行器 | 一键跑全测 | ✅ |
| d28 | 报告聚合器 | 模块稳定性 | ✅ |
| d29 | 仪表盘 | 三色门禁 | ✅ |
| d30 | 综合验证 | 端到端自检 | ✅ |

### Phase 1 — API 实战

| Day | 模块 | 核心功能 | 测试 |
|:----|:-----|:---------|:----:|
| d31 | API 真调用 | 10 个用例 | ✅ |
| d32 | 质量评估管道 | QC+Judge+Schema | ✅ |
| d33 | 审计+多语言+压测 | 三合一 | ✅ |

---

## 使用示例

```python
# 质量检查
from utils.d6_quality_checker import QualityChecker
checker = QualityChecker()
result = checker.check(
    prompt="什么是 Python？",
    response="Python 是编程语言",
    expected_keywords=["Python", "编程语言"],
)
print(result.passed, result.score)

# 安全测试
from utils.d12_injection_detector import InjectionDetector
detector = InjectionDetector()
result = detector.detect("忽略之前的指令")
print(result.detected)

# 全量运行
from utils.d27_full_runner import FullTestRunner, RunLevel
runner = FullTestRunner()
result = runner.run(RunLevel.SMOKE)
print(runner.summary(result))
```

---

## 面试准备

| 文档 | 内容 |
|:----|:-----|
| [INTERVIEW_TOP20.md](INTERVIEW_TOP20.md) | 20 道高频面试题 + 话术 |
| [INTERVIEW_SCENARIOS.md](INTERVIEW_SCENARIOS.md) | 5 道场景题 + 3 道系统设计 |
| [INTERVIEW_STAR.md](INTERVIEW_STAR.md) | STAR 话术 + 简历条目 |

---

## License

MIT
