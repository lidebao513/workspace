# Day 27 — 全量测试运行器

## 一、今日目标

> 把 26 个测试模块组织成"一键运行"的 FullTestRunner——支持 smoke / regression / security / e2e / full 五种模式，记录每次运行结果，输出摘要报告。Day 21 的 CLI 提供了命令行入口，Day 27 提供了批量运行的引擎。

- 理解全量运行器的层级设计和模块映射
- 掌握 pytest 结果解析和汇总
- 学会运行日志的 JSON 持久化
- 理解历史追踪和失败模块突出显示

---

## 二、为什么需要全量运行器？

手动执行 `python -m pytest tests/d6_test_quality.py` 跑 26 个模块太慢。需要一个工具：

- **一键跑通**：`runner.run(RunLevel.FULL)` 执行所有测试文件
- **分层跑**：PR 提交前只跑 `smoke` 层（<30s），每天定时跑 `full`
- **结果记录**：每次运行保存到 `run_logs/`，可回查历史
- **失败高亮**：只看哪些模块failed，不用人工翻 pytest 输出

---

## 三、层级设计

### 3.1 层级映射

| 层级 | 包含模块数 | 预估耗时 | 使用场景 |
|------|-----------|---------|---------|
| **SMOKE** | 5 | ~15s | 每次 commit |
| **REGRESSION** | 16 | ~30s | 每日回归 |
| **SECURITY** | 2 | ~10s | 每日安全 |
| **E2E** | 3 | ~15s | 每周端到端 |
| **FULL** | 全部 | ~60s | 全量验证 |

### 3.2 模块映射定义

```python
MODULE_MAP = {
    RunLevel.SMOKE: [
        "tests/d1_test_key_manager.py",
        "tests/d2_test_client.py",
        "tests/d4_test_request_format.py",
        "tests/d16_test_browser_checker.py",
        "tests/d17_test_suite_manager.py",
    ],
    RunLevel.REGRESSION: [
        "tests/d6_test_quality.py",
        "tests/d7_test_consistency.py",
        # ... 16 个回归模块
        "tests/d26_test_token_auditor.py",
    ],
    # ...
}
```

---

## 四、运行流程

```
run(level=FULL)
  │
  ├── 选择模块列表（按层级映射或自动发现）
  │
  ├── 逐个运行：
  │     ├── subprocess.run(["pytest", module, "-q"])
  │     ├── 解析 stdout 提取 passed/failed/skipped 数
  │     └── 记录 ModuleResult（模块名、通过数、用时）
  │
  ├── 汇总 RunResult
  │     ├── total_passed / total_failed
  │     ├── all_passed 布尔值
  │     └── summary() 可读报告
  │
  └── _save_log() 写入 run_logs/run_YYYY-MM-DDTHH-mm-ss.json
```

---

## 五、结果解析

pytest 的 `-q` 模式输出格式：

```
                                                     ← 点号表示进度
3 passed in 0.05s                                    ← 纯通过
3 passed, 1 failed in 0.05s                          ← 有失败
3 passed, 1 failed, 2 skipped in 0.05s               ← 有跳过
```

解析逻辑：

```python
for line in stdout.split("\n"):
    if "passed" in line and "failed" in line:
        parts = line.split()
        for i, p in enumerate(parts):
            if p == "passed":
                passed = int(parts[i-1])
            elif p == "failed":
                failed = int(parts[i-1])
```

---

## 六、运行日志

每次运行自动写入 JSON：

```json
{
  "timestamp": "2026-04-30T19:00:00",
  "level": "full",
  "total_modules": 26,
  "total_passed": 535,
  "total_failed": 0,
  "all_passed": true,
  "total_time_s": 42.5,
  "modules": [
    {"module": "tests/d1_test_key_manager.py", "passed": 8, "failed": 0, "skipped": 0, "duration_s": 0.3},
    ...
  ]
}
```

---

## 七、使用示例

```python
from utils.d27_full_runner import FullTestRunner, RunLevel

runner = FullTestRunner()

# 冒烟测试（快速）
result = runner.run(RunLevel.SMOKE)
print(runner.summary(result))

# 安全测试
result = runner.run(RunLevel.SECURITY)
print(runner.summary(result))

# 全量测试
result = runner.run(RunLevel.FULL)
print(runner.summary(result))
print(runner.history())
```

输出示例：
```
━━━ 全量测试报告 [full] ━━━
时间: 2026-04-30T19:00:00
模块数: 32
结果: [OK] All Passed
总计: 535 passed, 0 failed
总耗时: 42.50s
```

---

## 八、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| ModuleResult | 有失败 | success_rate < 1, passed_str == "[!!]" |
| RunResult 汇总 | 求和 | total_passed = sum(all模块) |
| RunResult 空 | 无模块 | all_passed=True |
| 层级映射 | 所有层级 | 都有模块 |
| 自动发现 | _discover_all | 26+ 模块 |
| 摘要 | 有通过/失败 | 包含对应关键词 |
| 历史 | 多次运行 | 仅显示最近 N 次 |
| 日志 | _save_log | 写入 JSON 文件 |

---

## 九、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d27_full_runner.py` | 全量测试运行器 | [OK] |
| `tests/d27_test_full_runner.py` | 17 个测试 | [OK] 17/17 PASS |
| `day27_study.md` | 本文档 | [OK] 已创建 |
