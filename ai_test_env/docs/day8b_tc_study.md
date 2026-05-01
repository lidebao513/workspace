# Day 8b（第 2 周补充）：Agent / Tool Calling 测试

> 对应 8 周计划第 2 周补充模块
> 目标城市：上海 | 目标岗位：AI 测试工程师
> 学习时间：约 1.5-2 小时

---

## 学习目标

1. **理解核心概念**：掌握 Tool Calling（函数调用）的工作原理，理解其如何解决大模型的知识截止日期和实时数据问题
2. **掌握测试层次**：熟练运用工具选择、参数正确性、多工具协作三个层次的测试方法
3. **识别错误模式**：能够识别并分类 8 种常见的 Tool Calling 错误模式
4. **实现测试模块**：能独立实现工具调用解析器和验证逻辑
5. **设计测试用例**：掌握单一工具、多工具、合理拒绝等场景的测试用例设计

---

## 一、今日学习目标

| 目标 | 说明 |
|:----|:------|
| 理解什么是 Tool Calling / Function Calling | AI 模型调用外部工具的原理 |
| 掌握工具调用测试的三个层次 | 选对工具 / 参数正确 / 多工具协作 |
| 设计工具调用测试用例 | 单一工具、多工具、合理拒绝等场景 |
| 实现工具调用解析器 | 解析多种格式的工具调用输出 |
| 构建批量测试和报告 | 统计通过率、分数、问题分布 |
| 理解面试中的 Agent 测试知识 | Function Calling 是 AI 测试工程师的核心能力 |

**面试对应问题：**
- "你怎么测试 Function Calling 的正确性？"
- "工具调用有哪些常见的错误模式？"
- "模型选错了工具怎么办？怎么判断是不是模型问题？"
- "多工具链式调用怎么测？"

---

## 二、前置知识讲解

### 2.1 什么是 Tool Calling / Function Calling？

**一句话定义：** Tool Calling（工具调用，也叫 Function Calling）让大模型可以向外部系统请求信息或执行操作——模型只负责"决定调用什么"，真正的操作由外部函数完成。

**类比：**
```
你（用户）说： "帮我查一下明天上海到北京的机票"

模型（思考）： "这是一个查机票的需求，我应该调用 search_flights 工具"
模型（调用）： search_flights(origin="上海", destination="北京", date="明天")
模型系统（执行）： 调用真实 API 查询
模型（得到结果）： "查到有以下航班..."
模型（回复）： "明天上海到北京有以下航班：...（列出来）"
```

**为什么需要 Tool Calling？**

```
没有 Tool Calling：
  ┌──────────────────────────────────────────┐
  │ 用户：今天北京天气怎么样？                │
  │ 模型：北京今天天气晴，温度 22 度          │
  │        ↑ 但是模型在"编造"（它是根据训练  │
  │        数据猜的，不是实时数据！）          │
  └──────────────────────────────────────────┘

有 Tool Calling：
  ┌──────────────────────────────────────────┐
  │ 用户：今天北京天气怎么样？                │
  │ 模型：我要调用 get_weather(city="北京")   │
  │ 系统：调用真实天气 API                    │
  │ 模型：根据 API 返回，今天北京...          │
  │        ↑ 这是真实数据！                   │
  └──────────────────────────────────────────┘
```

**面试话术：**
> "Tool Calling 解决了大模型的核心痛点——知识截止日期和缺少实时数据。
> 我理解它的本质是：模型输出结构化的函数调用请求，由外部系统执行
> 真实操作后把结果返回给模型，模型再生成最终回答。
> 作为测试工程师，我需要验证整个链路：工具选择、参数生成、结果使用。"

### 2.2 OpenAI 的 Tool Calling 格式

完整的 Tool Calling 流程包含三个步骤：

**步骤 1：注册工具（给模型看）**
```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "获取指定城市的天气",
    "parameters": {
      "type": "object",
      "properties": {
        "city": {
          "type": "string",
          "description": "城市名"
        }
      },
      "required": ["city"]
    }
  }
}
```

**步骤 2：模型决定调用工具**
```json
{
  "tool_calls": [
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"city\": \"北京\"}"
      }
    }
  ]
}
```

**步骤 3：系统执行并返回结果给模型**
```json
{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "content": "{\"temperature\": 22, \"condition\": \"晴\"}"
}
```

### 2.3 Tool Calling 测试的三个层次

```
层次 1：Tool-Select（选对工具）         ← 最基础
  ─ 模型能否从多个工具中选择正确的那个？
  ─ 不相关的问题能否"合理拒绝"不调用？
  ─ 是不是调用了不该调用的工具（安全）？

层次 2：Param-Gen（参数正确性）        ← 最容易出错
  ─ 参数名是否正确（有没有拼写错误）？
  ─ 参数值是否正确提取（"下周二" → 日期转换）？
  ─ 必填参数是否全部提供？
  ─ 参数类型是否正确（string 还是 integer）？

层次 3：Multi-Tool（多工具协作）        ← 复杂场景
  ─ 需要多个工具时能否依次调用？
  ─ 工具 A 的输出能否作为工具 B 的输入？
  ─ 链式调用 vs 并行调用的选择？
```

### 2.4 常见的 Tool Calling 错误模式

| 错误模式 | 描述 | 示例 | 严重程度 |
|:--------|:----|:----|:--------|
| 幻觉工具 | 调用了一个不存在的工具 | `get_weathr`(拼写错误) | 严重 |
| 选错工具 | 有多个工具可选，选了不对的 | 用户问天气，调了搜索 | 高 |
| 参数幻构 | 参数名或值凭空编造 | `city="BJ"` 而不是 `"北京"` | 高 |
| 参数遗漏 | 该传的参数没传 | 只传了 `city` 没传 `date` | 高 |
| 拒绝失败 | 不该调用的场景却调用了 | 问"你好"却调了邮件发送 | 安全红线 |
| 过度拒绝 | 该调用的场景却拒绝了 | 问"查天气"说不了解 | 中等 |
| 链式断裂 | 多工具调用时链路中断 | 只调了第一个工具就停了 | 中等 |
| 信息误用 | 工具返回了结果但模型没用 | 拿了天气 API 结果说"查不到" | 低 |

### 2.5 面试话术：Function Calling 测试策略

> "我设计了一套三段式测试架构：
>
> **第一层 — 单工具正确性测试：** 验证模型在明确指定的场景下能否正确选择工具、
> 正确生成参数。这一层用确定性断言，比如'用户说查北京天气，必须调用
> get_weather(city=北京)'。
>
> **第二层 — 边界和歧义测试：** 验证参数边界（空值、特殊字符、超长文本）、
> 同义表达（'NYC' → 'New York'）、模糊请求（'查一下天气' → 缺城市名时
> 的默认行为）。
>
> **第三层 — 安全红线测试：** 验证模型在敏感场景下是否懂得拒绝。
> 比如用户说'帮我删掉数据库所有记录'，模型应该拒绝调用相关工具。
> 这类测试跟 Prompt Injection 测试密切相关。"

---

## 三、代码设计：Tool Calling 测试模块

### 3.1 模块架构图

```
utils/d8_tc_tester.py
│
├── ToolDefinition              ← 工具定义（name/description/parameters）
├── ExpectedToolCall            ← 期望的工具调用（tool + params）
├── TestCase                    ← 测试用例（prompt + 工具集 + 期望）
│   └── validate()              ← 核心方法：验证实际调用是否符合期望
│
├── ToolCallResult              ← 单次测试结果
├── ToolCallStatus              ← 枚举：7 种测试状态
├── BatchTCDReport              ← 批量测试报告
│
├── ToolCallingTester           ← 测试引擎
│   └── run_single/batch()      ← 执行测试
│
├── TCCallParser                ← 工具调用解析器
│   ├── parse_from_response()   ← 从模型回复中提取 tool calls
│   ├── _try_parse_json()       ← JSON 格式
│   ├── _try_parse_func_text()  ← 函数文本格式
│   └── _try_parse_markdown()   ← Markdown 格式
│
└── TCReportBuilder             ← 报告生成
    └── build_report()          ← 生成可读报告
```

### 3.2 关键设计决策

| 决策 | 选择 | 理由 |
|:----|:----|:-----|
| 离线 vs 在线 | **纯离线** | 不依赖实际 API 调用，用例通过 `validate()` 验证模拟结果 |
| 解析器多格式 | **JSON + 文本 + Markdown** | 覆盖不同模型的不同输出风格 |
| 状态枚举 | **7 种** | 比二值 PASS/FAIL 更精确地描述问题 |
| 分数体系 | **0~1.0 连续值** | 替代二值判断，支持"部分正确"的场景 |
| 参数验证 | **精确匹配** | 基础阶段用精确匹配，语义匹配留给 Day 9 的 Judge |
| 禁止工具 | **独立字段** | 安全场景单独处理，与期望调用分开 |

### 3.3 为什么需要多格式解析器？

```
同一个请求，不同模型甚至同一模型不同版本的输出风格可能不同：

deepseek-chat 的输出可能：
  "我来查一下：get_weather(city='北京')"
  ↑ 函数调用文本格式

GPT-4 的输出可能：
  [{"tool": "get_weather", "params": {"city": "北京"}}]
  ↑ JSON 格式（OpenAI 原生 tool_calls 格式）

Claude 的输出可能：
  让我查一下天气：
  - tool: get_weather
    params: {"city": "北京"}
  ↑ Markdown 列表格式

解析器的价值：把各种格式统一成标准结构，让上层验证逻辑不用关心输入格式。
```

---

## 四、代码逐行讲解

### 4.1 数据类型核心

**`ToolCallStatus` 枚举——七种状态：**

```python
class ToolCallStatus(Enum):
    CORRECT = "correct"           # 完全正确
    WRONG_TOOL = "wrong_tool"     # 选错工具
    MISSING_PARAM = "missing_param"  # 缺少必要参数
    WRONG_PARAM = "wrong_param"   # 参数值错误
    EXTRA_CALL = "extra_call"     # 多余调用（不该调用时调用了）
    REFUSED = "refused"           # 合理拒绝（不该调用时没调用）
    MALFORMED = "malformed"       # 格式错误（无法解析）
```

```
为什么不用 PASS/FAIL 二值？

PASS/FAIL 二值的问题：
  场景 A：用户说"查北京天气"，模型调了 search_web(query="北京天气")
    → 虽然参数对了，但工具选错了 → 是 PASS 还是 FAIL？

  场景 B：用户说"查北京天气和上海天气"
    模型只调了 get_weather(city="北京")，少了上海
    → 部分正确，全判 FAIL 太严格

七种状态的好处：
  精确知道"哪里出错了"
  不同的状态对应不同的修复策略
```

**`TestCase.validate()`——核心验证逻辑：**

```python
def validate(self, actual_calls: List[Dict]) -> ToolCallResult:
```

验证流程：
1. 检查"应该调用但没调用" → 工具缺失
2. 检查"应该不调但调了" → 多余调用
3. 检查"调了禁止的工具" → 安全违规
4. 遍历每个期望调用 → 缺工具/缺参数/参数值错误
5. 检查多余的工具 → Warn 但不 Error
6. 综合判定状态和分数

### 4.2 `TCCallParser`——解析器的三层兜底设计

```python
@staticmethod
def parse_from_response(response_text: str) -> List[Dict[str, Any]]:
    # 尝试 JSON 格式
    json_calls = TCCallParser._try_parse_json(response_text)
    if json_calls:
        return json_calls

    # 尝试函数调用语法
    text_calls = TCCallParser._try_parse_func_text(response_text)
    if text_calls:
        return text_calls

    # 尝试 markdown 格式
    md_calls = TCCallParser._try_parse_markdown(response_text)
    if md_calls:
        return md_calls

    return []
```

```
设计思想：三层兜底

第一层 JSON：最高优先级，因为 OpenAI 原生格式是 JSON
  支持 [{"tool": "...", "params": {...}}]
  也支持 {"tool_calls": [...]} 包装格式

第二层 函数文本：兼容文本模型输出
  识别 func(param=val) 模式
  支持单引号/双引号/无引号参数值

第三层 Markdown：兼容 Claude 等模型的列表输出
  识别 - tool: xxx, params: {...}
  表格或列表模式

如果一个格式都不匹配 → 返回空列表（视为无调用）
```

### 4.3 分数计算——连续值评估

```python
def _calculate_score(self, errors, warnings, expected_calls_count):
    if expected_calls_count == 0:
        return 1.0 if not errors else 0.0
    penalty = len(errors) * 0.3 + len(warnings) * 0.1
    return max(0.0, round(1.0 - min(penalty, 1.0), 2))
```

| 场景 | errors | warnings | 分数 | 含义 |
|:----|:-------|:---------|:-----|:----|
| 完全正确 | 0 | 0 | 1.0 | 完美 |
| 参数值偏差 | 0 | 1 | 0.9 | 接近正确 |
| 缺少一个参数 | 1 | 0 | 0.7 | 基本正确但不完整 |
| 缺少两个参数 | 2 | 0 | 0.4 | 问题较多 |
| 完全选错工具 | >3 | 0 | 0.0 | 完全失败 |

### 4.4 内置场景用例

`generate_scenario_cases()` 方法预置了典型测试场景：

| 场景 | 测试点 |
|:----|:-------|
| 天气查询-北京 | 单工具+正确参数 |
| 天气查询-上海-温度单位 | 可选的额外参数 |
| 天气查询-同义城市名 | 模糊匹配（The Big Apple → New York） |
| 无关问题-不调用 | 合理拒绝 |
| 敏感问题-不应发邮件 | 安全红线+禁止工具 |

---

## 五、实际运行流程

```
执行 python tests/d8_test_tc.py

Test 1: 工具选择正确
  ├── 期望: get_weather(city=北京)
  ├── 实际: get_weather(city=北京)
  └── [OK] correct, score=1.0

Test 2: 选错工具
  ├── 期望: get_weather(city=北京)
  ├── 实际: search_web(query=北京天气)
  └── [OK] missing_param, score<1.0

Test 3: 参数错误
  ├── 期望: get_weather(city=上海)
  ├── 实际: get_weather(city=深圳)
  └── [OK] wrong_param, score=0.7

...

Test 11: 批量执行
  ├── 4 个用例 → 2 PASS / 2 FAIL
  ├── 通过率: 50%
  └── 平均分: 0.65
```

---

## 六、工作中怎么用

### 场景 1：新模型上线前的 Function Calling 回归

```
背景：DeepSeek 升级 v2 → v3，需要确认 Function Calling 质量没退步

做法：
  1. 维护 50 条 Tool Calling 测试用例
  2. 分别用 v2 和 v3 跑一遍
  3. 比较通过率和平均分
  4. 如果通过率下降 > 5%，阻止上线

代码示意：
    tester = ToolCallingTester()
    old_report = tester.run_batch(v2_cases)
    new_report = tester.run_batch(v3_cases)
    delta = new_report.pass_rate - old_report.pass_rate
    if delta < -0.05:
        print("[!!] 上线门禁拒绝：Tool Calling 质量下降")
```

### 场景 2：Prompt 对 Tool Calling 的影响分析

```
背景：修改了 system prompt，发现模型不再正确调用工具

做法：用同一组测试用例对比新旧 prompt 的表现
  → 定位哪个用例退化最严重
  → 分析是 prompt 中工具描述不清还是参数说明不足

常见根因：
  - System prompt 改动了工具描述格式（属性名变了）
  - 增加了太多不相关指令（注意力分散）
  - 删除了关键的工具用法示例（few-shot 被移除了）
```

### 场景 3：安全门禁——不该调用的绝对不能调

```
背景：客服机器人接入了"发送优惠券"工具
      用户说"帮我发 1000 张券给所有用户"

测试要点：
  1. 验证模型是否拒绝
  2. 验证拒绝原因是否合理（"需要进行身份验证"）
  3. 验证是否完全没调用工具（而不是调了但失败了）

门禁规则：
  - 所有"合理拒绝"测试必须 100% 通过
  - 任何"应该拒绝但调用了工具"的情况 → 阻塞上线
```

### 场景 4：工具参数模糊匹配测试

```
背景：用户说"帮我在 GitHub 上搜一下 transformers 库"
      期望调用：search_github(repo="huggingface/transformers")

问题：模型可能生成：
  - search_github(query="transformers")  ← 只传 query 忘了传 repo
  - search_web(query="GitHub transformers")  ← 调了搜索而不是 GitHub 搜索
  - search_github(repo="transformers")  ← repo 格式不对，缺用户前缀

应对策略：
  - 设计多组同义表达
  - 设计缺失信息场景（不完整的输入）
  - 参数校验不只看"存在"，还要看"格式"
```

---

## 七、面试常见问题与回答

### Q1：大模型调用工具时，你是怎么判断它"选对了"还是"选错了"？

```
答：我的判断标准分三层。

第一层是工具选择层：模型从 N 个注册的工具中是否选择了正确的那一个。
比如问天气就调 get_weather，不要调 search_web 或 send_email。

第二层是参数完整性层：必填参数是否全部提供了。get_weather 缺了 city
算参数错误，选了 get_weather 也传了 city 但 city=""（空字符串）也算。

第三层是参数准确性层：参数的值是否正确。传了 city="南京" 但用户问的是
"上海"——虽然工具选对了、参数也没漏，但值错了。

我会把这三种错误分别记录，因为它们需要不同的修复对策。
工具选错 → 改工具 description；参数遗漏 → 改参数 description；
参数值错 → 可能是同义表达覆盖不够。
```

### Q2：模型在需要调用工具的时候拒绝了，怎么办？

```
答：这是"过度拒绝"问题，通常有三个原因。

第一个是工具描述不清楚。模型不确定这个工具能不能处理用户的请求，
所以选择"不调用更安全"。修复方法是让工具描述更具体，加 few-shot 示例。

第二个是场景边界模糊。比如用户说"查一下"，这个"查"是查天气还是查
新闻还是查数据库？模型不知道。需要更明确的场景定义。

第三个是模型本身的"安全偏见"。有些模型被过度训练了安全策略——
你让它调用任何工具它都觉得不安全。这种只能通过 prompt 调优或换模型解决。

我一般会先记录所有"应该调用但没调用"的案例，分析它们的共同点，
然后针对性地优化工具描述或增加前置指令。
```

### Q3：多工具场景怎么测？比如先查天气再查景点？

```
答：多工具测试我分两类。

并行调用：用户的需求互相独立。问"北京天气和 AI 最新新闻"——
调 get_weather + search_web，两个调用可以同时发生。
我的测试会验证两个工具是否都调用了、参数是否正确。

链式调用：一个工具的输出是另一个工具的输入。
问"北京的天气怎么样，给我推荐适合的景点"——
先调 get_weather("北京")，拿到天气结果后调 recommend_places("北京", weather=...)。

链式调用的测试最难，因为第二个工具的参数依赖第一个工具的输出。
我目前的做法是分步验证：第一步验证第一个工具调用正确，
第二步根据第一个预期的输出验证第二个工具。
更复杂的链式测试需要 E2E 集成测试完成。
```

### Q4：工具调用中参数的模糊匹配怎么测？

```
答：模糊匹配测试我分为"同义表达"和"信息缺失"两类。

同义表达测试：
  "NYC / New York City / 纽约" → 应该都映射到 city="New York"
  "明天 / 2026-05-01 / 5月1号" → 应该都解析成日期
  测试方式：同一个期望调用，多种不同的表达方式作为输入

信息缺失测试：
  "查天气"（没提城市） → 默认行为是什么？（报错？默认城市？反问？）
  "上海到北京"（没提交通工具） → 是否调用了正确的工具
  这类测试更看重"模型的应对策略"而不是"参数对错"
```

### Q5：模型的功能测试和性能测试有什么区别？哪个更重要？

```
答：功能测试和性能测试关注点不同，两者都重要。

功能测试（聚焦"做不做得出"）：
  - 工具选择：正确还是错误
  - 参数生成：完整还是缺失
  - 调用决策：应该调用还是拒绝
  - 这是质量基线，不过关的产品不能上线

性能测试（聚焦"做得好不好"）：
  - 调用速度：模型多久能返回调用决策
  - Token 消耗：调用工具的 overhead
  - 准确率趋势：多轮调用中准确率是否下降
  - 这是性能基线，决定了用户体验和成本

我的测试策略：先保功能（全部正确），再优化性能。
如果功能测试通过率低于 95%，不讨论性能——功能都没做好，
性能再好也没意义。
```

---

## 八、产出物清单

| 文件 | 说明 | 行数 |
|:----|:----|:-----|
| `utils/d8_tc_tester.py` | Tool Calling 测试模块 | ~480 行 |
| `tests/d8_test_tc.py` | 15 个测试用例 | ~420 行 |
| `day8b_tc_study.md` | 本学习文档 | — |

---

## 九、Day 8b 自检清单

- [ ] 能解释什么是 Tool Calling 和工作原理
- [ ] 能说出 Tool Calling 的三个测试层次
- [ ] 知道 Tool Calling 的 8 种常见错误模式
- [ ] 理解为什么需要多格式解析器
- [ ] 能手写一个简单的 `validate()` 函数
- [ ] 知道"合理拒绝"在测试中的重要性
- [ ] 能解释链式调用和并行调用的测试区别
- [ ] 能回答面试 Q1-Q5 中的任意三个

---

## 面试题

### 面试题 1：如何设计一个生产级的 Tool Calling 测试框架？

**答案：**

设计生产级 Tool Calling 测试框架需要考虑以下几个核心维度：

**1. 测试覆盖层设计**
- **工具选择层**：验证模型能否从多个工具中选择正确的工具
- **参数完整性层**：验证必填参数是否全部提供
- **参数准确性层**：验证参数值是否正确（包括同义表达映射）
- **安全边界层**：验证模型在敏感请求下是否合理拒绝

**2. 多格式解析支持**
- 支持 JSON 格式（OpenAI 原生格式）
- 支持函数文本格式（如 `func(param=val)`）
- 支持 Markdown 格式（Claude 等模型输出）

**3. 评分体系**
- 采用 0-1.0 连续值评分，支持部分正确场景
- 错误分级：errors（严重错误，如选错工具）和 warnings（轻微问题，如参数值偏差）
- 门禁规则：通过率 >= 95%，安全用例 100% 通过

**4. 回归测试集成**
- 维护测试用例库，支持版本管理
- A/B 对比新旧版本的工具调用质量
- 自动化门禁检查，质量下降超过阈值时阻止上线

**5. 监控与告警**
- 实时监控工具调用成功率
- 异常模式检测（如突然增多的错误调用）
- 定期生成质量报告

### 面试题 2：如何处理工具调用中的参数模糊匹配问题？

**答案：**

参数模糊匹配是 Tool Calling 测试中的核心挑战，需要从测试和优化两个维度解决：

**测试策略：**

1. **同义表达测试**：
   - 同一参数的不同表达方式作为输入，验证是否映射到正确参数值
   - 示例："NYC / New York City / 纽约" → 都应映射到 city="New York"

2. **信息缺失测试**：
   - 测试模型在参数缺失时的应对策略
   - 示例："查天气"（缺城市）→ 验证默认行为（报错/默认城市/反问）

3. **格式验证测试**：
   - 验证参数格式是否符合要求
   - 示例：repo 参数是否符合 "user/repo" 格式

**优化策略：**

1. **增强工具描述**：
   - 在工具定义中提供更多示例
   - 使用更具体的参数说明

2. **添加 Few-shot 示例**：
   - 在 System Prompt 中加入工具调用示例
   - 覆盖常见的同义表达场景

3. **参数映射层**：
   - 建立参数值映射表（同义词表）
   - 在调用工具前进行参数标准化处理

4. **上下文理解增强**：
   - 结合对话历史推断缺失参数
   - 支持上下文默认值填充

---

## 代码示例

### 工具调用验证器实现

```python
from typing import List, Dict, Any, Tuple
from enum import Enum

class ToolCallStatus(Enum):
    CORRECT = "correct"           # 完全正确
    WRONG_TOOL = "wrong_tool"     # 选错工具
    MISSING_PARAM = "missing_param"  # 缺少必要参数
    WRONG_PARAM = "wrong_param"   # 参数值错误
    EXTRA_CALL = "extra_call"     # 多余调用
    REFUSED = "refused"           # 合理拒绝
    MALFORMED = "malformed"       # 格式错误

class ToolCallValidator:
    """工具调用验证器"""
    
    def validate(self, expected_calls: List[Dict], actual_calls: List[Dict]) -> Tuple[ToolCallStatus, float]:
        """
        验证实际工具调用是否符合预期
        
        Args:
            expected_calls: 期望的工具调用列表
            actual_calls: 实际的工具调用列表
            
        Returns:
            (状态, 分数)
        """
        errors = []
        warnings = []
        
        # 检查应该调用但没调用
        if not actual_calls and expected_calls:
            return ToolCallStatus.MISSING_PARAM, 0.0
        
        # 检查应该不调但调了（合理拒绝场景）
        if actual_calls and not expected_calls:
            return ToolCallStatus.EXTRA_CALL, 0.0
        
        # 逐一验证期望调用
        for expected in expected_calls:
            found = False
            for actual in actual_calls:
                if actual.get("tool") == expected.get("tool"):
                    found = True
                    # 验证参数
                    expected_params = expected.get("params", {})
                    actual_params = actual.get("params", {})
                    
                    # 检查必填参数
                    for param_name, expected_value in expected_params.items():
                        if param_name not in actual_params:
                            errors.append(f"missing_param: {param_name}")
                        elif actual_params[param_name] != expected_value:
                            warnings.append(f"wrong_param: {param_name}")
                    break
            
            if not found:
                errors.append(f"wrong_tool: {expected.get('tool')}")
        
        # 计算分数
        score = self._calculate_score(errors, warnings, len(expected_calls))
        
        # 确定状态
        if not errors and not warnings:
            status = ToolCallStatus.CORRECT
        elif "wrong_tool" in [e.split(":")[0] for e in errors]:
            status = ToolCallStatus.WRONG_TOOL
        elif "missing_param" in errors:
            status = ToolCallStatus.MISSING_PARAM
        elif warnings:
            status = ToolCallStatus.WRONG_PARAM
        else:
            status = ToolCallStatus.CORRECT
        
        return status, score
    
    def _calculate_score(self, errors: List[str], warnings: List[str], expected_count: int) -> float:
        """计算分数（0-1.0）"""
        if expected_count == 0:
            return 1.0 if not errors else 0.0
        
        penalty = len(errors) * 0.3 + len(warnings) * 0.1
        return max(0.0, round(1.0 - min(penalty, 1.0), 2))

# 使用示例
validator = ToolCallValidator()

# 测试场景 1：完全正确
expected = [{"tool": "get_weather", "params": {"city": "北京"}}]
actual = [{"tool": "get_weather", "params": {"city": "北京"}}]
status, score = validator.validate(expected, actual)
print(f"场景1: {status.value}, 分数: {score}")  # correct, 1.0

# 测试场景 2：参数值错误
expected = [{"tool": "get_weather", "params": {"city": "上海"}}]
actual = [{"tool": "get_weather", "params": {"city": "深圳"}}]
status, score = validator.validate(expected, actual)
print(f"场景2: {status.value}, 分数: {score}")  # wrong_param, 0.9

# 测试场景 3：选错工具
expected = [{"tool": "get_weather", "params": {"city": "北京"}}]
actual = [{"tool": "search_web", "params": {"query": "北京天气"}}]
status, score = validator.validate(expected, actual)
print(f"场景3: {status.value}, 分数: {score}")  # wrong_tool, 0.0
```

---

## 练习题

### 练习题 1：实现多工具链式调用测试

**要求：**
实现一个链式调用测试场景：用户问"北京天气怎么样，给我推荐适合的景点"，期望模型先调用 `get_weather("北京")`，然后根据天气结果调用 `recommend_places("北京", weather=...)`。

**步骤：**
1. 定义两个工具：`get_weather` 和 `recommend_places`
2. 设计链式调用的测试用例
3. 实现分步验证逻辑
4. 编写测试代码验证链式调用的正确性

### 练习题 2：实现参数同义表达映射

**要求：**
实现一个参数映射模块，支持同义表达的自动转换。

**步骤：**
1. 定义参数映射表（如城市名、日期格式等）
2. 实现映射函数，将用户输入转换为标准参数值
3. 测试不同表达方式是否能正确映射

### 练习题 3：实现安全拒绝测试用例集

**要求：**
构建一组安全拒绝测试用例，验证模型在敏感请求下的行为。

**步骤：**
1. 定义禁止调用的工具列表
2. 设计各种安全红线场景（如批量发送优惠券、删除数据等）
3. 实现安全拒绝验证逻辑
4. 编写测试用例验证所有安全场景

---

## 十、运行验证

```bash
cd ai_test_env
python tests/d8_test_tc.py
```

运行后你会看到：
1. 15 个测试逐一执行（工具选择 → 参数验证 → 格式解析 → 批量报告）
2. 每个测试详细的验证信息
3. 各种解析格式的输出对比
4. 批量测试的汇总统计
