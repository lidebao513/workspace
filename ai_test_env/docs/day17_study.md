# Day 17 — pytest 参数化 + 分层管理

## 学习目标

1. **理解测试分层**：掌握测试分层的意义和五层架构（Smoke/Regression/Security/Performance/E2E）
2. **掌握 TestSuiteManager**：熟练运用用例库管理、过滤、统计和导出功能
3. **掌握参数化生成**：理解 ParametrizedCase 的单维/多维/CSV 参数化组合生成
4. **理解 CompatRunner**：掌握如何将分散的测试模块映射为分层结构
5. **生成覆盖率报告**：能够识别测试缺口并量化测试覆盖率

---

## 一、今日目标

> 学会用 TestSuiteManager 将 Week 1-4 的所有测试分层管理，并用参数化用例生成器创建组合测试。这部分是连接单模块测试和完整 CI 流水线的关键桥梁。

- 理解测试分层体系及其在 CI 中的意义
- 掌握 TestSuiteManager API：注册、过滤、统计、导出
- 学会 ParametrizedCase 进行单维/多维/CSV 参数化组合生成
- 理解 CompatRunner 如何将分散的测试模块映射为分层结构
- 生成覆盖率报告，量化测试缺口

---

## 二、为什么需要测试分层？

单体项目测试量不大时，直接 `pytest` 全跑就完了。但一旦测试模块超过 10 个、用例数超过 200，每次全量运行的时间成本就开始显著。

分层测试的核心思路：

| 层级 | 响应要求 | 运行频次 | 包含内容 |
|------|---------|---------|---------|
| **Smoke**（冒烟） | <30 秒 | 每次 commit | 环境连通性、API 可通、基础格式 |
| **Regression**（回归） | <5 分钟 | 每天 | 质量检查、一致性、截断、LLM Judge |
| **Security**（安全） | <3 分钟 | 每天 | Prompt Injection、Robustness |
| **Performance**（性能） | <10 分钟 | 每周 | 并发测试、响应时间 |
| **E2E**（端到端） | <15 分钟 | 每周 | 完整业务场景 |

**核心原则**：Commit 阶段只跑最快的 smoke 层，确保"不把门堵上"；每天定时跑全量 regression + security 层；每周跑完整的 p5 + e2e。

---

## 三、TestSuiteManager 架构详解

### 3.1 数据结构

```
TestCaseMeta
├── name: str                      # 用例名称
├── level: TestLevel               # 所属层级 (SMOKE/REGRESSION/...)
├── tags: List[TagCategory]        # 功能标签 (API/QUALITY/SECURITY/...)
├── module: str                    # 来源模块名
├── priority: int [1-4]            # 优先级 (1=critical, 4=low)
├── estimated_ms: int              # 预估执行时间
├── source: str                    # 具体实现来源
├── ci_only: bool                  # 是否仅 CI 执行
└── description: str               # 用例描述
```

### 3.2 内置用例注册

`_init_default_cases()` 方法自动注册了 Week 1-4 的所有核心模块：

```
d1_key_manager       → SMOKE,  tags=[API]
d2_api_client        → SMOKE,  tags=[API, PERFORMANCE]
d4_request_format    → SMOKE,  tags=[API]
d6_quality_checker   → REGRESSION, tags=[QUALITY]
d7_consistency       → REGRESSION, tags=[QUALITY, CONVERSATION]
d8_truncation        → REGRESSION, tags=[QUALITY, BOUNDARY]
d8b_tc_tester        → REGRESSION, tags=[QUALITY]
d8c_format_validator → REGRESSION, tags=[QUALITY]
d8d_style_checker    → REGRESSION, tags=[QUALITY]
d8e_multilingual     → REGRESSION, tags=[QUALITY, CONVERSATION]
d8f_timeliness       → REGRESSION, tags=[QUALITY, BOUNDARY]
d9_llm_judge         → REGRESSION, tags=[QUALITY]
d10_pipeline         → REGRESSION, tags=[QUALITY]
d11_conversation     → E2E,     tags=[CONVERSATION]
d12_prompt_injection → SECURITY, tags=[SECURITY]
d13_robustness       → SECURITY, tags=[SECURITY, BOUNDARY]
d14_regression       → REGRESSION, tags=[REGRESSION]
d15_e2e_tester       → E2E,     tags=[CONVERSATION]
d16_browser_checker  → SMOKE,   tags=[API]
d17_suite_manager    → SMOKE,   tags=[API]
d18_ci_config_gen    → REGRESSION, tags=[API]
d19_toolchain        → REGRESSION, tags=[API]
d20_data_manager     → REGRESSION, tags=[API, SECURITY]
```

### 3.3 核心 API

```python
manager = TestSuiteManager()

# 过滤
smoke = manager.filter(level=TestLevel.SMOKE)
security_with_api = manager.filter(level=TestLevel.SECURITY, tag=TagCategory.API)
high_priority = manager.filter(priority_max=2)

# 统计
counts = manager.get_level_counts()
# → {"smoke": 5, "regression": 11, "security": 2, "e2e": 2, "total": 20}

# 导出
manager.export_json("testsuite_manifest.json")

# 覆盖率报告
report = manager.generate_coverage_report()
# → 按模块列出用例数、层级分布、估算耗时
```

---

## 四、参数化测试（ParametrizedCase）

### 4.1 为什么需要参数化？

很多 AI 测试需要验证不同参数组合下的模型行为：

- Temperature = {0, 0.5, 1, 2} × Top P = {0.9, 1} → 8 组合
- Prompt 长度 = {10, 100, 1000, 4000} tokens → 4 组合
- 注入类型 = {normal, injection, jailbreak} × 语言 = {zh, en} → 6 组合

手动写 8 个测试函数显然不是长久之计。

### 4.2 ParametrizedCase API

```python
# 单维度（笛卡尔积自动展开）
case = ParametrizedCase(
    name="temperature_test",
    params={"temperature": [0, 0.5, 1, 2]}
)
print(case.combinations())  # 4

# 多维度
case = ParametrizedCase(
    name="gen_params",
    params={"temperature": [0, 1], "top_p": [0.9, 1]}
)
print(case.combinations())  # 2 × 2 = 4

# CSV 导入：每列独立展开
case = ParametrizedCase.from_csv("params.csv")
# CSV:
#   temperature,top_p
#   0,0.9
#   1,1.0
# → 2 组合（不跨列做笛卡尔积）

# 实际生成 pytest 参数
@pytest.mark.parametrize("temp", [0, 0.5, 1, 2])
def test_response_consistency(temp):
    ...
```

### 4.3 CSV 导入注意事项

```python
# 有效 CSV
case = ParametrizedCase.from_csv("valid.csv")
# → {name, description, params} 自动解析

# 无效 CSV（格式错误）
case = ParametrizedCase.from_csv("invalid.csv")
# → 降级为普通 ParametrizedCase，参数为空
```

---

## 五、兼容运行器（CompatRunner）

### 5.1 解决的问题

现有测试模块（d6, d7, d8...）并非通过 TestSuiteManager 注册的。CompatRunner 提供了一层映射：

```python
runner = CompatRunner()

# 获取所有已知模块名
modules = runner.get_all_modules()
# → ["d6", "d7", "d8", ..., "d20"]

# 按层级获取模块
smoke_modules = runner.get_smoke_modules()
security_modules = runner.get_security_modules()

# 生成 label
label = runner.module_label("d12_prompt_injection_tester")
# → "SECURITY"
```

### 5.2 层级映射规则

| 条件 | 映射层级 |
|------|---------|
| 模块名匹配 `d1*`, `d2*`, `d4*`, `d16*`, `d17*` | SMOKE |
| 模块名匹配 `d12*`, `d13*` | SECURITY |
| 模块名匹配 `d15*`, `d11*` | E2E |
| 其余 | REGRESSION |

---

## 六、选择器表达式生成

PytestMarkerGenerator 将层级和标签转换为 pytest 的 `-m` 选择表达式：

```python
gen = PytestMarkerGenerator()

# 单层级
expr = gen.select_expr(levels=[TestLevel.SMOKE])
# → "smoke"

# 多层级 + 标签
expr = gen.select_expr(
    levels=[TestLevel.SECURITY, TestLevel.REGRESSION],
    tags=[TagCategory.API]
)
# → "(security or regression) and api"
```

这可以直接传给 CI 脚本：`pytest -m "$(gen.select_expr(...))"`

---

## 七、报告生成

### 7.1 TestReportSummary

```python
summary = TestReportSummary()
summary.add_result("d6_quality_checker", passed=15, failed=1, skipped=0)
summary.add_result("d7_consistency", passed=22, failed=0, skipped=0)
summary.add_result("d8_truncation", passed=8, failed=0, skipped=0)

# 带分层
summary.add_result("d12_injection", passed=27, failed=0, skipped=0,
                    level="security")
```

支持的输出特性：
- 基础统计：总用例、通过、失败、跳过、耗时
- 分层 breakdown：按 level 汇总通过率
- 格式化成表格字符串

---

## 八、完整使用示例

### 8.1 查看当前测试覆盖

```python
from utils.d17_suite_manager import TestSuiteManager

mgr = TestSuiteManager()
print(mgr.generate_coverage_report())
```

输出样式：
```
━━━ 测试覆盖报告 ━━━
总用例: 20

层级分布:
  smoke:      5 用例  (25%)
  regression: 11 用例  (55%)
  security:   2 用例  (10%)
  e2e:        2 用例  (10%)

标签分布:
  API:           5 用例
  QUALITY:       9 用例
  SECURITY:      2 用例
  CONVERSATION:  3 用例
  BOUNDARY:      2 用例
  PERFORMANCE:   1 用例
```

### 8.2 CI 选择执行

```bash
# 冒烟测试（每次提交）
pytest -m "smoke" --tb=short

# 全量回归（每日定时）
pytest -m "smoke or regression or security" --tb=short --html=report.html

# 端到端（每周）
pytest -m "e2e" --tb=long
```

---

## 九、面试话术

> "测试分层是工程化不可缺少的一环。我设计了一个 TestSuiteManager，将 20+ 个测试模块按 Smoke/Regression/Security/Performance/E2E 五层组织，支持按层级过滤、标签选择、生成 pytest marker 表达式。配合 ParametrizedCase 做多维度参数化组合生成，测试覆盖从 80% 提升到 95%+。这套架构直接输出 CI 可用的 `-m` 过滤表达式，本地开发只跑 smoke 层（<30秒），CI 每天全量跑一次。"

---

## 十、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d17_suite_manager.py` | 分层管理 + 参数化 + 兼容运行器 | [OK] 37 tests |
| `tests/d17_test_suite_manager.py` | 全套测试 | [OK] 37/37 PASS |
| `day17_study.md` | 本文档 | [OK] 已升级 |

**学习检查点**：
- [ ] 能说出 5 个测试层级各自的 CI 运行频率
- [ ] 会用 TestSuiteManager 按层级/标签过滤用例
- [ ] 会写 ParametrizedCase 的多维参数化
- [ ] 理解 CompatRunner 的层级映射规则
- [ ] 能生成 pytest marker 选择表达式
- [ ] 能生成测试覆盖报告并读出缺口

---

## 面试题

### 面试题 1：如何设计一个测试分层架构？

**答案：**

设计测试分层架构需要考虑响应要求、运行频次和包含内容：

**五层架构设计：**

| 层级 | 响应要求 | 运行频次 | 包含内容 |
|------|---------|---------|---------|
| **Smoke**（冒烟） | <30 秒 | 每次 commit | 环境连通性、API 可通、基础格式 |
| **Regression**（回归） | <5 分钟 | 每天 | 质量检查、一致性、截断、LLM Judge |
| **Security**（安全） | <3 分钟 | 每天 | Prompt Injection、Robustness |
| **Performance**（性能） | <10 分钟 | 每周 | 并发测试、响应时间 |
| **E2E**（端到端） | <15 分钟 | 每周 | 完整业务场景 |

**核心原则：**
- Commit 阶段只跑最快的 smoke 层，确保"不把门堵上"
- 每天定时跑全量 regression + security 层
- 每周跑完整的 performance + e2e

**实现要点：**
- 使用 pytest marker（`-m smoke`）实现分层过滤
- 设计 TestSuiteManager 统一管理所有用例元数据
- 支持按层级、标签、优先级多维度过滤
- 生成 CI 可用的 marker 表达式

### 面试题 2：如何解决参数化测试中的用例爆炸问题？

**答案：**

参数化测试中，组合爆炸是一个常见问题。解决策略如下：

**1. 正交表法（Pairwise Testing）**
- 不测试所有组合，只测试每对参数之间的正交组合
- 将 4×4×4×4 = 256 个组合减少到约 10-20 个
- 使用 `pairwise` 策略自动生成

**2. 关键值选择法**
- 只测试最有代表性的值（边界值、典型值、异常值）
- 例如：数字参数只测试 0、1、正常值、最大值

**3. 场景分组法**
- 按业务场景将参数分组
- 每个场景使用不同的参数子集
- 避免不合理的参数组合

**4. 权重采样法**
- 根据参数的重要性和风险程度分配权重
- 高权重参数组合优先测试
- 低权重组合抽样测试

**5. 动态参数化**
- 第一阶段用较少组合快速验证
- 发现问题后针对特定参数增加测试密度
- 实现测试资源的动态分配

---

## 代码示例

### 测试分层管理器实现

```python
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class TestLevel(Enum):
    SMOKE = "smoke"
    REGRESSION = "regression"
    SECURITY = "security"
    PERFORMANCE = "performance"
    E2E = "e2e"

class TagCategory(Enum):
    API = "api"
    QUALITY = "quality"
    SECURITY = "security"
    CONVERSATION = "conversation"
    BOUNDARY = "boundary"
    PERFORMANCE = "performance"

@dataclass
class TestCaseMeta:
    name: str
    level: TestLevel
    tags: Set[TagCategory] = field(default_factory=set)
    module: str = ""
    priority: int = 3
    estimated_ms: int = 1000
    source: str = ""
    ci_only: bool = False
    description: str = ""

class TestSuiteManager:
    """测试套件管理器"""
    
    def __init__(self):
        self._cases: Dict[str, TestCaseMeta] = {}
        self._init_default_cases()
    
    def _init_default_cases(self):
        defaults = [
            ("d1_key_manager", TestLevel.SMOKE, {TagCategory.API}),
            ("d2_api_client", TestLevel.SMOKE, {TagCategory.API, TagCategory.PERFORMANCE}),
            ("d4_request_format", TestLevel.SMOKE, {TagCategory.API}),
            ("d6_quality_checker", TestLevel.REGRESSION, {TagCategory.QUALITY}),
            ("d7_consistency", TestLevel.REGRESSION, {TagCategory.QUALITY, TagCategory.CONVERSATION}),
            ("d8_truncation", TestLevel.REGRESSION, {TagCategory.QUALITY, TagCategory.BOUNDARY}),
            ("d9_llm_judge", TestLevel.REGRESSION, {TagCategory.QUALITY}),
            ("d11_conversation", TestLevel.E2E, {TagCategory.CONVERSATION}),
            ("d12_injection", TestLevel.SECURITY, {TagCategory.SECURITY}),
            ("d13_robustness", TestLevel.SECURITY, {TagCategory.SECURITY, TagCategory.BOUNDARY}),
            ("d15_e2e_tester", TestLevel.E2E, {TagCategory.CONVERSATION}),
            ("d16_browser_checker", TestLevel.SMOKE, {TagCategory.API}),
        ]
        
        for name, level, tags in defaults:
            self.register(TestCaseMeta(
                name=name,
                level=level,
                tags=tags,
                module=name
            ))
    
    def register(self, case: TestCaseMeta):
        self._cases[case.name] = case
    
    def filter(
        self,
        level: TestLevel = None,
        tag: TagCategory = None,
        priority_max: int = None,
        ci_only: bool = None
    ) -> List[TestCaseMeta]:
        results = list(self._cases.values())
        
        if level:
            results = [c for c in results if c.level == level]
        if tag:
            results = [c for c in results if tag in c.tags]
        if priority_max:
            results = [c for c in results if c.priority <= priority_max]
        if ci_only is not None:
            results = [c for c in results if c.ci_only == ci_only]
        
        return results
    
    def get_level_counts(self) -> Dict[str, int]:
        counts = {level.value: 0 for level in TestLevel}
        for case in self._cases.values():
            counts[case.level.value] += 1
        counts["total"] = len(self._cases)
        return counts
    
    def export_json(self) -> str:
        import json
        return json.dumps([
            {
                "name": c.name,
                "level": c.level.value,
                "tags": [t.value for t in c.tags],
                "priority": c.priority
            }
            for c in self._cases.values()
        ], indent=2)
    
    def generate_coverage_report(self) -> str:
        lines = ["━━━ 测试覆盖报告 ━━━", f"总用例: {len(self._cases)}", ""]
        
        level_counts = self.get_level_counts()
        lines.append("层级分布:")
        for level in TestLevel:
            count = level_counts.get(level.value, 0)
            pct = count / len(self._cases) * 100 if self._cases else 0
            lines.append(f"  {level.value:12s}: {count:2d} 用例  ({pct:.0f}%)")
        
        tag_counts = {tag.value: 0 for tag in TagCategory}
        for case in self._cases.values():
            for tag in case.tags:
                tag_counts[tag.value] += 1
        
        lines.append("")
        lines.append("标签分布:")
        for tag, count in sorted(tag_counts.items()):
            lines.append(f"  {tag:14s}: {count} 用例")
        
        return "\n".join(lines)

class ParametrizedCase:
    """参数化用例生成器"""
    
    @staticmethod
    def generate_1d(param_name: str, values: List) -> List[Dict]:
        return [{param_name: v} for v in values]
    
    @staticmethod
    def generate_2d(params: Dict[str, List]) -> List[Dict]:
        results = []
        for name, values in params.items():
            for v in values:
                results.append({name: v})
        return results
    
    @staticmethod
    def generate_grid(params: Dict[str, List]) -> List[Dict]:
        if not params:
            return [{}]
        
        keys = list(params.keys())
        values = list(params.values())
        results = []
        
        def backtrack(index: int, current: Dict):
            if index == len(keys):
                results.append(current.copy())
                return
            for v in values[index]:
                current[keys[index]] = v
                backtrack(index + 1, current)
        
        backtrack(0, {})
        return results
    
    @staticmethod
    def generate_csv(csv_content: str) -> List[Dict]:
        import csv
        import io
        reader = csv.DictReader(io.StringIO(csv_content))
        return list(reader)

# 使用示例
manager = TestSuiteManager()

# 按层级过滤
smoke_cases = manager.filter(level=TestLevel.SMOKE)
print(f"Smoke 用例数: {len(smoke_cases)}")

# 按标签过滤
quality_cases = manager.filter(tag=TagCategory.QUALITY)
print(f"Quality 用例数: {len(quality_cases)}")

# 统计
counts = manager.get_level_counts()
print(f"层级分布: {counts}")

# 生成报告
print(manager.generate_coverage_report())

# 参数化生成
params_1d = ParametrizedCase.generate_1d("temperature", [0.0, 0.5, 1.0])
print(f"1D 参数化: {len(params_1d)} cases")

params_grid = ParametrizedCase.generate_grid({
    "model": ["gpt-3.5", "gpt-4"],
    "temperature": [0.0, 1.0],
    "max_tokens": [100, 500]
})
print(f"网格参数化: {len(params_grid)} cases")
```

---

## 练习题

### 练习题 1：实现测试优先级调度器

**要求：**
实现一个基于优先级的测试调度器，支持动态调整测试顺序。

**步骤：**
1. 定义优先级规则（失败历史、代码覆盖率、业务重要性）
2. 实现优先级评分计算
3. 按优先级排序执行测试
4. 支持时间预算控制

### 练习题 2：实现测试缺口分析器

**要求：**
实现一个测试缺口分析器，自动识别测试覆盖盲区。

**步骤：**
1. 解析代码结构，提取被测模块
2. 对比现有测试覆盖情况
3. 识别未覆盖的边界条件和异常路径
4. 生成测试补充建议报告

### 练习题 3：实现测试结果趋势分析

**要求：**
实现一个测试结果趋势分析模块，跟踪测试通过率历史。

**步骤：**
1. 设计结果存储结构（SQLite/JSON）
2. 记录每次测试运行的详细结果
3. 计算通过率趋势、失败模式分析
4. 生成趋势图表和告警规则

---
