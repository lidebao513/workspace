# Day 18 — CI/CD 集成（GitHub Actions）

## 一、今日目标

> 学会为 AI 测试项目配置 CI/CD 流水线，实现自动化的门禁检查和质量保障。

- 理解 CI 门禁策略（ALL_PASS / THRESHOLD / NO_REGRESSION / BLOCKING_ONLY）
- 掌握 GitHub Actions Workflow YAML 配置生成
- 了解分层 CI 触发策略（PR 触发 Smoke / 每日回归 / 每周安全）
- 会写门禁检查脚本（通过率低于阈值时 exit 1 阻止合并）

---

## 二、核心设计

### 门禁策略对比

| 策略 | 适用层级 | 行为 |
|------|---------|------|
| ALL_PASS | smoke, security | 必须 100% 通过 |
| THRESHOLD | regression, e2e | 可接受 >=95% 或 >=80% |
| NO_REGRESSION | A/B 对比 | 检测是否引入新失败 |
| BLOCKING_ONLY | performance | 安全失败直接拦截，其他用阈值 |

### CI 触发配置

```yaml
# 每次 PR 触发冒烟（3 分钟内完成）
on: [push, pull_request]
jobs:
  smoke: python -m pytest -m "smoke"

# 每天凌晨 2 点跑回归 + 安全
on:
  schedule:
    - cron: '0 2 * * *'

# 每周一跑深度安全
on:
  schedule:
    - cron: '0 6 * * 1'
```

### CIConfigGenerator 产出

| workflow 文件 | 触发 | 耗时 | 门禁 |
|--------------|------|------|------|
| smoke.yml | PR | ~2min | 100% |
| regression.yml | 每日 10:00 | ~10min | >=95% |
| security.yml | 每周一 | ~5min | 100% |
| full-pipeline.yml | PR + 每日 | ~15min | 分层 |

### 关键设计点

- **`SETUP_PYTHON_STEPS` 用方法内 f-string**：`python_version` 参数才能生效
- **`${{ secrets.DEEPSEEK_API_KEY }}`**：API Key 通过 GitHub Secrets 注入
- **Artifacts 上传**失败也上传（`if: always()`）
- **门禁脚本 `CIGate.run_gating_check()`** 失败时 `sys.exit(1)` 使整个 job fail

---

## 三、运行验证

```
22 passed in 0.03s
```

## 四、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/ci_config_gen.py` | CI 配置生成器 + 门禁检查 | [OK] |
| `tests/test_ci_config_gen.py` | 22 个测试 | [OK] 22/22 PASS |
| `day18_study.md` | 本篇文档 | [OK] 已完成 |
