# Day 19 — 开源工具整合（Tox + Coverage + Sanity）

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
