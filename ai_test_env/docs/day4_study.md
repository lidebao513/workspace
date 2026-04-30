# Day 4：响应结构验证 + Token 基线 + 响应时间基线

> 对应 8 周计划第 1 周 Day 4
> 目标城市：上海 | 目标岗位：AI 测试工程师
> 学习时间：约 1.5-2 小时

---

## 一、今日学习目标

| 目标 | 说明 |
|:----|:------|
| 完全理解 API 响应结构 | choices / usage / finish_reason / created 每个字段 |
| 掌握响应验证器的设计思想 | 一个自动化验证工具，检查 9 个字段 |
| 建立 Token 基线 | 确定不同场景的 Token 消耗基准 |
| 建立响应时间基线 | 记录首次请求延迟、平均响应时间 |
| 验证各字段边界行为 | 响应为空、finish_reason 异常等边界 |

**面试对应问题：**
- "API 返回了哪些字段？你关注哪些？"
- "你怎么做 AI 接口的性能测试？"
- "Token 怎么换算成钱的？"
- "finish_reason 的 stop / length / content_filter 分别代表什么？"
- "你的测试跑完后产出了什么数据？"

---

## 二、前置知识讲解

### 2.1 API 响应结构总览

当你调用 `client.chat.completions.create(...)` 时，API 返回的是一个**结构化对象**，而不是一段纯文本。这个对象包含多个字段，每个字段都有特定的含义。

**完整结构图解：**

```
response = client.chat.completions.create(...)

response (ChatCompletion 对象)
│
├── .id              ── 请求的唯一标识，类似快递单号
│                      格式: "chatcmpl-xxxxx" 或 UUID
│                      作用: 追踪日志、排查问题时凭这个 ID 查
│
├── .object          ── 响应类型标识，固定值 "chat.completion"
│                      作用: 区分不同类型的 API 返回
│
├── .created         ── Unix 时间戳（秒），API 完成处理的时间
│                      作用: 计算端到端延迟、冷启动判断
│
├── .model           ── 实际使用的模型名
│                      作用: 确认是否用了正确的模型
│                      注意: 可能和你传的不一样（API 自动路由）
│
├── .choices[ ]      ── 回复列表（重要！核心数据在这里）
│   │                   通常长度=1，但理论上可以有多个
│   │
│   └── choices[0]
│       ├── .index         ── 第几个选择（通常为 0）
│       ├── .finish_reason ── 为什么停止（stop / length / content_filter）
│       └── .message
│           ├── .role      ── "assistant"（固定值）
│           └── .content   ── AI 回复的文本内容（← 最终你要的数据）
│
└── .usage           ── Token 使用统计（算钱的核心数据）
    ├── .prompt_tokens     ── 你输入用了多少 Token
    ├── .completion_tokens ── AI 回复用了多少 Token
    └── .total_tokens      ── 总和 = prompt + completion
```

### 2.2 逐字段详解（为什么重要 + 面试话术）

#### id 字段

```python
response.id  # 例如: "chatcmpl-b7a8c9d0e1f2" 或 "uuid-xxxxxxxx"
```

**作用：** 每次调用的唯一凭据。线上出了问题，你把这个 ID 发给 DeepSeek 技术支持，他们就能查到这次请求的所有日志。

**测试重点：**
- 非空 —— 空的 id 说明 API 返回异常
- 格式是不是预期的（DeepSeek 之前用 "chatcmpl-xxx"，后来改成了 UUID）

**面试话术：**
> "id 字段是我每轮测试都会记录的唯一标识。线上排查时，没有 id 等于没有线索。我们的测试框架会把这个 id 和测试用例编号一起写入日志，方便溯源。"

#### object 字段

```python
response.object  # 总是 "chat.completion"
```

**作用：** 告诉你这个对象是什么类型。如果以后 DeepSeek 出了新的 API 版本，这个值可能变。

**测试重点：**
- 是否等于 `"chat.completion"` —— 如果变了，说明 API 版本升级了，需要适配

#### created 字段

```python
response.created  # 例如: 1714200000（Unix 时间戳）
```

**作用：** API 完成处理的时间，用来计算"端到端耗时"。

**测试重点：**
- 是不是一个合理的时间戳（不是 0，不是负数，不是 50 年前）
- 和当前时间的偏差是否在合理范围内（偏差太大可能时间不同步）

#### model 字段

```python
response.model    # 例如: "deepseek-chat" 或 "deepseek-v4-flash"
```

**作用：** 确认实际用了什么模型。有时候你传 `deepseek-chat`，但实际回的是 `deepseek-v4-flash`。

**测试重点：**
- 非空
- 是否需要记录模型版本变化

#### choices 数组

```python
response.choices         # 列表，长度通常为 1
response.choices[0]      # 第一个（也是唯一一个）回复
```

**作用：** 所有回复内容都在这里。虽然现在返回 1 个，但理论上 API 可以返回多个。

**测试重点：**
- choices 不能为空
- 长度 >= 1

#### finish_reason 字段（关键中的关键）

```python
response.choices[0].finish_reason
# 可能的值: "stop" | "length" | "content_filter" | null
```

**这是衡量回复质量的核心指标。**

| finish_reason | 含义 | 是否正常 | 调优方向 |
|:-------------|:-----|:--------|:--------|
| `stop` | AI 自行判断回答完毕 | ✅ 正常 | 无需处理 |
| `length` | 达到 max_tokens 上限被截断 | ⚠️ 截断 | 调大 max_tokens |
| `content_filter` | 命中内容过滤 | ❌ 敏感 | 检查 prompt 是否有违规内容 |
| `null` | 流式模式未结束 | - | 流式专用 |

**生产环境监控：**
```
一个健康的 AI 服务，finish_reason 的正常分布应该是：
  stop:    99%+       ← 绝大多数回复正常
  length:  0.5%以下   ← 超过 1% 说明 max_tokens 不够
  content_filter: 0   ← 出现就需要排查
```

**面试话术：**
> "我每天监控 finish_reason 的分布。正常情况下 99% 以上是 stop。如果 length 比例超过 1%，说明 max_tokens 有瓶颈——比如某个场景的回复长度超过了预设值。content_filter 只要出现就要立刻查，因为这可能意味着用户输入了违规内容，或者我们的 system prompt 触发了误杀。"

#### message 结构

```python
response.choices[0].message.role     # "assistant"（固定值）
response.choices[0].message.content  # AI 的回复文本（你要的数据）
```

**测试重点：**
- role 必须是 "assistant"
- content 不能为 None
- content 可以为空字符串吗？（这是边界情况）

#### usage 对象（算钱的核心）

```python
response.usage.prompt_tokens     # 输入 Token
response.usage.completion_tokens # 输出 Token
response.usage.total_tokens      # 总 Token
```

**关键验证：**
```
prompt_tokens + completion_tokens == total_tokens
↑ 这个等式必须成立。如果不成立，说明 API 有 bug。
```

**Token 费用的计算：**

```
DeepSeek 官方定价（2026年）：
  输入（prompt_tokens）：0.14 元 / 百万 Token
  输出（completion_tokens）：0.28 元 / 百万 Token

一次普通对话的例子：
  输入：200 Token × 0.14 / 1,000,000 = 0.000028 元
  输出：150 Token × 0.28 / 1,000,000 = 0.000042 元
  一次对话总成本：0.00007 元

  每天 10 万次调用：10万 × 0.00007 = 7 元/天
  每月（30 天）：7 × 30 = 210 元
```

**面试话术：**
> "我从来不直接信赖文档上的定价，而是自己实测。建了一个 Token 基线表，把 5 种场景的 P/C/T 都记下来。这样每次模型升级后跑一遍基线，如果同样的场景 Token 消耗多了 30%，那就说明新模型有变化——不管文档怎么写。这种做法在传统测试里就叫基线测试。"

### 2.3 为什么需要响应验证器？

**没有验证器的困境：**

```
你写了个 AI 客服功能，上线跑了一周。
某天 DeepSeek 更新了 API，改了响应格式（比如 id 长度变了）。
你的代码没做字段验证，调用了 response.id.xxx 时报错。
结果：用户看到白屏，你才发现 API 变了。
```

**有了验证器之后：**

```
每天 CI 跑一次 test_response_baseline.py。
某天跑出了 WARN：id 格式变了。
你看到了警告，查了一下发现了 API 变更。
在用户感知到问题之前，你已经在 dev 环境发现了。
```

这就是**自动化验证**的价值——在你之前发现问题。

---

### 2.4 JSON 数据格式——API 通信的"通用语言"

**一句话定义：** JSON（JavaScript Object Notation）是一种轻量级的数据交换格式，它把结构化数据变成文本，方便程序之间读写。

**类比：填表 vs 手写**
```
手写（无序的）：
  张三，今年 28 岁，在北京工作
  → 程序读这个费劲：哪个是姓名？哪个是城市？

填表（JSON 的思维）：
  姓名：张三
  年龄：28
  城市：北京
  → 每个字段都有名字，程序一眼就能看懂
```

**JSON 的四种基本结构：**
```json
// 1. 对象（Object）—— 用 {} 包起来的一堆键值对
{
  "name": "张三",
  "age": 28
}

// 2. 数组（Array）—— 用 [] 包起来的一堆值
["苹果", "香蕉", "橘子"]

// 3. 基础值——字符串、数字、布尔、null
"hello"     // 字符串
42          // 数字
true        // 布尔
null        // 空

// 4. 嵌套——对象里套数组，数组里套对象
{
  "name": "张三",
  "hobbies": ["编程", "读书"],  // 数组套在对象里
  "address": {
    "city": "北京",
    "zip": "100000"
  }           // 对象套在对象里
}
```

**API 响应的 JSON 结构（这就是 Day 4 在操作的对象）：**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1714200000,
  "model": "deepseek-chat",
  "choices": [              // ← 数组（可能有多个回复）
    {
      "index": 0,
      "finish_reason": "stop",
      "message": {
        "role": "assistant",  // ← 嵌套对象
        "content": "你好！有什么可以帮助你的？"
      }
    }
  ],
  "usage": {
    "prompt_tokens": 27,
    "completion_tokens": 25,
    "total_tokens": 52
  }
}

// 访问路径（就是一层层往里走）：
// response.choices[0].message.content
//     ↑对象    ↑数组[0]  ↑对象    ↑字段
```

**Python 中操作 JSON：**
```python
import json

# API 返回的已经是 Python 对象了（SDK 自动解析了）
response = client.chat(...)  # ← 这是对象，不是字符串
reply = response.choices[0].message.content  # 直接点号访问

# 如果你自己收到 JSON 字符串：
text = '{"name": "张三"}'  # 字符串
parsed = json.loads(text)   # 转成 Python 字典
print(parsed["name"])       # 输出：张三

back_to_text = json.dumps(parsed)  # 字典转回字符串
```

**为什么响应验证器要对 JSON 字段做检查？**
- 如果 API 某天改了字段名（比如 `completion_tokens` 改成 `output_tokens`），你的访问代码就会报错
- 如果 API 某天改了字段类型（比如 `created` 从数字变成了字符串），同样会报错
- 定期验证 JSON 结构 = 提前发现 API 变更

---

### 2.5 Unix 时间戳——API 时间的"通用语言"

**一句话定义：** Unix 时间戳是从 1970 年 1 月 1 日 00:00:00 UTC 到现在的总秒数。API 用它表示时间而不是用"2026-04-30 09:24:00"。

**类比：**
```
普通日期（人类友好，机器不友好）：
  "2026年4月30日上午9点24分"
  → 不同时区的人看到的时间含义不同
  → 字符串比较不方便（"2月"

### 3.1 模块架构图

```
tests/test_response_baseline.py     ← 测试入口
    │  6 个测试用例
    │
    └── 依赖 ├── utils/api_client.py        ← 发起 API 调用
              │
              └── utils/response_validator.py ← 验证响应
                      │
                      ├── validate(response)          → 全面验证 9 个字段
                      ├── _check_id(response)         → 验证 id 非空且格式正确
                      ├── _check_object(response)     → 验证 object == "chat.completion"
                      ├── _check_created(response)    → 验证时间戳合理
                      ├── _check_model(response)      → 验证 model 非空
                      ├── _check_choices(response)    → 验证 choices 非空
                      ├── _check_finish_reason(response) → 验证 finish_reason 合法
                      ├── _check_role(response)       → 验证 role == "assistant"
                      ├── _check_content(response)    → 验证 content 非空
                      └── _check_usage(response)      → 验证 P + C == T
```

### 3.2 验证报告格式

每个验证项输出一个报告项：

```python
{
    "field": "id",           # 字段名
    "status": "PASS",        # PASS / FAIL / WARN
    "message": "..."         # 描述信息
}
```

**三种状态的判断标准：**

| 状态 | 含义 | 用例 |
|:----|:-----|:-----|
| **PASS** | 字段完全符合预期 | id 非空且格式正确 |
| **FAIL** | 字段不符合要求，需要修复 | usage 不存在，或 P + C != T |
| **WARN** | 字段异常但不致命，需要注意 | id 格式变了（UUID 替代 chatcmpl-x） |

### 3.3 响应时间基线设计

**为什么要分首次和后续？**
```
首次请求（冷启动 Cold Start）：
  API 需要加载模型 → 慢（可能 2-5 秒）
  
后续请求（热请求 Warm Request）：
  模型已加载 → 快（通常 1-2 秒）

如果不区分训练和首次，你的"平均响应时间"会被首次拉高。
好的做法：首次单独记录，后续取平均值。
```

**响应时间基线表格（理想值）：**

| 请求类别 | 基线（秒） | 说明 |
|:--------|:----------|:-----|
| 首次请求（冷启动） | 3-8s | 模型加载 + 请求处理 |
| 热请求（平均） | 1-3s | 模型已就绪 |
| 最大可接受延迟 | 10s | 超过此值需要排查 |
| timeout 设置 | 30s | 生产环境的超时保护 |

---

## 四、实际运行流程

```
python tests/test_response_baseline.py
  │
  ├── [Test 1] 完整结构验证（9 个字段逐一检查）
  │   ├── check id         → 非空 ✓
  │   ├── check object     → "chat.completion" ✓
  │   ├── check created    → 合理时间戳 ✓
  │   ├── check model      → 非空 ✓
  │   ├── check choices    → 非空 ✓
  │   ├── check finish     → "stop" 或 "length" ✓
  │   ├── check role       → "assistant" ✓
  │   ├── check content    → 非空 ✓
  │   ├── check usage      → P + C == T ✓
  │   └── 汇总：所有字段通过 → PASS
  │
  ├── [Test 2] Token 一致性验证（4 种场景）
  │   ├── 简短问答：P + C = T ✓
  │   ├── 中等长度：P + C = T ✓
  │   ├── 带 system prompt：P + C = T ✓
  │   └── 短回复：P + C = T ✓
  │
  ├── [Test 3] 响应时间基线
  │   ├── 第 1 次：5.2s（冷启动）
  │   ├── 第 2 次：1.8s
  │   ├── 第 3 次：1.5s
  │   ├── 第 4 次：2.1s
  │   ├── 第 5 次：1.6s
  │   └── 平均（不含首次）：1.75s
  │
  ├── [Test 4] 短回复 finish_reason
  │   ├── "1+1=2 对吗？" → finish=stop ✓
  │   ├── "只回复数字 7" → finish=stop ✓
  │   └── 短内容正常结束
  │
  ├── [Test 5] 截断时 finish_reason
  │   ├── max_tokens=5  → finish=length ✓
  │   ├── max_tokens=20 → finish=length ✓
  │   ├── max_tokens=50 → finish=length ✓
  │   └── max_tokens=500 → finish=stop ✓
  │
  ├── [Test 6] Token 基线统计（5 种场景）
  │   ├── 简短问答：P=27 + C=25 = T=52
  │   ├── 普通问答：P=38 + C=82 = T=120
  │   ├── 带 system：P=47 + C=65 = T=112
  │   ├── 多轮对话：P=58 + C=88 = T=146
  │   ├── 长输入：P=241 + C=76 = T=317
  │   └── 基线汇总 + 费用计算
  │
  └── Day 4 完成！
```

---

## 五、工作中怎么用

### 场景 1：上线前的基线检查

**背景：** 要上线一个新功能或换新模型版本，需要确认响应结构没变。

```python
# 步骤 1：跑一遍 test_response_baseline.py
# 步骤 2：对比上一次的基线数据
# 步骤 3：判断是否升级

new_report = run_baseline()
old_report = load_baseline("last_production.json")

if new_report["changes_detected"]:
    print("检测到 API 响应变化，请确认：")
    for change in new_report["changes"]:
        print(f"  - {change}")
    print("建议：暂缓上线，确认变化原因")
else:
    print("基线一致，可以上线")
```

### 场景 2：每天跑一轮 CI 监控

**背景：** 在 CI 中每天自动跑基线测试，防止 API 偷偷变化没发现。

```python
# .github/workflows/daily_ci.yml
# 每天早上 8 点执行：
#   cd ai_test_env && python tests/test_response_baseline.py
#
# 如果基线检查失败 → 发邮件告警：API 可能发生了变化
# 如果 Token 消耗变化超过 20% → 发送告警：成本异常
```

### 场景 3：性能退化分析

**背景：** 某天用户投诉"AI 回复越来越慢了"。

```python
# 检查响应时间基线表
# 发现本周平均响应时间从 1.8s 涨到了 3.5s

# 排查方法：
# 1. 网络延迟：用 curl 测一下 API 的 TCP 延迟
# 2. API 服务：看是否接近高峰时段
# 3. 模型变化：查一下有没有模型升级

# 最终发现是网络波动造成的（某云节点故障）
# 对照基线数据确认问题 + 给出恢复预期
```

### 场景 4：新 API 集成测试

**背景：** 你们决定从 DeepSeek 切换到通义千问，或者增加第二供应商。

```python
# 1. 换一个 base_url，跑一遍 test_response_baseline.py
# 2. 对比两份报告：

print("=== 两个 API 的对比基线 ===")
print(f"{'维度':<15} {'DeepSeek':<20} {'通义千问':<20}")
print(f"{'平均响应时间':<15} {'1.8s':<20} {'2.3s':<20}")
print(f"{'平均 Total Token':<15} {'120':<20} {'135':<20}")
print(f"{'平均费用/次':<15} {'0.00007元':<20} {'0.00009元':<20}")

# 这种对比数据，直接支撑了技术选型决策
```

---

## 六、代码逐行讲解

### 6.1 `utils/response_validator.py` — 验证器模块

这个文件的每个方法，都有三个状态（PASS / FAIL / WARN）的处理逻辑。

#### validate 方法（入口）

```python
@staticmethod
def validate(response):
    checks = []
    # 逐一检查 9 个字段
    checks.append(ResponseValidator._check_id(response))
    checks.append(ResponseValidator._check_object(response))
    checks.append(ResponseValidator._check_created(response))
    checks.append(ResponseValidator._check_model(response))
    checks.append(ResponseValidator._check_choices(response))
    checks.append(ResponseValidator._check_finish_reason(response))
    checks.append(ResponseValidator._check_role(response))
    checks.append(ResponseValidator._check_content(response))
    checks.append(ResponseValidator._check_usage(response))

    # 统计 PASS / FAIL / WARN 数量
    passed = sum(1 for c in checks if c["status"] == "PASS")
    failed = sum(1 for c in checks if c["status"] == "FAIL")

    return {
        "all_pass": failed == 0,  # 只要没有 FAIL，就算全部通过（WARN 不阻塞）
        "checks": checks,
        "summary": {"total": len(checks), "passed": passed, "failed": failed,
                     "warned": len(checks) - passed - failed},
    }
```

**设计要点：**
- **WARN 不阻塞流程**：格式变了但能用（比如 id 从旧格式变成 UUID），记下来但不拦
- **"all_pass" 的判断条件**：只要没有 FAIL 就算通过——WARN 只是提醒不是错误

#### _check_id 方法——WARN 的典型用法

```python
@staticmethod
def _check_id(response):
    if not response.id:
        return {"field": "id", "status": "FAIL", "message": "id 为空"}
    if "chatcmpl" not in response.id.lower():
        return {"field": "id", "status": "WARN", "message": f"id 格式异常: {response.id}"}
    return {"field": "id", "status": "PASS", "message": response.id[:40]}
```

**为什么 id 格式变了只发 WARN 不发 FAIL？**
- id 格式变化不影响功能（你只是用它做日志追踪的 ID）
- 但这是一个信号——DeepSeek 可能改了后端实现
- 如果后来他们换了其他东西，可能就有影响了

**实际发现（Day 4 运行时）：**
```
[WARN] id: id 格式异常: 33cadc80-...  ← UUID 格式
```
DeepSeek 新版确实改了 id 格式，验证器发现并告警了。

#### _check_created 方法——时间验证

```python
@staticmethod
def _check_created(response):
    now = int(time.time())
    if not response.created:
        return {"field": "created", "status": "FAIL", "message": "created 为空"}
    if abs(response.created - now) > 300:  # 超过 5 分钟偏差
        return {"field": "created", "status": "WARN",
                "message": f"时间戳偏差: response={response.created}, now={now}"}
    return {"field": "created", "status": "PASS", "message": f"时间戳 {response.created}"}
```

**为什么偏差超过 5 分钟才告警？**
- 你的机器和 API 服务器时间可能有 1-2 秒偏差
- 网络延迟也可能造成几秒偏差
- 300 秒（5 分钟）的偏差才说明真正有问题
- 如果偏差很大 → 可能是 API 服务器时间跑偏了 → 日志时间会混乱

#### _check_usage 方法——核心校验

```python
@staticmethod
def _check_usage(response):
    if not response.usage:
        return {"field": "usage", "status": "FAIL", "message": "usage 为空"}
    usage = response.usage
    prompt = getattr(usage, "prompt_tokens", None)
    completion = getattr(usage, "completion_tokens", None)
    total = getattr(usage, "total_tokens", None)

    # 子字段都存在吗？
    if prompt is None or completion is None or total is None:
        return {"field": "usage", "status": "FAIL", "message": "缺少子字段"}

    # Token 有可能是负数吗？（理论上不会，但边界测试要覆盖）
    if prompt < 0 or completion < 0 or total < 0:
        return {"field": "usage", "status": "FAIL", "message": "Token 为负数"}

    # 核心等式检查
    if prompt + completion != total:
        return {"field": "usage", "status": "FAIL",
                "message": f"P({prompt}) + C({completion}) != T({total})"}

    return {"field": "usage", "status": "PASS", "message": f"P={prompt} C={completion} T={total}"}
```

**设计思路：**
- 先检查 usage 是否存在（不存在 → 直接 FAIL）
- 再检查三个子字段是否都正确（存在但不全 → FAIL）
- 接着检查数据合理性（负数 → FAIL，虽然理论上不会发生）
- 最后检查核心等式（P+C=T，验证 API 自己的统计是否自洽）
- 全部通过 → PASS

#### print_report 方法——美化输出

```python
@staticmethod
def print_report(report):
    print(f"\n{'=' * 50}")
    print(f"API 响应验证报告")
    print(f"{'=' * 50}")
    icons = {"PASS": "[OK]", "FAIL": "[XX]", "WARN": "[??]"}
    for check in report["checks"]:
        icon = icons.get(check["status"], "  ")
        print(f"  {icon} [{check['status']}] {check['field']}: {check['message']}")
    s = report["summary"]
    print(f"\n  汇总: {s['passed']}/{s['total']} 通过, {s['failed']} 失败, {s['warned']} 警告")
    print(f"  {'全部通过' if report['all_pass'] else '需要修复'}")
```

### 6.2 `tests/test_response_baseline.py` — 测试入口

这个文件包含 6 个测试函数，覆盖了响应验证、Token 一致性、响应时间、finish_reason 边界、Token 基线这 5 个维度。

#### Test 1：完整结构验证

```python
def test_full_structure_validation(client):
    messages = [{"role": "user", "content": "你好，请简单介绍一下你自己。"}]
    response = client.chat(messages, max_tokens=200)
    report = ResponseValidator.validate(response)
    ResponseValidator.print_report(report)
```

**设计意图：**
- 这是一个"黄金路径"测试——用最正常的请求验证所有字段
- 如果这里的 9 个字段有任何异常，就说明 API 有问题了

#### Test 2：Token 一致性验证

```python
def test_token_consistency(client):
    cases = [
        ("简短问答", [{"role": "user", "content": "你好"}]),
        ("中等长度", [{"role": "user", "content": "请用 200 字介绍 Python 语言。"}]),
        ("带 system", [
            {"role": "system", "content": "你是一个 Python 专家。"},
            {"role": "user", "content": "tuple 和 list 的区别是什么？"}
        ]),
        ("短回复", [{"role": "user", "content": "是"}]),
    ]
    for name, messages in cases:
        response = client.chat(messages, max_tokens=200)
        p, c, t = ...  # 提取三个 Token 值
        assert p + c == t, "Token 不一致！"
```

**为什么选这 4 种场景？**
- 简短问答：最轻量级（基线最低值）
- 中等长度：典型场景（平均值）
- 带 system：system prompt 会增加 prompt_tokens（测试 system 是否占用 token）
- 短回复：验证"是"这种极简回复的 Token 消耗（边界）

#### Test 3：响应时间基线

```python
def test_response_time(client):
    for count in [1, 3, 5]:           # 分别记录 1 次、3 次、5 次
        times = []
        for i in range(count):
            start = time.time()
            response = client.chat(messages)
            elapsed = time.time() - start
            times.append(elapsed)
        avg = sum(times) / len(times)
        print(f"{count} 次平均: {avg:.2f}s")
```

**设计思路：**
- 1 次单独记录（冷启动值）
- 3 次取平均（快速基线）
- 5 次取平均（稳定基线）
- 通过三个层级的记录，既能看到冷启动影响，也能看出稳定后的性能

#### Test 4 和 Test 5：finish_reason 的双向验证

这两个测试是成对出现的——一个测正常结束，一个测截断结束。

```python
# Test 4：正常场景
response = client.chat(messages, max_tokens=100)
assert response.choices[0].finish_reason == "stop"

# Test 5：截断场景
response = client.chat(messages, max_tokens=5)
assert response.choices[0].finish_reason == "length"
```

**为什么需要两个测试？**
- 只有一个测试的话，你可能默认 finish_reason 一直是 "stop"
- 通过"短回复+stop"和"截断+length"两个测试，你完整验证了 finish_reason 的两种主要状态
- 以后发现 finish_reason 有其他值（比如 content_filter），可以再加测试

#### Test 6：Token 基线统计

```python
def test_token_baseline(client):
    scenarios = [
        ("简短问答", ...),
        ("普通回答", ...),
        ("带 system", ...),
        ("多轮对话", ...),
        ("长输入", ...),
    ]
    records = []
    for name, messages in scenarios:
        response = client.chat(messages, max_tokens=300)
        records.append(extract_usage(response))

    # 汇总
    for record in records:
        print(f"  {record['scenario']}: P={p} + C={c} = T={t}")
    print(f"\n  平均 Prompt Tokens: {avg_p}")
    print(f"  平均 Completion Tokens: {avg_c}")
    print(f"  本次费用: 约 {cost} 元")
```

**基线数据怎么用？**

场景 | Prompt Tokens | Completion Tokens | Total Tokens
--- | --- | --- | ---
简短问答 | ~27 | ~25 | ~52
普通回答 | ~38 | ~82 | ~120
带 system | ~47 | ~65 | ~112
多轮对话 | ~58 | ~88 | ~146
长输入 | ~241 | ~76 | ~317

**面试话术：**
> "我建了 5 种场景的 Token 基线表。每次 DeepSeek 模型升级或我们换了 prompt 模板，我都会重新跑一次基线。快速问答的 Token 消耗多了 20% 就说明变化了——不需要看 release notes，数据会说话。"

---

## 七、面试常见问题与回答

### Q1：API 返回了哪些字段？你关注哪些？

> "顶层有 id、object、created、model、choices、usage 六个字段。我最关注 finish_reason 和 usage。
>
> finish_reason 是衡量回复质量的入口——stop 说明正常，length 说明被截断，content_filter 可能触发了安全策略。我每天看 finish_reason 的分布，就像看服务器的 200/4xx/5xx 分布一样。
>
> usage 是算钱的依据。我写了一行验证：prompt_tokens + completion_tokens 必须等于 total_tokens。一开始觉得这肯定对，后来真碰上一次 P+C < T 的情况——API 少报了 3 个 Token，虽然钱很少，但态度很重要：API 本身的统计都不准，你敢信它的其他输出吗？
>
> 我把这 9 个字段写进了验证器，每次调用自动检查一遍，输出一份验证报告。"

### Q2：你怎么做 AI 接口的性能测试？

> "我区分冷启动和热请求。首次请求因为模型加载会慢 2-3 倍，这个单独记录。稳定后的平均耗时才是真实性能。我跑 5 次取平均，记录最短、最长、平均三个值。波动超过 50% 说明网络或服务不稳定。
>
> 生产环境我会把这个做成自动化：每天 CI 跑一轮，响应时间超出基线 30% 就发告警。之前遇到过某云节点网络抖动，2 分钟超时影响了 30% 的请求——我们没有时效性监控，过了两天才发现。后来加了基线监控，类似的问题当天就能发现。"

### Q3：Token 怎么换算成钱的？

> "DeepSeek 的定价是输入 0.14 元/百万 Token，输出 0.28 元/百万 Token。一次普通问答消耗 300-800 Token，成本只有 0.00007-0.0001 元。表面上很便宜，但如果每天 100 万次调用，一天就 70-100 元，一个月 2000-3000 元。
>
> 其实 AI 测试的真正瓶颈不是费用。一个精心设计的测试用例可能只花 0.0001 元，但一个没有覆盖到的边界情况可能导致上线后的大问题。成本 vs 覆盖率的权衡，才是 AI 测试要思考的核心问题。"

### Q4：finish_reason 有哪些值？各代表什么？

> "标准情况下有 4 种：stop（正常结束）、length（被 max_tokens 截断）、content_filter（命中安全策略）、null（流式模式进行中）。
>
> 我监控 finish_reason 的分布比例。如果 length 超过 1%，说明某个场景的 max_tokens 设小了——比如我们有个场景要生成 500 字的报告，但 max_tokens 只设了 200，一半的回复都被截断了。这种问题不做分布监控很难发现，因为用户只会觉得 AI 回答'总说一半'，不会直接报 bug。"

### Q5：你的测试跑完后产出了什么数据？

> "一份 9 字段验证报告（哪几个字段 PASS/FAIL/WARN）、一份 Token 基线表（5 种场景的 P/C/T 数据）、一份响应时间基线（首次和平均耗时）。这些数据是后续所有测试的参考基准。版本升级后，先跑基线对比，字段变了或 Token 消耗变了都立刻发现。
>
> 实际上在 Day 4 的测试中我就发现了一个问题——DeepSeek 换了一个 id 格式，从 chatcmpl-xxx 改成了 UUID。验证器捕捉到了这个 WARN，证明了响应的自动化验证不是无用功，它有真实价值。"

---

## 八、今日产出物清单

| 文件/模块 | 说明 | 面试价值 |
|:---------|:-----|:--------|
| `utils/response_validator.py` | 9 字段验证器 | 展示自动化验证能力 |
| `tests/test_response_baseline.py` | 6 个测试（验证+基线+时间） | 展示基线测试思路 |
| **Token 基线表** | 5 种场景的 P/C/T 数据 | 展示数据驱动测试思维 |
| **响应时间基线** | 冷启动 + 热请求数据 | 展示性能测试基础 |

---

## 九、Day 4 自检清单

完成后打勾：

- [ ] 理解 API 响应结构的 6 个顶层字段
- [ ] 理解 finish_reason 的三种值及其含义
- [ ] 理解 Token 的 P + C == T 验证等式
- [ ] 理解为什么 id 格式变化应该发 WARN 而不是 FAIL
- [ ] 理解冷启动和热请求的区别
- [ ] 能默写 Token 费用换算公式
- [ ] 能说出 5 种场景的 Token 消耗大概范围
- [ ] 能回答上面 5 个面试问题中的至少 4 个

---

## 十、敲完代码后运行

```bash
cd ai_test_env
python tests/test_response_baseline.py
```

运行后你会看到：
1. 9 个字段逐一验证报告（PASS / FAIL / WARN）
2. 4 种场景的 Token 一致性验证（P+C=T 是否成立）
3. 首次请求时间