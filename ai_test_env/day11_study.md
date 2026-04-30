# Day 11 — 多轮对话上下文测试

## 一、今日目标

> 学会构造多轮对话场景，量化评估 AI 模型在长对话中的信息保持能力。

- 理解"多轮对话上下文测试"是什么、为什么重要
- 掌握"注入→干扰→验证"三部曲测试方法
- 学会计算上下文召回率（recall_rate）
- 理解遗忘曲线测试的基本思路

---

## 二、前置知识讲解

### 2.1 什么是多轮对话？

**一句话定义：** 多轮对话是指用户和 AI 之间连续多次交替发言的交互过程，每轮对话都可能依赖前面轮次中的信息。

**现实场景：**

```
用户：我叫张三，帮我查一下尾号 8888 的银行卡余额
AI：   好的张三，已查到尾号 8888 的银行卡，余额为 12,800 元
  —— 5 分钟后/10 轮对话后 ——
用户：那上次那笔消费退款到了吗？
AI：   （如果还记得）"您说的是尾号 8888 的银行卡吗？上次有 500 元退款已到账"
      （如果不记得）"请问您说的是哪张卡？什么退款？"
```

**类比：** 就像和一个容易健忘的朋友聊天——你第一次见面说了你的名字，聊了 10 分钟后他叫你"喂"，你会觉得他根本没在听。

**面试话术：**
> "多轮对话测试是 AI 测试中容易被忽视但影响用户体验极大的方向。一个泛化能力强的模型可能在单轮问答上表现完美，但在第 8 轮对话后忘记用户 3 轮前提供的关键信息。我们测试过，某模型在第 5 轮后关键实体召回率从 100% 降到 68%，这直接导致用户需要反复重复自己的信息，体验极差。"

---

### 2.2 上下文窗口（Context Window）

**一句话定义：** 上下文窗口是指模型一次能"看见"的最大 Token 数，超过这个长度的内容会被截断或遗忘。

| 模型 | 上下文窗口 | 约等于多少字 |
|------|-----------|------------|
| GPT-3.5 | 4K ~ 16K | 3,000 ~ 12,000 字 |
| GPT-4 | 8K ~ 128K | 6,000 ~ 96,000 字 |
| DeepSeek-V2/V3 | 128K | 约 96,000 字 |
| Claude 3 | 200K | 约 150,000 字 |

**关键认知：**
- 窗口大 ≠ 窗口中所有信息都有效
- 模型存在"中间迷失"问题：开头和结尾的信息召回率高，中间的被遗忘
- 实际有效上下文远小于标称窗口

**类比：** 就像你一次性读了 100 页的书——你记得开头第一章和最后一章，但中间第 30-70 页的内容基本模糊了。模型也一样。

**面试话术：**
> "上下文窗口是模型的能力上限，但实际测试中要注意'有效上下文'的概念。我们在测试 DeepSeek-V3 时发现，即使它有 128K 窗口，但实际在 16K 之后的信息召回率就开始明显下降。测试策略是：不要只看标称值，要实测各区间（前 1/4、中间 1/2、后 1/4）的召回率差异。"

---

### 2.3 关键信息注入与召回

**一句话定义：** 在对话中人为放置特定信息（如姓名、账号、金额），然后在后续轮次中验证模型是否能正确使用这些信息。

**三个核心概念：**

| 术语 | 含义 | 测试示例 |
|------|------|---------|
| 注入 | 在第 N 轮放置关键信息 | "我叫张三，尾号 8888" |
| 干扰 | 注入后继续无关对话 | 聊天气、问功能、闲聊 |
| 验证 | 在后续轮次询问注入的信息 | "我的名字是什么？" |

**召回率计算公式：**

```
召回率 = 正确回召的关键信息数 / 总注入关键信息数

示例：注入 {name, phone, card_last4} 三个信息
      验证轮正确回召了 {name, card_last4} 两个
      召回率 = 2/3 = 0.667
```

**面试话术：**
> "召回率是量化模型记忆能力的核心指标。我们在客服场景设定标准：关键实体召回率 >= 0.9 为通过，0.8-0.9 为关注，< 0.8 为不通过。金融场景这个标准更严格，因为忘记用户卡号或金额可能导致严重业务问题。"

**实操关联：** 今天代码中的 `analyze_context()` 就是计算这个指标的函数。

---

## 三、需求分析

### 3.1 为什么需要多轮对话上下文测试

| 测试维度 | 单轮测试 | 多轮测试 |
|---------|---------|---------|
| 测试覆盖 | 独立问答 | 连续交互场景 |
| 发现的问题 | API 可用性、回复格式 | 信息保持、实体传递、长期依赖 |
| 典型 bug | 返回空、格式错误 | 忘记用户信息、前后矛盾 |
| 业务影响 | 用户体验 | 严重（需要用户反复输入） |

### 3.2 业务价值
- **客服场景**：用户在第 1 轮提供了订单号，第 5 轮查询状态时模型应该还记得
- **金融场景**：用户告知了卡号和金额，后续确认时必须使用正确的信息
- **医疗场景**：用户描述了症状和病史，后续诊断建议需要基于这些信息

### 3.3 测试目标
- 量化模型在多轮对话中的信息保持能力（召回率）
- 发现模型"断片"的临界点（第几轮开始遗忘）
- 分析 Token 消耗趋势（长对话的成本影响）

---

## 四、代码设计

### 4.1 模块结构

```
ConversationTester          ← 主测试类
├── build_conversation_script()    ← 构造测试脚本
├── analyze_context()              ← 分析上下文保持率
├── forget_curve()                 ← 遗忘曲线测试
└── history() / reset()            ← 历史管理

ConversationManager        ← 会话管理器
├── create_conversation()
├── export_messages()       ← 转为 API 格式
└── token_trend()           ← Token 趋势分析

detect_key_info()           ← 辅助函数
```

### 4.2 "注入→干扰→验证"三部曲

```
轮次 1-2: 寒暄（无关对话，建立场景）
           "你好！今天天气不错。"
           "我想咨询一下你们的产品。"

轮次 3:   注入关键信息
           "我来说说我的信息，name=张三, card_last4=8888，你记好了。"

轮次 4-6: 干扰对话
           "你们有没有手机 App？"
           "周末你们上班吗？"

轮次 7-8: 验证
           "我刚才说的我的名字是什么？"
           "我的银行卡尾号是多少？"
```

### 4.3 上下文召回分析

```
输入：
  key_info = {"name": "张三", "card_last4": "8888"}
  recall_responses = {"name": "张三", "card_last4": "6666"}

处理：
  name:     "张三" == "张三"    → 正确
  card_last4: "6666" != "8888"  → 遗忘

输出：
  recall_rate = 1/2 = 0.5
  turns_until_forget = 7（第 7 轮开始遗忘）
```

---

## 五、代码逐行讲解

### 5.1 `Turn` 和 `Conversation` 数据结构

```python
@dataclass
class Turn:
    """单轮对话"""
    role: str                    # user / assistant
    content: str                 # 本轮内容
    tokens: int = 0              # 本轮消耗 Token（可选）
    latency_ms: float = 0.0      # 本轮延迟（可选）
```

- `@dataclass`：Python 自动生成 `__init__`、`__repr__` 等方法
- `role`：标记是谁说的（用户还是 AI）
- `tokens/latency_ms`：可选的量化数据，便于后续做成本分析

```python
@dataclass
class Conversation:
    """一次完整的对话会话"""
    turns: List[Turn] = field(default_factory=list)
    total_tokens: int = 0
    total_latency_ms: float = 0.0
```

- `field(default_factory=list)`：防止所有实例共享同一个列表（Python 的常见坑）
- `to_messages()`：转为 OpenAI API 的 messages 格式 `[{"role": "user", "content": "..."}, ...]`

### 5.2 `build_conversation_script()` 构造测试脚本

```python
def build_conversation_script(
    self,
    key_info: Dict[str, str],
    context_turns_before: int = 2,    # 注入前的寒暄轮次
    context_turns_after: int = 3,     # 注入后的干扰轮次
    verification_delays: List[int] = None,  # 验证延迟
) -> List[Dict]:
```

**核心逻辑：**

1. **寒暄阶段**：用常规问候填充前 N 轮，让模型进入"对话模式"
2. **注入阶段**：将关键信息包装成自然语句送出
3. **干扰阶段**：用无关对话"冲刷"注意力
4. **验证阶段**：生成针对性问题，如"我的名字是什么？"

**设计巧思：**
- `_tag` 字段标记每轮的功能（`greeting`/`info_injection`/`distractor`/`verification`）
- `_turn_id` 记录轮次号，便于后续分析
- `_expected` 在验证轮记录期望值

### 5.3 `analyze_context()` 分析上下文保持率

```python
def analyze_context(
    self,
    key_info: Dict[str, str],
    recall_responses: Dict[str, str],
    conversation: Optional[Conversation] = None,
    verification_turn: int = 0,
) -> ContextTestResult:
```

**匹配逻辑：**
1. 精确匹配（`"张三" == "张三"`）→ 召回
2. 包含匹配（`"您说的是张三，对吧？"` 含 `"张三"`）→ 召回
3. 空值 → 遗忘
4. 不匹配 → 遗忘

**结论分级：**
- `recall_rate >= 1.0`：全部保持
- `recall_rate >= 0.8`：大部分保持
- `recall_rate >= 0.5`：约半数遗忘
- `recall_rate < 0.5`：严重遗忘

### 5.4 `forget_curve()` 遗忘曲线测试

```python
def forget_curve(
    self,
    key_info: Dict[str, str],
    api_func: Callable,
    delays: List[int] = None,
    ...
) -> List[ContextTestResult]:
```

**思路：** 在不同间隔轮次（1、3、5、10 轮后）分别验证召回率，绘制 "召回率 vs 轮次间隔" 曲线。

**今天代码中为骨架版本**，仅构造脚本但不实际调用 API。实际使用时传入 `api_func` 来发送请求并获取回复。

### 5.5 `ConversationManager` 会话管理器

```python
class ConversationManager:
    def create_conversation(self) -> Conversation
    def token_trend(self) -> List[Dict]
    def export_messages(self, conversation) -> List[Dict]
```

**用途：** 管理多次测试会话，支持导出为 API 格式，分析 Token 消耗趋势。

**Token Trend 示例输出：**
```json
[
  {
    "conversation_id": 0,
    "total_turns": 8,
    "total_tokens": 1250,
    "trend": [
      {"turn": 1, "cumulative_tokens": 120},
      {"turn": 2, "cumulative_tokens": 280},
      ...
      {"turn": 8, "cumulative_tokens": 1250}
    ]
  }
]
```

### 5.6 `detect_key_info()` 辅助函数

```python
def detect_key_info(response: str, key_info: Dict[str, str]) -> Dict[str, str]:
    """从模型回复中检测关键信息是否正确。简单字符串匹配版。"""
```

**用途：** 快速从一段文本中扫描是否包含关键信息。简单但有效。

---

## 六、实际运行流程

### 6.1 离线分析流程

```
1. 构造对话脚本
   └─ key_info = {"name": "张三", "card_last4": "8888"}
   └─ context_turns_before = 2, context_turns_after = 3

2. 运行对话（手动或 API 调用）
   └─ 获取模型在每个验证轮的回复

3. 分析召回率
   └─ recall_responses = {"name": "张三", "card_last4": "8888"}
   └─ → recall_rate = 1.0, "全部保持"

4. 查看历史记录
   └─ tester.history() → 所有测试结果
```

### 6.2 测试执行

```python
# 1. 创建测试器
tester = ConversationTester()

# 2. 构造脚本
script = tester.build_conversation_script(
    key_info={"name": "张三", "card_last4": "8888"},
    context_turns_before=2,
    context_turns_after=3,
)

# 3. 分析结果（离线模式，传模拟回复）
result = tester.analyze_context(
    key_info={"name": "张三", "card_last4": "8888"},
    recall_responses={"name": "张三", "card_last4": "8888"},
    verification_turn=7,
)
print(f"召回率: {result.recall_rate}")
print(f"结论: {result.conclusion}")
```

---

## 七、工作中怎么用

### 场景 1：客服机器人上下文测试
**测试点：**
- 用户在第 1 轮说"我要查询上个月的账单"，第 5 轮说"帮我导出"
- AI 应该知道导出的是"上个月的账单"

### 场景 2：模型迭代回归测试
**场景：** 每次模型升级时，用同一套多轮对话脚本跑测试
- 新版本 0.85 | 旧版本 0.90 → 上下文能力退步，需要拦截

### 场景 3：上下文长度压力测试
**测试：** 分别在 4K、8K、16K、32K Token 时验证召回率
- 找出模型的"有效上下文窗口"临界点

### 场景 4：不同的注入方式对比
**对比：**
- 方式 A（开头注入）："我叫张三，卡号 8888" → 召回率 0.95
- 方式 B（中间注入）：经过 5 轮寒暄后说"我叫张三，卡号 8888" → 召回率 0.75

---

## 八、面试问题

### Q1：多轮对话和单轮对话测试的核心区别是什么？
**A：** 单轮测试验证的是模型的"知识储备"和"语言理解能力"；多轮测试验证的是"信息保持能力"。单轮中模型只需要理解当前这一句，多轮中模型需要记住前面几轮说了什么。这是两种完全不同的能力维度。

### Q2：你如何量化"模型记住了多少"？
**A：** 核心指标是召回率（recall_rate）。我们在对话的前几轮注入关键信息（如姓名、金额、订单号），在后续轮次中询问这些信息，用"正确回召数/总注入数"来量化。还可以配合遗忘曲线，看不同间隔轮次下的召回率变化趋势。

### Q3：什么场景下多轮对话测试最重要？
**A：** 金融客服、医疗问诊、法律咨询这类需要持续依赖用户早期提供的详细信息的场景。一次对话中用户可能提供姓名、身份证号、金额、时间等多个信息，如果模型在第 5 轮忘了其中的关键信息，用户就要重复输入，体验极差。

### Q4：模型有 128K 上下文窗口，还需要测试多轮吗？
**A：** 需要。上下文窗口大 ≠ 能有效利用。我们的测试发现，很多模型在大窗口下存在"中间迷失"问题——开头和结尾的信息保持好，但中间段的有效召回率显著下降。此外，超长上下文的计算成本也很高，从成本优化的角度也需要了解模型的"甜蜜点"。

### Q5：如何用代码实现"注入→干扰→验证"三部曲？
**A：** 我们设计了 `build_conversation_script()` 方法，参数化控制寒暄轮数、干扰轮数和验证延迟。脚本中使用 `_tag` 标记每轮的功能类型，`_expected` 记录期望值。`analyze_context()` 方法读取验证轮的回复，逐个 key 匹配并计算召回率。

---

## 九、产出物清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/conversation_tester.py` | 多轮对话上下文测试模块 | [OK] 已创建 |
| `tests/test_conversation.py` | 22 个单元测试 | [OK] 22/22 PASS |
| `day11_study.md` | 本篇学习文档 | [OK] 已完成 |

---

## 十、自检清单

- [ ] 我知道什么是多轮对话上下文测试
- [ ] 我理解"注入→干扰→验证"三部曲的设计思路
- [ ] 我理解召回率的计算方式
- [ ] 我知道什么时候用精确匹配、什么时候用包含匹配
- [ ] 我理解遗忘曲线的测试目的
- [ ] 我能说明 `build_conversation_script` 各参数的含义
- [ ] 我能回答面试问题至少 3 个

---

## 十一、运行验证

```
tests/test_conversation.py::TestTurnAndConversation::test_conversation_add_turn PASSED
tests/test_conversation.py::TestTurnAndConversation::test_conversation_summary PASSED
tests/test_conversation.py::TestTurnAndConversation::test_conversation_to_messages PASSED
tests/test_conversation.py::TestTurnAndConversation::test_turn_creation PASSED
tests/test_conversation.py::TestConversationTesterBuildScript::test_build_script_has_all_phases PASSED
tests/test_conversation.py::TestConversationTesterBuildScript::test_build_script_message_count PASSED
tests/test_conversation.py::TestConversationTesterBuildScript::test_verification_questions_match_keys PASSED
tests/test_conversation.py::TestConversationTesterAnalyze::test_analyze_contain_match PASSED
tests/test_conversation.py::TestConversationTesterAnalyze::test_analyze_empty_key_info PASSED
tests/test_conversation.py::TestConversationTesterAnalyze::test_analyze_full_recall PASSED
tests/test_conversation.py::TestConversationTesterAnalyze::test_analyze_history_tracked PASSED
tests/test_conversation.py::TestConversationTesterAnalyze::test_analyze_partial_recall PASSED
tests/test_conversation.py::TestConversationTesterAnalyze::test_analyze_zero_recall PASSED
tests/test_conversation.py::TestConversationManager::test_create_conversation PASSED
tests/test_conversation.py::TestConversationManager::test_export_messages PASSED
tests/test_conversation.py::TestConversationManager::test_latest_conversation PASSED
tests/test_conversation.py::TestConversationManager::test_reset PASSED
tests/test_conversation.py::TestConversationManager::test_summary_all PASSED
tests/test_conversation.py::TestConversationManager::test_token_trend PASSED
tests/test_conversation.py::TestDetectKeyInfo::test_detect_exact_match PASSED
tests/test_conversation.py::TestDetectKeyInfo::test_detect_no_match PASSED
tests/test_conversation.py::TestDetectKeyInfo::test_detect_partial_match PASSED

22 passed in 0.04s
```
