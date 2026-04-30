# Day 21 — Week 4 综合项目：AI 测试平台 CLI

## 一、今日目标

> 将 Week 4 所有模块整合为一个统一的命令行工具。

- 理解 CLI 入口 `run.py` 的 7 个子命令
- 掌握各子命令的参数设计和输出格式
- 学会用统一的命令行接口串连测试工具链

---

## 二、CLI 架构

```
run.py
├── test        — 运行分层测试（smoke/regression/security/e2e/performance/all）
├── param       — 参数化用例生成（单维/多维/CSV）
├── ci          — CI 配置生成 + 门禁检查
├── sanity      — 代码健全性检查
├── coverage    — 覆盖率报告
├── data        — 测试数据管理（generate/mask/version）
├── tox         — 生成 tox.ini
└── health      — 项目健康报告
```

### 使用示例

```bash
python run.py test --level smoke        # 冒烟
python run.py param --params "temp=0,0.5,1;top_p=0.9,1.0"
python run.py ci check --level regression --total 20 --passed 19
python run.py sanity --fail-on-issue
python run.py coverage
python run.py data generate --kind prompt --count 50
python run.py data mask --input secrets.txt --output safe.txt
python run.py tox --output tox.ini
python run.py health
```

### 设计要点

- **子命令用 `argparse` subparsers** 实现
- **`func=cmd_xxx`** 模式分发到处理函数
- **所有命令返回 int**（0=成功，非0=失败），兼容 CI exit code

---

## 三、运行验证

```
28 passed in 0.16s
```

## 四、Week 4 产出汇总

| 天 | 主题 | 文件 | 测试 |
|---|------|------|------|
| Day 16 | Playwright 浏览器自动化 | browser_checker.py | 28/28 PASS |
| Day 17 | pytest 参数化 + 分层管理 | suite_manager.py | 37/37 PASS |
| Day 18 | CI/CD 集成 | ci_config_gen.py | 22/22 PASS |
| Day 19 | 开源工具整合 | toolchain_integration.py | 29/29 PASS |
| Day 20 | 测试数据管理 | data_manager.py | 42/42 PASS |
| Day 21 | 综合项目 CLI | run.py | 28/28 PASS |

### 代码统计

```
utils/     → 21 个模块
tests/     → 20 个测试文件（~500 个测试用例）
文档       → day1_study.md ~ day21_study.md 共 21 篇
入口       → run.py, smoke_test.py
```

## 五、面试话术

**架构相关：**
"我设计了一个分层式的 AI 测试平台。底层是 21 个工具模块，每个专注于一个测试维度；上层是统一的 CLI 入口 run.py。这种架构的好处是：底层模块可以独立演进和单元测试，上层不关心内部实现细节。"

**工具链相关：**
"Week 4 聚焦在工具链和基础设施上。从 Playwright 浏览器自动化到 CI 门禁、从 Tox 多环境测试到数据脱敏版本管理，目的是让 AI 测试从手工脚本进化为可重复、可自动化的工程体系。"

**可扩展性：**
"架构设计考虑了可扩展性。要加新测试维度，只需要在 utils/ 下建新模块 + tests/ 写测试 + run.py 加一个子命令。三件套搞定。"
