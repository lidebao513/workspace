# Day 31 — DeepSeek API 真调用实战

## 一、今日目标

> 把离线模拟的测试平台接上真实 DeepSeek API。发送真实请求、记录 Token 消耗、估算费用、保存调用日志。从"模拟"到"真调"的一步。

- 理解真实 API 调用与离线 mock 的区别
- 掌握环境变量管理 API Key 的安全做法
- 学会记录每次调用的耗时、Token、费用
- 理解真实调用结果中的 finish_reason 和异常处理

---

## 二、为什么需要 D31？

d1-d30 的代码大部分是**离线模拟**——测试里的 `mock_response` 是手工构造的。但真正要验证平台可用，必须：

1. **发真实请求** → 确认客户端代码正确
2. **记录真实 Token** → d26 TokenAuditor 才能运作
3. **调质量评估** → d32 计划
4. **跑真实并发** → d33 计划

D31 就是"第一行真实 API 调用"。

---

## 三、架构设计

```
┌─────────────────────────────────────────────┐
│         d31_deepseek_tester.py              │
│                                             │
│  create_prompts() ← 10 个预置测试用例        │
│       │                                     │
│       ▼                                     │
│  run_single_call(client, prompt)            │
│       │                                     │
│       ├─ client.chat() → 真实 DeepSeek API  │
│       ├─ get_reply_text() → 提取回复        │
│       ├─ get_token_usage() → Token 统计     │
│       └─ estimate_cost() → 费用计算         │
│                                             │
│  main() ← 汇总 + JSON 日志                  │
└─────────────────────────────────────────────┘
```

---

## 四、安全设计

**绝不硬编码 API Key：**

```python
# 只从环境变量读取
api_key = os.environ.get("DEEPSEEK_API_KEY")

# 检查是否为占位符
if api_key == "your_deepseek_api_key_here":
    print("[!!] API Key 未配置")
```

配置方式（三种任选）：

```bash
# 1. 系统环境变量（推荐）
$env:DEEPSEEK_API_KEY='sk-xxx'

# 2. .env 文件
echo "DEEPSEEK_API_KEY=sk-xxx" > .env

# 3. 直接 export
export DEEPSEEK_API_KEY='sk-xxx'
```

---

## 五、费用估算

DeepSeek 官方定价（截至 2025-01）：

| 类型 | 价格 | 10 次调用预估 |
|------|------|--------------|
| 输入 tokens | ¥0.001 / 1K tokens | ~¥0.002 |
| 输出 tokens | ¥0.002 / 1K tokens | ~¥0.004 |
| **总计** | | **~¥0.006** |

计算公式：
```python
cost = (prompt_tokens / 1000 * 0.001
        + completion_tokens / 1000 * 0.002)
```

---

## 六、测试用例

| # | 标签 | 类型 | prompt 特征 | 预期 |
|--|------|------|------------|------|
| 1 | cn_basic | 基础 | 中文问答 | 中文回复 |
| 2 | en_basic | 多语言 | 英文解释 | 英文回复 |
| 3 | jp_basic | 多语言 | 日文问题 | 日文回复 |
| 4 | knowledge_cutoff | 时效性 | 2024 年事件 | 知识截止响应 |
| 5 | code_generation | 代码 | Python 代码 | 有代码块 |
| 6 | role_constraint | 安全 | 系统角色约束 | 数学老师语气 |
| 7 | edge_temperature_0 | 边界 | temperature=0 | 确定性输出 |
| 8 | edge_temperature_2 | 边界 | temperature=2 | 随机性高 |
| 9 | multi_turn | 多轮 | 5 轮对话 | 名称保持 |
| 10 | long_context | 边界 | 5000+ tokens | 正常回复 |

---

## 七、输出格式

每次调用记录为一个 JSON：

```json
{
  "label": "cn_basic",
  "category": "基础",
  "status": "OK",
  "duration_s": 1.234,
  "prompt_tokens": 45,
  "completion_tokens": 120,
  "total_tokens": 165,
  "cost_yuan": 0.000285,
  "finish_reason": "stop",
  "reply_length_chars": 85,
  "reply_preview": "人工智能（AI）是计算机科学的一个分支...",
  "error": null,
  "timestamp": "2026-04-30T..."
}
```

---

## 八、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| 无 API Key | `check_api_key()` | False |
| 占位符 Key | `DEEPSEEK_API_KEY=your_...` | False |
| 费用估算 | 1000+500 tokens | 公式正确 |
| prompts 完整性 | `create_prompts()` | 每个都有 messages+params |
| 多轮对话 | `create_multi_turn_prompt(5)` | 5 轮消息 |
| 长上下文 | `create_long_context_prompt()` | 2000+ chars |
| 无 Key 时 main | 无 API Key | exit code 1 |

---

## 九、产出物

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d31_deepseek_tester.py` | API 真调用入口 | [OK] |
| `tests/d31_test_deepseek_tester.py` | 12 个测试 | [OK] 12/12 PASS |
| `day31_study.md` | 本文档 | [OK] |
