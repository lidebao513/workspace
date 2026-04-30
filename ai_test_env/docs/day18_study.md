# Day 18 — CI/CD 集成（GitHub Actions）

## 一、今日目标

> 学会为 AI 测试项目配置完整的 CI/CD 流水线，包括门禁策略、Workflow YAML 自动生成、分层触发调度。Day 17 建立了测试分层体系，Day 18 让它真正跑起来。

- 理解 4 种门禁策略的适用场景
- 掌握 CIConfigGenerator 生成 GitHub Actions Workflow YAML
- 会用 CIGate 做门禁检查（通过率阈值、回归检测）
- 理解分层调度：PR 触发 smoke < 每日 regression < 每周 security

---

## 二、门禁策略详解

### 2.1 四种策略

| 策略 | 含义 | 适合层级 | 说明 |
|------|------|---------|------|
| **ALL_PASS** | 100% 通过 | Smoke, Security | 硬性门禁，一个失败就 block merge |
| **THRESHOLD** | 超过阈值 | Regression, E2E | 设定通过率下限（如 >=95%） |
| **NO_REGRESSION** | 无回归 | Any | 与基线对比，新增加失败才 block |
| **BLOCKING_ONLY** | 仅阻塞级 | Performance | 只有标记为 blocking 的用例失败才拦 |

### 2.2 策略选择逻辑

```python
from utils.d18_ci_config_gen import PolicyLevel, GatingPolicy

# 按层级自动匹配默认策略
policy = GatingPolicy()

# 获取 smoke 层级应用的策略
pl = policy.get_policy_for_level("smoke")
print(pl)  # PolicyLevel.ALL_PASS

# 获取 regression 的策略
pl = policy.get_policy_for_level("regression")
print(pl)  # PolicyLevel.THRESHOLD

# 自定义
policy.set_policy("smoke", PolicyLevel.THRESHOLD, 0.9)
```

### 2.3 CIGate 门禁检查

```python
from utils.d18_ci_config_gen import CIGate, PolicyLevel

gate = CIGate(policy=GatingPolicy())

# 查单个条目是否通过门禁
result = gate.check_case(
    level="smoke",
    passed=10, failed=0, total=10
)
print(result.passed)  # True

result2 = gate.check_case(
    level="regression",
    passed=18, failed=2, total=20
)
print(result2.passed)  # True (18/20 = 90%, >= 85% threshold)

# 批量检查（门禁预览）
results = gate.run_gating_check({
    "smoke": {"passed": 10, "failed": 0, "total": 10},
    "regression": {"passed": 18, "failed": 2, "total": 20},
    "security": {"passed": 25, "failed": 0, "total": 25},
})
```

**评分逻辑**：
- ALL_PASS：`failed == 0` 才通过，`passed/total = 1.0` 得满分
- THRESHOLD：以 85% 为基准，低于则 fail，每 10 分一档
- NO_REGRESSION：根据 `+failed_added`（新引入失败数）判断
- BLOCKING_ONLY：只检查 blocking 失败数

分数范围 0-10：
- ALL_PASS: 10 (完美) / 0 (有失败)
- THRESHOLD: 10 (>=85%) / 5 (>=70%) / 3 (>=50%) / 0 (<50%)
- NO_REGRESSION: 10 (无新增) / 5 (少量<3) / 0 (大量>=3)
- BLOCKING_ONLY: 10 (无阻塞) / 3 (有阻塞)

---

## 三、CI 配置生成器（CIConfigGenerator）

### 3.1 生成 YAML

```python
from utils.d18_ci_config_gen import CIConfigGenerator

gen = CIConfigGenerator(
    project_name="ai-test-suite",
    python_version="3.9",
    api_key_secret="DEEPSEEK_API_KEY",
)

# 生成完整的 GitHub Actions YAML
yaml_content = gen.generate_config(
    workflow_name="AI Test Suite",
    trigger_branches=["main", "develop"],
    include_steps=["setup", "install", "smoke", "regression", "report"],
)
```

### 3.2 默认分层 Pipeline

`generate_full_pipeline()` 方法返回预定义的三层 YAML：

1. **PR Smoke**：快速验证（~2min），ON: push + pull_request to main/develop
2. **Daily Regression**：每日定时，00:00 UTC（即北京时间 08:00）
3. **Weekly Security**：每周一 06:00 UTC（14:00 Beijing）

每层的 YAML 包括：
```yaml
- name: Setup Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.9'

- name: Install dependencies
  run: pip install -r requirements.txt

- name: Run tests
  run: python -m pytest -m "smoke" --tb=short --junitxml=smoke-report.xml

- name: Upload artifacts
  uses: actions/upload-artifact@v3
  if: always()
  with:
    path: smoke-report.xml
```

### 3.3 自定义扩展 Workflow

```python
# 按步骤组合
custom_yaml = gen.generate_config(
    workflow_name="Custom Pipeline",
    trigger_branches=["main"],
    include_steps=["setup", "install", "lint", "smoke", "report"],
)
```

---

## 四、分层调度策略

```
PR/Merge Request
  └── Smoke (ALL_PASS)          ← 3 分钟内，不过不放行
       ├── 环境连通性
       ├── API 可通性
       └── 基础格式

Daily (00:00 UTC)
  └── Regression (THRESHOLD)    ← 10 分钟，通过率 ≥85%
  │    ├── 质量检查
  │    ├── 一致性
  │    ├── 截断
  │    └── ... 所有非安全模块
  └── Security (ALL_PASS)
       ├── Prompt Injection
       └── Robustness

Weekly (Mon 06:00 UTC)
  └── E2E (THRESHOLD)            ← 15 分钟
  └── Performance (BLOCKING)
```

---

## 五、Artifact 管理

所有 Job 失败也会上传报告：

```yaml
- uses: actions/upload-artifact@v3
  if: always()
  with:
    name: test-report
    path: reports/
    retention-days: 7
```

关键点：
- `if: always()` — 确保即使 test 失败也上传
- retention-days 设为 7 天避免空间浪费
- 支持自定义 artifact 名称和路径

---

## 六、完整流程示例

### 6.1 本地预览 CI 配置

```bash
python -c "
from utils.d18_ci_config_gen import CIConfigGenerator
gen = CIConfigGenerator()
print(gen.generate_full_pipeline())
"
```

### 6.2 门禁检查集成

在 CI YAML 的 test step 后加入：
```yaml
- name: Gate check
  run: |
    python -c "
    from utils.d18_ci_config_gen import CIGate, GatingPolicy
    import json, sys
    results = json.load(open('test-results.json'))
    gate = CIGate(policy=GatingPolicy())
    if not gate.run_gating_check(results).passed:
      sys.exit(1)
    "
```

### 6.3 完整 Workflow 示例片段

```yaml
name: AI Test Suite - Smoke
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  smoke-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install
        run: pip install -r requirements.txt
      - name: Smoke Tests
        run: python -m pytest -m "smoke" --tb=short -x
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
```

---

## 七、面试话术

> "我设计了一套完整的 CI 门禁体系。测试按层组织后，CI 也对应分成三层：PR 触发 Smoke（ALL_PASS，3 分钟内完成，不过不放行）、每日定时跑 Regression + Security（THRESHOLD + ALL_PASS 混合）、每周跑 E2E + Performance。CIConfigGenerator 自动生成 GitHub Actions YAML，CIGate 做门禁检查——不同层级用不同策略，避免 Smoke 的硬性门禁误伤开发。JUnit XML 报告 + 失败的 Artifact 上传确保问题可追溯。"

---

## 八、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d18_ci_config_gen.py` | CI 配置生成器 + 门禁检查 | [OK] |
| `tests/d18_test_ci_config_gen.py` | 22 个测试 | [OK] 22/22 PASS |
| `day18_study.md` | 本文档 | [OK] 已升级 |

**学习检查点**：
- [ ] 能说出 4 种门禁策略各自适合的层级
- [ ] 会用 CIConfigGenerator 生成自定义 Workflow YAML
- [ ] 理解 CIGate 各策略的评分逻辑
- [ ] 能在 CI YAML 中集成门禁检查脚本
- [ ] 会配置分层 CI 调度（PR + Daily + Weekly）
