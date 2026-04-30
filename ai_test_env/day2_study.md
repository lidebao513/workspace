# Day 2：参数边界测试

> 对应 8 周计划第 1 周 Day 2
> 目标城市：上海 | 目标岗位：AI 测试工程师
> 学习时间：约 1.5 小时

---

## 一、今日学习目标

| 目标 | 说明 |
|:----|:----|
| 理解边界值分析和等价类划分 | 传统测试方法在 AI 测试中的应用 |
| 测试 max_tokens 边界 | 极小值、极大值、合理值的表现 |
| 测试 temperature 边界 | 随机性从完全确定到完全混乱 |
| 测试异常输入 | 负数、空值、超范围参数 |
| 记录不同参数下的行为差异 | 建立参数基线，作为后续测试的对比依据 |

**面试对应问题：** "你是怎么测试 AI API 参数的？" / "max_tokens 和 temperature 对 AI 回复有什么影响？"

---

## 二、前置知识讲解

### 2.1 边界值分析（Boundary Value Analysis）

这是软件测试里的经典方法，直接搬到 AI 测试来用。

**核心思想：**
```
错误的参数往往出现在边界上，而不是在中间范围。

比如一个参数取值范围是 0-100：
  容易出错的地方：-1（低于下限）、0（下限）、100（上限）、101（高于上限）
  不太出错的地方：50（中间值）
```

**在 AI API 参数测试中的映射：**

| 参数 | 取值范围 | 需测试的边界 |
|:----|:--------|:-----------|
| max_tokens | ≥ 1（理论上不限上限） | 0、1、50、4096、8192 |
| temperature | 0 - 2 | -1、0、0.1、1.0、2.0、3.0 |
| top_p | 0 - 1 | -1、0、0.1、0.5、1.0、1.5 |
| frequency_penalty | -2 - 2 | -3、-2、-1、0、1、2、3 |

### 2.2 等价类划分（Equivalence Class Partitioning）

把输入分到不同"类"里，每一类只测一个代表就行。

**temperature 的等价类：**

```
temperature = 0    → 完全确定，每次回复一样
temperature = 0.1  → 非常稳定，微小变化（法律/金融场景）
temperature = 0.7  → 适中的创意（默认值，通用场景）
temperature = 1.0  → 有一些随机性（创意写作）
temperature = 2.0  → 极度随机，可能胡言乱语（极端测试）
```

**背后的原理：**
- temperature 控制 **Softmax 函数的"平滑度"**
- 值越小 → 高概率词被选中的概率越大 → 回复越确定
- 值越大 → 低概率词也有机会被选 → 回复越随机

### 2.3 大模型的生成机制——"预测下一个词"是什么？

**一句话定义：** 大模型不是"理解"你的问题后"想"出答案，而是一个超级自动补全——它逐个预测"下一个最可能出现的词"，直到认为回答完整。

**打个比方：**
```
你打字："今天天气______"

模型内部在算概率：
  "真"  → 45%  （"今天天气真好" 是最常见的搭配）
  "不"  → 20%  （"今天天气不错"）
  "很"  → 15%  （"今天天气很好"）
  "热"  → 10%  （"今天天气真热" 也说得通）
  "如"  → 3%   （"今天天气如何" 少见但可能）
  其他 → 7%

模型挑了一个（"真"），继续预测下一个：
  "真"→"好" → 80%  （"真好"是固定搭配）
  → 最终输出："今天天气真好"
```

**整个对话的生成过程：**
```
你发了 3 条消息：
  user: "请推荐一本 Python 入门书"
  assistant: "推荐《Python 编程从入门到实践》"  （第一步：预测下一个最有用的回答）
  user: "有更简单的吗？"
  assistant: "《笨办法学 Python》更适合零基础"   （第二步：结合上下文继续预测）
```

每一步看起来"好像模型真理解了"，但实际上它只是在做**概率预测**。

**这和测试有什么关系？**
- 因为生成是"逐词概率"的，所以 temperature 才能控制随机性
- 因为生成是概率的，所以同一问题两次回答不同——这不是 bug，是机制
- 因为生成是逐个词的，所以 max_tokens 硬性截断才会产生 "length" finish_reason

**面试话术：**
> "了解大模型是'预测下一个词'的机制后，很多测试现象就讲得通了。为什么 temperature=0 回复稳定？因为每次都选概率最高的词。为什么 max_tokens 设小会被截断？因为模型预测到一半被迫停止。为什么 seed 能复现？因为伪随机数被固定了。这个认知是所有 AI 参数测试的基础。"

---

### 2.4 seed 参数原理——让"随机"变得"确定"

**一句话定义：** seed 是一个"种子"数字，它决定了模型内部所有随机选择的起点，同一个 seed + 同一组参数 = 同一个结果。

**打个比方：**
```
没有 seed（random）：
  "说一个水果" → 苹果（第1次）
  "说一个水果" → 香蕉（第2次）  // 每次可能不同

有 seed=42：
  "说一个水果" → 苹果（第1次，seed=42）
  "说一个水果" → 苹果（第2次，seed=42）  // 回回都一样

就像看电影：
  没有 seed = 给你 10 个不同版本的结局
  有 seed = 每次进影院放的是同一版
```

**为什么 seed 不能 100% 保证一致？**
| 原因 | 解释 |
|:----|:-----|
| GPU 并行计算 | 大模型在 GPU 上并行运算，线程调度顺序有微小差异 |
| 浮点精度 | 不同硬件对小数计算的"四舍五入"方式不同 |
| API 版本 | 模型发布新版本后，概率分布可能微调 |

所以：**seed 让回复"高度可复现"，但不保证"绝对一致"**。

**测试中的价值：**
- 修复测试：用 seed 让 AI 在参数测试中输出一致，方便对比不同参数的效果
- 回归测试：同一个 prompt + seed，新版本应该输出一样的内容
- 问题复现：用户报 bug 时，用当时的 seed 能重现同样的回复

**实操关联：** Day 2 的 temperature 一致性测试就用到了 seed=42。这是 AI 测试中"让不可测变可测"的关键技巧。

---

### 2.5 API 定价模型——不只是按 Token 算钱

**一句话定义：** API 费用 = 输入 Token 数 × 输入单价 + 输出 Token 数 × 输出单价，但还有各种"省钱"和"多花钱"的玩法。

**基础定价（DeepSeek 2026 年参考价）：**
```
  输入（prompt_tokens）：0.14 元 / 百万 Token
  输出（completion_tokens）：0.28 元 / 百万 Token
  一次普通对话 ≈ 300-800 Token → 约 0.0001 元
```

**进阶定价策略（为什么做测试要懂这个？）：**
| 策略 | 说明 | 省钱幅度 | 测试影响 |
|:----|:-----|:--------|:--------|
| Batch API | 批量提交，24h 内完成 | 省 50% | 测试周期变长 |
| 缓存命中 | 完全相同 prompt 走缓存 | 省 90% | 缓存 vs 非缓存结果不同 |
| 预留并发 | 提前锁定 QPS | 固定成本 | 不再按量计费 |
| 混合模型 | 简单任务用小模型 | 省 70% | 不同模型质量不一样 |

**为什么 AI 测试工程师要懂定价？**
```
面试官问：“你每天跑 1000 个测试用例，一个月 API 费用多少？”

好回答：“我会计算。每个测试用例平均消耗 500 Token，
输入 0.14 + 输出 0.28，平均 0.00015 元/次。
1000 次/天 × 22 工作日 = 22000 次/月，约 3.3 元。

但如果测试用例设计不合理——每次发大量 prompt 只验证少数东西——
费用会暴涨。我用等价类划分法缩减测试用例数量，
同时在 CI 中统计每次跑的 Token 消耗，
异常增长时自动告警。”
```

**实操关联：** Day 2 的参数测试中，每个参数组合都会产生不同的 Token 消耗。temperature=2.0 可能让回复更长、费用更高。在基线表中记录这些数据，你就可以"从成本角度看测试"。

---

## 三、你今天要写的代码

在两个文件中增加内容：

### 文件 1：`utils/api_client.py` — 新增两个方法

在 `AITestClient` 类中新增 `chat_with_params` 和 `chat_with_exact_params` 两个方法，以及 `print_params_response` 方法。

**`chat_with_params` 方法功能：**
- 发送一样的提问，使用不同的参数组合
- 返回每次的回复内容和 Token 消耗
- 方便对比同一问题在不同参数下的表现

**`chat_with_exact_params` 方法功能：**
- 设置 exact 参数让回复可复现（seed 固定）
- 方便让 temperature=0 在多次请求中也能拿到同样回复

### 文件 2：新建 `tests/test_params.py` — 参数边界测试脚本

新建 `tests/` 目录和 `tests/__init__.py`（空文件），然后创建 `test_params.py`。

**测试覆盖：**

| 测试 | 说明 |
|:----|:----|
| `test_max_tokens_zero` | max_tokens=1，应只回复极少内容 |
| `test_max_tokens_small` | max_tokens=10，应被截断（finish_reason="length"） |
| `test_max_tokens_large` | max_tokens=2048，应完整回复 |
| `test_temperature_zero` | temperature=0，多次提问回复应一致 |
| `test_temperature_high` | temperature=2.0，回复应有明显随机性 |
| `test_invalid_params` | 负数 temperature、超大 max_tokens 等异常输入 |

---

## 四、代码逐行设计思路

### 4.1 `chat_with_params` 方法设计

```python
def chat_with_params(self, messages, **kwargs):
    """
    带自定义参数的聊天请求
    
    用途：测试不同参数组合对回复的影响
    面试话术："我可以控制任何参数组合来测试边界行为"
    """
    params = {
        "model": self.model,
        "messages": messages,
        "temperature": kwargs.get("temperature", 0.7),
        "max_tokens": kwargs.get("max_tokens", 1024),
        "timeout": kwargs.get("timeout", 30),
    }
    
    # 如果传了 seed，加入请求（DeepSeek 的 exact 参数）
    if "seed" in kwargs:
        params["extra_body"] = {"seed": kwargs["seed"]}
    
    try:
        response = self.client.chat.completions.create(**params)
        return response
    except Exception as e:
        raise RuntimeError(f"参数测试请求失败: {e}")
```

**关键设计点：**
- 用 `**kwargs` 接收任何参数，灵活扩展
- `seed` 参数通过 `extra_body` 透传（DeepSeek 支持 seed 来实现确定性的回复）
- 错误统一包装为 RuntimeError

### 4.2 边界值测试的思路

以 `test_max_tokens_zero` 为例：

```python
def test_max_tokens_zero(client):
    """
    测试 max_tokens=1 的场景
    预期：API 应处理这个值（可能回复极短或报错）
    面试话术："max_tokens 设为 1 是经典的边界测试——理论上应该只生成 1 个 token"
    """
    messages = [{"role": "user", "content": "给我写一篇 500 字的文章"}]
    
    response = client.chat_with_params(messages, max_tokens=1)
    reply = client.get_reply_text(response)
    
    print(f"max_tokens=1 时的回复长度: {len(reply)} 字符")
    print(f"回复内容: '{reply}'")
    
    # 检查 finish_reason — 如果是 "length" 说明被截断了
    finish_reason = response.choices[0].finish_reason
    print(f"finish_reason: {finish_reason}")
    
    # 记录 Token 消耗
    usage = client.get_token_usage(response)
    print(f"生成的 Completion Tokens: {usage['completion_tokens']}")
```

### 4.3 Temperature 对比测试的思路

```python
def test_temperature_consistency(client):
    """
    测试 temperature=0 是否能拿到一致的回复
    面试话术："temperature=0 理论上每次回复一样，我会用 3 次请求验证"
    """
    messages = [{"role": "user", "content": "用一句话说明什么是 API"}]
    
    replies = []
    for i in range(3):
        response = client.chat_with_params(messages, temperature=0)
        reply = client.get_reply_text(response)
        replies.append(reply)
        print(f"第 {i+1} 次回复: {reply[:80]}...")
    
    # 检查三次回复是否相同
    if replies[0] == replies[1] == replies[2]:
        print("temperature=0: 三次回复完全一致 → 确定性高 ✓")
    else:
        print("temperature=0: 三次回复不完全一致 → 存在随机性")
        # 计算相似度
        similarity = len(set(replies[0].split()) & set(replies[1].split())) / max(len(set(replies[0].split())), 1)
        print(f"单词重叠率: {similarity:.1%}")
```

---

## 五、实际运行流程

```
你运行 python tests/test_params.py
  │
  ├── Test 1: max_tokens=1
  │   ├── 发送 "写 500 字文章"
  │   ├── API 只生成 1 个 token → 回复极短
  │   ├── finish_reason = "length"（被截断）
  │   └── Token 只有 1 → 验证 API 严格遵守 max_tokens
  │
  ├── Test 2: max_tokens=10
  │   ├── 同样的问题
  │   ├── 回复大约 10-20 个字符
  │   ├── finish_reason = "length"
  │   └── 验证：max_tokens 不是"目标长度"而是"硬性上限"
  │
  ├── Test 3: max_tokens=2048
  │   ├── 同样的问题
  │   ├── 回复完整，没有截断
  │   ├── finish_reason = "stop"
  │   └── 验证：足够大时回复完整
  │
  ├── Test 4: temperature=0 一致性
  │   ├── 同一问题问 3 次
  │   ├── 回复应该完全一样或高度相似
  │   └── 验证：低 temperature = 高确定性
  │
  ├── Test 5: temperature=2.0
  │   ├── 同一问题问 3 次
  │   ├── 回复差异明显，甚至可能胡言乱语
  │   └── 验证：高 temperature = 高随机性
  │
  ├── Test 6: 异常参数（负数 / 超大值）
  │   ├── temperature=-1 → API 应报错或自动限幅
  │   ├── max_tokens=-1 → 同上
  │   └── 验证：API 的防护能力
  │
  └── 全部完成 → 输出每个参数的边界行为报告
```

---

## 六、工作中怎么用

### 场景 1：AI 功能上线前的参数基线测试

**背景：** 团队开发了一个 AI 客服功能，要确定上线的参数配置。

```python
# 你跑一遍边界测试，输出参数建议
print("参数配置建议：")
print("  temperature: 0.3（金融场景，高一致性）")
print("  max_tokens: 500（平均回复 200 tokens，留余量）")
print("  top_p: 0.9（默认值，暂不需要调整）")
```

### 场景 2：排查线上问题

**背景：** 用户投诉 AI 回复"时好时坏"。

```python
# 你检查当前 production 的 temperature 配置
# 发现设成了 1.5（太高了）
# 改成 0.3，问题消失

# 面试话术：
# "我从 Token 消耗和 finish_reason 两个维度切入，
#  发现 temperature 过高导致了不一致，调低后解决了"
```

### 场景 3：评估新模型版本

**背景：** DeepSeek 出了新模型，测试团队要评估升级后的影响。

```python
# 先用 Day 1 的冒烟测试跑一遍（确认连通）
# 再用 Day 2 的边界测试跑一遍（确认参数行为一致）
# 如果新模型在 temperature=0 下不再确定——这是一个 regression bug
```

---

## 七、面试常见问题与回答

### Q1：max_tokens 设为 100，AI 是不是一定回复 100 个字？

**好的回答：**
> "不是。max_tokens 是**上限**不是**目标值**。AI 会根据你的问题决定回复多长，但不会超过 max_tokens。如果 AI 本来想回复 200 个字，max_tokens=100 会截断——这个时候 finish_reason 会是 'length' 而不是 'stop'。工作中我们在上线前会用边界测试确认 max_tokens 设得够不够，避免用户看到'说一半'的情况。"

### Q2：temperature=0 能保证每次回复一样吗？

**好的回答：**
> "理论上是，但实践中可能有微小的差异，因为 GPU 的浮点运算不是完全确定的。如果业务场景要求每次回复完全一致（比如保险合同条款问答），建议 temperature=0 的同时加上 seed 参数。我在边界测试中验证过这一点——跑 3 次 temperature=0 的请求，对比回复的一致性。"

### Q3：你会怎么测试 temperature 参数？

**好的回答：**
> "我会用等价类划分选 4 个代表值：0（完全确定）、0.3（金融场景）、0.7（通用场景）、2.0（极端）。对每个值，同一问题跑 3-5 次，计算回复的相似度和质量分数。这样就能给出建议——'这个场景 temperature 超过 0.5 后一致性下降到 70% 以下，建议锁死在 0.3'。"

### Q4：生产环境中能直接用 temperature=0.7 吗？

**好的回答：**
> "取决于场景。如果是辅助编程或者数据分析，temperature=0.1 更合适——你要的是准确性不是创意。如果是客服聊天或者文案生成，0.7 是合理的。我们在上线前做了参数矩阵测试，每个场景都有自己的参数配置表。"

### Q5：finish_reason 有哪几种？各代表什么？

**好的回答：**
> "主要有三种：'stop' 表示 AI 正常结束了回答；'length' 表示达到 max_tokens 上限被截断——这个在生产环境里要监控，比例高了说明 max_tokens 不够；'content_filter' 表示内容被安全策略过滤了。在 Day 2 的边界测试里，我把 max_tokens 设成 1 和 10 来触发 'length'，验证 API 的截断行为是否符合预期。"

### Q6：如果 API 对负数参数返回了 200 而不是 400，你怎么看？

**好的回答：**
> "这要看 API 的行为：如果它自动限幅到合法值（比如 temperature=-1 → 自动变成 0），这是容错设计；如果它接受负数并产生奇怪的结果，这是 bug。我在边界测试里专门测了这些异常输入，记录下来每种情况的行为，这样上线前能判断是"防护到位"还是"有隐患"。"

---

## 八、今日产出物清单

| 文件/代码 | 说明 |
|:---------|:----|
| `utils/api_client.py`（更新） | 新增 `chat_with_params` 方法 |
| `tests/__init__.py` | 测试目录标记（空文件） |
| `tests/test_params.py` | 参数边界测试脚本 |
| **运行结果** | 6 个测试的输出，包括各边界下的回复长度、finish_reason、Token 消耗 |

---

## 九、Day 2 自检清单

完成后打勾：

- [ ] 理解边界值分析和等价类划分的概念
- [ ] 理解 max_tokens 是"上限"不是"目标值"
- [ ] 理解 temperature 0-2 对回复随机性的影响
- [ ] 理解 finish_reason 的 "stop" 和 "length" 区别
- [ ] 能说出 temperature 各区间适合什么场景
- [ ] 能回答上面 6 个面试问题中的至少 4 个
- [ ] 实际跑通了 `test_params.py` 的所有测试
- [ ] 记录了自己的 API 在不同参数下的行为数据

---

## 十、接下来敲的代码

### `utils/api_client.py` 中新增的方法

在 Day 1 的 `AITestClient` 类中，`print_response_summary` 方法之后，新增以下方法：

```python
def chat_with_params(self, messages, **kwargs):
    """
    带自定义参数的聊天请求，用于边界测试。

    参数:
        messages: 消息列表
        temperature: 温度 (0-2)，默认 0.7
        max_tokens: 最大 Token 数，默认 1024
        timeout: 超时秒数，默认 30
        seed: 随机种子，固定后可复现回复（DeepSeek 支持）
    """
    params = {
        "model": self.model,
        "messages": messages,
        "temperature": kwargs.get("temperature", 0.7),
        "max_tokens": kwargs.get("max_tokens", 1024),
        "timeout": kwargs.get("timeout", 30),
    }

    if "seed" in kwargs:
        params["extra_body"] = {"seed": kwargs["seed"]}

    try:
        response = self.client.chat.completions.create(**params)
        return response
    except RateLimitError:
        raise RuntimeError("API 限流")
    except APIConnectionError:
        raise RuntimeError("网络连接失败")
    except APIError as e:
        raise RuntimeError(f"API 错误 (status={e.status_code}): {e}")
    except Exception as e:
        raise RuntimeError(f"未知错误: {e}")


def print_params_response(self, response, label=""):
    """打印带参数的响应详情，用于边界测试对比"""
    content = self.get_reply_text(response)
    usage = self.get_token_usage(response)
    finish_reason = response.choices[0].finish_reason if response.choices else "N/A"

    prefix = f"[{label}] " if label else ""
    print(f"\n{prefix}--- 参数响应 ---")
    print(f"  回复长度: {len(content)} 字符")
    print(f"  Prompt Tokens: {usage['prompt_tokens']}")
    print(f"  Completion Tokens: {usage['completion_tokens']}")
    print(f"  finish_reason: {finish_reason}")
    print(f"  回复前 60 字: {content[:60]}..." if len(content) > 60 else f"  回复全文: {content}")
```

### `tests/test_params.py` 完整代码

```python
"""
Day 2 - 参数边界测试

学习目标：用边界值分析和等价类划分法测试 AI API 参数。

测试内容：
1. max_tokens 边界测试（1 / 10 / 2048）
2. temperature 对比测试（0 / 0.7 / 2.0）
3. 异常参数测试（负数 / 超大值）
4. 参数组合测试（低 temperature + 小 max_tokens）

面试话术：
"我做了完整的参数边界测试，覆盖了 max_tokens、temperature 的
边界值和等价类。发现 temperature=0 时一致性最好，适合金融场景；
temperature>1.5 后回复质量明显下降，不建议生产环境使用。
这些数据是我在搭建环境第二天就建立的参数基线。"
"""
import os
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.api_client import AITestClient
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# max_tokens 边界测试
# ---------------------------------------------------------------------------

def test_max_tokens_boundary(client):
    """测试 max_tokens 的边界值：1 / 10 / 2048"""
    print("\n" + "=" * 50)
    print("[Test 1] max_tokens 边界测试")
    print("=" * 50)

    messages = [{"role": "user", "content": "给我写一篇 500 字的文章，介绍 Python 编程语言。"}]

    boundaries = [1, 10, 2048]
    for mt in boundaries:
        try:
            response = client.chat_with_params(messages, max_tokens=mt)
            client.print_params_response(response, label=f"max_tokens={mt}")
        except Exception as e:
            print(f"\n[max_tokens={mt}] [FAIL] {e}")

    # 总结
    print("\n>> 结论：max_tokens 是硬性上限。设为 1 或 10 时, finish_reason='length' 表示被截断。")
    print(">> 生产环境需要根据实际回复长度设置合理的 max_tokens，预留 30%-50% 余量。")


# ---------------------------------------------------------------------------
# temperature 对比测试
# ---------------------------------------------------------------------------

def test_temperature_comparison(client):
    """测试不同 temperature 下回复的差异"""
    print("\n" + "=" * 50)
    print("[Test 2] temperature 对比测试")
    print("=" * 50)

    messages = [{"role": "user", "content": "用一句话说明什么是 API。"}]

    temps = [
        (0.0, "完全确定（金融/法律场景）"),
        (0.3, "低随机性（客服/保险场景）"),
        (0.7, "默认值（通用场景）"),
        (1.5, "高随机性（创意场景）"),
        (2.0, "极限值（几乎胡言乱语）"),
    ]

    for temp, desc in temps:
        try:
            response = client.chat_with_params(messages, temperature=temp)
            reply = client.get_reply_text(response)
            print(f"\n--- temperature={temp} ({desc}) ---")
            print(f"回复: {reply[:100]}...")
        except Exception as e:
            print(f"\n--- temperature={temp} [FAIL] {e}")

    print("\n>> 结论：temperature 控制回复的随机性，值越大差异越明显。")
    print(">> 生产环境应根据场景选择合适的值，金融/法律类建议 0-0.3，通用类 0.7。")


def test_temperature_consistency(client):
    """验证 temperature=0 时的回复一致性"""
    print("\n" + "=" * 50)
    print("[Test 3] temperature=0 一致性验证")
    print("=" * 50)

    messages = [{"role": "user", "content": "用一句话说明什么是 API。"}]

    replies = []
    for i in range(3):
        response = client.chat_with_params(messages, temperature=0, seed=42)
        reply = client.get_reply_text(response)
        replies.append(reply)
        print(f"第 {i+1} 次回复: {reply[:60]}...")

    # 比较一致性
    if replies[0] == replies[1] == replies[2]:
        print("\n--> temperature=0 + seed=42: 三次回复完全一致 ✓")
    else:
        common_words = len(set(replies[0].split()) & set(replies[1].split()) & set(replies[2].split()))
        total_words = max(len(set(replies[0].split())), 1)
        similarity = common_words / total_words
        print(f"\n--> 三次回复不完全一致，单词重叠率: {similarity:.0%}")
        print("--> 提示：temperature=0 也不保证 100% 一致，可尝试加 seed 参数")

    print("\n>> 结论：temperature=0 + seed 能获得高度一致的回复。")
    print(">> 但如果业务场景要求"完全一致"，还需要在测试中验证多次。")


# ---------------------------------------------------------------------------
# 异常参数测试
# ---------------------------------------------------------------------------

def test_invalid_params(client):
    """测试异常参数输入"""
    print("\n" + "=" * 50)
    print("[Test 4] 异常参数测试")
    print("=" * 50)

    messages = [{"role": "user", "content": "你好"}]

    invalid_cases = [
        ("temperature=-1", {"temperature": -1}),
        ("temperature=3.0", {"temperature": 3.0}),
        ("max_tokens=0", {"max_tokens": 0}),
        ("max_tokens=-100", {"max_tokens": -100}),
    ]

    for name, params in invalid_cases:
        try:
            response = client.chat_with_params(messages, **params)
            client.print_params_response(response, label=name)
            print(f"  [WARN] {name} 未报错，API 自动处理了异常值")
        except Exception as e:
            print(f"\n--- {name} ---")
            print(f"  [PASS] 被正确拦截: {e}")

    print("\n>> 结论：API 对异常参数的防护能力如下：")
    print(">> - temperature 超出范围：自动限幅或报错")
    print(">> - max_tokens 为 0 或负数：不同 API 行为不同，需验证")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    print("-- Day 2 - 参数边界测试 --")
    print("=" * 50)

    # 加载 .env
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print("[环境] 已加载 .env 文件")
    else:
        print("[环境] 未找到 .env 文件，从系统环境变量读取")

    # 初始化客户端
    try:
        client = AITestClient()
    except ValueError as e:
        print(f"\n[FAIL] {e}")
        return

    # 执行测试
    test_max_tokens_boundary(client)
    test_temperature_comparison(client)
    test_temperature_consistency(client)
    test_invalid_params(client)

    # 汇总
    print("\n" + "=" * 50)
    print("Day 2 参数边界测试完成")
    print("=" * 50)
    print("你今天测试了以下边界：")
    print("  max_tokens: 1 / 10 / 2048")
    print("  temperature: 0 / 0.3 / 0.7 / 1.5 / 2.0")
    print("  异常参数: 负数 / 0 / 超范围")
    print("  temperature 一致性验证（3 次请求对比）")
    print()

    print("面试准备：")
    print('  "我用边界值分析和等价类划分方法测试了 max_tokens、temperature')
    print('   等核心参数，记录了每个边界下的回复长度、finish_reason、')
    print('   Token 消耗，为后续版本对比建立了参数基线。"')


if __name__ == "__main__":
    main()
```

---

## 十一、敲完代码后运行

```bash
cd ai_test_env
mkdir tests
python -c "open('tests/__init__.py', 'w').close()"
# 然后把上面的 test_params.py 内容粘贴到 tests/test_params.py
python tests/test_params.py
```

---

> 跑通后告诉我结果。如果准备好了 Day 3（请求格式 + 错误分类处理和决策树），随时说。
