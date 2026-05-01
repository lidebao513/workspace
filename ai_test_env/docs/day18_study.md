# Day 18 — CI/CD 集成（GitHub Actions）

## 学习目标

1. **理解门禁策略**：掌握 4 种门禁策略（ALL_PASS/THRESHOLD/NO_REGRESSION/BLOCKING_ONLY）的适用场景
2. **掌握 CI 配置生成**：熟练使用 CIConfigGenerator 生成 GitHub Actions Workflow YAML
3. **掌握门禁检查**：理解 CIGate 的评分逻辑和检查机制
4. **配置分层调度**：理解分层 CI 调度（PR 触发 smoke / 每日 regression / 每周 security）
5. **集成告警机制**：实现测试失败自动告警和报告上传

---

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

---

## 面试题

### 面试题 1：如何设计一套完整的 CI/CD 门禁体系？

**答案：**

设计完整的 CI/CD 门禁体系需要考虑分层策略、触发机制和集成方式：

**1. 分层门禁设计**

| 层级 | 触发条件 | 门禁策略 | 响应时间 |
|------|---------|---------|---------|
| Smoke | PR/Commit | ALL_PASS | < 3 分钟 |
| Regression | 每日定时 | THRESHOLD (>= 85%) | < 10 分钟 |
| Security | 每日定时 | ALL_PASS | < 5 分钟 |
| E2E | 每周 | THRESHOLD (>= 80%) | < 20 分钟 |

**2. CI 配置生成器核心功能**
- 自动生成 GitHub Actions Workflow YAML
- 支持自定义 Python 版本、依赖、环境变量
- 生成 JUnit XML 测试报告
- 集成 Artifact 上传功能

**3. CIGate 门禁检查逻辑**
- ALL_PASS：失败数 = 0 才通过，10 分满分
- THRESHOLD：以 85% 为基准，10 分（>=85%）/ 5 分（>=70%）/ 3 分（>=50%）/ 0 分（<50%）
- NO_REGRESSION：对比基线，新增加失败数判断，10 分（无新增）/ 5 分（<3）/ 0 分（>=3）
- BLOCKING_ONLY：只检查 blocking 失败数

**4. 报告与追溯**
- JUnit XML 报告生成
- 失败用例的截图/日志上传
- 测试结果 JSON 导出供后续分析

### 面试题 2：如何处理 CI 门禁误伤问题？

**答案：**

CI 门禁误伤是指测试本身不稳定（flaky）导致的假失败。处理策略如下：

**1. 识别 Flaky 测试**
- 记录测试失败历史，识别重复失败的用例
- 分析失败模式（是断言失败还是超时）
- 使用重试机制验证稳定性

**2. 分层缓解策略**
- Smoke 层使用 ALL_PASS，但设置合理的超时时间
- Regression 层使用 THRESHOLD，允许一定的失败率
- 对 flaky 测试降级到 E2E 层，降低对主流程影响

**3. 测试稳定性改进**
- 增加显式等待时间
- 使用自动重试装饰器
- 分离环境依赖，使用 mock
- 定期清理过时的测试用例

**4. 灰度发布机制**
- 对新上线功能使用灰度策略
- 先在小范围验证，稳定性提高后再全量

---

## 代码示例

### CI 配置生成器与门禁检查实现

```python
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class PolicyLevel(Enum):
    ALL_PASS = "all_pass"
    THRESHOLD = "threshold"
    NO_REGRESSION = "no_regression"
    BLOCKING_ONLY = "blocking_only"

class GatingPolicy:
    """门禁策略配置"""
    
    DEFAULT_POLICIES = {
        "smoke": PolicyLevel.ALL_PASS,
        "regression": PolicyLevel.THRESHOLD,
        "security": PolicyLevel.ALL_PASS,
        "performance": PolicyLevel.BLOCKING_ONLY,
        "e2e": PolicyLevel.THRESHOLD,
    }
    
    DEFAULT_THRESHOLDS = {
        "smoke": 1.0,
        "regression": 0.85,
        "security": 1.0,
        "performance": 0.80,
        "e2e": 0.80,
    }
    
    def get_policy_for_level(self, level: str) -> PolicyLevel:
        return self.DEFAULT_POLICIES.get(level, PolicyLevel.THRESHOLD)
    
    def get_threshold_for_level(self, level: str) -> float:
        return self.DEFAULT_THRESHOLDS.get(level, 0.85)

@dataclass
class GatingResult:
    level: str
    policy: PolicyLevel
    passed: bool
    score: float
    message: str

class CIGate:
    """CI 门禁检查器"""
    
    def __init__(self, policy: Optional[GatingPolicy] = None):
        self.policy = policy or GatingPolicy()
    
    def check_case(
        self,
        level: str,
        passed: int,
        failed: int,
        total: int,
        blocking_failed: int = 0,
        baseline_failed: int = 0
    ) -> GatingResult:
        """检查单个层级的门禁状态"""
        policy = self.policy.get_policy_for_level(level)
        threshold = self.policy.get_threshold_for_level(level)
        
        pass_rate = passed / total if total > 0 else 0.0
        failed_added = failed - baseline_failed
        
        if policy == PolicyLevel.ALL_PASS:
            score = 10.0 if failed == 0 else 0.0
            passed_check = failed == 0
            message = "All passed" if passed_check else f"{failed} failed"
        
        elif policy == PolicyLevel.THRESHOLD:
            score = self._calculate_threshold_score(pass_rate, threshold)
            passed_check = pass_rate >= threshold
            message = f"Pass rate {pass_rate:.1%} ({threshold:.0%} threshold)"
        
        elif policy == PolicyLevel.NO_REGRESSION:
            score = self._calculate_regression_score(failed_added)
            passed_check = failed_added < 3
            message = f"Added failures: {failed_added}"
        
        else:  # BLOCKING_ONLY
            score = 10.0 if blocking_failed == 0 else 3.0
            passed_check = blocking_failed == 0
            message = "No blocking failures" if passed_check else f"{blocking_failed} blocking failures"
        
        return GatingResult(
            level=level,
            policy=policy,
            passed=passed_check,
            score=score,
            message=message
        )
    
    def _calculate_threshold_score(self, pass_rate: float, threshold: float) -> float:
        if pass_rate >= threshold:
            return 10.0
        elif pass_rate >= threshold - 0.15:
            return 5.0
        elif pass_rate >= threshold - 0.35:
            return 3.0
        else:
            return 0.0
    
    def _calculate_regression_score(self, added_failures: int) -> float:
        if added_failures == 0:
            return 10.0
        elif added_failures < 3:
            return 5.0
        else:
            return 0.0
    
    def run_gating_check(self, results: Dict[str, Dict]) -> GatingResult:
        """批量检查门禁"""
        all_passed = True
        total_score = 0.0
        details = []
        
        for level, stats in results.items():
            result = self.check_case(
                level=level,
                passed=stats.get("passed", 0),
                failed=stats.get("failed", 0),
                total=stats.get("total", 0),
                blocking_failed=stats.get("blocking_failed", 0),
                baseline_failed=stats.get("baseline_failed", 0)
            )
            details.append(result)
            if not result.passed:
                all_passed = False
            total_score += result.score
        
        avg_score = total_score / len(results) if results else 0.0
        
        return GatingResult(
            level="overall",
            policy=PolicyLevel.THRESHOLD,
            passed=all_passed,
            score=avg_score,
            message=f"Average score: {avg_score:.1f}/10"
        )

class CIConfigGenerator:
    """CI 配置生成器"""
    
    def __init__(
        self,
        project_name: str = "ai-test-suite",
        python_version: str = "3.9",
        api_key_secret: str = "DEEPSEEK_API_KEY"
    ):
        self.project_name = project_name
        self.python_version = python_version
        self.api_key_secret = api_key_secret
    
    def generate_full_pipeline(self) -> str:
        """生成完整的 GitHub Actions YAML"""
        return f"""name: AI Test Suite - CI

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
          python-version: '{self.python_version}'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run Smoke Tests
        run: python -m pytest -m "smoke" --tb=short -x
        env:
          {self.api_key_secret}: ${{{{ secrets.{self.api_key_secret} }}}}
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: smoke-results
          path: test-results.xml

  daily-regression:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'
    cron: "0 2 * * *"
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '{self.python_version}'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run Regression Tests
        run: python -m pytest -m "regression or security" --tb=short --junitxml=test-results.xml
        env:
          {self.api_key_secret}: ${{{{ secrets.{self.api_key_secret}}}}}
      - name: Gate Check
        run: |
          python -c "
          from utils.d18_ci_config_gen import CIGate, GatingPolicy
          import json, sys
          results = json.load(open('test-results.json'))
          gate = CIGate(policy=GatingPolicy())
          if not gate.run_gating_check(results).passed:
              sys.exit(1)
          "
"""

# 使用示例
gate = CIGate()

# 单个层级检查
result = gate.check_case(
    level="smoke",
    passed=10, failed=0, total=10
)
print(f"Smoke: {result.passed}, Score: {result.score}")

# 批量门禁检查
results = {
    "smoke": {"passed": 10, "failed": 0, "total": 10},
    "regression": {"passed": 18, "failed": 2, "total": 20},
    "security": {"passed": 25, "failed": 0, "total": 25},
}
overall = gate.run_gating_check(results)
print(f"Overall: {overall.passed}, Score: {overall.score:.1f}/10")

# 生成 CI 配置
gen = CIConfigGenerator(project_name="my-ai-test")
print(gen.generate_full_pipeline())
```

---

## 练习题

### 练习题 1：实现测试结果趋势对比

**要求：**
扩展 CIGate，支持与历史测试结果对比，检测性能退化。

**步骤：**
1. 设计结果存储结构（SQLite）
2. 记录每次测试运行的详细结果
3. 实现与历史基线对比功能
4. 生成趋势报告和告警

### 练习题 2：实现多项目 CI 配置管理

**要求：**
实现一个支持多项目 CI 配置的管理系统。

**步骤：**
1. 设计多项目配置存储结构
2. 实现配置的增删改查
3. 支持项目级自定义门禁策略
4. 生成项目对比报告

### 练习题 3：实现 Slack/钉钉告警集成

**要求：**
实现 CI 测试结果的告警通知系统。

**步骤：**
1. 设计告警规则配置
2. 实现 Slack/钉钉 Webhook 通知
3. 支持告警模板定制
4. 实现告警聚合和抑制

---
