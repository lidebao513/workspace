# Day 32 — 质量评估实战

## 一、今日目标

> 把 D31 真实 API 调用的结果，送入 d6 QualityChecker、d9 LLMJudge、d10 SchemaValidator 做多维质量评估。输出综合质量报告。

- 理解"调用日志回放"的管道模式
- 掌握 QualityChecker 不同 prompt 设定不同关键词检查
- 理解 LLMJudge 的离线评分逻辑
- 学会 SchemaValidator 对代码回复的 JSON 结构验证

---

## 二、管道架构

```
D31 API 调用日志 (run_logs/d31_api_*.json)
  │
  ├── QualityChecker.check()
  │     └── 根据 prompt_label 设定 expected_keywords / forbidden_keywords
  │
  ├── LLMJudge.score_offline()
  │     └── 基于回复长度和词汇多样性打分
  │
  └── SchemaValidator.validate_json_string()
        └── 只对 code_generation 类型的回复做 JSON 校验
  │
  └── 输出: d32_eval_*.json（综合评估报告）
```

---

## 三、QualityChecker 关键词策略

每个 prompt 类型有不同检查标准：

| Label | 期望关键词 | 检查目的 |
|-------|-----------|---------|
| cn_basic | 人工智能, AI, 计算机 | 确保讨论了定义 |
| en_basic | machine learning, data, algorithm | 英文关键词检查 |
| jp_basic | 人工知能, AI | 日语回复检查 |
| code_generation | binary_search, def | 代码必备元素 |
| role_constraint | 导数, 数学 | 数学老师角色保持 |
| multi_turn | 张三 | 上下文记忆检查 |

---

## 四、LLMJudge 离线评分

离线模式不调用真实 API，而是基于回复的**表层特征**估算分数：

```python
relevance    = min(10, len(reply) // 20)       # 回复越长→越相关
completeness = min(10, len(set(reply.split())) // 5)  # 词汇越多→越完整
fluency      = 8.0                              # 默认流畅
weighted     = rel*0.4 + comp*0.3 + fluency*0.3
```

> 实际使用时用 `score_online()` 调用 DeepSeek API 做评委，效果更准确。

---

## 五、SchemaValidator 代码验证

只对 `code_generation` 类型验证：

```python
schema = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "code": {"type": "string"},
    },
    "required": ["content"],
}
```

如果回复不是合法 JSON，标记为 invalid。

---

## 六、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| QualityChecker 中文 | 含"人工智能" | passed=True |
| QualityChecker 未知 label | 无关键词要求 | passed=True |
| LLMJudge 中文 | 任意回复 | 返回 overall/relevance/completeness |
| Schema 跳过 | 非代码类型 | checked=False |
| Schema 代码 | 合法 JSON | checked=True |
| 日志加载空目录 | 无日志 | 空列表 |

---

## 七、产出物

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d32_quality_eval.py` | 质量评估实战 | [OK] |
| `tests/d32_test_quality_eval.py` | 9 个测试 | [OK] 9/9 PASS |
| `day32_study.md` | 本文档 | [OK] |
