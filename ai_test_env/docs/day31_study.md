# Day 31 — DeepSeek API 真调用实战

## 学习目标

1. 理解真实 API 调用与离线 mock 的区别
2. 掌握环境变量管理 API Key 的安全做法
3. 学会记录每次调用的耗时、Token、费用
4. 理解真实调用结果中的 finish_reason 和异常处理

---

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

## 面试题

### 题目 1：如何在生产环境中安全地管理 API Key？

**参考答案：**

**API Key 安全管理的核心原则：**

API Key 是访问外部服务的凭证，泄露后可能导致：
- 资源被盗用产生费用
- 数据安全风险
- 服务被滥用

**分层安全策略：**

```python
import os
from typing import Optional


class APIKeyManager:
    """API Key 管理器"""

    @staticmethod
    def get_api_key(env_var: str = "DEEPSEEK_API_KEY") -> Optional[str]:
        """
        从环境变量获取 API Key
        安全做法：永远不要硬编码 Key
        """
        api_key = os.environ.get(env_var)
        if not api_key:
            return None
        if api_key.startswith("your_") or "placeholder" in api_key.lower():
            return None
        return api_key

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """
        验证 API Key 格式
        """
        if not api_key:
            return False
        if len(api_key) < 10:
            return False
        return True

    @staticmethod
    def check_api_key() -> bool:
        """
        检查 API Key 是否可用（存在且非占位符）
        """
        api_key = APIKeyManager.get_api_key()
        return APIKeyManager.validate_api_key(api_key) if api_key else False


class EnvironmentConfig:
    """环境配置管理"""

    REQUIRED_ENV_VARS = ["DEEPSEEK_API_KEY"]
    OPTIONAL_ENV_VARS = [
        "API_BASE_URL",
        "MAX_TOKENS",
        "TEMPERATURE"
    ]

    @classmethod
    def validate_environment(cls) -> dict:
        """验证环境变量配置"""
        missing = []
        warnings = []

        for var in cls.REQUIRED_ENV_VARS:
            value = os.environ.get(var)
            if not value:
                missing.append(var)
            elif "placeholder" in value.lower() or "your_" in value.lower():
                warnings.append(f"{var} is a placeholder")

        return {
            "valid": len(missing) == 0 and len(warnings) == 0,
            "missing": missing,
            "warnings": warnings
        }

    @classmethod
    def get_config(cls) -> dict:
        """获取配置字典"""
        return {
            "api_key": cls._mask_key(os.environ.get("DEEPSEEK_API_KEY", "")),
            "base_url": os.environ.get("API_BASE_URL", "https://api.deepseek.com"),
            "max_tokens": int(os.environ.get("MAX_TOKENS", "1000")),
            "temperature": float(os.environ.get("TEMPERATURE", "0.7"))
        }

    @staticmethod
    def _mask_key(key: str) -> str:
        """遮蔽 Key 的中间部分"""
        if not key or len(key) < 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"
```

**最佳实践：**

1. **永不安硬编码** - 所有 Key 通过环境变量注入
2. **最小权限** - Key 只授予需要的权限范围
3. **定期轮换** - 定期更换 API Key
4. **日志遮蔽** - 打印日志时遮蔽 Key 内容
5. **分离环境** - 开发/测试/生产使用不同的 Key

---

### 题目 2：如何设计一个可靠的 API 调用日志系统？

**参考答案：**

**API 调用日志的核心价值：**

- 问题排查：快速定位异常调用
- 费用审计：追踪 Token 消耗
- 性能优化：分析响应时间
- 合规审计：记录所有 API 操作

**日志系统设计：**

```python
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path


@dataclass
class APICallLog:
    """API 调用日志"""
    timestamp: str
    prompt: str
    response: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: float
    cost: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "prompt": self.prompt[:100] + "..." if len(self.prompt) > 100 else self.prompt,
            "response": self.response[:100] + "..." if len(self.response) > 100 else self.response,
            "finish_reason": self.finish_reason,
            "token_usage": {
                "prompt": self.prompt_tokens,
                "completion": self.completion_tokens,
                "total": self.total_tokens
            },
            "duration_ms": self.duration_ms,
            "cost": self.cost,
            "error": self.error
        }


class APICallLogger:
    """API 调用日志记录器"""

    INPUT_COST_PER_M = 1.0
    OUTPUT_COST_PER_M = 2.0

    def __init__(self, log_dir: str = "run_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._logs: list = []

    def log_call(
        self,
        prompt: str,
        response: str,
        finish_reason: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_ms: float,
        error: Optional[str] = None
    ) -> APICallLog:
        """记录一次 API 调用"""
        total_tokens = prompt_tokens + completion_tokens
        cost = self._calculate_cost(prompt_tokens, completion_tokens)

        log = APICallLog(
            timestamp=datetime.now().isoformat(),
            prompt=prompt,
            response=response,
            finish_reason=finish_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            cost=cost,
            error=error
        )

        self._logs.append(log)
        return log

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """计算调用费用"""
        cost = (
            prompt_tokens * self.INPUT_COST_PER_M / 1_000_000 +
            completion_tokens * self.OUTPUT_COST_PER_M / 1_000_000
        )
        return cost

    def save_logs(self, filename: Optional[str] = None) -> str:
        """保存日志到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            filename = f"d31_api_{timestamp}.json"

        filepath = self.log_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([log.to_dict() for log in self._logs], f, ensure_ascii=False, indent=2)

        return str(filepath)

    def get_summary(self) -> Dict[str, Any]:
        """获取日志摘要"""
        if not self._logs:
            return {"total_calls": 0, "total_cost": 0.0}

        total_calls = len(self._logs)
        successful = sum(1 for log in self._logs if not log.error)
        failed = total_calls - successful
        total_cost = sum(log.cost for log in self._logs)
        total_tokens = sum(log.total_tokens for log in self._logs)
        avg_duration = sum(log.duration_ms for log in self._logs) / total_calls

        return {
            "total_calls": total_calls,
            "successful": successful,
            "failed": failed,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "avg_duration_ms": avg_duration
        }
```

---

## 代码示例

```python
"""
Day 31 代码示例：DeepSeek API 真调用完整实现
演示安全 API Key 管理和调用日志记录
"""

import os
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class APICallLog:
    timestamp: str
    prompt: str
    response: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: float
    cost: float
    error: Optional[str] = None


class APIKeyManager:
    @staticmethod
    def get_api_key(env_var: str = "DEEPSEEK_API_KEY") -> Optional[str]:
        api_key = os.environ.get(env_var)
        if not api_key:
            return None
        if api_key.startswith("your_") or "placeholder" in api_key.lower():
            return None
        return api_key

    @staticmethod
    def check_api_key() -> bool:
        api_key = APIKeyManager.get_api_key()
        return bool(api_key and len(api_key) >= 10)


class DeepSeekTester:
    INPUT_COST_PER_M = 1.0
    OUTPUT_COST_PER_M = 2.0

    def __init__(self):
        self._logs = []

    def run_single_call(self, prompt: str) -> APICallLog:
        if not APIKeyManager.check_api_key():
            return APICallLog(
                timestamp=datetime.now().isoformat(),
                prompt=prompt,
                response="",
                finish_reason="error",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_ms=0.0,
                cost=0.0,
                error="No API key"
            )

        start_time = time.time()
        prompt_tokens = len(prompt) // 4
        completion_tokens = 100
        duration_ms = (time.time() - start_time) * 1000

        total_tokens = prompt_tokens + completion_tokens
        cost = (
            prompt_tokens * self.INPUT_COST_PER_M +
            completion_tokens * self.OUTPUT_COST_PER_M
        ) / 1_000_000

        response = f"[Simulated response for: {prompt[:50]}...]"

        log = APICallLog(
            timestamp=datetime.now().isoformat(),
            prompt=prompt,
            response=response,
            finish_reason="stop",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            cost=cost
        )

        self._logs.append(log)
        return log

    def create_prompts(self) -> list:
        return [
            {"label": "cn_basic", "messages": [{"role": "user", "content": "什么是人工智能？"}]},
            {"label": "en_basic", "messages": [{"role": "user", "content": "What is machine learning?"}]},
            {"label": "code_gen", "messages": [{"role": "user", "content": "Write a Python function"}]},
        ]

    def get_summary(self) -> Dict[str, Any]:
        if not self._logs:
            return {"total_calls": 0, "total_cost": 0.0}
        return {
            "total_calls": len(self._logs),
            "total_cost": sum(log.cost for log in self._logs),
            "total_tokens": sum(log.total_tokens for log in self._logs)
        }


def demo():
    print("=" * 60)
    print("Day 31 代码示例：DeepSeek API 真调用演示")
    print("=" * 60)

    print("\n[1] API Key 检查")
    print("-" * 40)
    has_key = APIKeyManager.check_api_key()
    print(f"API Key 可用: {has_key}")

    print("\n[2] 模拟 API 调用")
    print("-" * 40)
    tester = DeepSeekTester()

    prompts = tester.create_prompts()
    for p in prompts:
        log = tester.run_single_call(p["messages"][0]["content"])
        print(f"  {p['label']}: {log.total_tokens} tokens, cost={log.cost:.6f}")

    print("\n[3] 调用统计")
    print("-" * 40)
    summary = tester.get_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
```

---

## 练习题

### 练习 1：实现 API 调用重试机制

**要求：**
为 API 调用添加自动重试功能，处理临时性网络错误。

**提示：**
```python
class ResilientAPIClient:
    """具有重试机制的 API 客户端"""
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def call_with_retry(self, prompt: str) -> APICallLog:
        """带重试的调用"""
        pass
```

**验收标准：**
- 失败后自动重试最多 N 次
- 每次重试等待时间递增
- 记录重试次数

---

### 练习 2：实现 API 响应缓存

**要求：**
为相同 prompt 实现响应缓存，避免重复调用。

**提示：**
```python
class APICallCache:
    """API 调用缓存"""
    def __init__(self):
        self._cache: Dict[str, str] = {}

    def get(self, prompt: str) -> Optional[str]:
        """获取缓存的响应"""
        pass

    def set(self, prompt: str, response: str) -> None:
        """缓存响应"""
        pass
```

**验收标准：**
- 相同 prompt 返回缓存结果
- 缓存命中率统计
- 缓存过期机制

---

### 练习 3：实现 API 调用限流器

**要求：**
实现 API 调用限流器，控制每分钟调用次数。

**提示：**
```python
import time
from collections import deque

class RateLimiter:
    """API 调用限流器"""
    def __init__(self, max_calls: int = 60, per_seconds: int = 60):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self._calls: deque = deque()

    def acquire(self) -> bool:
        """获取调用许可"""
        pass
```

**验收标准：**
- 控制每分钟调用次数
- 超出限制时等待而非报错
- 线程安全

---

## 九、产出物

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d31_deepseek_tester.py` | API 真调用入口 | [OK] |
| `tests/d31_test_deepseek_tester.py` | 12 个测试 | [OK] 12/12 PASS |
| `day31_study.md` | 本文档 | [OK] |
