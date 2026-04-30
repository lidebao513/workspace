# Day 33 — Token 审计 + 多语言 + 压测集成

## 一、今日目标

> 三件事合一把手：用 d26 TokenAuditor 审计真实 API 费用、用 d8e 多语言检测验证中英日回复、规划 d22 压测方案。Phase 1（API 实战）的最后一天。

- 理解 Token 审计与异常检测的实际应用
- 掌握多语言检测器对不同语言的识别能力
- 理解压测方案的三种模式
- 学会把多个模块的输出整合为一个统一报告

---

## 二、三件事的管道

```
D31 API 日志 (run_logs/d31_api_*.json)
  │
  ├── TokenAuditor.record_call()
  │     └── prompt_tokens + completion_tokens → 费用 + 异常检测
  │
  ├── LanguageDetector.detect()
  │     └── 回复文本 → "zh" / "en" / "ja" / "code"
  │
  └── LoadTestPlan（方案描述）
        └── 3 种压测模式说明
  │
  └── d33_integration_*.json（综合报告）
```

---

## 三、Token 审计输出

```
总调用: 8
总 Token: 530
总费用: ¥0.00091（≈ 0.09 分）
异常检测: 无异常
```

---

## 四、多语言检测

| Label | 回复 | 检测 | 预期 | 结果 |
|-------|------|------|------|:----:|
| cn_basic | 人工智能... | zh | zh | ✅ |
| en_basic | Machine learning... | en | en | ✅ |
| jp_basic | 人工知能... | ja | ja | ✅ |
| code_generation | def binary_search... | code | code | ✅ |

---

## 五、压测方案

通过 d22 LoadTester 接口，提供三种方案：

| 名称 | 模式 | 描述 |
|------|------|------|
| steady_3 | 稳态 | 3 并发 × 10 次请求 |
| step_2_to_10 | 阶梯 | 2→5→10 逐级增加 |
| spike_10 | 突发 | 2 基准 → 10 突发 |

> 实际执行需要配置 DEEPSEEK_API_KEY，每次压测约消耗 ¥0.02。

---

## 六、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| Token 审计 | 3 条 OK 记录 | total_calls=3 |
| Token 审计空 | 空 results | total_calls=0 |
| 多语言 | 中文/英文/代码 | 正确检测 |
| 多语言空 | 空 results | total_checked=0 |
| 日志加载 | 无日志 | 返回 {} |
| 压测方案 | 调用 | 3 个 profile |

---

## 七、Phase 1 总结

| Day | 模块 | 测试 | 状态 |
|:----|:-----|:----|:----:|
| 31 | API 真调用 | 12/12 | ✅ |
| 32 | 质量评估实战 | 9/9 | ✅ |
| 33 | 审计+多语言+压测 | 7/7 | ✅ |

---

## 八、产出物

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d33_integration.py` | Token 审计+多语言+压测集成 | [OK] |
| `tests/d33_test_integration.py` | 7 个测试 | [OK] 7/7 PASS |
| `day33_study.md` | 本文档 | [OK] |
