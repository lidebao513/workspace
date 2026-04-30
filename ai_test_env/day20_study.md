# Day 20 — 测试数据管理

## 一、今日目标

> 学会管理 AI 测试中的数据集：合成生成、脱敏处理和版本追踪。

- 理解 DataProfile 配置模式（类型比例、种子、版本控制）
- 掌握 PromptDataFactory 的模板替换和随机填充
- 掌握 ResponseDataFactory 的多种回复类型生成
- 学会 DataMasker 的 5 种脱敏方式
- 理解 DataVersionTracker 的版本管理和 diff

---

## 二、核心设计

### DataProfile 配置

```python
profile = DataProfile(
    name="injection_suite",
    count=100,
    seed=42,
    version="2.1.0",
    categories=["sql", "xss", "csfr"],
    response_type_ratios={
        "valid": 0.70,       # 正常回复
        "truncated": 0.10,   # 截断
        "rejected": 0.10,    # 拒绝
        "empty": 0.05,       # 空
        "error": 0.05,       # 错误
    }
)
```

### PromptDataFactory 模板类型

| 类型 | 模板 | 示例 |
|------|------|------|
| 定义 | What is {topic}? | "What is machine learning?" |
| 解释 | Explain {concept} in {style} terms | "Explain dependency injection in expert terms" |
| 写作 | Write a {length} {genre} about {subject} | "Write a short poem about AI testing" |
| 对比 | Compare and contrast {A} and {B} | "Compare and contrast CNNs and RNNs" |
| 步骤 | Step-by-step guide to {topic} | "Step-by-step guide to fine-tuning" |

### DataMasker 脱敏效果

| 类型 | 输入 | 输出 |
|------|------|------|
| 邮箱 | user@example.com | u***@example.com |
| 手机 | 13812345678 | 138****5678 |
| 身份证 | 110101199001011234 | 110101********1234 |
| API Key | sk-abcdefghijklmnopqrst | sk-****************qrst |
| IP | 192.168.1.1 | 192.168.*.* |

### DataVersionTracker 版本流

```
0.0.1 → add_entries("Initial import") → 0.0.2
     → update_entries("Fix typos") → 0.0.3
     → update_entries("Add 50 cases") → 0.0.4
```

版本间 diff 跟踪：added / removed / modified 三类变更。

---

## 三、运行验证

```
42 passed in 0.05s
```

## 四、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/data_manager.py` | 数据管理模块 | [OK] |
| `tests/test_data_manager.py` | 42 个测试 | [OK] 42/42 PASS |
| `day20_study.md` | 本篇文档 | [OK] 已完成 |

---

## 五、面试话术

**合成数据相关：**
"我用 PromptDataFactory 按模板批量生成测试 Prompt。种子一致性保证每次生成相同数据，支持跨版本对比测试。"

**脱敏相关：**
"上线前必须跑 DataMasker 脱敏扫描。mask_all 能一次性处理 5 种敏感信息。如果 API Key 因长度不够没被匹配，我们有 has_sensitive_data 做双重校验。"

**版本管理相关：**
"每个数据集都有版本号，update_entries 会自动做 diff——新增了多少条、修改了多少条、删除了多少条，都在 changelog 里。"
