# Day 28 — 冒烟测试：边界值 + 错误处理 + 消息格式

## 学习目标

1. 掌握边界值分析（BVA）方法，学会设计关键参数的边界测试用例
2. 理解 HTTP 状态码分类，学会区分 4xx 和 5xx 错误的处理策略
3. 掌握消息格式验证方法，学会覆盖有效/无效角色、空内容等场景
4. 理解冒烟测试的价值，学会设计快速反馈的测试套件

## 一、引言

冒烟测试是项目的第一道关口——不跑过冒烟，不进其它测试。为 `ai_test_engine` 建立 62 个冒烟测试用例，覆盖 API 参数的边界条件、4xx/5xx/网络错误、消息格式校验。

## 二、前置知识讲解

### 2.1 什么是边界值分析（BVA）？

**一句话定义：** 测试时重点验证取值范围的最小值、最大值、比最小少 1、比最大多 1 等边界。

**类比：** 限高 1.2 米的游乐设施——1.19 米能玩，1.20 米也能玩，1.21 米不行。边界最危险。

**代码：**
```python
# 测试 max_tokens 边界
max_tokens: 0, 1, 4096, -1
# 测试 temperature 边界
temperature: 0.0, 0.5, 1.0, 2.0, -0.5
```

**面试话术：** "80% 的 bug 发生在边界。temperature 传 -0.5 应该报错，传 0 应该稳定输出。如果 API 不校验边界，测试得替它兜底。"

### 2.2 HTTP 状态码分类

**一句话定义：** HTTP 响应码按首位数字分类：2xx 成功、4xx 客户端错误、5xx 服务端错误。

**面试话术：** "4xx 说明你的请求有问题（401 没权限、429 太频繁），5xx 说明服务端有问题（500 挂了、502 网关超时）。错误分级就是按这个分——4xx 的 429 轻量级 WARN，5xx 的 500 标记为 ERROR 需要告警。"

### 2.3 消息格式验证为什么重要？

**一句话定义：** AI API 对消息格式（role/content 结构）很敏感，格式错直接返回 400。

**面试话术：** "我见过最搞笑的 bug——测试脚本把 'user' 拼成 'uaser'，API 返回 400，排查了 20 分钟才发现。消息格式测试必须在冒烟阶段就覆盖。"

## 三、需求分析

三个冒烟测试文件：
1. `test_boundary.py` — max_tokens/temperature/top_p 边界 + 消息格式
2. `test_errors.py` — 4xx/5xx/网络/配置/校验五类
3. `test_connectivity.py` — 核心模块可用性

## 四、代码说明

### test_boundary.py
- TestMaxTokensBoundary: 0/1/4096/-1
- TestTemperatureBoundary: 0/0.5/1.0/2.0/-0.5
- TestTopPBoundary: 0/0.5/1.0/-0.1
- TestMessageFormat: 有效/无效角色、空内容、超长内容、多轮结构

### test_errors.py
- Test4xxErrors: 400/401/403/429
- Test5xxErrors: 500/502/503
- TestNetworkErrors: timeout/connection_refused/reset
- TestConfigErrors: 缺少 Key/无效 Base URL/错误模型名
- TestValidationErrors: 类型/范围/必填字段

### test_connectivity.py
- TestSettings: 默认值/校验/序列化
- TestAIEngineClient: 初始化/提取方法
- TestErrorHandler: 分类/可重试/致命判断
- TestKeyManager: 轮换/降级/失败计数

## 五、运行结果

```
62 passed (connectivity: 26 + boundary: 20 + errors: 16)
```

## 六、工作场景

- 新 API 版本升级——跑冒烟测试确认参数格式没变
- 接入新模型——冒烟确认参数范围兼容
- 每次提交——冒烟在 CI 中作为 gate 门控

## 七、面试问题

**Q: 冒烟测试的标准是什么？应该测试多少用例？**
A: 冒烟的核心是"快速反馈"。我的标准是：如果冒烟不过，其它测试不用跑。62 个用例覆盖了最关键的参数和错误路径，跑 0.07 秒。

**Q: 如何处理 API Key 对冒烟测试的限制？**
A: 所有冒烟测试都是无 API 调用、纯逻辑测试。连通性测试不调真实 API，只验证参数构造是否正确。这是刻意设计的——让测试可以离线跑。

**Q: 为什么边界值分析在 AI API 测试中特别重要？**
A: AI API 对参数非常敏感，比如 temperature 超过 2.0 或小于 0 会导致不可预测的行为，max_tokens 设为负数会直接报错。80% 的参数相关 bug 都发生在边界，所以必须重点覆盖。

**Q: 如何设计消息格式测试用例？**
A: 我会覆盖以下场景：有效角色（user/system/assistant）、无效角色（uaser、admin）、空内容、超长内容、多轮对话结构、混合格式（文本+工具调用）。特别要注意角色拼写错误，这是最容易被忽略的 bug。

## 八、代码示例

### 边界值测试用例实现

```python
import pytest

class TestMaxTokensBoundary:
    """测试 max_tokens 参数边界"""
    
    def test_max_tokens_zero(self):
        """测试 max_tokens=0 的边界情况"""
        from ai_test_engine.core.client import AIEngineClient
        
        client = AIEngineClient()
        # max_tokens=0 应该被拒绝或返回空响应
        with pytest.raises(ValueError):
            client._validate_params({"max_tokens": 0})
    
    def test_max_tokens_min(self):
        """测试 max_tokens=1 的最小有效值"""
        from ai_test_engine.core.client import AIEngineClient
        
        client = AIEngineClient()
        params = client._validate_params({"max_tokens": 1})
        assert params["max_tokens"] == 1
    
    def test_max_tokens_max(self):
        """测试 max_tokens=4096 的最大有效值"""
        from ai_test_engine.core.client import AIEngineClient
        
        client = AIEngineClient()
        params = client._validate_params({"max_tokens": 4096})
        assert params["max_tokens"] == 4096
    
    def test_max_tokens_negative(self):
        """测试 max_tokens=-1 的无效值"""
        from ai_test_engine.core.client import AIEngineClient
        
        client = AIEngineClient()
        with pytest.raises(ValueError):
            client._validate_params({"max_tokens": -1})

class TestTemperatureBoundary:
    """测试 temperature 参数边界"""
    
    def test_temperature_boundaries(self):
        """测试 temperature 的各种边界值"""
        from ai_test_engine.core.client import AIEngineClient
        
        client = AIEngineClient()
        
        # 有效值应该通过
        assert client._validate_params({"temperature": 0.0})["temperature"] == 0.0
        assert client._validate_params({"temperature": 0.5})["temperature"] == 0.5
        assert client._validate_params({"temperature": 1.0})["temperature"] == 1.0
        assert client._validate_params({"temperature": 2.0})["temperature"] == 2.0
        
        # 无效值应该被拒绝
        with pytest.raises(ValueError):
            client._validate_params({"temperature": -0.5})

class TestMessageFormat:
    """测试消息格式验证"""
    
    def test_valid_roles(self):
        """测试有效角色"""
        from ai_test_engine.core.client import AIEngineClient
        
        client = AIEngineClient()
        valid_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        assert client._validate_messages(valid_messages) is None
    
    def test_invalid_role(self):
        """测试无效角色"""
        from ai_test_engine.core.client import AIEngineClient
        
        client = AIEngineClient()
        invalid_messages = [
            {"role": "uaser", "content": "Hello"}  # 拼写错误
        ]
        with pytest.raises(ValueError):
            client._validate_messages(invalid_messages)
    
    def test_empty_content(self):
        """测试空内容"""
        from ai_test_engine.core.client import AIEngineClient
        
        client = AIEngineClient()
        empty_messages = [
            {"role": "user", "content": ""}
        ]
        with pytest.raises(ValueError):
            client._validate_messages(empty_messages)
```

## 九、产出物

- `tests/smoke/test_boundary.py` — 20 个边界 + 格式测试
- `tests/smoke/test_errors.py` — 16 个错误分类测试
- `tests/smoke/test_connectivity.py` — 26 个核心可用性测试

## 十、练习题

1. **基础题：** 为 `top_p` 参数设计边界测试用例，覆盖 0、0.5、1.0、-0.1 这几个边界值。

2. **进阶题：** 实现一个测试用例，验证多轮对话消息格式的正确性。消息应包含 user、assistant、user 三轮交替的角色。

3. **挑战题：** 设计一个错误分类测试用例，覆盖以下场景：
   - 400 Bad Request（无效参数）
   - 401 Unauthorized（缺少 API Key）
   - 403 Forbidden（Key 无效）
   - 429 Too Many Requests（限流）
   - 500 Internal Server Error（服务端错误）

## 十一、自检清单

- [ ] 覆盖 max_tokens 0/1/4096/-1
- [ ] 覆盖 temperature 0/0.5/1.0/2.0/-0.5
- [ ] 覆盖 top_p 0/0.5/1.0/-0.1
- [ ] 覆盖 4xx/5xx/网络/配置/校验五类错误
- [ ] 消息格式：有效角色、无效角色、空内容、多轮

## 十二、运行验证

```bash
cd ai_test_engine
python -m pytest tests/smoke/ -v
```
