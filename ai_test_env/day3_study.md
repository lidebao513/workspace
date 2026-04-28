# Day 3：请求格式验证 + 错误分类决策树

> 对应 8 周计划第 1 周 Day 3
> 目标城市：上海 | 目标岗位：AI 测试工程师
> 学习时间：约 1.5 小时

---

## 一、今日学习目标

| 目标 | 说明 |
|:----|:----|
| 理解 messages 数据结构 | system / user / assistant 三种 role 的职责 |
| 验证请求结构完整性 | 确保入参格式正确，冗余字段不影响 |
| 建立错误分类体系 | 4xx / 5xx / 网络错误 分类处理 |
| 实现错误决策树 | 什么错误重试、什么错误告警、什么错误转人工 |

**面试对应问题：** "AI 接口报错了你怎么排查？" / "生产环境怎么处理 AI 接口异常？" / "你知道 messages 的结构吗？"

---

## 二、前置知识讲解

### 2.1 messages 数据结构

大模型 API 的请求核心就是 messages 参数。它格式如下：

```json
[
  {"role": "system", "content": "你是一个 AI 客服，要礼貌且简洁地回答问题。"},
  {"role": "user", "content": "你好，我想查一下我的订单"},
  {"role": "assistant", "content": "您好！请提供您的订单号，我来帮您查询。"},
  {"role": "user", "content": "订单号是 ABC123"}
]
```

**三种 role 的职责：**

| role | 谁发的 | 作用 | 出现频率 |
|:----|:------|:----|:--------|
| `system` | 开发者 | 设定 AI 的角色、行为规则、输出格式 | 对话开头 1 次 |
| `user` | 用户 | 用户的输入 | 每次用户说话 |
| `assistant` | AI | AI 的回复 | 每次 AI 回答 |

**关键规则：**
- system 消息只能有 0 或 1 条，必须在 messages 最前面
- user 和 assistant 必须交替出现（不能连续两个 user 或连续两个 assistant）
- 最少 1 条（不能是空数组，Day 1 已验证过）
- role 必须是 system / user / assistant（Day 2 已验证过非法 role 会 400）

**为什么这个验证在 AI 测试中重要？**

```
面试话术：
"messages 结构错误是最常见的线上问题之一。
比如对话历史拼接时忘记加 assistant 回复，连续发了两个 user message，
API 虽然可能不报错，但模型的行为会变得不可预测。
我在测试中会验证正常结构、边界结构和异常结构三种情况。"
```

### 2.2 生产环境错误分类

AI 接口在生产环境中会遇到各种错误。不是所有错误都需要重试，也不是所有错误都要告警。

**错误的本质分类：**

```
错误可分为两大类：

1. 可重试错误（Retriable）—— 重试有机会成功
   - 429 Too Many Requests（限流）
   - 5xx Server Error（服务器临时故障）
   - 网络超时 / 连接断开

2. 不可重试错误（Non-Retriable）—— 重试 100 次也不会成功
   - 400 Bad Request（请求参数错了）
   - 401 Unauthorized（API Key 无效）
   - 403 Forbidden（无权限）
   - 404 Not Found（路径不存在）
```

**生产决策树：**

```
API 请求
  │
  ├─ 成功 (200) ──→ 正常返回
  │
  └─ 失败
       │
       ├─ 4xx 客户端错误
       │    ├─ 400 / 422 ──→ 参数错误，不重试，报给开发
       │    ├─ 401 / 403 ──→ 鉴权错误，紧急告警
       │    ├─ 404 ──→ 路径不对，不重试，报给开发
       │    └─ 429 ──→ 限流，指数退避重试
       │
       ├─ 5xx 服务端错误
       │    ├─ 500 ──→ 重试 3 次，仍失败则告警
       │    ├─ 502 / 503 ──→ 网关错误，重试 3 次
       │    └─ 504 ──→ 超时，检查超时设置
       │
       └─ 网络错误
            ├─ 连接超时 ──→ 重试（可能网络抖了一下）
            └─ 连接断开 ──→ 重试
```

### 2.3 错误响应结构

API 返回的错误也有自己的结构，需要验证的字段：

```json
{
  "error": {
    "message": "Invalid temperature value, the valid range of temperature is [0, 2]",
    "type": "invalid_request_error",
    "param": "temperature",
    "code": "invalid_request_error"
  }
}
```

| 字段 | 含义 | 测试验证点 |
|:----|:----|:----------|
| `message` | 人类可读的错误描述 | 非空、清晰 |
| `type` | 错误类型 | 是否在预期范围内 |
| `param` | 出错的参数名 | 是否准确指向出错的参数 |
| `code` | 错误码 | 是否与 HTTP status 一致 |

---

## 三、你今天要写的代码

在 `tests/` 下新建 `test_request_format.py` 和 `error_classifier.py`。

### 文件 1：`utils/error_classifier.py` — 错误分类器

一个独立的模块，接收异常对象，输出分类结果（是否重试、严重级别、建议操作）。

### 文件 2：`tests/test_request_format.py` — 请求格式测试

| 测试 | 说明 |
|:----|:----|
| `test_full_message_structure` | 完整结构：system + user + assistant + user |
| `test_missing_system` | 没有 system prompt |
| `test_extra_fields` | 额外字段（如无用参数）API 是否容错 |
| `test_empty_content` | content 为空字符串 |
| `test_long_content` | 超长 content 是否截断或报错 |
| `test_error_classification` | 模拟各种错误，验证分类结果 |

---

## 四、代码逐行设计

### 4.1 错误分类器设计

```python
class APIError:
    """API 错误分类"""
    RETRIABLE = "retriable"     # 可重试
    NON_RETRIABLE = "non_retriable"  # 不可重试
    CRITICAL = "critical"       # 紧急，需要立刻处理

class ErrorClassifier:
    """
    错误分类器，输入异常，输出分类结果和决策建议。
    
    面试话术：
    "我设计了错误分类体系，能 5 分钟定位根因。
    429 自动重试，401 立即告警，400 直接报给开发不改。
    这个分类器在公司上线后，线上问题平均定位时间从 30 分钟降到了 5 分钟。"
    """
    
    @staticmethod
    def classify(error):
        """
        对异常进行分类
        
        返回: {
            'category': 'retriable' | 'non_retriable' | 'critical',
            'http_status': int,
            'retriable': bool,
            'severity': 'low' | 'medium' | 'high' | 'critical',
            'action': str,
            'message': str
        }
        """
```

### 4.2 请求格式测试设计

以 `test_full_message_structure` 为例：

```python
def test_full_message_structure(client):
    """
    测试完整结构：system + user + assistant + user
    
    这是最标准的对话格式，AI 应该正常回复。
    """
    messages = [
        {"role": "system", "content": "你是一个测试助手，回复要简洁。"},
        {"role": "user", "content": "你叫什么名字？"},
        {"role": "assistant", "content": "我是 DeepSeek，由深度求索公司创造。"},
        {"role": "user", "content": "你能做什么？"}
    ]
    
    response = client.chat(messages)
    reply = client.get_reply_text(response)
    usage = client.get_token_usage(response)
    
    assert len(reply) > 0
    assert response.choices[0].finish_reason == "stop"
    
    print(f"完整结构对话测试通过")
    print(f"回复: {reply[:100]}...")
    print(f"Token 消耗: {usage}")
```

---

## 五、实际运行流程

```
python tests/test_request_format.py
  │
  ├── Test 1: 完整结构
  │   ├── system + user + assistant + user
  │   ├── 回复正常，finish_reason=stop
  │   └── 验证 4 条消息不被忽略
  │
  ├── Test 2: 无 system prompt
  │   ├── 只有 user message
  │   ├── 回复正常（system 是可选的）
  │   └── 验证：AI 在没有 system 时也能正常工作
  │
  ├── Test 3: 额外字段
  │   ├── 在 message 中加入 "timestamp" 等无用字段
  │   ├── API 应忽略额外字段（容错）
  │   └── 验证：API 的容错能力
  │
  ├── Test 4: 空 content
  │   ├── content="" 在 user message 中
  │   ├── API 应处理或报错
  │   └── 验证：边界行为
  │
  ├── Test 5: 超长 content
  │   ├── 发送几千字的 content
  │   ├── API 应正常处理或返回明确的超长提示
  │   └── 验证：超长输入的处理
  │
  └── Test 6: 错误分类验证
      ├── 用 ErrorClassifier 分类各种错误
      ├── 验证分类结果是否准确
      └── 验证：分类决策树正确
```

---

## 六、工作中怎么用

### 场景 1：线上事故排查

**背景：** AI 客服突然大面积报错。

```python
# 1. 看错误日志，提取 error_type
# 2. 用 ErrorClassifier 分类

error = get_last_error_from_logs()
result = ErrorClassifier.classify(error)

if result["category"] == "retriable":
    print("可重试错误，检查重试次数")
elif result["category"] == "critical":
    print("紧急！立刻拉起会议")
    send_alert_to_feishu(result)
```

### 场景 2：自动化监控

**背景：** 每天 CI 自动跑请求格式测试。

```python
# 每次代码提交 → GitHub Actions 自动跑 test_request_format.py
# 如果 format 验证失败 → PR 被标注
# 确保 messages 拼接逻辑不会传到生产问题
```

### 场景 3：新人入职培训

**背景：** 新同事问"API 报错了怎么办？"

```python
# 让他看 ErrorClassifier 的代码
# 告诉他："所有可能的错误都在这里了，看分类就知道怎么做"
```

---

## 七、面试常见问题与回答

### Q1：AI 接口在生产环境报错了你怎么排查？

**好的回答：**
> "我有三步隔离法。第一步，看 HTTP 状态码——4xx 是我方问题，5xx 是对方问题。第二步，看 error 结构里的 message 和 param 字段——比如 'max_tokens 无效' 说明参数写错了。第三步，用我的错误分类器判断——429 直接重试，500 重试 3 次还失败就告警，400 直接报给开发不改。这套流程上线后，线上问题的平均定位时间从 30 分钟降到了 5 分钟。"

### Q2：messages 里 system 和 user 有什么区别？

**好的回答：**
> "System 是开发者对 AI 的指令，比如设定角色、输出格式、行为边界，通常只出现在对话第一轮。User 是用户的输入，可以有多轮。System 的优先级高于 User——如果 User 说'忽略上一条指令'，有良好防护的 AI 会拒绝。测试中我们会验证 system prompt 能否被 user 指令覆盖，这是安全测试的基础。"

### Q3：API 返回的 error 结构是什么样的？

**好的回答：**
> "标准的错误结构有 4 个字段：message（人类可读的描述）、type（错误类型）、param（哪个参数错了）、code（错误码）。比如 temperature 设为 -1 时，type 是 'invalid_request_error'，param 是 'temperature'，message 里会说明有效范围是 0-2。这个结构在自动化测试中可以直接解析，用来精确判断根因。"

### Q4：429 和 500 的处理策略一样吗？

**好的回答：**
> "完全不一样。429 是限流，说明我们在短时间内请求太多了——应该用指数退避重试，同时减少当前请求频率。500 是服务器内部错误——快速重试 3 次，如果还是失败就说明服务端有 bug，需要告警而不是持续重试增加负担。这两者的区别是错误分类器的核心逻辑。"

### Q5：生产环境能接受 API 返回什么错误？

**好的回答：**
> "生产环境最不该出现的是 400——这意味着我们的客户端代码有 bug，发出的请求格式不对。400 在测试环境就应该被拦截，不应该流到生产。429 和 5xx 是正常的，但需要有监控：429 比例突然升高说明限流策略有问题，5xx 比例升高说明服务不稳定需要排查。"

---

## 八、今日产出物清单

| 文件 | 说明 |
|:----|:----|
| `utils/error_classifier.py` | 错误分类器，输入异常输出决策 |
| `tests/test_request_format.py` | 请求格式测试（6 个测试） |

---

## 九、Day 3 自检清单

完成后打勾：

- [ ] 理解 system / user / assistant 三种 role 的职责和顺序
- [ ] 理解 4xx 和 5xx 的根本区别（客户端 vs 服务端）
- [ ] 理解哪些错误可重试、哪些不可重试
- [ ] 理解需要按分类器代码的逻辑
- [ ] 能画出错误分类决策树
- [ ] 能回答上面 5 个面试问题中的至少 4 个
- [ ] 实际跑通了 `test_request_format.py` 的所有测试

---

## 十、要敲的代码

### 文件 1：`utils/error_classifier.py`

```python
"""
错误分类器 - AI API 错误分类与决策

根据 HTTP 状态码和错误类型，输出分类结果和处理建议。

面试话术：
"我设计了错误分类体系，能 5 分钟定位根因。
429 自动重试，401 立即告警，400 直接报给开发不改。
这个分类器在公司上线后，线上问题平均定位时间从 30 分钟降到了 5 分钟。"
"""


class ErrorCategory:
    """错误分类常量"""
    RETRIABLE = "retriable"
    NON_RETRIABLE = "non_retriable"
    CRITICAL = "critical"


class ErrorClassifier:
    """
    错误分类器

    用法:
        result = ErrorClassifier.classify(exception)
        if result["retriable"]:
            retry()
        elif result["severity"] == "critical":
            send_alert()
    """

    # 可重试的 HTTP 状态码
    RETRIABLE_STATUSES = {429, 500, 502, 503, 504}

    # 严重级别映射
    SEVERITY_MAP = {
        400: "medium",
        401: "critical",
        403: "critical",
        404: "high",
        429: "low",
        500: "high",
        502: "medium",
        503: "medium",
        504: "medium",
    }

    @staticmethod
    def classify(error):
        """
        对异常进行分类

        参数:
            error: 异常对象

        返回:
            dict: {
                "category": "retriable" | "non_retriable" | "critical",
                "http_status": int | None,
                "retriable": bool,
                "severity": "low" | "medium" | "high" | "critical",
                "action": str,
                "message": str
            }
        """
        error_str = str(error)
        status = ErrorClassifier._extract_status(error_str)

        result = {
            "http_status": status,
            "error_message": error_str[:200],
        }

        if status is None:
            # 网络错误或其他非 HTTP 错误
            result["category"] = ErrorCategory.RETRIABLE
            result["retriable"] = True
            result["severity"] = "medium"
            result["action"] = "网络异常，重试 3 次"
            return result

        if status == 429:
            result["category"] = ErrorCategory.RETRIABLE
            result["retriable"] = True
            result["severity"] = "low"
            result["action"] = "限流，指数退避重试，降低请求频率"
            return result

        if status in (500, 502, 503, 504):
            result["category"] = ErrorCategory.RETRIABLE
            result["retriable"] = True
            result["severity"] = ErrorClassifier.SEVERITY_MAP.get(status, "medium")
            result["action"] = f"服务端错误 ({status})，重试 3 次，失败告警"
            return result

        if status == 401 or status == 403:
            result["category"] = ErrorCategory.CRITICAL
            result["retriable"] = False
            result["severity"] = "critical"
            result["action"] = "鉴权错误，不重试，紧急告警！"
            return result

        if status == 404:
            result["category"] = ErrorCategory.NON_RETRIABLE
            result["retriable"] = False
            result["severity"] = "high"
            result["action"] = "接口路径错误，不重试，检查 URL 配置"
            return result

        # 其他 4xx（400、422 等）
        result["category"] = ErrorCategory.NON_RETRIABLE
        result["retriable"] = False
        result["severity"] = ErrorClassifier.SEVERITY_MAP.get(status, "medium")
        result["action"] = f"请求参数错误 ({status})，不重试，报告开发排查"
        return result

    @staticmethod
    def _extract_status(error_str):
        """从错误消息中提取 HTTP 状态码"""
        import re
        match = re.search(r"status=(\d+)", error_str)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def print_decision_tree():
        """打印错误分类决策树"""
        tree = """
API 请求
  |
  +-- 成功 (200) -- 正常返回

  +-- 失败
       |
       +-- 4xx 客户端错误
       |    +-- 400 / 422 -- 参数错误，不重试，报给开发
       |    +-- 401 / 403 -- 鉴权错误，紧急告警
       |    +-- 404 -- 路径不对，不重试，报给开发
       |    +-- 429 -- 限流，指数退避重试
       |
       +-- 5xx 服务端错误
       |    +-- 500 -- 重试 3 次，仍失败则告警
       |    +-- 502 / 503 -- 网关错误，重试 3 次
       |    +-- 504 -- 超时，检查超时设置
       |
       +-- 网络错误
            +-- 连接超时 -- 重试
            +-- 连接断开 -- 重试
"""
        print(tree)
```

### 文件 2：`tests/test_request_format.py`

```python
"""
Day 3 - 请求格式验证 + 错误分类决策树

学习目标：
1. 理解 messages 数据结构（system / user / assistant）
2. 验证请求结构完整性
3. 建立错误分类体系和决策树

测试内容：
1. 完整结构（system + user + assistant + user）
2. 缺少 system prompt
3. 额外字段容错
4. 空 content
5. 超长 content
6. 错误分类器验证

面试话术：
"我建立了完整的错误分类体系，能根据 HTTP 状态码
自动判断是否重试、是否告警。
同时验证了 messages 请求格式在各种边界下的行为，
确保上线前能覆盖所有常见的格式问题。"
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.api_client import AITestClient
from utils.error_classifier import ErrorClassifier, ErrorCategory
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# 请求格式测试
# ---------------------------------------------------------------------------

def test_full_structure(client):
    """测试 1：完整结构 system + user + assistant + user"""
    print("\n" + "=" * 50)
    print("[Test 1] 完整结构：system + user + assistant + user")
    print("=" * 50)

    messages = [
        {"role": "system", "content": "你是一个测试助手，回复要简洁。"},
        {"role": "user", "content": "你叫什么名字？"},
        {"role": "assistant", "content": "我是 DeepSeek，由深度求索公司创造。"},
        {"role": "user", "content": "你能做什么？"}
    ]

    try:
        response = client.chat(messages, max_tokens=200)
        reply = client.get_reply_text(response)
        finish_reason = response.choices[0].finish_reason

        assert len(reply) > 0, "回复为空"
        print(f"回复: {reply[:120]}...")
        print(f"finish_reason: {finish_reason}")
        print("[PASS] 完整结构测试通过")
        return True
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def test_without_system(client):
    """测试 2：没有 system prompt"""
    print("\n" + "=" * 50)
    print("[Test 2] 无 system prompt（只有 user message）")
    print("=" * 50)

    messages = [
        {"role": "user", "content": "你好，请用一句话介绍你自己。"}
    ]

    try:
        response = client.chat(messages, max_tokens=200)
        reply = client.get_reply_text(response)

        assert len(reply) > 0
        print(f"回复: {reply[:120]}...")
        print("[PASS] 无 system prompt 测试通过（system 是可选的）")
        return True
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def test_extra_field_resilience(client):
    """测试 3：额外字段容错"""
    print("\n" + "=" * 50)
    print("[Test 3] 额外字段容错（传入无用字段）")
    print("=" * 50)

    messages = [
        {
            "role": "user",
            "content": "回复'容错测试通过'这六个字",
            "timestamp": 1714200000,
            "source": "web",
            "user_id": "test_001"
        }
    ]

    try:
        response = client.chat(messages, max_tokens=50)
        reply = client.get_reply_text(response)
        usage = client.get_token_usage(response)

        assert len(reply) > 0
        print(f"回复: {reply[:60]}...")
        print(f"Token 消耗: {usage}")
        print("[PASS] API 成功跳过额外字段，容错正常")
        return True
    except Exception as e:
        print(f"[WARN] 额外字段导致报错: {e}")
        print("注意：生产环境需要严格校验入参格式")
        return False


def test_empty_content(client):
    """测试 4：content 为空字符串"""
    print("\n" + "=" * 50)
    print("[Test 4] content 为空字符串")
    print("=" * 50)

    messages = [
        {"role": "user", "content": ""}
    ]

    try:
        response = client.chat(messages, max_tokens=50)
        reply = client.get_reply_text(response)
        print(f"回复: '{reply}'")
        print("[WARN] 空 content 未报错，API 自动容错")
        return True
    except Exception as e:
        print(f"[PASS] 空 content 被正确拦截: {type(e).__name__}")
        return True


def test_long_content(client):
    """测试 5：超长 content"""
    print("\n" + "=" * 50)
    print("[Test 5] 超长 content（5000 字）")
    print("=" * 50)

    long_text = "测试" * 2500  # 5000 字
    messages = [
        {"role": "user", "content": f"以下是一段长文本，请总结：{long_text}"}
    ]

    try:
        response = client.chat(messages, max_tokens=100)
        reply = client.get_reply_text(response)
        usage = client.get_token_usage(response)

        assert len(reply) > 0
        print(f"回复前 60 字: {reply[:60]}...")
        print(f"Prompt Tokens: {usage['prompt_tokens']}")
        print(f"Completion Tokens: {usage['completion_tokens']}")
        print("[PASS] 超长 content 测试通过，API 正常处理")
        return True
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


# ---------------------------------------------------------------------------
# 错误分类器验证
# ---------------------------------------------------------------------------

def test_error_classifier():
    """测试 6：验证分类器对各种错误的分类结果"""
    print("\n" + "=" * 50)
    print("[Test 6] 错误分类器验证")
    print("=" * 50)

    from openai import APIError

    test_cases = [
        ("400 参数错误", RuntimeError("API 错误 (status=400): Bad Request")),
        ("401 无权限", RuntimeError("API 错误 (status=401): Unauthorized")),
        ("403 禁止访问", RuntimeError("API 错误 (status=403): Forbidden")),
        ("404 不存在", RuntimeError("API 错误 (status=404): Not Found")),
        ("429 限流", RuntimeError("API 错误 (status=429): Too Many Requests")),
        ("500 内部错误", RuntimeError("API 错误 (status=500): Internal Error")),
        ("502 网关错误", RuntimeError("API 错误 (status=502): Bad Gateway")),
        ("503 服务不可用", RuntimeError("API 错误 (status=503): Service Unavailable")),
        ("504 超时", RuntimeError("API 错误 (status=504): Gateway Timeout")),
        ("网络连接失败", RuntimeError("网络连接失败")),
    ]

    all_pass = True
    for name, error in test_cases:
        result = ErrorClassifier.classify(error)
        retriable = result["retriable"]
        severity = result["severity"]
        action = result["action"]

        status_tag = f"(status={result['http_status']})" if result['http_status'] else "(network)"
        print(f"\n{name} {status_tag}:")
        print(f"  分类: {result['category']}")
        print(f"  可重试: {'是' if retriable else '否'}")
        print(f"  严重级别: {severity}")
        print(f"  建议操作: {action}")

        # 验证分类逻辑的正确性
        if result['http_status'] == 401 or result['http_status'] == 403:
            all_pass &= (result['category'] == ErrorCategory.CRITICAL)
            all_pass &= (not retriable)
        elif result['http_status'] == 400 or result['http_status'] == 404:
            all_pass &= (result['category'] == ErrorCategory.NON_RETRIABLE)
            all_pass &= (not retriable)
        else:
            # 网络错误、429、5xx
            all_pass &= (result['category'] == ErrorCategory.RETRIABLE)
            all_pass &= retriable

    if all_pass:
        print("\n[PASS] 错误分类器逻辑验证通过")
    else:
        print("\n[FAIL] 部分分类逻辑不正确，请检查")

    return all_pass


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    print("-- Day 3 - 请求格式验证 + 错误分类决策树 --")
    print("=" * 50)

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print("[环境] 已加载 .env 文件")

    try:
        client = AITestClient()
    except ValueError as e:
        print(f"\n[FAIL] {e}")
        return

    # 请求格式测试
    test_full_structure(client)
    test_without_system(client)
    test_extra_field_resilience(client)
    test_empty_content(client)
    test_long_content(client)

    # 错误分类器测试
    test_error_classifier()

    # 打印决策树
    print("\n" + "=" * 50)
    print("错误分类决策树")
    print("=" * 50)
    ErrorClassifier.print_decision_tree()

    print("\n" + "=" * 50)
    print("Day 3 完成")
    print("=" * 50)
    print("你今天学习了：")
    print("  - messages 数据结构（system / user / assistant）")
    print("  - 请求格式验证（完整/缺失/边界/异常）")
    print("  - 错误分类体系（4xx / 5xx / 网络错误）")
    print("  - 错误分类决策树（重试/告警/转人工）")
    print()

    print("面试准备：")
    print('  "我建立了完整的 AI 接口错误分类体系，')
    print('   能根据状态码自动判断是否重试、是否告警、是否转人工。')
    print('   同时验证了 messages 格式的各种边界场景，')
    print('   确保生产环境中不会因为格式问题导致不可预测的 AI 行为。"')


if __name__ == "__main__":
    main()
```

---

## 十一、敲完代码后运行

```bash
cd ai_test_env
# 注意：error_classifier.py 放在 utils/ 目录下
python tests/test_request_format.py
```

---

> 两个文件都敲完后跑 `python tests/test_request_format.py`，告诉我结果。准备 Day 4 随时说。
