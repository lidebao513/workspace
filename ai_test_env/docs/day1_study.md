# Day 1：AI API 环境搭建 + 冒烟测试

> 对应 8 周计划第 1 周 Day 1
> 目标城市：上海 | 目标岗位：AI 测试工程师
> 学习时间：约 1.5 小时

***

## 学习目标

通过学习本章节，你将能够：

1. 理解 API、API Key、Base URL、Token 等核心概念
2. 独立搭建完整的 AI 测试环境，包括虚拟环境配置、依赖安装和环境变量管理
3. 掌握 OpenAI SDK 的基本使用方法，能够封装可复用的 API 客户端
4. 设计并实现有效的冒烟测试用例，覆盖连通性、基本功能、Token 基线和异常处理
5. 理解 AI 测试与传统测试的核心区别，建立非确定性测试的思维方式

***

## 一、今日学习目标

| 目标                   | 说明                              |
| :------------------- | :------------------------------ |
| 搭建 DeepSeek API 调用环境 | 从零创建一个 Python 项目，配置虚拟环境、安装依赖    |
| 理解 API 调用基础          | 了解 HTTP 请求、API Key、Base URL 的概念 |
| 实现第一个冒烟测试            | 验证 API 连通性、基本对话、Token 记录、异常处理   |
| 建立测试基线               | 记录首次 Token 消耗数据，作为后续对比基准        |

**面试对应问题：** "你搭建过 AI 测试环境吗？" / "你的 AI 测试环境是怎么做的？"

***

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

| 类比             | 说明                            |
| :------------- | :---------------------------- |
| API Key = 会员卡号 | 服务端通过 Key 识别你是谁、权限够不够、扣哪个账号的钱 |
| 不要把 Key 写代码里   | 就像不会把银行卡密码写在便利贴上贴电脑上          |
| 用 .env 文件管理    | 环境变量文件，不入 git，只有本地能看到         |

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

| 提供商      | Base URL                         | 特点        |
| :------- | :------------------------------- | :-------- |
| DeepSeek | `https://api.deepseek.com`       | 国内访问快，价格低 |
| OpenAI   | `https://api.openai.com/v1`      | 国际通用，价格较高 |
| 通义千问     | `https://dashscope.aliyuncs.com` | 阿里云生态     |

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

***

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

| 维度     | 传统测试         | AI 测试             |
| :----- | :----------- | :---------------- |
| 预期结果   | 确定的（输入X→输出Y） | 概率的（输入X→输出在合理范围内） |
| 断言方式   | 相等/不等        | 评估/打分/分类          |
| 回归验证   | 旧用例100%通过    | 旧用例可能产生不同回复       |
| bug 定位 | 代码行级别        | 黑盒，原因在千亿参数里       |
| 测试覆盖   | 路径覆盖         | 场景覆盖 + 质量维度覆盖     |

**面试话术：**

> "大模型不是写出来的，是训练出来的。这意味着你不能用传统的方式测它——你不能说'这里应该输出'发烧''，而是说'这里应该输出一个表示体温异常的回答，且不能输出医疗诊断'。AI 测试的思维转变是：从验证'对不对'到评估'好不好'。"

***

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
- 兼容多家供应商——DeepSeek / 通义千问 / 零一万物都兼容 OpenAI SDK 格式，改个 base\_url 就换

**实操关联：** 我们今天创建 `api_client.py` 时用的就是 OpenAI SDK。它让我们的测试代码干净、可读、好维护。

***

### 2.8 大模型的能力边界——什么能做、什么不能做

**一句话定义：** 大模型很强大，但有自己的"硬伤"。测试时如果让它做它不擅长的事，结果不可靠。

**能做（擅长的领域）：**

| 能力   | 例子          | 测试关注点     |
| :--- | :---------- | :-------- |
| 文本总结 | 总结文章要点      | 完整性、准确性   |
| 翻译   | 中译英、英译中     | 语义保留、流畅度  |
| 代码生成 | 写 Python 函数 | 语法正确、逻辑正确 |
| 创意写作 | 写邮件、写文案     | 符合风格要求    |
| 信息提取 | 从文本中提取日期/人名 | 召回率、精确率   |
| 角色扮演 | 扮演客服回答      | 行为一致性     |

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

**实操关联：** 今天写的 smoke\_test.py 中的测试用例（"请介绍你自己"、"Python 是什么"）都是在模型擅长的范围内测试。没有测试数学运算、精确计数等模型不擅长的事。这本身就是好的测试设计。

***

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

***

## 📌 新增内容：虚拟环境使用指南

> 以下内容为补充内容，帮助新手解决环境配置问题。

### 3.1 为什么要用虚拟环境？

**一句话解释：** 虚拟环境就像给每个项目分配一个独立的"房间"，里面有自己的依赖版本，不会和其他项目打架。

| 场景              | 不用虚拟环境    | 用虚拟环境                                  |
| :-------------- | :-------- | :------------------------------------- |
| 项目A需要openai=1.0 | 装在全局      | 项目A的房间里装1.0                            |
| 项目B需要openai=2.0 | 冲突！只能二选一  | 项目B的房间里装2.0                            |
| 同事接手项目          | "我这边跑不起来" | 跑 `pip install -r requirements.txt` 搞定 |

### 3.2 创建和激活虚拟环境

```bash
# 1. 创建虚拟环境（在你项目目录下）
python -m venv venv

# 2. Windows PowerShell 激活
.\venv\Scripts\Activate.ps1

# 3. 激活成功后，命令行会显示 (venv) 前缀
(venv) PS C:\Users\xxx\ai_test_env>
```

**常见问题：**

- 如果 PowerShell 报错"禁止运行脚本"，需要先执行：
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

### 3.3 安装项目依赖

```bash
# 确保已激活虚拟环境（看到 (venv) 前缀）

# 一键安装所有依赖
pip install -r requirements.txt

# 验证安装成功
pip list | grep openai
```

### 3.4 退出虚拟环境

```bash
# 退出虚拟环境（回到系统 Python）
deactivate
```

### 3.5 requirements.txt 文件内容

```txt
# 核心依赖 - 必装
openai>=1.13.0              # OpenAI SDK，支持 DeepSeek 等兼容 API
python-dotenv>=1.0.0        # 支持从 .env 文件读取环境变量

# 测试框架 - Day 2 及以后会用到
pytest>=7.4.0               # Python 单元测试框架
pytest-html>=4.0.0           # 生成 HTML 测试报告
```

### 3.6 .gitignore 配置详解

```gitignore
# ========== Python 相关 ==========
# Python 字节码缓存（自动生成，不需要上传）
__pycache__/
*.py[cod]        # *.pyc, *.pyo, *.pyd
*$py.class       # Windows 编译的 Python 类

# 虚拟环境（每个人的环境不同，不需要同步）
venv/
env/
.venv/

# ========== 敏感信息 ==========
# 环境变量文件（包含 API Key！）
.env
.env.local
.env.*.local

# ========== IDE 配置 ==========
.vscode/
.idea/
*.swp
*.swo
*~

# ========== 日志和临时文件 ==========
*.log
*.tmp
.DS_Store      # macOS 系统文件
Thumbs.db       # Windows 系统文件

# ========== 测试相关 ==========
htmlcov/
.coverage
.pytest_cache/
```

**为什么忽略这些？**

- `venv/`：虚拟环境，每个人的 Python 版本和依赖版本可能不同
- `.env`：包含 API Key 等敏感信息，绝对不能上传
- `__pycache__/`：Python 运行时自动生成的缓存，没必要上传

***

### 📌 新增内容：环境变量优先级与配置管理

### 3.7 环境变量优先级

当存在多个配置来源时，Python 按以下优先级（从高到低）读取：

```python
# 优先级从高到低：
# 1. 操作系统环境变量（export LINUX_VAR=value）
# 2. .env 文件中的变量
# 3. 代码中的默认值

# 示例：假设 .env 中写的是 deepseek-chat
# 但系统环境变量 MODEL_NAME=deepseek-reasoner
# 那么实际使用的是 deepseek-reasoner

self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
#                         ↑ 系统环境变量优先于默认值
```

### 3.8 python-dotenv 高级用法

**多环境配置：**

```bash
# .env.development - 开发环境
DEEPSEEK_API_KEY=sk-dev-xxxxx
API_BASE=https://api.deepseek.com
DEBUG=true

# .env.production - 生产环境
DEEPSEEK_API_KEY=sk-prod-xxxxx
API_BASE=https://api.deepseek.com
DEBUG=false
```

```python
# 加载指定环境的配置
from dotenv import load_dotenv

# 开发环境
load_dotenv(".env.development")

# 生产环境
load_dotenv(".env.production")
```

**变量引用：**

```bash
# .env 支持变量引用
PROJECT_NAME=ai_test_env
LOG_DIR=${PROJECT_NAME}/logs
CONFIG_PATH=${PROJECT_NAME}/config
```

***

### 📌 新增内容：测试结果保存与问题排查

### 3.9 保存 Token 基线数据

```python
import json
import datetime

def save_token_baseline(usage, filename="token_baseline.json"):
    """保存 Token 基线数据，用于后续对比"""
    baseline = {
        "timestamp": datetime.datetime.now().isoformat(),
        "model": "deepseek-chat",
        "usage": usage,
        "cost_cny": (
            usage['prompt_tokens'] * 1 +
            usage['completion_tokens'] * 2
        ) / 1_000_000  # DeepSeek 定价
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)

    print(f"✅ 基线已保存: {baseline['cost_cny']:.6f} CNY")

# 使用示例
usage = client.get_token_usage(response)
save_token_baseline(usage)
```

### 3.10 与基线对比检测异常

```python
def compare_with_baseline(current_usage, baseline_file="token_baseline.json"):
    """对比当前消耗与基线，检测异常"""
    import os
    if not os.path.exists(baseline_file):
        print("⚠️  基线文件不存在，跳过对比")
        return

    with open(baseline_file, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    current_total = current_usage['total_tokens']
    baseline_total = baseline['usage']['total_tokens']

    # 计算偏差比例
    deviation = (current_total - baseline_total) / baseline_total

    print(f"\n📊 Token 消耗对比：")
    print(f"   基线: {baseline_total} tokens")
    print(f"   当前: {current_total} tokens")
    print(f"   偏差: {deviation:+.1%}")

    # 偏差超过 50% 则告警
    if abs(deviation) > 0.5:
        print(f"⚠️  Token 消耗异常！请检查是否模型版本变更或输入变长")
    else:
        print(f"✅ Token 消耗正常")

# 运行对比
usage = client.get_token_usage(response)
compare_with_baseline(usage)
```

***

### 3.11 常见问题排查指南

| 错误现象                                            | 可能原因              | 排查步骤                                                                          |
| :---------------------------------------------- | :---------------- | :---------------------------------------------------------------------------- |
| `ModuleNotFoundError: No module named 'openai'` | 没装依赖或没激活虚拟环境      | 1. 检查命令行是否有 `(venv)` 前缀2. 运行 `pip install openai`3. 检查是否在正确的目录下               |
| `ValueError: DEEPSEEK_API_KEY 未配置`              | .env 文件没配置或路径不对   | 1. 确认 `.env` 文件存在于项目根目录2. 检查 KEY 是否正确复制（不要有空格）3. 确认文件名是 `.env` 而不是 `.env.txt` |
| `RateLimitError: Rate limit reached`            | API 调用频率超限        | 1. 等待 1 分钟再试2. 检查是否有多余的程序在调用 API3. 登录 DeepSeek 平台查看用量                         |
| `APIConnectionError`                            | 网络问题或 Base URL 错误 | 1. 检查网络连接2. 确认 Base URL 是 `https://api.deepseek.com`3. 尝试访问 API 地址是否正常        |
| `AuthenticationError: Incorrect API key`        | API Key 无效或过期     | 1. 检查 Key 是否正确复制2. 登录 DeepSeek 平台确认 Key 状态3. 确认 Key 没有被删除或禁用                  |
| 程序卡住没有响应                                        | 请求超时              | 1. 检查网络是否稳定2. 增加 timeout 参数的值3. 按 Ctrl+C 中断，查看错误信息                            |

**快速诊断命令：**

```bash
# 检查 Python 版本（需要 3.8+）
python --version

# 检查虚拟环境是否激活
which python  # Windows 用 where python

# 检查已安装的包
pip list | grep -E "openai|dotenv"

# 测试 API 连通性
curl https://api.deepseek.com
```

***

***

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

| 参数            | 值                                  | 作用      | 面试常问                    |
| :------------ | :--------------------------------- | :------ | :---------------------- |
| `model`       | `deepseek-chat`                    | 指定用哪个模型 | "你知道有哪些模型可用？"           |
| `messages`    | `[{"role":"user","content":"你好"}]` | 对话内容    | "messages 结构是什么样的？"     |
| `temperature` | 0.7 (范围 0-2)                       | 控制回复随机性 | "temperature 高低各有什么影响？" |
| `max_tokens`  | 1024                               | 最大生成长度  | "max\_tokens 设太小会怎样？"   |
| `timeout`     | 30 秒                               | 超时保护    | "生产环境 timeout 设多少合适？"   |

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

***

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

***

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

***

## 七、面试常见问题与回答

### Q1：你搭建过 AI 测试环境吗？

**普通回答：** "我了解过怎么调 API。"

**好的回答（你今天学完后可以这样说的）：**

> "是的，我从零搭建过完整的 AI 测试环境。我用 python-dotenv 做环境变量管理，把 API Key 和模型配置分离到 .env 文件，不入 Git。然后用 OpenAI SDK 封装了统一的客户端，包含异常分类处理（限流、网络失败、API 错误分别处理）。第一天就跑通了冒烟测试，覆盖了连通性、基本对话、Token 基线、异常请求四个维度。"

### Q2：AI 测试和传统测试有什么区别？

**好的回答：**

> "最大的区别是**非确定性**。传统测试是'输入 A 期待输出 B'，对就是对错就是错。但 AI 测试里，同一个问题问两次，答案可能不同。所以我们的断言方式变了——不是判断'对错'，而是评估多个**质量维度**：准确性、一致性、安全性、完整性。比如 Day 1 我们做的事情，在传统测试里只是'通不通'的问题，但在 AI 测试里，这是建立基线的开始——第一次的 Token 消耗、回复长度、finish\_reason 都是日后对比的依据。"

### Q3：API 调用失败了你怎么办？

**好的回答：**

> "我有一套分类处理策略：如果是限流（429），做指数退避重试；如果是连接超时，先重试再检查网络；如果是 400 参数错误，直接报错不重试，因为重试也没用；如果是 500 服务器错误，重试 3 次，还是失败就告警。这些分类逻辑我在 Day 1 的客户端封装里就做了。"

### Q4：什么是 Token？你怎么管理 Token 消耗？

**好的回答：**

> "Token 是大模型理解文本的最小语义单位，不是按字数算的。一般 1 个中文字 ≈ 1-2 个 Token。我们第一天就建立了 Token 消耗基线——每次调用记录 prompt\_tokens 和 completion\_tokens，并换算成费用。这样以后版本升级如果 Token 消耗突然暴增，我们第一时间就能发现。我还会把这个基线做成每日报告，月底跟财务对账用。"

### Q5：你知道 messages 的结构吗？

**好的回答：**

> "messages 是一个列表，每个元素是一个字典，包含 role 和 content。role 有三种：system（设定 AI 角色和行为规则）、user（用户输入）、assistant（AI 回复）。System prompt 只在第一轮发送，user 和 assistant 交替出现组成对话历史。非法传入其他 role 会返回 400 错误，我在 Day 1 的测试中验证过这一点。"

### Q6：你对这个项目有什么可以改进的？

**好回答（展示思考深度的）：**

> "目前只是一个 Python 脚本，如果后续要规模化使用，我会做三件事：第一，用 pytest 组织用例，支持 `-m smoke` 只跑冒烟；第二，加 CI 自动跑；第三，把 Token 基线保存到文件或数据库，方便追踪趋势。"

**这就是面试中展示"工程化思维"的方式**——不只是回答"我做了什么"，而是说"如果让我继续做，我会怎么做"。

***

## 八、今日产出物清单

| 文件                    | 说明        | 面试价值       |
| :-------------------- | :-------- | :--------- |
| `ai_test_env/`        | 完整项目目录    | 展示你有工程化能力  |
| `.env`                | 环境变量隔离    | 展示你有安全意识   |
| `utils/api_client.py` | API 客户端封装 | 展示你的封装设计能力 |
| `smoke_test.py`       | 冒烟测试脚本    | 展示你的测试设计能力 |
| **运行结果**              | 4 个测试全部通过 | 直接证明你能动手   |

***

## 九、Day 1 自检清单

完成后打勾：

- 理解 API / API Key / Base URL / Token 的概念
- 理解冒烟测试的含义
- 理解 `.env` 文件为什么要入 `.gitignore`
- 读懂 `api_client.py` 的 `__init__` 和 `chat` 方法
- 理解 `finish_reason` 的三种值和含义
- 理解 Token 消耗的费用换算方法
- 能在面试中说出"我的 Day 1 做了什么"
- 能回答上面 6 个面试问题中的至少 4 个

***

***

## 面试题

### 面试题 1：如何设计一个可靠的 AI API 冒烟测试方案？

**参考答案：**

一个可靠的 AI API 冒烟测试方案应该包含以下核心维度：

1. **连通性测试**：验证 API 服务是否可达
   - 发送简单请求，验证响应状态码和基本响应结构
   - 设置合理的超时时间，避免测试挂起
2. **基本功能测试**：验证核心对话能力
   - 发送标准问候语，检查回复是否非空且符合预期格式
   - 测试不同类型的问题（事实性、创造性、指令性）
3. **Token 基线建立**：记录首次调用的 Token 消耗
   - 记录 prompt\_tokens、completion\_tokens 和总消耗
   - 换算成费用，作为后续对比的基准
4. **异常处理测试**：验证错误响应机制
   - 测试空消息、非法参数、超长时间请求等边界情况
   - 验证 API 返回正确的错误码（400/429/500）和错误信息
5. **稳定性保障**：
   - 添加重试机制，处理瞬时网络波动
   - 设定合理的断言阈值，适应 AI 响应的非确定性
6. **可观测性**：
   - 记录测试时间、响应耗时、Token 消耗等指标
   - 生成结构化的测试报告，便于问题定位

**代码示例：**

```python
def run_smoke_test():
    client = AITestClient()
    
    # 连通性测试
    try:
        response = client.chat([{"role": "user", "content": "hello"}])
        assert response is not None, "API 未返回响应"
        print("✅ 连通性测试通过")
    except Exception as e:
        print(f"❌ 连通性测试失败: {e}")
        return False
    
    # Token 基线记录
    usage = client.get_token_usage(response)
    print(f"📊 Token 消耗: {usage['total_tokens']}")
    
    return True
```

***

### 面试题 2：在 AI 测试中，如何处理 API Key 的安全管理？

**参考答案：**

在 AI 测试中，API Key 的安全管理至关重要，以下是最佳实践：

1. **使用环境变量管理**：
   - 绝对不要将 API Key 硬编码在代码中
   - 使用 `.env` 文件存储敏感信息，配合 `python-dotenv` 加载
   - 将 `.env` 文件添加到 `.gitignore`，防止误提交
2. **多环境配置分离**：
   - 为开发、测试、生产环境分别创建独立的配置文件（`.env.development`、`.env.production`）
   - 各环境使用不同的 API Key，权限最小化
3. **密钥轮换策略**：
   - 定期轮换 API Key（建议每月或每季度）
   - 在 CI/CD 流程中使用密钥管理服务（如 Vault、AWS Secrets Manager）
4. **访问控制**：
   - 限制 API Key 的调用频率和额度
   - 设置 IP 白名单，只允许指定地址访问
5. **日志脱敏**：
   - 在日志输出前对敏感信息进行脱敏处理
   - 避免在错误信息中暴露完整的 API Key
6. **权限审计**：
   - 定期审查 API Key 的使用记录
   - 及时撤销不再使用的密钥

**正确做法示例：**

```python
# .env 文件（不提交到 Git）
DEEPSEEK_API_KEY=sk-your-secret-key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 代码中使用
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL")
)
```

**错误做法示例：**

```python
# ❌ 错误：硬编码 API Key
client = OpenAI(api_key="sk-abc123def456")  # 密钥会随代码泄露
```

***

## 代码示例

### 完整可运行的冒烟测试脚本

```python
"""
AI API 冒烟测试脚本
用于验证 AI 测试环境是否正确配置
"""

import os
from openai import OpenAI, RateLimitError, APIConnectionError, APIError
from dotenv import load_dotenv

class AITestClient:
    """AI API 测试客户端封装"""
    
    def __init__(self, env_path: str = None):
        """
        初始化客户端
        
        Args:
            env_path: .env 文件路径，默认为 None（从系统环境变量读取）
        """
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()
        
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
        self._validate_config()
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
    
    def _validate_config(self):
        """验证配置是否完整"""
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY 环境变量未配置")
        if not self.base_url:
            raise ValueError("DEEPSEEK_BASE_URL 环境变量未配置")
    
    def chat(self, messages, temperature=0.7, max_tokens=1024, timeout=30):
        """
        发送聊天请求
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数，控制回复随机性（0-2）
            max_tokens: 最大生成长度
            timeout: 请求超时时间（秒）
        
        Returns:
            API 响应对象
        
        Raises:
            RuntimeError: 当 API 调用失败时
        """
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
            raise RuntimeError("API 限流，请稍后重试")
        except APIConnectionError:
            raise RuntimeError("网络连接失败，请检查网络或 API 地址")
        except APIError as e:
            raise RuntimeError(f"API 错误: {e}")
        except Exception as e:
            raise RuntimeError(f"未知错误: {e}")
    
    def get_reply_text(self, response) -> str:
        """从响应中提取回复文本"""
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content or ""
        return ""
    
    def get_token_usage(self, response) -> dict:
        """从响应中提取 Token 使用情况"""
        if not response.usage:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        return {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

def test_connectivity(client: AITestClient) -> bool:
    """测试 API 连通性"""
    print("🔍 测试 1: 连通性测试")
    try:
        messages = [{"role": "user", "content": "请回复'连通性测试通过'"}]
        response = client.chat(messages, max_tokens=50)
        reply = client.get_reply_text(response)
        
        assert len(reply) > 0, "回复为空"
        print(f"   ✅ 通过 - 回复: {reply}")
        return True
    except Exception as e:
        print(f"   ❌ 失败 - {e}")
        return False

def test_basic_chat(client: AITestClient) -> bool:
    """测试基本对话功能"""
    print("🔍 测试 2: 基本对话测试")
    test_cases = [
        {"name": "自我介绍", "content": "请用一句话介绍你自己"},
        {"name": "技术问答", "content": "Python 是什么类型的编程语言？"},
    ]
    
    all_pass = True
    for tc in test_cases:
        try:
            messages = [{"role": "user", "content": tc["content"]}]
            response = client.chat(messages, max_tokens=150)
            reply = client.get_reply_text(response)
            
            assert len(reply) > 0, f"{tc['name']} 回复为空"
            print(f"   ✅ {tc['name']} - 回复长度: {len(reply)} 字符")
        except Exception as e:
            print(f"   ❌ {tc['name']} - {e}")
            all_pass = False
    
    return all_pass

def test_token_baseline(client: AITestClient) -> bool:
    """记录 Token 消耗基线"""
    print("🔍 测试 3: Token 基线测试")
    try:
        messages = [{"role": "user", "content": "你好"}]
        response = client.chat(messages)
        
        usage = client.get_token_usage(response)
        input_cost = usage['prompt_tokens'] * 1 / 1_000_000   # 输入: 1 CNY/1M
        output_cost = usage['completion_tokens'] * 2 / 1_000_000  # 输出: 2 CNY/1M
        
        print(f"   📊 Token 消耗:")
        print(f"      - Prompt Tokens: {usage['prompt_tokens']}")
        print(f"      - Completion Tokens: {usage['completion_tokens']}")
        print(f"      - 总 Tokens: {usage['total_tokens']}")
        print(f"      - 预估费用: {(input_cost + output_cost):.6f} CNY")
        print(f"   ✅ Token 基线已建立")
        return True
    except Exception as e:
        print(f"   ❌ 失败 - {e}")
        return False

def test_error_handling(client: AITestClient) -> bool:
    """测试异常处理能力"""
    print("🔍 测试 4: 异常处理测试")
    
    # 测试空消息
    try:
        client.chat([])
        print("   ❌ 空消息未被正确拦截")
        return False
    except RuntimeError:
        print("   ✅ 空消息被正确拦截")
    
    # 测试非法 role
    try:
        client.chat([{"role": "invalid", "content": "test"}])
        print("   ❌ 非法 role 未被正确拦截")
        return False
    except RuntimeError:
        print("   ✅ 非法 role 被正确拦截")
    
    return True

def main():
    """主函数：运行所有冒烟测试"""
    print("🚀 开始 AI API 冒烟测试\n")
    
    try:
        # 初始化客户端
        client = AITestClient()
        print("✅ 客户端初始化成功")
    except ValueError as e:
        print(f"❌ 客户端初始化失败: {e}")
        return
    
    # 运行测试
    tests = [
        test_connectivity,
        test_basic_chat,
        test_token_baseline,
        test_error_handling,
    ]
    
    results = []
    for test in tests:
        results.append(test(client))
        print()
    
    # 汇总结果
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    if passed == total:
        print(f"🎉 所有测试通过！({passed}/{total})")
        print("✅ AI 测试环境配置正确")
    else:
        print(f"⚠️  部分测试失败！({passed}/{total})")
        print("请检查环境配置或 API 服务状态")

if __name__ == "__main__":
    main()
```

**使用方法：**

1. 在项目根目录创建 `.env` 文件，添加你的 API Key
2. 确保已安装依赖：`pip install openai python-dotenv`
3. 运行脚本：`python smoke_test.py`

***

## 练习题

### 练习题 1：环境配置验证

**题目：** 编写一个脚本来验证 AI 测试环境的配置是否正确。脚本需要检查：

1. Python 版本是否 >= 3.8
2. 虚拟环境是否已激活
3. 必要的依赖（openai、python-dotenv）是否已安装
4. `.env` 文件是否存在且包含必要的配置项

**要求：**

- 输出详细的检查结果
- 如果某项检查失败，给出修复建议

***

### 练习题 2：Token 消耗计算器

**题目：** 扩展 `AITestClient` 类，添加以下功能：

1. 添加一个方法 `calculate_cost()`，根据 Token 消耗计算费用
2. 添加一个方法 `set_price()`，允许动态设置不同模型的价格
3. 添加一个方法 `get_cost_estimate()`，根据输入文本预估费用

**价格参考：**

- DeepSeek-chat: 输入 1 CNY/1M tokens，输出 2 CNY/1M tokens
- DeepSeek-reasoner: 输入 2 CNY/1M tokens，输出 4 CNY/1M tokens

***

### 练习题 3：多模型对比测试

**题目：** 创建一个测试脚本，对比不同模型在同一输入下的表现：

1. 同时调用 deepseek-chat 和 deepseek-reasoner
2. 记录并对比两者的：
   - 响应时间
   - Token 消耗
   - 回复内容长度
   - finish\_reason
3. 生成对比报告

**要求：**

- 使用参数化方式运行测试
- 输出清晰的对比表格
- 分析哪个模型更适合不同的场景

***

> 准备好了就开始 Day 2？Day 2 将学习**参数边界测试**，用等价类划分和边界值分析法测试 temperature、max\_tokens 等参数的极限行为。

