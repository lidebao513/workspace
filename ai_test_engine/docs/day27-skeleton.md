# Day 27 — 项目骨架 + 核心模块

## 学习目标

1. 理解分层架构设计原则，掌握 config/core/tests 三层分离模式
2. 掌握 dataclass 在配置管理中的应用，学会环境变量加载与校验
3. 学会错误分级处理体系（FATAL/ERROR/WARN/INFO）的设计与实现
4. 理解 Key 轮换与降级策略，实现高可用的 API 调用机制

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

**Q: 分层架构中，config 层和 core 层的职责边界是什么？**
A: config 层负责配置的加载、校验和序列化，不包含业务逻辑；core 层负责核心业务逻辑（API 调用、错误处理、Key 管理），可以依赖 config 层获取配置。这样分离的好处是配置变更不影响核心逻辑，核心逻辑变更不影响配置加载方式。

**Q: 如何设计一个生产级的错误处理体系？**
A: 首先定义错误分级（FATAL/ERROR/WARN/INFO），然后实现统一的错误分类器（ErrorHandler），为每种错误类型定义处理策略（是否重试、是否告警）。关键是将错误分类与处理逻辑解耦，让下游模块可以根据分类结果决定如何处理。

## 八、代码示例

### 完整的 Settings 配置类实现

```python
from dataclasses import dataclass, asdict
import os
from typing import Optional

@dataclass
class Settings:
    api_key: str = ""
    api_base: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    max_retries: int = 3
    timeout: int = 30
    max_tokens: int = 4096
    temperature: float = 0.7
    
    @classmethod
    def load_from_env(cls) -> 'Settings':
        """从环境变量加载配置，带兜底默认值"""
        return cls(
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            api_base=os.getenv("API_BASE_URL", "https://api.deepseek.com"),
            model=os.getenv("MODEL_NAME", "deepseek-chat"),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            timeout=int(os.getenv("TIMEOUT", "30")),
            max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
            temperature=float(os.getenv("TEMPERATURE", "0.7"))
        )
    
    def validate(self) -> bool:
        """校验关键字段是否存在"""
        if not self.api_key or "placeholder" in self.api_key.lower():
            return False
        if not self.api_base:
            return False
        return True
    
    def to_dict(self, exclude_sensitive: bool = True) -> dict:
        """序列化配置，可选排除敏感字段"""
        data = asdict(self)
        if exclude_sensitive and "api_key" in data:
            data["api_key"] = "***"
        return data

# 使用示例
if __name__ == "__main__":
    settings = Settings.load_from_env()
    print("配置加载成功:", settings.validate())
    print("配置信息:", settings.to_dict())
```

### 完整的 KeyManager 实现

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class KeyInfo:
    key: str
    model: str = "deepseek-chat"
    failure_count: int = 0
    healthy: bool = True

class KeyManager:
    def __init__(self):
        self._keys: List[KeyInfo] = []
        self._current_index = 0
    
    def add_key(self, key: str, model: str = "deepseek-chat") -> None:
        """添加 Key 到 Key 池"""
        if key and "placeholder" not in key.lower():
            self._keys.append(KeyInfo(key=key, model=model))
    
    @property
    def current_key(self) -> Optional[str]:
        """获取当前 Key"""
        if self._keys:
            return self._keys[self._current_index].key
        return None
    
    @property
    def current_model(self) -> str:
        """获取当前模型"""
        if self._keys:
            return self._keys[self._current_index].model
        return "deepseek-chat"
    
    def rotate_key(self) -> bool:
        """切换到下一个健康的 Key"""
        if not self._keys:
            return False
        
        original_index = self._current_index
        while True:
            self._current_index = (self._current_index + 1) % len(self._keys)
            if self._keys[self._current_index].healthy:
                return True
            if self._current_index == original_index:
                # 所有 Key 都不健康
                return False
    
    def degrade(self) -> bool:
        """降级策略：先换模型，再换 Key"""
        if not self._keys:
            return False
        
        # 尝试切换到轻量模型
        if self.current_model == "deepseek-chat":
            self._keys[self._current_index].model = "deepseek-chat-light"
            return True
        
        # 模型已降级，尝试切换 Key
        return self.rotate_key()
    
    def mark_failure(self) -> None:
        """标记当前 Key 失败"""
        if self._keys:
            self._keys[self._current_index].failure_count += 1
            # 连续 3 次失败标记为不健康
            if self._keys[self._current_index].failure_count >= 3:
                self._keys[self._current_index].healthy = False

# 使用示例
if __name__ == "__main__":
    km = KeyManager()
    km.add_key("sk-xxx1", "deepseek-chat")
    km.add_key("sk-xxx2", "deepseek-chat")
    
    print("当前 Key:", km.current_key)
    print("当前模型:", km.current_model)
    
    # 模拟失败
    km.mark_failure()
    km.mark_failure()
    km.mark_failure()
    
    print("Key 是否健康:", km._keys[0].healthy)
    km.rotate_key()
    print("切换后 Key:", km.current_key)
```

## 九、产出物

- `config/settings.py`
- `core/client.py`
- `core/error_handler.py`
- `core/key_manager.py`

## 十、练习题

1. **基础题：** 修改 `Settings` 类，添加 `api_version` 字段，默认值为 "v1"，并在 `load_from_env()` 方法中添加对应环境变量 `API_VERSION` 的读取。

2. **进阶题：** 为 `KeyManager` 添加 `reset_failure_count()` 方法，用于重置指定 Key 的失败计数。该方法应接受一个可选的 key_index 参数，如果不传则重置当前 Key 的计数。

3. **挑战题：** 实现一个 `ErrorHandler` 类，包含以下功能：
   - 定义 4 种错误级别：FATAL、ERROR、WARN、INFO
   - `classify()` 方法根据异常类型返回错误分类字典
   - `should_retry()` 方法判断是否应该重试（仅 ERROR 和 WARN 级别可重试）
   - `should_alert()` 方法判断是否应该告警（FATAL 和 ERROR 级别需要告警）

## 十一、自检清单

- [ ] Settings 能读环境变量
- [ ] validate 能检测缺少 Key
- [ ] AIEngineClient 能构造正确参数
- [ ] ErrorHandler 能分类 5 种异常
- [ ] KeyManager 能轮换和降级

## 十二、运行验证

```bash
cd ai_test_engine
python -m pytest tests/smoke/test_connectivity.py -v
```
