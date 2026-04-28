# Day 4：响应结构验证 + Token 基线 + 响应时间基线

> 对应 8 周计划第 1 周 Day 4
> 目标城市：上海 | 目标岗位：AI 测试工程师
> 学习时间：约 1.5 小时

---

## 一、今日学习目标

| 目标 | 说明 |
|:----|:------|
| 完全理解 API 响应结构 | choices / usage / finish_reason / created 每个字段 |
| 建立 Token 基线 | 确定不同场景的 Token 消耗基准 |
| 建立响应时间基线 | 记录首次请求延迟、平均响应时间 |
| 验证各字段边界行为 | 响应为空、finish_reason 异常等边界 |

**面试对应问题：**
- 面试官："API 返回了哪些字段？你关注哪些？"
- 面试官："你怎么做 AI 接口的性能测试？"
- 面试官："Token 怎么换算成钱的？"

---

## 二、API 响应结构逐字段讲解

### 2.1 顶层结构

```python
response.id            # 请求的唯一 ID，如 "chatcmpl-xxx"
response.object        # 固定值 "chat.completion"
response.created       # 时间戳（Unix 秒），API 处理完成的时间
response.model         # 实际使用的模型名
response.choices       # 回复列表（数组），通常只有 1 个元素
response.usage         # Token 使用统计
```

### 2.2 choices 数组

```python
choice = response.choices[0]
choice.index                  # 在数组中的索引，通常是 0
choice.finish_reason          # 停止原因
choice.message.role           # "assistant"
choice.message.content        # AI 回复的文本内容（重点！）
```

### 2.3 finish_reason 详解

| finish_reason | 含义 | 是否正常 | 调优方向 |
|:-------------|:-----|:--------|:--------|
| `stop` | AI 自行判断回答完毕 | ✅ 正常 | 无需处理 |
| `length` | 达到 max_tokens 上限被截断 | ⚠️ 截断 | 调大 max_tokens |
| `content_filter` | 命中内容过滤 | ❌ 敏感 | 检查 prompt |
| `null` | 流式模式未结束 | - | 流式专用 |

**面试话术：**
> "我每天监控 finish_reason 的分布。正常情况下 99% 以上是 stop。如果 length 比例超过 5%，说明 max_tokens 不够。content_filter 频率升高说明 prompt 有问题。"

### 2.4 usage 对象

```python
usage.prompt_tokens           # 输入 Token（含 system + user + 历史）
usage.completion_tokens       # 输出 Token
usage.total_tokens            # 总用量
```

**Token 换算：**
```
DeepSeek 定价：
  输入：0.14 元 / 百万 Token
  输出：0.28 元 / 百万 Token

一次普通对话 ≈ 200-500 输入 + 100-300 输出 Token
≈ 0.00003~0.0001 元/次
1 万次调用 ≈ 0.3~1 元
```

**面试话术：**
> "一次正常对话消耗 300-800 Token，成本约 0.0001 元。AI 测试中费用不是瓶颈，瓶颈在于设计高效的测试用例。"

---

## 三、今日代码清单

### 文件 1：`utils/response_validator.py`

独立模块，接收 API 响应对象，逐字段验证。

验证的 9 个字段：

| 字段 | 验证点 | 正常范围 |
|:-----|:------|:--------|
| `id` | 非空、含 "chatcmpl" | 非空字符串 |
| `object` | 等于 "chat.completion" | 固定值 |
| `created` | 是时间戳（Unix 秒） | 合理范围内 |
| `model` | 非空 | 非空字符串 |
| `choices` | 数组长度 >= 1 | 正常返回 1 |
| `finish_reason` | 在预期集合中 | stop / length / content_filter |
| `message.role` | 等于 "assistant" | 固定值 |
| `message.content` | 非空 | 非空字符串 |
| `usage` | prompt+completion=total | 等式成立 |

### 文件 2：`tests/test_response_baseline.py`

| 测试 | 说明 |
|:-----|:------|
| Test 1 | 完整字段验证（9 个字段逐一检查） |
| Test 2 | Token 一致性（4 种场景 P+C=T） |
| Test 3 | 响应时间基线（1/3/5 次请求） |
| Test 4 | finish_reason 短回复验证 |
| Test 5 | finish_reason 截断验证 |
| Test 6 | Token 基线统计（5 种场景对比） |

---

## 四、要敲的代码

### 4.1 文件：`utils/response_validator.py`

```python
"""
响应验证器 - AI API 响应结构验证

验证 API 返回的每个字段，生成验证报告。

面试话术：
"我写了响应验证器，每次调用后自动检查 choices、usage、finish_reason
等所有字段。测试报告中会标明每个字段的状态——字段缺失标 FAIL，
字段异常标 WARN，所有正常才标 PASS。这个验证器在我代码上线前
帮我捉到过 3 次字段变化的问题。"
"""
import time


class ResponseValidator:
    """
    API 响应验证器

    用法:
        report = ResponseValidator.validate(response)
        if report["all_pass"]:
            print("所有字段验证通过")
        else:
            for check in report["checks"]:
                print(f"  [{check['status']}] {check['field']}: {check['message']}")
    """

    EXPECTED_OBJECT = "chat.completion"
    EXPECTED_ROLE = "assistant"
    VALID_FINISH_REASONS = {"stop", "length", "content_filter", None}

    @staticmethod
    def validate(response):
        """
        全面验证 API 响应

        参数:
            response: API 响应对象

        返回:
            dict: {
                "all_pass": bool,
                "checks": [{"field", "status", "message"}, ...],
                "summary": {"total", "passed", "failed", "warned"}
            }
        """
        checks = []

        checks.append(ResponseValidator._check_id(response))
        checks.append(ResponseValidator._check_object(response))
        checks.append(ResponseValidator._check_created(response))
        checks.append(ResponseValidator._check_model(response))
        checks.append(ResponseValidator._check_choices(response))
        checks.append(ResponseValidator._check_finish_reason(response))
        checks.append(ResponseValidator._check_role(response))
        checks.append(ResponseValidator._check_content(response))
        checks.append(ResponseValidator._check_usage(response))

        passed = sum(1 for c in checks if c["status"] == "PASS")
        failed = sum(1 for c in checks if c["status"] == "FAIL")
        warned = sum(1 for c in checks if c["status"] == "WARN")

        return {
            "all_pass": failed == 0,
            "checks": checks,
            "summary": {"total": len(checks), "passed": passed, "failed": failed, "warned": warned},
        }

    @staticmethod
    def _check_id(response):
        if not response.id:
            return {"field": "id", "status": "FAIL", "message": "id 为空"}
        if "chatcmpl" not in response.id.lower():
            return {"field": "id", "status": "WARN", "message": f"id 格式异常: {response.id}"}
        return {"field": "id", "status": "PASS", "message": response.id[:40]}

    @staticmethod
    def _check_object(response):
        if response.object != ResponseValidator.EXPECTED_OBJECT:
            return {"field": "object", "status": "FAIL",
                    "message": f"预期='{ResponseValidator.EXPECTED_OBJECT}', 实际='{response.object}'"}
        return {"field": "object", "status": "PASS", "message": response.object}

    @staticmethod
    def _check_created(response):
        now = int(time.time())
        if not response.created:
            return {"field": "created", "status": "FAIL", "message": "created 为空"}
        if abs(response.created - now) > 300:
            return {"field": "created", "status": "WARN",
                    "message": f"时间戳偏差: response={response.created}, now={now}"}
        return {"field": "created", "status": "PASS", "message": f"时间戳 {response.created}"}

    @staticmethod
    def _check_model(response):
        if not response.model:
            return {"field": "model", "status": "FAIL", "message": "model 为空"}
        return {"field": "model", "status": "PASS", "message": response.model}

    @staticmethod
    def _check_choices(response):
        if not response.choices:
            return {"field": "choices", "status": "FAIL", "message": "choices 为空"}
        if len(response.choices) < 1:
            return {"field": "choices", "status": "FAIL", "message": f"choices 长度为 {len(response.choices)}"}
        if len(response.choices) > 1:
            return {"field": "choices", "status": "WARN", "message": f"choices > 1: {len(response.choices)} 个"}
        return {"field": "choices", "status": "PASS", "message": f"{len(response.choices)} 个"}

    @staticmethod
    def _check_finish_reason(response):
        if not response.choices:
            return {"field": "finish_reason", "status": "FAIL", "message": "choices 为空"}
        reason = response.choices[0].finish_reason
        if reason not in ResponseValidator.VALID_FINISH_REASONS:
            return {"field": "finish_reason", "status": "WARN", "message": f"未知: {reason}"}
        return {"field": "finish_reason", "status": "PASS", "message": reason}

    @staticmethod
    def _check_role(response):
        if not response.choices:
            return {"field": "message.role", "status": "FAIL", "message": "choices 为空"}
        role = response.choices[0].message.role
        if role != ResponseValidator.EXPECTED_ROLE:
            return {"field": "message.role", "status": "FAIL",
                    "message": f"预期='{ResponseValidator.EXPECTED_ROLE}', 实际='{role}'"}
        return {"field": "message.role", "status": "PASS", "message": role}

    @staticmethod
    def _check_content(response):
        if not response.choices:
            return {"field": "message.content", "status": "FAIL", "message": "choices 为空"}
        content = response.choices[0].message.content
        if content is None:
            return {"field": "message.content", "status": "FAIL", "message": "content 为 None"}
        if content == "":
            return {"field": "message.content", "status": "WARN", "message": "content 为空"}
        return {"field": "message.content", "status": "PASS", "message": f"长度 {len(content)} 字符"}

    @staticmethod
    def _check_usage(response):
        if not response.usage:
            return {"field": "usage", "status": "FAIL", "message": "usage 为空"}
        usage = response.usage
        prompt = getattr(usage, "prompt_tokens", None)
        completion = getattr(usage, "completion_tokens", None)
        total = getattr(usage, "total_tokens", None)
        if prompt is None or completion is None or total is None:
            return {"field": "usage", "status": "FAIL", "message": "缺少子字段"}
        if prompt < 0 or completion < 0 or total < 0:
            return {"field": "usage", "status": "FAIL", "message": "Token 为负数"}
        if prompt + completion != total:
            return {"field": "usage", "status": "FAIL",
                    "message": f"P({prompt}) + C({completion}) != T({total})"}
        return {"field": "usage", "status": "PASS", "message": f"P={prompt} C={completion} T={total}"}

    @staticmethod
    def print_report(report):
        """打印验证报告"""
        print(f"\n{'=' * 50}")
        print(f"API 响应验证报告")
        print(f"{'=' * 50}")
        icons = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}
        for check in report["checks"]:
            icon = icons.get(check["status"], "  ")
            print(f"  {icon} [{check['status']}] {check['field']}: {check['message']}")
        s = report["summary"]
        print(f"\n  汇总: {s['passed']}/{s['total']} 通过, {s['failed']} 失败, {s['warned']} 警告")
        print(f"  {'✅ 全部通过' if report['all_pass'] else '❌ 需要修复'}")
```

### 4.2 文件：`tests/test_response_baseline.py`

```python
"""
Day 4 - 响应结构验证 + Token 基线 + 响应时间基线

学习目标：
1. 完全理解 API 响应每个字段的含义
2. 建立 Token 消耗基线
3. 记录首次请求时间和平均响应时间
4. 验证 finish_reason 的 stop / length 行为

测试内容：
1. 完整结构验证（9 个字段逐一检查）
2. Token 一致性验证（4 种场景）
3. 响应时间记录（首次 + 平均）
4. finish_reason 短回复验证
5. finish_reason 截断验证
6. 多次请求 Token 基线统计

面试话术：
"我建立了完整的 API 响应验证体系和 Token 基线表。
每个字段都有自动化验证，每次上线前跑一遍确保字段没有变化。
同时记录了 Token 消耗和响应时间的基线数据，
为性能测试和成本估算提供了依据。"
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.api_client import AITestClient
from utils.response_validator import ResponseValidator
from dotenv import load_dotenv


def test_full_structure_validation(client):
    """测试 1：响应结构完整验证（9 个字段）"""
    print("\n" + "=" * 60)
    print("[Test 1] 响应结构完整验证（9 个字段）")
    print("=" * 60)
    messages = [{"role": "user", "content": "你好，请简单介绍一下你自己。"}]
    try:
        response = client.chat(messages, max_tokens=200)
        report = ResponseValidator.validate(response)
        ResponseValidator.print_report(report)
        return report
    except Exception as e:
        print(f"[FAIL] API 调用失败: {e}")
        return None


def test_token_consistency(client):
    """测试 2：验证 prompt_tokens + completion_tokens = total_tokens"""
    print("\n" + "=" * 60)
    print("[Test 2] Token 使用一致性验证")
    print("=" * 60)
    cases = [
        ("简短问答", [{"role": "user", "content": "你好"}]),
        ("中等长度", [{"role": "user", "content": "请用 200 字介绍 Python 语言。"}]),
        ("带 system", [
            {"role": "system", "content": "你是一个 Python 专家，回复要简洁专业。"},
            {"role": "user", "content": "tuple 和 list 的区别是什么？"}
        ]),
        ("短回复", [{"role": "user", "content": "是"}]),
    ]
    all_pass = True
    for name, messages in cases:
        try:
            response = client.chat(messages, max_tokens=200)
            usage = client.get_token_usage(response)
            p, c, t = usage["prompt_tokens"], usage["completion_tokens"], usage["total_tokens"]
            eq = (p + c == t)
            flag = "✅" if eq else "❌"
            print(f"  {flag} {name}: P={p} + C={c} = T={t} {'(一致)' if eq else '(不一致!)'}")
            if not eq:
                all_pass = False
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            all_pass = False
    print(f"\n{'[PASS]' if all_pass else '[FAIL]'} Token 一致性验证")
    return all_pass


def test_response_time(client):
    """测试 3：响应时间基线记录"""
    print("\n" + "=" * 60)
    print("[Test 3] 响应时间基线记录")
    print("=" * 60)
    messages = [{"role": "user", "content": "用一句话说明什么是 API。"}]
    for count in [1, 3, 5]:
        times = []
        for i in range(count):
            start = time.time()
            try:
                response = client.chat(messages, max_tokens=100)
                elapsed = time.time() - start
                times.append(elapsed)
                print(f"  第 {i+1} 次: {elapsed:.2f}s")
            except Exception as e:
                print(f"  第 {i+1} 次: 失败 - {e}")
        if times:
            avg = sum(times) / len(times)
            print(f"  最短: {min(times):.2f}s  最长: {max(times):.2f}s  平均: {avg:.2f}s")
            tag = "首次（含冷启动）" if count == 1 else f"{count} 次平均"
            print(f"  → {tag}: {avg:.2f}s")
    print("\n>> 首次请求通常比后续慢（冷启动），稳定后波动 >50% 说明网络不稳")


def test_finish_reason_short(client):
    """测试 4：短回复时 finish_reason 应为 stop"""
    print("\n" + "=" * 60)
    print("[Test 4] finish_reason 验证 - 短回复")
    print("=" * 60)
    cases = [
        ("是/否回答", [{"role": "user", "content": "1+1=2 对吗？只回答'对'或'错'"}], 50),
        ("单字回复", [{"role": "user", "content": "请只回复一个数字：7"}], 50),
        ("简短介绍", [{"role": "user", "content": "你叫什么？"}], 100),
    ]
    for name, messages, mt in cases:
        try:
            response = client.chat(messages, max_tokens=mt)
            reason = response.choices[0].finish_reason
            content = client.get_reply_text(response)
            flag = "✅" if reason == "stop" else "⚠️"
            print(f"  {flag} {name}: finish={reason}, 长度={len(content)}")
        except Exception as e:
            print(f"  ❌ {name}: {e}")


def test_finish_reason_truncation(client):
    """测试 5：max_tokens 不够时 finish_reason=length"""
    print("\n" + "=" * 60)
    print("[Test 5] finish_reason 验证 - 截断")
    print("=" * 60)
    messages = [{"role": "user", "content": "请写一篇 500 字的文章，介绍人工智能的发展历史。"}]
    for mt in [5, 20, 50]:
        try:
            response = client.chat(messages, max_tokens=mt)
            reason = response.choices[0].finish_reason
            content = client.get_reply_text(response)
            flag = "✅" if reason == "length" else "⚠️"
            print(f"  {flag} max_tokens={mt}: finish={reason}, 回复前20={content[:20]}...")
        except Exception as e:
            print(f"  ❌ max_tokens={mt}: {e}")
    try:
        response = client.chat(messages, max_tokens=500)
        reason = response.choices[0].finish_reason
        print(f"  ✅ max_tokens=500: finish={reason}（足够时正常结束）")
    except Exception as e:
        print(f"  ❌ max_tokens=500: {e}")


def test_token_baseline(client):
    """测试 6：Token 消耗基线统计"""
    print("\n" + "=" * 60)
    print("[Test 6] Token 消耗基线统计（5 种场景）")
    print("=" * 60)
    scenarios = [
        ("简短问答", [{"role": "user", "content": "你好"}]),
        ("普通回答", [{"role": "user", "content": "请介绍 Python 语言，100 字左右。"}]),
        ("带 system", [
            {"role": "system", "content": "你是一个技术专家，回复要简洁专业。"},
            {"role": "user", "content": "什么是 RESTful API？"}
        ]),
        ("多轮对话", [
            {"role": "user", "content": "你叫什么？"},
            {"role": "assistant", "content": "我叫 DeepSeek。"},
            {"role": "user", "content": "你能做什么？"}
        ]),
        ("长输入", [{"role": "user", "content": "请总结以下文本：AI 测试 " * 20}]),
    ]
    records = []
    for name, messages in scenarios:
        try:
            response = client.chat(messages, max_tokens=300)
            usage = client.get_token_usage(response)
            record = {
                "scenario": name,
                "prompt_tokens": usage["prompt_tokens"],
                "completion_tokens": usage["completion_tokens"],
                "total_tokens": usage["total_tokens"],
                "finish_reason": response.choices[0].finish_reason,
            }
            records.append(record)
            print(f"  {name}: P={record['prompt_tokens']:>5} + C={record['completion_tokens']:>4} = T={record['total_tokens']:>5}")
        except Exception as e:
            print(f"  ❌ {name}: {e}")
    if records:
        avg_p = sum(r["prompt_tokens"] for r in records) / len(records)
        avg_c = sum(r["completion_tokens"] for r in records) / len(records)
        print(f"\n  --- Token 基线 ---")
        print(f"  场景数: {len(records)}")
        print(f"  平均 Prompt Tokens:     {avg_p:>8.1f}")
        print(f"  平均 Completion Tokens: {avg_c:>8.1f}")
        print(f"  平均 Total Tokens:      {avg_p + avg_c:>8.1f}")
        cost = (avg_p * 0.14 + avg_c * 0.28) / 1_000_000 * len(records)
        print(f"  本次费用: 约 {cost:.6f} 元")
        print(f"  （输入 0.14 元/百万, 输出 0.28 元/百万）")


def main():
    print("-- Day 4 - 响应结构验证 + Token 基线 + 响应时间基线 --")
    print("=" * 60)
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print("[环境] 已加载 .env 文件")
    try:
        client = AITestClient()
    except ValueError as e:
        print(f"\n[FAIL] {e}")
        return

    test_full_structure_validation(client)
    test_token_consistency(client)
    test_response_time(client)
    test_finish_reason_short(client)
    test_finish_reason_truncation(client)
    test_token_baseline(client)

    print("\n" + "=" * 60)
    print("Day 4 完成")
    print("=" * 60)
    print("今天学习了：")
    print("  - API 响应结构（id/object/created/model/choices/usage）")
    print("  - finish_reason 的 stop/length 区别")
    print("  - Token 一致性验证（prompt+completion=total）")
    print("  - 响应时间基线（首次 vs 后续）")
    print("  - Token 基线（5 种场景消耗对比）")
    print("  - 响应验证器（9 字段逐一检查）")

if __name__ == "__main__":
    main()
```

---

## 五、敲完运行

```bash
cd ai_test_env
python tests/test_response_baseline.py
```

运行后你会看到：
1. ✅ 9 个字段逐一通过
2. ✅ 4 种场景 Token 一致性
3. 首次请求时间（冷启动）
4. 短回复 finish_reason=stop
5. 截断场景 finish_reason=length
6. 5 种场景的 Token 基线汇总

---

## 六、面试问题

### Q1：API 返回了哪些字段？你关注哪些？

> "我最关注 finish_reason、content 和 usage。finish_reason 判断是否截断，content 是业务数据，usage 算成本。我写了响应验证器自动检查 9 个字段。"

### Q2：你怎么做 AI 接口的性能测试？

> "首次请求通常比后续慢 2-3 倍（冷启动），我区分首次和热请求记录基线。用 5 次请求的平均耗时作为基线值，波动超过 50% 说明网络或服务不稳定。"

### Q3：Token 怎么换算成钱的？

> "DeepSeek 输入 0.14 元/百万 Token，输出 0.28 元/百万 Token。一次普通问答消耗 300-800 Token，成本约 0.0001 元。AI 测试真正的瓶颈不是费用，是测试用例设计。"

### Q4：finish_reason 有哪些值？

> "stop 表示完整回答，length 表示被 max_tokens 截断，content_filter 表示命中内容过滤。我每天监控分布，length 比例超过 5% 就告警调整 max_tokens。"

### Q5：你的测试跑完后产出了什么数据？

> "一份 Token 基线表（5 种场景的 P/C/T 数据）、一份响应时间基线（首次和平均耗时）、一份 9 字段验证报告。这些数据是后续测试的参考基准——任何版本升级后，先跑基线对比，字段变了或 Token 消耗变了都立刻发现。"
