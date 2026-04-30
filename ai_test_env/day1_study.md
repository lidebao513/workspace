# Day 1：AI API 环境搭建 + 冒烟测试

> 对应 8 周计划第 1 周 Day 1
> 目标城市：上海 | 目标岗位：AI 测试工程师
> 学习时间：约 1.5 小时

---

## 一、今日学习目标

| 目标 | 说明 |
|:----|:----|
| 搭建 DeepSeek API 调用环境 | 从零创建一个 Python 项目，配置虚拟环境、安装依赖 |
| 理解 API 调用基础 | 了解 HTTP 请求、API Key、Base URL 的概念 |
| 实现第一个冒烟测试 | 验证 API 连通性、基本对话、Token 记录、异常处理 |
| 建立测试基线 | 记录首次 Token 消耗数据，作为后续对比基准 |

**面试对应问题：** "你搭建过 AI 测试环境吗？" / "你的 AI 测试环境是怎么做的？"

---

## 二、前置知识讲解

### 2.1 什么是 API？

API（Application Programming Interface，应用程序编程接口）是程序之间通信的桥梁。

**打个比方：**
```
你去餐厅吃饭
└── 你（客户端）→ 告诉服务员（API）→ 厨房（服务器）
    └── 你点菜（发送请求）→ 服务员记录（API 处理）
        └── 厨房做菜（服务器处理）
            └── 服务员端菜（API 返回响应）→ 你吃（客户端使用）
```

大模型 API 也是这样：你发送"帮我写首诗"，API 处理请求，大模型生成回复，API 把回复返回给你。

### 2.2 API Key 是什么？

API Key 是调用 API 的**身份凭证**，相当于你的"会员卡号"。

| 类比 | 说明 |
|:----|:----|
| API Key = 会员卡号 | 服务端通过 Key 识别你是谁、权限够不够、扣哪个账号的钱 |
| 不要把 Key 写代码里 | 就像不会把银行卡密码写在便利贴上贴电脑上 |
| 用 .env 文件管理 | 环境变量文件，不入 git，只有本地能看到 |

**为什么不能用 Key 直接写代码里？**
```python
# 错误做法：Key 写死在代码里
client = OpenAI(api_key="sk-xxx...")  # 一旦代码上传 GitHub，全世界都能看到你的 Key

# 正确做法：从环境变量读取
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"))  # Key 只在你本地
```

### 2.3 什么是 Base URL？

每个 API 服务都有一个"地址"，所有请求都发到这个地址。DeepSeek 的地址是 `https://api.deepseek.com`。

**类比：**
- Base URL = 餐厅的总店地址
- API 路径 = 餐厅里的不同窗口（点餐窗口 / 结账窗口 / 投诉窗口）

不同 API 提供商的 Base URL 不同：
| 提供商 | Base URL | 特点 |
|:------|:---------|:----|
| DeepSeek | `https://api.deepseek.com` | 国内访问快，价格低 |
| OpenAI | `https://api.openai.com/v1` | 国际通用，价格较高 |
| 通义千问 | `https://dashscope.aliyuncs.com` | 阿里云生态 |

### 2.4 什么是 Token？

Token 是大模型理解和生成文本的**最小单位**。它不是按字数算的，而是按"语义片段"算的。

```
"你好，今天天气真好" → Token 化 → [你好] [今天] [天气] [真] [好]
                                    1个    2个    3个   4个   5个 Token

"Hello, how are you?" → Token 化 → [Hello] [, ] [how] [are] [you] [?]
                                     1个     2个    3个    4个    5个   6个 Token
```

**关键理解：**
- 1 个中文 ≈ 1-2 个 Token
- 1 个英文单词 ≈ 1-2 个 Token
- API 按 Token 收费，不是按次数收费
- 你发送的文字叫 **Prompt Tokens**（输入），AI 回复的文字叫 **Completion Tokens**（输出）
- 总消耗 = 输入 + 输出

### 2.5 什么是冒烟测试？

冒烟测试（Smoke Test）来源于硬件测试：**通电后看会不会冒烟**。如果不冒烟，说明硬件是起码能工作的。

在软件领域：
> 冒烟测试 = 最基本的"能跑通吗"测试
> 不测功能细节，只测"能不能连通"、"会不会崩"

**AI 测试的冒烟测试应该覆盖：**
1. 连通性 — API 地址能不能访问
2. 基本功能 — 能不能正常对话
3. 基线 — 记一笔基线数据用于对比
4. 异常 — 非法输入会不会优雅处理

---

### 2.6 大模型是什么？—— 从"写规则"到"喂数据"的范式转移

**一句话定义：** 大语言模型（Large Language Model, LLM）是通过海量文本训练出来的神经网络，它不是"写逻辑"，而是"预测下一个词"。

**传统程序 vs 大模型的根本区别：**

```
传统程序（规则驱动）：
  你写：if temperature > 37.5: return "发烧"
  → 逻辑是你写的，可预测、可调试、出错你知道为什么

大模型（数据驱动）：
  你喂："体温38度是什么情况？" → 模型回复"可能是发烧"
  → 模型没被告诉过"温度>37.5=发烧"这条规则，
    它看了几百万份病历和健康问答后"习得"了这条知识
```

**这对测试意味着什么？**

| 维度 | 传统测试 | AI 测试 |
|:----|:--------|:--------|
| 预期结果 | 确定的（输入X→输出Y） | 概率的（输入X→输出在合理范围内）|
| 断言方式 | 相等/不等 | 评估/打分/分类 |
| 回归验证 | 旧用例100%通过 | 旧用例可能产生不同回复 |
| bug 定位 | 代码行级别 | 黑盒，原因在千亿参数里 |
| 测试覆盖 | 路径覆盖 | 场景覆盖 + 质量维度覆盖 |

**面试话术：**
> "大模型不是写出来的，是训练出来的。这意味着你不能用传统的方式测它——你不能说'这里应该输出'发烧''，而是说'这里应该输出一个表示体温异常的回答，且不能输出医疗诊断'。AI 测试的思维转变是：从验证'对不对'到评估'好不好'。"

---

### 2.7 什么是 OpenAI SDK？—— 为什么 AI 测试要用它

**一句话定义：** SDK（Software Development Kit）是别人写好的工具包，你调它的函数，它帮你处理底层细节。

**不用 SDK 直接调 API vs 用 SDK 的对比：**

```python
# 不用 SDK：手动构造 HTTP 请求（约 30 行）
import requests
import json

response = requests.post(
    "https://api.deepseek.com/chat/completions",
    headers={
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    },
    json={
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "你好"}]
    }
)
if response.status_code == 200:
    data = response.json()
    reply = data["choices"][0]["message"]["content"]
else:
    # 手动解析错误
    error_data = response.json()
    print(error_data["error"]["message"])

# 用 SDK：3 行搞定
from openai import OpenAI
client = OpenAI(api_key=api_key, base_url=base_url)
response = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":"你好"}])
reply = response.choices[0].message.content
```

**SDK 自动帮你做的事：**
- 构造 HTTP 请求——你不用手写 headers、序列化 JSON
- 解析响应——返回的是 Python 对象，不是字符串，可以直接 `response.choices[0].message.content`
- 错误包装——HTTP 400/429/500 自动转成 Python 异常对象，可以 `except APIError as e:` 分类处理
- 兼容多家供应商——DeepSeek / 通义千问 / 零一万物都兼容 OpenAI SDK 格式，改个 base_url 就换

**实操关联：** 我们今天创建 `api_client.py` 时用的就是 OpenAI SDK。它让我们的测试代码干净、可读、好维护。

---

### 2.8 大模型的能力边界——什么能做、什么不能做

**一句话定义：** 大模型很强大，但有自己的"硬伤"。测试时如果让它做它不擅长的事，结果不可靠。

**能做（擅长的领域）：**
| 能力 | 例子 | 测试关注点 |
|:----|:-----|:----------|
| 文本总结 | 总结文章要点 | 完整性、准确性 |
| 翻译 | 中译英、英译中 | 语义保留、流畅度 |
| 代码生成 | 写 Python 函数 | 语法正确、逻辑正确 |
| 创意写作 | 写邮件、写文案 | 符合风格要求 |
| 信息提取 | 从文本中提取日期/人名 | 召回率、精确率 |
| 角色扮演 | 扮演客服回答 | 行为一致性 |

**不能做（硬伤——测试要避开或用特殊策略测）：**

**1. 精确数学计算**
```
问："12345 × 67890 = ？"
答："838,102,050"（实际是 838,102,050——碰巧对了，
    但换个数字就可能错，因为模型不是"算"的，是"猜"的）
→ 测试策略：不要用数学题测 AI 的"对错"，用计算器工具+AI 组合
```

**2. 实事知识有时效性**
```
问："2026 年世界杯在哪举办？"
答："2026 年世界杯将在美国、加拿大和墨西哥联合举办。"
→ 但如果训练数据截止于 2024 年，最新的消息它就不知道
→ 测试策略：区分"常识性问答"和"时效性问答"，后者需要联网搜索能力
```

**3. 幻觉（Hallucination）——自信地胡说**
```
问："推荐几本关于 AI 测试的书"
答："《AI 测试实战》作者张三..."
→ 这本书可能根本不存在，但模型用"很确信的语气"编了一个
→ 测试策略：对关键事实做交叉验证，不要只测一次
```

**4. 精确计数**
```
问："这句话有几个字：'今天天气真好啊'"
答："7 个字"（实际上是 6 个字）
→ 模型不擅长逐字计数
→ 测试策略：涉及数量的问题不要依赖模型自身的回答
```

**5. 多步推理链**
```
问："甲比乙大 3 岁，乙比丙大 2 岁，三人年龄总和 50 岁，甲几岁？"
→ 简单的三步推理，模型可能中间一步就错了
→ 测试策略：让模型"分步思考"（Chain-of-Thought），每一步都写出来
```

**面试话术：**
> "AI 测试的第一课是知道模型的能力边界。我不会让模型做数学运算——那是计算器的事。我不会让它回答今天几号——那是 API 的事。但我会用它做写作、总结、翻译、代码生成——这些是它真正擅长的。区分'什么是 AI 该做的事'和'什么事不该用 AI 做'，是 AI 测试的基本功。"

**实操关联：** 今天写的 smoke_test.py 中的测试用例（"请介绍你自己"、"Python 是什么"）都是在模型擅长的范围内测试。没有测试数学运算、精确计数等模型不擅长的事。这本身就是好的测试设计。

---

## 三、项目结构讲解

```
ai_test_env/                    ← 项目根目录
├── .env                        ← 环境变量文件（你的 API Key 放这里）
│                               └── 格式: KEY=VALUE，每行一个
│
├── .env.example                ← 环境变量模板（填好 Key 后复制为 .env）
│                               └── 这个文件可以上传到 GitHub，里面是假的 Key
│
├── .gitignore                  ← 告诉 Git 不要上传 .env（保护 Key 安全）
│
├── requirements.txt            ← 依赖清单
│                               └── pip install -r requirements.txt 一键安装
│
├── README.md                   ← 项目说明书
│                               └── 告诉别人这个项目是干什么的、怎么跑
│
├── smoke_test.py               ← 今天的主角：冒烟测试脚本
│                               └── 运行它就能验证你的 AI 环境是否正常
│
├── day1_study.md               ← 今天的学习文档（你正在看这个）
│
└── utils/                      ← 工具包目录
    └── api_client.py           ← API 客户端封装
                                └── 把所有调 API 的复杂逻辑藏在这里
```

---

## 四、代码逐行讲解

### 4.1 `.env` 文件

```
DEEPSEEK_API_KEY=sk-1b47dfe4e7c144118831d17e371968d0
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

**每行解释：**
- `DEEPSEEK_API_KEY` — 你的 API Key，作用是"告诉服务器你是谁、从你账号扣钱"
- `DEEPSEEK_BASE_URL` — API 地址，DeepSeek 就是这个
- `DEEPSEEK_MODEL` — 使用的模型名，`deepseek-chat` 是最新的对话模型

**重要原则：** `.env` 文件**永不提交**到 Git 仓库。为了安全，我们已经配置了 `.gitignore` 忽略它。

### 4.2 `utils/api_client.py` — API 客户端封装

这是今天最核心的代码。它把"调 API"这件事封装成一个类，方便其他代码直接使用。

#### `__init__` 方法：初始化客户端

```python
class AITestClient:
    def __init__(self, env_path: str = None):
        if env_path:
            from dotenv import load_dotenv
            load_dotenv(env_path)

        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
        self._check_environment()  # 检查配置是否完整
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
```

**逐行理解：**
1. `load_dotenv(env_path)` — 读取 `.env` 文件，把里面写的 KEY=VALUE 加载到环境变量
2. `os.getenv("DEEPSEEK_API_KEY")` — 从环境变量读取 API Key
3. `_check_environment()` — 检查 Key 是否为空，如果为空直接报错（防呆设计）
4. `OpenAI(api_key=..., base_url=...)` — 创建 OpenAI SDK 的客户端实例

**为什么不用 requests 直接调 API？**
- OpenAI SDK 封装了请求构建、响应解析、错误处理
- 用 SDK 3 行代码搞定的事，用 requests 要 20 行
- SDK 自动处理重连、超时等底层细节

#### `chat` 方法：发送请求

```python
def chat(self, messages, temperature=0.7, max_tokens=1024, timeout=30):
    try:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return response
    except RateLimitError:
        raise RuntimeError("API 限流")
    except APIConnectionError:
        raise RuntimeError("网络连接失败")
    except APIError as e:
        raise RuntimeError(f"API 错误: {e}")
    except Exception as e:
        raise RuntimeError(f"未知错误: {e}")
```

**参数讲解：**

| 参数 | 值 | 作用 | 面试常问 |
|:----|:---|:----|:--------|
| `model` | `deepseek-chat` | 指定用哪个模型 | "你知道有哪些模型可用？" |
| `messages` | `[{"role":"user","content":"你好"}]` | 对话内容 | "messages 结构是什么样的？" |
| `temperature` | 0.7 (范围 0-2) | 控制回复随机性 | "temperature 高低各有什么影响？" |
| `max_tokens` | 1024 | 最大生成长度 | "max_tokens 设太小会怎样？" |
| `timeout` | 30 秒 | 超时保护 | "生产环境 timeout 设多少合适？" |

**异常处理的设计思路：**
```python
# 不好的写法：什么都没处理
response = client.chat.completions.create(...)  # 如果网络断了，程序直接崩溃

# 好的写法：分类处理
try:
    response = client.chat.completions.create(...)
except RateLimitError:
    # 限流了 - 等一会儿重试
    time.sleep(5)
    retry()
except APIConnectionError:
    # 网络断了 - 检查网络，重试
    retry()
except APIError as e:
    if e.status_code == 400:
        # 参数错了 - 不要重试，报错给开发
        raise
    elif e.status_code == 500:
        # 服务器炸了 - 等一会儿重试
        time.sleep(5)
        retry()
```

**这就是生产级思维** — 大多数面试官听到这里会点头。

#### `get_reply_text` 和 `get_token_usage`：解析响应

```python
def get_reply_text(self, response) -> str:
    """从 API 响应中提取回复文本"""
    if response.choices and len(response.choices) > 0:
        return response.choices[0].message.content or ""
    return ""

def get_token_usage(self, response) -> Dict:
    """从 API 响应中提取 Token 使用情况"""
    if not response.usage:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens,
    }
```

**API 响应结构图示：**
```
API 响应
├── choices[0]           ← 回复内容（AI 说的话）
│   ├── message
│   │   ├── role         ← 角色（always "assistant"）
│   │   └── content      ← 实际回复文本 ← 这是我们要的
│   └── finish_reason    ← 为什么结束（"stop" / "length" / "content_filter"）
│                          ├── "stop" = 正常结束
│                          ├── "length" = 达到 max_tokens 被截断
│                          └── "content_filter" = 内容被过滤
└── usage                 ← Token 用量
    ├── prompt_tokens     ← 你的输入用了多少 Token
    ├── completion_tokens ← AI 回复用了多少 Token
    └── total_tokens      ← 总用量 = 输入 + 输出
```

**面试重点：** `finish_reason` 字段非常关键 — 如果大量出现 "length"，说明你的 `max_tokens` 设小了，回复经常被截断。

### 4.3 `smoke_test.py` — 冒烟测试脚本

#### 测试 1：连通性测试

```python
def test_connectivity(client):
    messages = [
        {"role": "user", "content": "你好，请回复'连通性测试通过'这六个字"}
    ]
    response = client.chat(messages, max_tokens=50)
    reply = client.get_reply_text(response)
    assert len(reply) > 0, "回复为空"
```

**设计思路：** 最简单的测试——问一句话，看能不能收到回复。不求内容多，只求"能通"。

#### 测试 2：基本对话测试

```python
test_cases = [
    {"name": "自我介绍", "content": "请用一句话介绍你自己"},
    {"name": "简单问答", "content": "Python 是什么类型的编程语言？"},
]
```

**设计思路：** 两个不同类型的对话场景，验证模型能理解并回应不同复杂度的问题。`参数化`设计——后面 Week 4 学 pytest 时会扩展成自动化的参数化用例。

#### 测试 3：Token 基线

```python
# 记录 Token 消耗
usage = client.get_token_usage(response)
# 换算费用
input_cost = usage['prompt_tokens'] * 1 / 1_000_000   # 1 CNY / 1M tokens
output_cost = usage['completion_tokens'] * 2 / 1_000_000  # 2 CNY / 1M tokens
```

**实际跑出来的数据：**
```
Prompt Tokens: 27       → 输入费用: 0.000027 CNY
Completion Tokens: 25   → 输出费用: 0.000050 CNY
总计: 52                → 总费用: 0.000077 CNY
```

**意味着什么：** 问一次问题大约花 0.000077 元。DeepSeek 新用户送的 10 元额度，可以问 **约 13 万次**。

#### 测试 4：异常请求测试

```python
# 测试空消息
response = client.chat([])  # 应该报错

# 测试非法 role
response = client.chat([{"role": "hacker", "content": "你好"}])  # 应该报错
```

**实际跑出来的结果：**
- 空消息 -> 正确拦截（RuntimeError）
- 非法 role -> API 返回 400，明确说"未知的 role hacker，期望是 system/user/assistant/tool 之一"

**面试加分点：** 这说明 DeepSeek API 的校验做得不错。如果你在公司发现某个 API 对非法输入返回 500（服务器内部错误）而不是 400（客户端参数错误），说明服务端没做好输入校验——这是个值得提的 bug。

---

## 五、实际运行流程

```
你运行 python smoke_test.py
  │
  ├── 读取 .env 文件，获取 API Key
  │
  ├── 创建 AITestClient 实例
  │   ├── 检查 Key 是否为空
  │   ├── 读取模型名和 Base URL
  │   └── 初始化 OpenAI 客户端
  │
  ├── Test 1: 连通性测试
  │   ├── 发送 "你好，请回复'连通性测试通过'"
  │   ├── DeepSeek 收到请求，调用模型
  │   ├── 模型生成回复："连通性测试通过"
  │   └── API 返回响应，检查内容非空 → PASS
  │
  ├── Test 2: 基本对话测试
  │   ├── 发送 "请用一句话介绍你自己"
  │   ├── DeepSeek 回复自我介绍
  │   ├── 发送 "Python 是什么类型的编程语言？"
  │   ├── DeepSeek 回复 Python 介绍
  │   └── 两次回复都非空 → PASS
  │
  ├── Test 3: Token 基线
  │   ├── 发送带 system prompt 的请求
  │   ├── 记录 usage（27 + 25 = 52 tokens）
  │   ├── 换算费用（0.000077 CNY）
  │   └── 建立基线 → PASS
  │
  ├── Test 4: 异常请求
  │   ├── 发送空消息 → 被拦截
  │   ├── 发送非法 role → 被 400 拒绝
  │   └── API 防护能力验证 → PASS
  │
  └── 全部通过！🎉
```

---

## 六、工作中怎么用

### 场景 1：新模型上线前的冒烟测试

**背景：** 公司部署了新的大模型版本，需要上线前做最基本的检查。

```python
# 你写的冒烟测试可以直接当上线前巡检用
def pre_release_smoke_check():
    client = AITestClient()
    
    checks = [
        ("连通性", test_connectivity),      # API 能不能通
        ("基础对话", test_basic_chat),      # 回不回复
        ("Token 异常", test_token_sanity),  # Token 消耗是否异常（突然暴增说明模型有问题）
        ("错误处理", test_error_handling),  # 异常输入是否优雅处理
    ]
    
    for name, check in checks:
        if not check(client):
            print(f"[BLOCKED] {name} 检查不通过，阻断发布！")
            return False
    
    print("[PASS] 所有冒烟检查通过，可以上线")
    return True
```

### 场景 2：环境配置检查

**背景：** 新同事入职，需要在他的电脑上配好 AI 测试环境。

```python
# 直接运行 smoke_test.py
# 如果全部通过 → 环境配置正确
# 如果连通性失败 → 检查网络 / API Key
# 如果依赖报错 → pip install 重装
# 新人不用问任何人，自己跑一遍就知道了
```

### 场景 3：定期巡检

**背景：** 每天 CI 自动跑一遍，确保 API 服务正常。

```python
# 把这个加入 GitHub Actions 的 daily workflow
# 每天早上 8 点自动跑 smoke_test.py
# 如果失败 → 自动发告警到钉钉/飞书
# 项目没有因为"API 挂了但没人发现"而出线上事故
```

---

## 七、面试常见问题与回答

### Q1：你搭建过 AI 测试环境吗？

**普通回答：** "我了解过怎么调 API。"

**好的回答（你今天学完后可以这样说的）：**
> "是的，我从零搭建过完整的 AI 测试环境。我用 python-dotenv 做环境变量管理，把 API Key 和模型配置分离到 .env 文件，不入 Git。然后用 OpenAI SDK 封装了统一的客户端，包含异常分类处理（限流、网络失败、API 错误分别处理）。第一天就跑通了冒烟测试，覆盖了连通性、基本对话、Token 基线、异常请求四个维度。"

### Q2：AI 测试和传统测试有什么区别？

**好的回答：**
> "最大的区别是**非确定性**。传统测试是'输入 A 期待输出 B'，对就是对错就是错。但 AI 测试里，同一个问题问两次，答案可能不同。所以我们的断言方式变了——不是判断'对错'，而是评估多个**质量维度**：准确性、一致性、安全性、完整性。比如 Day 1 我们做的事情，在传统测试里只是'通不通'的问题，但在 AI 测试里，这是建立基线的开始——第一次的 Token 消耗、回复长度、finish_reason 都是日后对比的依据。"

### Q3：API 调用失败了你怎么办？

**好的回答：**
> "我有一套分类处理策略：如果是限流（429），做指数退避重试；如果是连接超时，先重试再检查网络；如果是 400 参数错误，直接报错不重试，因为重试也没用；如果是 500 服务器错误，重试 3 次，还是失败就告警。这些分类逻辑我在 Day 1 的客户端封装里就做了。"

### Q4：什么是 Token？你怎么管理 Token 消耗？

**好的回答：**
> "Token 是大模型理解文本的最小语义单位，不是按字数算的。一般 1 个中文字 ≈ 1-2 个 Token。我们第一天就建立了 Token 消耗基线——每次调用记录 prompt_tokens 和 completion_tokens，并换算成费用。这样以后版本升级如果 Token 消耗突然暴增，我们第一时间就能发现。我还会把这个基线做成每日报告，月底跟财务对账用。"

### Q5：你知道 messages 的结构吗？

**好的回答：**
> "messages 是一个列表，每个元素是一个字典，包含 role 和 content。role 有三种：system（设定 AI 角色和行为规则）、user（用户输入）、assistant（AI 回复）。System prompt 只在第一轮发送，user 和 assistant 交替出现组成对话历史。非法传入其他 role 会返回 400 错误，我在 Day 1 的测试中验证过这一点。"

### Q6：你对这个项目有什么可以改进的？

**好回答（展示思考深度的）：**
> "目前只是一个 Python 脚本，如果后续要规模化使用，我会做三件事：第一，用 pytest 组织用例，支持 `-m smoke` 只跑冒烟；第二，加 CI 自动跑；第三，把 Token 基线保存到文件或数据库，方便追踪趋势。"

**这就是面试中展示"工程化思维"的方式**——不只是回答"我做了什么"，而是说"如果让我继续做，我会怎么做"。

---

## 八、今日产出物清单

| 文件 | 说明 | 面试价值 |
|:----|:----|:--------|
| `ai_test_env/` | 完整项目目录 | 展示你有工程化能力 |
| `.env` | 环境变量隔离 | 展示你有安全意识 |
| `utils/api_client.py` | API 客户端封装 | 展示你的封装设计能力 |
| `smoke_test.py` | 冒烟测试脚本 | 展示你的测试设计能力 |
| **运行结果** | 4 个测试全部通过 | 直接证明你能动手 |

---

## 九、Day 1 自检清单

完成后打勾：

- [ ] 理解 API / API Key / Base URL / Token 的概念
- [ ] 理解冒烟测试的含义
- [ ] 理解 `.env` 文件为什么要入 `.gitignore`
- [ ] 读懂 `api_client.py` 的 `__init__` 和 `chat` 方法
- [ ] 理解 `finish_reason` 的三种值和含义
- [ ] 理解 Token 消耗的费用换算方法
- [ ] 能在面试中说出"我的 Day 1 做了什么"
- [ ] 能回答上面 6 个面试问题中的至少 4 个

---

> 准备好了就开始 Day 2？Day 2 将学习**参数边界测试**，用等价类划分和边界值分析法测试 temperature、max_tokens 等参数的极限行为。
