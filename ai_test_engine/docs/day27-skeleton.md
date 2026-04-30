# Day 27 — 项目骨架 + 核心模块

## 一、引言

开始搭建 `ai_test_engine` 实战项目。目标是将前 5 周学到的 API 测试、质量评估、安全、性能等模块重新组织为可落地的项目骨架。

## 二、前置知识讲解

### 2.1 什么是分层架构？

**一句话定义：** 软件按职责切分成不同的层（展示层/业务层/数据层），每层只依赖相邻下层。

**类比：** 饭店——前台（展示层）负责点菜，厨房（业务层）负责做菜，仓库（数据层）负责存货。前台不关心仓库怎么放，厨房不关心前台怎么接单。

**面试话术：** "分层架构的核心是**关注点分离**——每一层只做自己的事。我选的 3 层：config（配置）、core（引擎）、tests（测试），任何一层改了不影响其它层。"

**实操关联：** `ai_test_engine` 中修改 `client.py` 的 API 调用方式不会影响 `tests/smoke/` 中的测试用例。

### 2.2 什么是 dataclass？

**一句话定义：** Python 3.7+ 的装饰器，自动生成 `__init__`、`__repr__`、`__eq__` 等模板方法。

**代码对比：**
```python
# 传统方式（15 行）
class Settings:
    def __init__(self, api_key="", api_base="..."):
        self.api_key = api_key
        ...

# dataclass（3 行）
from dataclasses import dataclass
@dataclass
class Settings:
    api_key: str = ""
    api_base: str = "https://api.deepseek.com"
```

**面试话术：** "dataclass 让配置类从 15 行缩到 3 行，且直接支持序列化（`asdict()`）。测试配置对象时可以像用普通变量一样操作，不需要手动写 `__init__`。"

### 2.3 什么是环境变量加载？

**一句话定义：** 敏感信息（API Key）不从代码中读取，而是从操作系统环境变量或 `.env` 文件读。

**类比：** 保险箱密码——写在墙上不安全，只有持钥匙的人才能开。`.env` 就是那把钥匙，不提交到 git。

**代码：**
```python
# settings.py
api_key = os.getenv("DEEPSEEK_API_KEY", "")
# .env.example → 提交 git（模板）
# .env → .gitignore（实际值）
```

### 2.4 什么是错误分级体系？

**一句话定义：** 错误按严重程度分 FATAL/ERROR/WARN/INFO，不同级别触发不同处理动作。

**面试话术：** "生产环境最怕 ERROR 和 FATAL 混在一起。我设计了 4 级 + 配套动作：FATAL 直接 STOP、ERROR 重试后告警、WARN 记录日志、INFO 仅监控。`ErrorHandler` 统一分类，`should_retry()`/`should_alert()` 留给下游调用。"

### 2.5 Key 轮换 + 降级策略是什么？

**一句话定义：** 当 API Key 失效或触发限流时，自动切换到备 Key 或降级到弱模型，避免服务中断。

**面试话术：** "Key 管理有点像汽车备胎——爆了一个轮子不能停。`KeyManager` 持有 Key 池，`rotate_key()` 顺序切换，`degrade()` 先换模型再换 Key。连续 3 次失败标记为不健康（`healthy_keys` 只计数 <3 失败的 Key）。"

## 三、需求分析

需要 4 个核心模块：
1. `Settings` — 统一配置管理
2. `AIEngineClient` — API 调用封装
3. `ErrorHandler` — 错误分类 + 处理
4. `KeyManager` — Key 轮换 + 降级

## 四、代码说明

### config/settings.py
- `Settings` dataclass：7 个字段（api_key/api_base/model/max_retries/timeout/max_tokens/temperature）
- `load_from_env()`：读环境变量 + 兜底默认值
- `validate()`：校验关键字段是否存在
- `to_dict()`：序列化（不包含 api_key）

### core/client.py
- `AIEngineClient`：封装 OpenAI SDK
- `chat()`：同步调用
- `chat_stream()`：流式调用（yield 逐 token）
- `get_reply_text()`：提取回复文本
- `get_token_usage()`：提取 Token 统计

### core/error_handler.py
- `AppError` 基类 + 5 个子类
- `ErrorHandler.classify()`：按异常类型返回分类字典
- `should_retry/should_alert/is_fatal`：便捷方法

### core/key_manager.py
- `add_key()`：加入 Key 池
- `current_key/current_model`：获取当前
- `rotate_key()`：切换到下一个
- `degrade()`：先换模型再换 Key
- `mark_failure()`：标记失败

## 五、运行结果

```
26 tests passed (connectivity: 26)
```

## 六、工作场景

- 新项目启动时用 Settings 管理配置，不用到处写 os.getenv
- API 调用不直接 import openai，都经过 AIEngineClient 封装，方便统一改造
- Key 管理解决多 Key 切换 + Key 失效降级

## 七、面试问题

**Q: 为什么不用 dict 而是用 dataclass 管理配置？**
A: dataclass 提供类型提示和 IDE 自动补全，运行时检查更快；dict 值是 `Any`，出错了要到运行时才知道。

**Q: Key 轮换和降级的顺序为什么先换模型再换 Key？**
A: 成本优先级——切换模型是零成本（改个字符串），切换 Key 需要确认下一个 Key 也是健康的。优先尝试低成本方案。

## 八、产出物

- `config/settings.py`
- `core/client.py`
- `core/error_handler.py`
- `core/key_manager.py`

## 九、自检清单

- [ ] Settings 能读环境变量
- [ ] validate 能检测缺少 Key
- [ ] AIEngineClient 能构造正确参数
- [ ] ErrorHandler 能分类 5 种异常
- [ ] KeyManager 能轮换和降级

## 十、运行验证

```bash
cd ai_test_engine
python -m pytest tests/smoke/test_connectivity.py -v
```
