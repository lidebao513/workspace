# Day 19 — 开源工具整合（Tox + Coverage + Sanity）

## 学习目标

1. **理解 Tox**：掌握 Tox 多环境测试的配置和运行机制
2. **掌握覆盖率门禁**：理解模块级覆盖率阈值设置和检查逻辑
3. **掌握代码健康检查**：学会使用 CodeSanityChecker 检测硬编码密钥、TODO 遗存等问题
4. **理解健康评分**：掌握健康评分公式的构成和解读
5. **集成 CI 流水线**：能够将 Tox、Coverage、Sanity 整合到 CI 流水线

---

## 一、今日目标

> 学会将 AI 测试项目接入标准工程基础设施：Tox 多环境测试、Coverage 覆盖率门禁、Code Sanity 代码健康检查。Day 18 把 CI 流水线搭起来，Day 19 填充具体 toolchain。

- 理解 Tox 配置和运行机制（多 Python 版本测试）
- 掌握 CoverageThresholdChecker 模块级覆盖率门禁
- 学会 CodeSanityChecker 检测硬编码密钥 / TODO 遗存 / 大文件
- 会生成项目健康报告（Health Report）

---

## 二、Tox + Coverage + Sanity 三大件概览

```
ToolchainIntegration
├── ToxManager
│   ├── create_config()        # 生成 tox.ini
│   ├── set_envlist()          # 设定 Python 版本列表
│   └── validate_config()      # 校验 tox.ini 合法性
├── CoverageThresholdChecker
│   ├── set_thresholds()       # 设定模块级阈值
│   ├── check()                # 检查当前覆盖率
│   └── get_report()           # 生成报告
└── CodeSanityChecker
    ├── check_file()            # 单文件检查
    ├── check_project()         # 全项目检查
    └── get_report()            # 生成报告
```

---

## 三、ToxManager — 多环境测试管理

### 3.1 Tox 是什么？

Tox 是 Python 的多环境测试工具。它自动创建虚拟环境、安装依赖、运行测试。核心价值：
- **多版本兼容**：在 py38/py39/py310/py311 上分别跑
- **环境隔离**：不同依赖组合互不影响
- **CI 一致**：本地运行和 CI 执行环境完全一致的 tox.ini

### 3.2 配置生成

```python
from utils.d19_toolchain_integration import ToxManager

mgr = ToxManager()
mgr.set_envlist(["py39", "py310", "py311"])

config = mgr.create_config(
    test_dir="tests/",
    deps=["pytest", "pytest-cov", "pytest-html", "openai", "python-dotenv"],
    coverage_source="utils",
    coverage_omit=["*/tests/*", "*/__pycache__/*"],
)
print(config)
```

输出 tox.ini：
```ini
[tox]
envlist = py39, py310, py311
skip_missing_interpreters = True
minversion = 4.0

[testenv]
deps =
    pytest
    pytest-cov
    pytest-html
    openai
    python-dotenv
commands =
    python -m pytest tests/ --cov=utils --cov-report=xml --cov-report=term

[coverage:run]
source = utils
omit = */tests/*, */__pycache__/*

[coverage:report]
exclude_lines = pragma: no cover
```

### 3.3 配置校验

```python
# 有效配置（包含 [tox], [testenv], 并且 envlist 非空）
mgr.validate_config()  # True

# 无效配置（空的或缺失必填段）
bad = ToxManager()
bad.validate_config(empty_config)  # False
```

校验规则：
- 必须有 `[tox]` 段
- 必须有 `[testenv]` 段
- envlist 不能为空

---

## 四、CoverageThresholdChecker — 覆盖率门禁

### 4.1 模块级阈值设定

```python
from utils.d19_toolchain_integration import CoverageThresholdChecker

checker = CoverageThresholdChecker()

# 设置默认阈值
checker.set_thresholds({
    "api_client": 0.90,
    "key_manager": 0.90,
    "quality_checker": 0.85,
    "prompt_injection_tester": 0.85,
    "e2e_tester": 0.75,
    "browser_checker": 0.75,
})
```

### 4.2 执行检查

```python
# mock 结果
mock_coverage = {
    "api_client": 0.94,
    "quality_checker": 0.88,
    "prompt_injection_tester": 0.86,
}

results = checker.check(mock_coverage)
# → [{"module": "api_client", "actual": 0.94, "threshold": 0.90, "passed": True}, ...]
```

### 4.3 报告生成

```python
report = checker.get_report()
```

输出：
```
━━━ 覆盖率门禁报告 ━━━
api_client:         94% → 90% [OK]
quality_checker:    88% → 85% [OK]
prompt_injection:   86% → 85% [OK]
━━━ 总分: 3/3 模块达标 ━━━
```

---

## 五、CodeSanityChecker — 代码健康检查

### 5.1 检查项

| 检查项 | 检测内容 | 严重性 | 检测方式 |
|--------|---------|--------|---------|
| **HARDCODED_KEY** | `sk-xxx`、`ghp_xxx` 等密钥 | 🔴 高危 | 正则 `sk-[a-zA-Z0-9]+` |
| **TODO_REMAINING** | TODO / FIXME 注释 | 🟡 中危 | 正则 `# TODO` / `# FIXME` |
| **FILE_TOO_LARGE** | 超过 500 行的文件 | 🔵 低危 | 行数统计 |
| **TRAILING_NEWLINE** | 末尾缺少换行符 | 🔵 低危 | 末尾字符检测 |

### 5.2 执行检查

```python
from utils.d19_toolchain_integration import CodeSanityChecker, SanityIssue

# 单文件检查
issues = CodeSanityChecker.check_file("utils/d12_prompt_injection_tester.py")
for issue in issues:
    print(f"[{issue.severity}] {issue.type}: {issue.message} (line {issue.line})")

# 全项目检查
all_issues = CodeSanityChecker.check_project()
# → 递归扫描项目文件（排除 __pycache__/ .git/ 等）
```

### 5.3 报告

```python
CodeSanityChecker.get_report()
# → "代码健康报告: 发现 X 个问题"
```

---

## 六、健康综合评分

### 6.1 评分公式

```
Score = min(Coverage × 50 + max(30 - issues × 3, 0) + CI_exists × 10, 100)
```

- **Coverage**：覆盖率百分比，权重 50 分
- **Issues**：代码健康问题数，每个扣 3 分（最多扣完 30 分基础分）
- **CI_exists**：CI 配置是否存在，10 分
- **总分**：0-100

### 6.2 解读

| 分数区间 | 评估 | 建议操作 |
|---------|------|---------|
| 90-100 | 🟢 健康 | 维持 |
| 70-89 | 🟡 一般 | 修复高严重度 issue |
| 50-69 | 🟠 需关注 | 提升覆盖率 + 清理 TODO |
| <50 | 🔴 不健康 | 全面整改 |

---

## 七、完整使用示例

### 7.1 一键项目健康检查

```bash
python -c "
from utils.d19_toolchain_integration import (
    ToxManager, CoverageThresholdChecker, CodeSanityChecker
)

# 1. 检查覆盖率
cc = CoverageThresholdChecker()
cc.set_thresholds({'api_client': 0.90, 'key_manager': 0.85})
print(cc.get_report())

# 2. 代码健康
health = CodeSanityChecker.check_project()
print(CodeSanityChecker.get_report())

# 3. Tox 配置
tm = ToxManager()
tm.set_envlist(['py39', 'py310'])
print('[OK] Tox config ready')
"
```

### 7.2 CI 集成（在 d18 的 Workflow 中）

```yaml
- name: Coverage Gate
  run: |
    python -c "
    from utils.d19_toolchain_integration import CoverageThresholdChecker
    cc = CoverageThresholdChecker()
    cc.set_thresholds({'utils': 0.85})
    results = cc.check({'utils': 0.88})
    if not all(r['passed'] for r in results):
      exit(1)
    "

- name: Code Sanity
  run: |
    python -c "
    from utils.d19_toolchain_integration import CodeSanityChecker
    CodeSanityChecker.check_project()
    "
```

---

## 八、面试话术

> "工程基础设施层面，我做了三件事：**Tox 多环境测试**——py39/py310/py311 三个环境，`skip_missing_interpreters` 确保不阻塞；**覆盖率门禁**——按模块设阈（核心 90%、边缘 75%），门禁过低直接 fail CI；**代码健康检查**——自动检测硬编码密钥、TODO 遗存、超大文件。最后用健康评分公式把三个维度合成一个 0-100 的分数，一眼看出项目状态。"

---

## 九、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d19_toolchain_integration.py` | ToxManager + Coverage + Sanity | [OK] |
| `tests/d19_test_toolchain_integration.py` | 29 个测试 | [OK] 29/29 PASS |
| `day19_study.md` | 本文档 | [OK] 已升级 |

**学习检查点**：
- [ ] 会配置 ToxManager 的 envlist 和依赖
- [ ] 知道覆盖率阈值如何按模块差异化设定
- [ ] 能写 CodeSanityChecker 的自定义检查项
- [ ] 理解健康评分公式的构成
- [ ] 能在 CI YAML 中集成覆盖率门禁

---

## 面试题

### 面试题 1：如何设计一个模块级覆盖率门禁系统？

**答案：**

设计模块级覆盖率门禁系统需要考虑差异化阈值、检测逻辑和告警机制：

**1. 差异化阈值设计**

| 模块类型 | 示例模块 | 推荐阈值 |
|---------|---------|---------|
| 核心模块 | api_client, key_manager | >= 90% |
| 业务模块 | quality_checker, e2e_tester | >= 80% |
| 边缘模块 | helpers, utils | >= 70% |
| 测试模块 | tests/ | 不做要求 |

**2. 检查逻辑**
```python
def check(coverage_data: Dict[str, float]) -> List[Dict]:
    results = []
    for module, actual in coverage_data.items():
        threshold = thresholds.get(module, DEFAULT_THRESHOLD)
        results.append({
            "module": module,
            "actual": actual,
            "threshold": threshold,
            "passed": actual >= threshold,
            "gap": actual - threshold
        })
    return results
```

**3. 告警机制**
- 未达标的模块列出详细差距
- 计算总体覆盖率（加权平均）
- 生成详细的检查报告

**4. CI 集成**
- 覆盖率门禁失败时阻止代码合并
- 支持覆盖率为零的模块豁免
- 提供修复建议

### 面试题 2：如何构建项目健康度评估体系？

**答案：**

构建项目健康度评估体系需要多维度指标和综合评分：

**1. 核心指标维度**

| 维度 | 指标 | 计算方式 |
|------|------|---------|
| 覆盖率 | 模块覆盖率 | 实际覆盖率 / 目标覆盖率 |
| 代码质量 | Sanity Score | 100 - 扣分 |
| 测试完整性 | 测试用例数 | 用例数 / 目标用例数 |

**2. 健康评分公式**
```
总分 = 覆盖率得分 × 0.4 + Sanity得分 × 0.3 + 测试完整性得分 × 0.3
```

**3. 评分解读**

| 分数区间 | 评估 | 建议操作 |
|---------|------|---------|
| 90-100 | 🟢 健康 | 维持现状 |
| 70-89 | 🟡 一般 | 修复高严重度 issue |
| 50-69 | 🟠 需关注 | 提升覆盖率 + 清理 TODO |
| <50 | 🔴 不健康 | 全面整改 |

**4. 实施步骤**
1. 定义各维度的目标和权重
2. 实现自动化采集和计算
3. 定期生成健康报告
4. 设置阈值告警

---

## 代码示例

### 工具链整合管理器实现

```python
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class CoverageThresholdResult:
    module: str
    actual: float
    threshold: float
    passed: bool
    gap: float

class CoverageThresholdChecker:
    """覆盖率阈值检查器"""
    
    def __init__(self):
        self.thresholds: Dict[str, float] = {}
        self.default_threshold = 0.80
    
    def set_thresholds(self, thresholds: Dict[str, float]):
        self.thresholds = thresholds
    
    def check(self, coverage_data: Dict[str, float]) -> List[CoverageThresholdResult]:
        results = []
        for module, actual in coverage_data.items():
            threshold = self.thresholds.get(module, self.default_threshold)
            results.append(CoverageThresholdResult(
                module=module,
                actual=actual,
                threshold=threshold,
                passed=actual >= threshold,
                gap=actual - threshold
            ))
        return results
    
    def get_report(self) -> str:
        lines = ["━━━ 覆盖率检查报告 ━━━"]
        if not self.thresholds:
            lines.append("未设置阈值")
            return "\n".join(lines)
        
        for module, threshold in self.thresholds.items():
            lines.append(f"{module}: >= {threshold:.0%}")
        
        return "\n".join(lines)

class CodeSanityIssue:
    def __init__(self, file: str, line: int, severity: Severity, category: str, message: str):
        self.file = file
        self.line = line
        self.severity = severity
        self.category = category
        self.message = message

class CodeSanityChecker:
    """代码健康检查器"""
    
    SEVERITY_SCORES = {
        Severity.CRITICAL: 20,
        Severity.HIGH: 10,
        Severity.MEDIUM: 5,
        Severity.LOW: 2,
        Severity.INFO: 0
    }
    
    def __init__(self):
        self.issues: List[CodeSanityIssue] = []
    
    @staticmethod
    def check_file(file_path: str, content: str) -> List[CodeSanityIssue]:
        issues = []
        lines = content.split("\n")
        
        for i, line in enumerate(lines, 1):
            # 硬编码密钥检测
            if any(kw in line.lower() for kw in ["api_key", "secret", "password", "token"]):
                if "=" in line and not line.strip().startswith("#"):
                    issues.append(CodeSanityIssue(
                        file=file_path,
                        line=i,
                        severity=Severity.CRITICAL,
                        category="hardcoded_secret",
                        message="发现疑似硬编码密钥"
                    ))
            
            # TODO 检测
            if "TODO" in line or "FIXME" in line:
                issues.append(CodeSanityIssue(
                    file=file_path,
                    line=i,
                    severity=Severity.MEDIUM,
                    category="todo",
                    message=f"发现未完成标记: {line.strip()}"
                ))
            
            # 大文件检测 (>1000行)
            if len(lines) > 1000:
                issues.append(CodeSanityIssue(
                    file=file_path,
                    line=0,
                    severity=Severity.LOW,
                    category="large_file",
                    message=f"文件超过 1000 行: {len(lines)} 行"
                ))
        
        return issues
    
    @staticmethod
    def check_project(file_map: Dict[str, str]) -> Tuple[int, List[CodeSanityIssue]]:
        all_issues = []
        for file_path, content in file_map.items():
            issues = CodeSanityChecker.check_file(file_path, content)
            all_issues.extend(issues)
        
        total_score = 100
        for issue in all_issues:
            total_score -= CodeSanityChecker.SEVERITY_SCORES.get(issue.severity, 0)
        
        return max(0, total_score), all_issues
    
    @staticmethod
    def get_report(score: int, issues: List[CodeSanityIssue]) -> str:
        lines = ["━━━ 代码健康报告 ━━━", f"总分: {score}/100", ""]
        
        by_category = {}
        for issue in issues:
            if issue.category not in by_category:
                by_category[issue.category] = []
            by_category[issue.category].append(issue)
        
        lines.append(f"发现问题: {len(issues)} 个")
        for category, cat_issues in by_category.items():
            lines.append(f"  [{category}]: {len(cat_issues)} 个")
        
        return "\n".join(lines)

class ToxManager:
    """Tox 配置管理器"""
    
    def __init__(self):
        self.envlist: List[str] = []
        self.test_dir = "tests/"
        self.deps: List[str] = []
        self.config = ""
    
    def set_envlist(self, envlist: List[str]):
        self.envlist = envlist
    
    def create_config(
        self,
        test_dir: str,
        deps: List[str],
        coverage_source: str = "utils",
        coverage_omit: List[str] = None
    ) -> str:
        omit_str = "\n    ".join(coverage_omit) if coverage_omit else ""
        
        config = f"""[tox]
envlist = {", ".join(self.envlist)}
skip_missing_interpreters = True
minversion = 4.0

[testenv]
deps =
    {"".join(f"\\n    {dep}" for dep in deps)}
commands =
    python -m pytest {test_dir} --cov={coverage_source} --cov-report=xml --cov-report=term

[coverage:run]
source = {coverage_source}
omit = */tests/*, */__pycache__/*

[coverage:report]
exclude_lines = pragma: no cover
"""
        self.config = config
        return config
    
    def validate_config(self, config: str = None) -> bool:
        cfg = config or self.config
        if not cfg:
            return False
        return "[tox]" in cfg and "[testenv]" in cfg and len(self.envlist) > 0

class HealthReporter:
    """项目健康度报告器"""
    
    @staticmethod
    def calculate_score(
        coverage_score: float,
        sanity_score: int,
        test_completeness: float
    ) -> float:
        return coverage_score * 0.4 + sanity_score * 0.3 + test_completeness * 0.3
    
    @staticmethod
    def get_grade(score: float) -> Tuple[str, str]:
        if score >= 90:
            return "🟢 健康", "维持现状"
        elif score >= 70:
            return "🟡 一般", "修复高严重度 issue"
        elif score >= 50:
            return "🟠 需关注", "提升覆盖率 + 清理 TODO"
        else:
            return "🔴 不健康", "全面整改"
    
    @staticmethod
    def generate_report(
        coverage_results: List[CoverageThresholdResult],
        sanity_score: int,
        sanity_issues: List[CodeSanityIssue],
        test_count: int,
        target_test_count: int
    ) -> str:
        lines = ["━━━ 项目健康度报告 ━━━", ""]
        
        # 覆盖率
        passed_cov = sum(1 for r in coverage_results if r.passed)
        total_cov = len(coverage_results)
        cov_rate = passed_cov / total_cov if total_cov > 0 else 0
        lines.append(f"覆盖率: {passed_cov}/{total_cov} 模块达标 ({cov_rate:.0%})")
        
        # 代码健康
        lines.append(f"代码健康: {sanity_score}/100 ({len(sanity_issues)} 个问题)")
        
        # 测试完整性
        test_rate = min(test_count / target_test_count, 1.0) if target_test_count > 0 else 0
        lines.append(f"测试完整性: {test_count}/{target_test_count} ({test_rate:.0%})")
        
        # 综合评分
        coverage_weighted = cov_rate * 100 * 0.4
        sanity_weighted = sanity_score * 0.3
        completeness_weighted = test_rate * 100 * 0.3
        total_score = coverage_weighted + sanity_weighted + completeness_weighted
        
        grade, suggestion = HealthReporter.get_grade(total_score)
        lines.append("")
        lines.append(f"综合评分: {total_score:.0f}/100 {grade}")
        lines.append(f"建议: {suggestion}")
        
        return "\n".join(lines)

# 使用示例
# 覆盖率检查
cc = CoverageThresholdChecker()
cc.set_thresholds({"api_client": 0.90, "quality_checker": 0.85})
coverage_data = {"api_client": 0.88, "quality_checker": 0.82}
results = cc.check(coverage_data)
for r in results:
    status = "✓" if r.passed else "✗"
    print(f"[{status}] {r.module}: {r.actual:.0%} (需要 {r.threshold:.0%})")

# 代码健康检查
mock_files = {
    "utils/api_client.py": "API_KEY = 'sk-123456'  # TODO: use env var",
    "utils/helper.py": "# Helper functions" + "\n" * 500
}
score, issues = CodeSanityChecker.check_project(mock_files)
print(CodeSanityChecker.get_report(score, issues))

# Tox 配置
tm = ToxManager()
tm.set_envlist(["py39", "py310", "py311"])
config = tm.create_config(
    test_dir="tests/",
    deps=["pytest", "pytest-cov", "openai"]
)
print(config)

# 健康报告
report = HealthReporter.generate_report(results, score, issues, 50, 60)
print(report)
```

---

## 练习题

### 练习题 1：实现差异化的覆盖率阈值引擎

**要求：**
实现一个支持差异化覆盖率的配置引擎。

**步骤：**
1. 定义核心模块、边缘模块的配置格式
2. 实现覆盖率自动检测
3. 支持阈值继承和覆盖
4. 生成覆盖率提升建议

### 练习题 2：实现代码安全扫描器

**要求：**
扩展 CodeSanityChecker，实现代码安全扫描。

**步骤：**
1. 添加 SQL 注入、XSS 等常见漏洞模式检测
2. 实现依赖包漏洞检测
3. 添加敏感信息检测规则
4. 生成安全报告

### 练习题 3：实现多项目健康度仪表盘

**要求：**
实现一个支持多项目健康度对比的仪表盘。

**步骤：**
1. 设计多项目数据存储
2. 实现健康度计算和对比
3. 生成可视化图表
4. 支持导出 PDF/HTML 报告

---
