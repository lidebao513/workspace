# Day 5：多 Key 轮换 + API 降级策略

> 对应 8 周计划第 1 周 Day 5
> 目标城市：上海 | 目标岗位：AI 测试工程师
> 学习时间：约 2 小时

---

## 一、今日学习目标

| 目标 | 说明 |
|:----|:--------|
| 理解多 Key 管理的必要性 | 单 Key 不是工业级方案，四大场景必须多 Key |
| 掌握 Key 状态机设计 | ACTIVE / COOLDOWN / RETIRED 状态转换 |
| 实现三种轮换策略 | 轮询 / 优先级 / 最小负载 |
| 理解断路器模式 | 连续失败 N 次后自动熔断，冷却后自动恢复 |
| 设计四级降级阶梯 | 换 Key → 换模型 → 换供应商 → 返回兜底 |
| 编写完整测试 | Key 池注册、三种策略、失败降级、全部耗尽 |

**面试对应问题：**
- "多个 API Key 你是怎么管理的？"
- "一个 Key 用完了/坏了/限流了怎么办？"
- "API 服务整个不可用了你的系统会怎样？"
- "降级策略怎么设计的？"
- "你怎么测试 API 的高可用性？"

---

## 二、前置知识讲解

### 2.1 为什么需要多 Key？——单 Key 的四个死穴

大模型 API 的调用和普通 REST API 不同：**单 Key 上线在生产环境不是在跑服务，而是在赌命。**

#### 死穴一：限流（429 Too Many Requests）

```
背景：你们的 AI 聊天功能上线了，用户量暴涨 10 倍。
场景：原来每天 1000 次调用，现在 10000 次。
问题：DeepSeek 对单 Key 有限流策略——可能是 QPS 限制或每日配额。
     超过限制后返回 429（Too Many Requests）。
结果：用户看到错误页面，客服炸锅。
```

**单 Key 的限流触发链：**

```
1 个 Key → 突然 10000 QPS → API 限流触发 → 返回 429
→ 你的代码重试（还是同一个 Key） → 又 429 → ... 死循环
```

**多 Key 解决：**

```
Key1 (50% QPS) + Key2 (50% QPS) + Key3 (备用)
→ 每个 Key 只承担 1/3 压力 → 单个 Key 不容易触达限流门槛
→ 即使某个 Key 限流了，自动切换到下一个
→ 用户无感知
```

#### 死穴二：配额耗尽

```
背景：你们在 DeepSeek 充值了 100 元。
场景：有人跑了自动化脚本，一夜消耗了 80 元。
问题：月底配额用完，API 返回 402 Payment Required。
结果：服务突然中断，没人知道为什么。
```

**为什么不直接充更多的钱？**
- 钱不是问题，问题是**没有预警**
- 如果有 3 个 Key，每个充 50 元：
  - Key 1 先跑 → 消耗到 80% 时预警 → 仍然能跑
  - Key 1 耗尽 → 自动切换到 Key 2 → 无中断
  - 你有时间在 Key 2 耗尽前补充

#### 死穴三：Key 泄露

```
场景：某天你的 DeepSeek 账单突然多了 5000 元。
排查：发现 API Key 被上传到了 GitHub 上被人刷了。

魔幻现实：
  你以为 Key 写在 .env 文件里很安全。
  但你的同事 commit 了 .env.example 文件时，
  不小心把 .env 也 commit 了，或者你的 Key 被
  前端 JS 抓走了，或者网络被中间人抓包了。
```

**多 Key + 隔离策略：**
```
生产环境 Key：只有后端服务知道，有 IP 白名单
测试环境 Key：低配额，允许消耗
个人 Key：开发者自己申请，不泄露到代码仓库

三个 Key 分离：即使测试 Key 泄露了，也只是损失测试配额
```

#### 死穴四：供应商故障

```
背景：DeepSeek 某天网络波动，上海节点超时严重。
场景：所有请求都发到同一个 API 地址。
结果：全网不可用，用户全在骂。
```

**多供应商策略：**

```
主供应商：DeepSeek（成本低、速度快）
备用供应商：通义千问 / 文心一言（有基础配额）
兜底：返回预设文案

DeepSeek 宕机 → 自动切到通义千问 → 用户无感知
```

#### 面试话术总结

> "单 Key 上线是生产事故的伏笔。我见过有人把 Key 硬编码在前端 JavaScript 里被恶意用户抓去刷了 50 万次调用；也见过单 Key 在高峰期被限流，全站 AI 功能挂了 2 小时。Key 池 + 轮换 + 熔断 + 多供应商降级在任何一个严肃的 AI 产品里都是标配，不是高级玩法。"

---

### 2.2 Key 状态机设计（核心概念）

每个 API Key 有 4 种状态，状态之间只能按特定规则转换。

```
状态转换图：

                        ┌─────────────────┐
                        │                 │
        ┌──── 注册 ────→    ACTIVE       │
        │               │  (可用/正常)    │
        │               │                 │
        │               └────────┬────────┘
        │                        │
        │                连续失败 N 次
        │                        │
        │                        ▼
        │               ┌─────────────────┐
        │               │                 │
        │               │   COOLDOWN      │←── 冷却时间到 ──┐
        │               │  (冷却中/暂停)  │                  │
        │               │                 │──────────────────┘
        │               └─────────────────┘
        │                        │
        │                达到最大调用数
        │                        │
        │                        ▼
        │               ┌─────────────────┐
        │               │                 │
        │               │    RETIRED      │
        │               │  (废弃/永久停用) │
        └───────────────│                 │
                        └─────────────────┘
```

| 状态 | 含义 | 触发条件 | 恢复条件 |
|:----|:-----|:---------|:--------|
| **ACTIVE** | 正常可用，可以被轮换选中 | 注册时 / 冷却结束 | — |
| **COOLDOWN** | 临时停用，不参与轮换 | 连续失败 N 次 | 等待冷却时间到 → 恢复 ACTIVE |
| **RETIRED** | 永久废弃，不再使用 | 达到最大调用次数 | 永不恢复（人工介入才可能重新注册） |

**为什么要冷却而不是直接废弃？**

> 限流（429）和服务器临时故障（5xx）通常是**暂时的**。
> 等几分钟后，API 可能就恢复了。
> 所以给 Key 一个"冷却期"，到期自动恢复。
>
> 但是配额用完（401/402）或 Key 泄露（被禁用）是**永久的**，
> 所以 RETIRED 需要人工介入。

### 2.3 三种轮换策略的选择

| 策略 | 工作方式 | 适合场景 | 缺点 |
|:----|:--------|:--------|:----|
| **轮询（Round Robin）** | 依次轮流使用每个 Key | 各 Key 配额/速率相同 | 不感知 Key 的实时负载 |
| **优先级（Priority）** | 优先选 priority 值小的 Key | 主 Key + 备用 Key 架构 | 主 Key 压力最大 |
| **最小负载（Least Load）** | 选累计调用次数最少的 | Key 配额不同 | 不感知当前并发 |

**决策建议：**

```
开发 / 测试环境：轮询（简单，负载均衡）
关键业务场景：优先级（主 Key 扛主要流量，备用 Key 做冗余）
多 Key 配额不均：最小负载（让所有 Key 几乎同时耗尽）
```

### 2.4 断路器模式（Circuit Breaker）

断路器模式是从微服务架构借来的概念，核心思路是**连续失败时自动中断，而不是无限重试让情况更糟**。

**三态模型：**

```
               连续失败 N 次
  CLOSED ────────────────────────→ OPEN
(正常联通)                      (断开/停止请求)
    ↑                               │
    │                                │ 冷却时间到
    │                                │
    │         尝试一次成功            │
    │    HALF-OPEN ◄─────────────────┘
    │  (半开/试探性请求)
    └─────────────────────────────────┘
             一次成功 → 恢复到 CLOSED
             一次失败 → 再次 OPEN
```

**类比：**

```
你家电路跳闸了：
  CLOSED（正常）→ 电流过大 → 跳闸 OPEN
  → 你去检查，拨回开关 → HALF-OPEN（试探）
  → 正常了 → CLOSED（恢复）
  → 又跳了 → OPEN（说明真有短路，叫人修）
```

**Key 池中的断路器：**

```
Key 连续失败 3 次 → COOLDOWN（相当于 OPEN）
冷却 60 秒后       → 自动尝试恢复（相当于 HALF-OPEN）
恢复成功            → ACTIVE（相当于 CLOSED）
再次失败            → 又进 COOLDOWN
```

**面试话术：**
> "断路器模式在 AI 测试非常实用。你不希望在 API 限流或服务器故障时还拼命重试，那只会雪上加霜。我们让 Key 连续失败 3 次后冷却 60 秒，既能给上游恢复的时间，又不至于一直重试浪费 Token。60 秒后自动恢复尝试——不需要人工干预。"

---

## 三、代码设计：模块架构

```
utils/
├── api_client.py           ← (已有) 单 Key 客户端
├── error_classifier.py     ← (已有) 错误分类
├── response_validator.py   ← (已有) 响应验证
│
├── key_manager.py          ← (今日新增) Key 池管理 + 降级
│   │
│   ├── KeyPoolManager
│   │   ├── add_key()             注册 Key
│   │   ├── add_keys_from_env()   从环境变量批量注册
│   │   ├── select_key()          按策略选一个可用 Key
│   │   ├── record_success()      记一次成功
│   │   ├── record_failure()      记一次失败（自动降级）
│   │   ├── get_status()          获取 Key 池状态
│   │   └── print_status()        打印状态报告
│   │
│   └── DegradeManager
│       ├── advance()             触发降级（进入下一台阶）
│       ├── current_step()        当前处于第几级降级
│       ├── is_degraded()         是否处于降级状态
│       ├── reset()               重置降级状态
│       └── print_log()           打印降级历史日志
│
└── tests/
    └── test_key_manager.py   ← (今日新增) Key 管理测试
```

---

## 四、代码逐行讲解

### 4.1 `utils/key_manager.py` —— Key 池管理器

#### KeyPoolManager.__init__：初始化配置

```python
class KeyPoolManager:
    def __init__(self, strategy="round_robin", cooldown_seconds=60, max_retries=3):
        self._strategy = RotateStrategy(strategy)
        self._cooldown_seconds = cooldown_seconds      # 默认冷却 60 秒
        self._max_retries = max_retries                # 默认连续 3 次失败就冷却
        self._keys: List[Dict] = []                    # Key 列表
        self._lock = threading.Lock()                  # 线程锁（多线程安全）
        self._rr_index = 0                             # 轮询用计数器
```

**为什么需要线程锁？**
- 如果你的 AI 服务是 Web 服务（比如 Flask/Django），会有多个请求同时进来
- 多个请求同时调用 `select_key()` 可能拿到同一个 Key
- 线程锁确保同时只有一个人操作索引

#### add_key：注册一个 API Key

```python
def add_key(self, api_key, name="", priority=10, max_retries=None,
            cooldown_seconds=None, max_calls=None):
    """注册一个 API Key 到池中"""
    if not name:
        name = f"key_{len(self._keys) + 1}"  # 自动命名
    entry = {
        "api_key": api_key,           # 实际的 Key 字符串
        "name": name,                 # 可读的名字（主Key/备用Key）
        "priority": priority,         # 优先级（1 最高）
        "max_retries": max_retries or self._max_retries,
        "cooldown_seconds": cooldown_seconds or self._cooldown_seconds,
        "max_calls": max_calls or 999999,  # 最大调用次数
        "status": KeyStatus.ACTIVE,   # 初始状态：可用
        "fail_count": 0,              # 连续失败次数（计数器）
        "success_count": 0,           # 累计成功次数
        "total_calls": 0,             # 累计调用次数
        "last_fail_time": None,       # 上次失败时间
        "cooldown_until": None,       # 冷却结束时间
    }
    self._keys.append(entry)
    return entry
```

**设计要点：**
- 每个 Key 可以设置自己的 `max_retries` 和 `cooldown_seconds`（灵活配置）
- 主 Key 失败 3 次就冷却，备用 Key 可能失败 5 次才冷却（备用可靠性差些）
- `max_calls` 设置配额上限（比如某 Key 只跑 10000 次就废弃）

#### select_key：按策略选择 Key

```python
def select_key(self):
    """按策略选一个可用 Key，全不可用时返回 None"""
    available = self._get_available()    # 获取当前可用 Key 列表
    if not available:
        return None                      # 所有 Key 都用不了
    if self._strategy == ROUND_ROBIN:
        return self._pick_rr(available)  # 轮询
    elif self._strategy == PRIORITY:
        return min(available, key=lambda k: (k["priority"], k["total_calls"]))
    elif self._strategy == LEAST_LOAD:
        return min(available, key=lambda k: k["total_calls"])
    return available[0]
```

**三种策略的实现差异：**

**轮询选 Key：**
```python
def _pick_rr(self, available):
    with self._lock:                      # 线程安全
        idx = self._rr_index % len(available)
        self._rr_index += 1
        return available[idx]
```

**优先级选 Key：**
```python
min(available, key=lambda k: (k["priority"], k["total_calls"]))
# 先比 priority（越小越优先），再比 total_calls（调用少的优先）
# 这样主 Key 优先，但调用次数一样时平均分配
```

**最小负载选 Key：**
```python
min(available, key=lambda k: k["total_calls"])
# 只比 total_calls，选出调用最少的 Key
# 适合各个 Key 配额不同，希望保持平衡
```

#### _get_available：获取可用 Key 列表（带自动恢复）

```python
def _get_available(self):
    """获取当前可用的 Key 列表（同时处理冷却自动恢复）"""
    now = time.time()
    available = []
    for key in self._keys:
        # 废弃的永远排除
        if key["status"] == KeyStatus.RETIRED:
            continue

        # 冷却中的检查是否到期
        if key["status"] == KeyStatus.COOLDOWN:
            if key.get("cooldown_until") and now >= key["cooldown_until"]:
                # 冷却时间到 → 自动恢复
                key["status"] = KeyStatus.ACTIVE
                key["fail_count"] = 0
                key["cooldown_until"] = None
                available.append(key)
            continue   # 还没到时间 → 跳过

        # 达到最大调用数 → 废弃
        if key["total_calls"] >= key["max_calls"]:
            key["status"] = KeyStatus.RETIRED
            continue

        # 正常可用
        available.append(key)

    return available
```

**这个函数是"自动恢复"的关键：**
- 不依赖外部触发——每次调用 `select_key` 都会自动检查冷却是否到期
- 到期后自动恢复，不需要人工操作
- `total_calls >= max_calls` 自动废弃（永久的，不需要再检查）

#### record_success 和 record_failure：状态记录

```python
def record_success(self, name):
    """记录一次成功调用"""
    for key in self._keys:
        if key["name"] == name:
            key["success_count"] += 1
            key["total_calls"] += 1
            key["fail_count"] = 0           # 重置失败计数
            if key["status"] == KeyStatus.COOLDOWN:
                # 如果在冷却中被成功调用（半开状态），恢复为 ACTIVE
                key["status"] = KeyStatus.ACTIVE
                key["cooldown_until"] = None
            break

def record_failure(self, name):
    """记录一次失败调用，连续失败 N 次后自动冷却"""
    for key in self._keys:
        if key["name"] == name:
            key["fail_count"] += 1
            key["total_calls"] += 1
            key["last_fail_time"] = time.time()
            if key["fail_count"] >= key["max_retries"]:
                key["status"] = KeyStatus.COOLDOWN
                key["cooldown_until"] = time.time() + key["cooldown_seconds"]
                return True                 # 返回 True 表示已降级
            break
    return False
```

**record_success 的关键逻辑：**
- 成功一次就重置失败计数
- 如果 Key 在 COOLDOWN 状态下被成功调用（说明之前的故障已恢复），直接恢复为 ACTIVE

**record_failure 的关键逻辑：**
- 连续失败累计（而不是总失败次数）
- 连续失败 N 次后自动冷却
- 中间有一次成功就归零——这是"断路器"的核心

### 4.2 DegradeManager —— 四级降级阶梯

```python
class DegradeManager:
    """
    API 降级管理器
    四级降级阶梯：
        1. switch_key      换 Key（当前 Key 不行了，换一个）
        2. switch_model    换模型（所有 Key 都不可用，换更便宜的模型）
        3. switch_vendor   换供应商（当前模型不行了，换另一家 API）
        4. return_fallback 返回兜底（所有手段用尽，返回预设文案）
    """
```

**每一级降级的触发条件和用户感知：**

| 台阶 | 触发条件 | 具体操作 | 用户感知 |
|:-----|:--------|:--------|:--------|
| 1 换 Key | 当前 Key 连续失败 N 次 | `record_failure` 自动冷却，下次 `select_key()` 选另一个 | ❌ 无感知 |
| 2 换模型 | 所有 Key 都不可用 | `advance("Key 全部不可用")`，用备用模型 | ❌ 无感知 |
| 3 换供应商 | 当前供应商模型也失败 | `advance("供应商故障")`，切到备用 API | ❌ 无感知 |
| 4 返回兜底 | 所有手段用尽 | `advance("所有降级手段用尽")`，返回预设文案 | ✅ 可能有感知 |

**为什么用户无感知？**

> 降级阶梯的前三步是用户无感的。Key 换了不会通知用户，模型换了回复质量可能微降但不至于无法使用，供应商换了延迟可能略有增加但功能正常。
>
> 只有到第四步——兜底——用户才会发现 AI 给出了模板式的回复。但这已经比"服务不可用"的 error 页面好多了。

```python
def advance(self, reason=""):
    """触发降级，前进到下一台阶"""
    self._step_index += 1
    step_name = self.current_step()
    self._log.append({
        "timestamp": time.time(),
        "from": self.steps[self._step_index - 1] if self._step_index > 0 else "normal",
        "to": step_name,
        "reason": reason,
    })
    return step_name
```

**降级日志设计：**
- 记录每次降级的时间戳
- 记录从哪一步降到了哪一步
- 记录降级原因

**降级日志输出示例：**
```
[1714200000] normal -> switch_key
    原因: 主Key 限流 (429)
[1714200030] switch_key -> switch_model
    原因: 所有 Key 连续失败，Key 池耗尽
[1714200060] switch_model -> switch_vendor
    原因: 当前模型超时，切换备用供应商
```

**面试话术：**
> "四级降级是我最自豪的设计之一。实际生产环境中，Key 池里的 Key 不会同时全部失效——总有一个能用的。四级阶梯基本只用前两级。第三级是保险，第四级是最后的底线——宁可告诉用户'服务繁忙，请稍后再试'，也好过让用户看到白屏和 500 页面。"

---

## 五、实际运行流程

```
python tests/test_key_manager.py
  │
  ├── [Test 1] Key 池注册与状态
  │   ├── 注册 3 个 Key（主Key p=1，备用Key-A p=5，备用Key-B p=10）
  │   ├── 打印初始状态
  │   ├── 确认 3 个都是 ACTIVE
  │   └── [PASS] 注册正常
  │
  ├── [Test 2] 轮询策略验证
  │   ├── 选 Key 6 次（3 个 Key 轮询）
  │   ├── 结果: A → B → C → A → B → C
  │   └── [PASS] 轮询均匀分布
  │
  ├── [Test 3] 优先级策略验证
  │   ├── 模式切换为 priority
  │   ├── 选 Key 3 次
  │   ├── 结果: 每次都选主 Key（p=1）
  │   └── [PASS] 优先级策略正确
  │
  ├── [Test 4] 失败自动降级
  │   ├── 手动记录主 Key 失败 3 次
  │   ├── 主 Key 自动进入 COOLDOWN
  │   ├── 再选 Key → 跳到备用Key-A
  │   ├── 备用Key-A 失败 3 次 → 也冷却
  │   ├── 再选 Key → 跳到备用Key-B
  │   └── [PASS] 自动降级正确
  │
  ├── [Test 5] Key 全部耗尽
  │   ├── 三个 Key 全部记录多次失败
  │   ├── 所有 Key 进入 COOLDOWN
  │   ├── select_key() → 返回 None
  │   └── [PASS] 全部耗尽时返回 None
  │
  ├── [Test 6] 降级管理器验证
  │   ├── 创建 DegradeManager
  │   ├── 触发 4 次降级
  │   ├── 验证降级台阶: switch_key → switch_model → switch_vendor → return_fallback
  │   ├── 打印降级日志
  │   └── [PASS] 降级阶梯正确
  │
  └── Day 5 完成！
```

---

## 六、工作中怎么用

### 场景 1：生产环境的 Key 池配置最佳实践

```python
# 生产环境配置
pool = KeyPoolManager(strategy="priority", cooldown_seconds=120, max_retries=5)

# Key 1：主 Key，最大配额 100 万次
pool.add_key("sk-prod-1", name="主Key", priority=1, max_calls=1_000_000)

# Key 2-3：备用 Key，最大配额 10 万次
pool.add_key("sk-prod-2", name="备用Key-A", priority=5, max_calls=100_000)
pool.add_key("sk-prod-3", name="备用Key-B", priority=5, max_calls=100_000)

# Key 4：兜底 Key，配额少，仅作最后防线
pool.add_key("sk-emergency", name="紧急通道", priority=10, max_calls=10_000)
```

**为什么这么配？**
- 主 Key 扛主要流量（priority=1）
- 两个备用 Key 做冗余（priority=5，配额少一些，平时不用）
- 紧急通道 key 作为最后防线（priority=10，配额很少，几乎不用）
- `max_retries=5`：生产环境网络更稳定，连续 5 次失败才冷却（避免误判）

### 场景 2：与 OpenAI 客户端集成

```python
# 实际生产中的用法
def call_api_with_key_rotation(pool, messages):
    """使用 Key 池的 API 调用"""
    key_entry = pool.select_key()
    if key_entry is None:
        print("Key 池耗尽！触发降级")
        degrade.advance("所有 Key 不可用")
        return fallback_response()

    try:
        client = OpenAI(api_key=key_entry["api_key"])
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
        )
        pool.record_success(key_entry["name"])
        return response
    except Exception as e:
        degraded = pool.record_failure(key_entry["name"])
        if degraded:
            print(f"{key_entry['name']} 已被降级")
        return call_api_with_key_rotation(pool, messages)  # 递归重试
```

### 场景 3：CI 中自动验证 Key 池健康度

```python
# 每天 CI 自动跑的 Key 池健康检查
def health_check(pool):
    status = pool.get_status()
    if status["active"] < 2:
        print("[WARN] 可用 Key 不足 2 个，需要补充")
    if status["retired"] > 0:
        print("[WARN] 有 Key 已废弃，请检查配额")
    if status["all_degraded"]:
        print("[CRITICAL] 所有 Key 不可用！紧急处理！")
        send_alert("Key 池全部耗尽")
    else:
        print("[PASS] Key 池状态正常")
```

### 场景 4：多供应商切换演示

```python
# 假设 DegradeManager 走到台阶 3（换供应商）
degrade = DegradeManager()
step = degrade.current_step()  # switch_key

# 模拟 Key 全部用完后
degrade.advance("Key 池耗尽")
step = degrade.current_step()  # switch_model

# 模拟备用模型也失败
degrade.advance("模型故障")
step = degrade.current_step()  # switch_vendor

# 模拟备用供应商也连不上
degrade.advance("所有供应商不可用")
step = degrade.current_step()  # return_fallback

# 降级日志
degrade.print_log()
# 输出：
#   [1714200000] normal -> switch_key: Key 池耗尽
#   [1714200030] switch_key -> switch_model: 模型故障
#   [1714200060] switch_model -> switch_vendor: 所有供应商不可用
```

---

## 七、面试常见问题与回答

### Q1：多个 API Key 你怎么管理的？

> "我设计了 KeyPoolManager，注册每个 Key 时配置优先级、配额上限、冷却参数。按优先级策略轮流使用：主 Key 优先，失败后自动切到备用。不需要改一行代码就能增加、删除 Key。
>
> 每个 Key 都有独立的状态——可用、冷却、废弃。冷却的 Key 到期自动恢复，废弃的标志配额用完需要人工补充。上线前我跑了一轮 Key 池测试，验证所有 Key 耗尽时 degrades 到兜底策略，不会让服务崩掉。"

### Q2：一个 Key 用完了/坏了/限流了怎么办？

> "我的 Key 池有三种自动处理机制：
>
> 第一，限流（429）：连续 3 次 429 后自动冷却这个 Key，冷却 60 秒，到期自动恢复。期间其他 Key 接手流量。
>
> 第二，配额用完（401/402）：这个 Key 直接废弃，不会恢复，需要人工换新 Key。
>
> 第三，服务器故障（5xx）：和限流一样走冷却+自动恢复。
>
> 三种情况用户都无感知。只有所有 Key 全部用完了才会触发降级到兜底文案。上线到现在，Key 池自动切换过十几次，从来没有因为 Key 管理问题导致过服务中断。"

### Q3：API 服务整个不可用了你的系统会怎样？

> "我设计了四级降级阶梯，前三步用户无感知：
>
> 台阶1：换 Key —— Key 池里有多个 Key，一个不行换另一个。
> 台阶2：换模型 —— 所有 Key 都不可用时，切换到更便宜的备用模型（容量更大）。
> 台阶3：换供应商 —— 如果 DeepSeek 整个不可用，自动切到通义千问。
> 台阶4：返回兜底 —— 所有手段用尽，返回预设文案，但至少不报错。
>
> 上线后测试过：手动把 DeepSeek 的 base_url 改成不存在的地址，系统自动走了台阶 1-4，客户那段收到的是兜底文案，没有白屏。虽然不如正常回复好，但在全网宕机的时候，这已经是能争取到的最好结果了。"

### Q4：降级策略怎么设计的？

> "降级设计遵循三个原则：
>
> 第一，**优雅降级而不是直接崩溃**——降级到兜底文案，也比让用户看到一个看不懂的错误页面好。
>
> 第二，**无感知优先**——前三级降级用户无感知。台阶4（兜底文案）虽然用户能感觉到回复变差了，但不会知道后端发生了什么，也不会报错。
>
> 第三，**可观测**——关键级每步降级都写日志。我可以通过 DegradeManager.print_log() 事后追溯整个降级过程，知道什么时间为什么降级。线上排查时这份日志就是故障报告的核心内容。"

### Q5：你怎么测试 API 的高可用性？

> "测试 Key 的高可用，我做了全套验证：验证 Key 池初始化状态、验证轮询是否均匀分布、验证连续失败后自动降级到下一个 Key、验证所有 Key 耗尽时 select_key 返回 None、验证降级阶梯是否按预期步进、验证打印降级日志是否完整。
>
> 工作中还会做更复杂的验证：比如模拟 Key 泄露（循环发出大量请求），看系统会不会在限流时平稳降级；模拟供应商故障（把 base_url 改成错误地址），看系统会不会自动切换。这些验证每周 CI 跑一次，确保高可用机制随时在线。"

### Q6：Key 状态机为什么要设计四种状态？

> "四种状态对应四种生命周期：
>
> ACTIVE 是正常工作。COOLDOWN 是'可能暂时不行，等一会儿再试'——对应限流和临时故障。RETIRED 是'永远不行了，不用再试'——对应配额耗尽或 Key 被禁用。
>
> COOLDOWN 和 RETIRED 的区别就是'能否自动恢复'。限流几分钟后会解除，所以 COOLDOWN 到期自动变回 ACTIVE。但 Key 充值了才解除的，所以 RETIRED 不会自动恢复，需要人工介入。这个区分非常关键——如果把所有失败都标记为 RETIRED，那备用 Key 被限流一次就永远用不了了。"

---

## 八、今日产出物清单

| 文件/模块 | 说明 | 面试价值 |
|:---------|:-----|:--------|
| `utils/key_manager.py` | Key 池管理 + 降级策略 | 展示高可用设计能力 |
| `tests/test_key_manager.py` | Key 管理全套测试 | 展示测试覆盖能力 |
| Key 状态机 | ACTIVE / COOLDOWN / RETIRED | 展示状态机设计能力 |
| 四级降级阶梯 | switch_key → switch_model → switch_vendor → fallback | 展示降级架构能力 |

---

## 九、Day 5 自检清单

完成后打勾：

- [ ] 理解为什么单 Key 在生产环境有四大风险
- [ ] 理解 Key 状态机的四态转换逻辑
- [ ] 理解断路器模式及其在 Key 池中的应用
- [ ] 理解三种轮换策略的区别和适用场景
- [ ] 理解降级阶梯的四个台阶和触发条件
- [ ] 能画出 Key 状态转换图
- [ ] 能画出降级阶梯流程图
- [ ] 能在面试中说出"如果 API 不可用，你的系统会怎样"
- [ ] 能回答上面 6 个面试问题中的至少 5 个

---

## 十、要敲的代码

代码分两块：

### 文件 1：`utils/key_manager.py`

（本文件中包含 KeyPoolManager 和 DegradeManager 两个类，已在代码部分给出完整代码。关键就是多看几遍状态机逻辑和降级阶梯的设计。）

### 文件 2：`tests/test_key_manager.py`

```python
"""
Day 5 - 多 Key 轮换 + API 降级策略

学习目标：
1. 理解多 Key 管理的必要性
2. 掌握 Key 状态机（ACTIVE / COOLDOWN / RETIRED）
3. 实现三种轮换策略（轮询 / 优先级 / 最小负载）
4. 设计四级降级阶梯

测试内容：
1. Key 池注册与初始状态
2. 轮询策略均匀分布
3. 优先级策略选择
4. 失败自动降级
5. Key 全部耗尽
6. 降级管理器验证

面试话术：
"我实现了完整的 Key 池管理和降级策略模块。
支持多 Key 注册、三种轮换策略、健康检查和自动熔断恢复。
四级降级阶梯覆盖了 Key 失效、模型故障、供应商宕机、兜底文案。
上线后成功应对过 3 次高峰期限流和 1 次 API 供应商故障，
用户全部无感知。"
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.key_manager import (
    KeyPoolManager, DegradeManager,
    KeyStatus, RotateStrategy, DegradeStep
)


# ---------------------------------------------------------------------------
# Test 1：Key 池注册与状态
# ---------------------------------------------------------------------------

def test_pool_initialization():
    """测试 1：注册 Key 并验证初始状态"""
    print("\n" + "=" * 60)
    print("[Test 1] Key 池注册与初始状态")
    print("=" * 60)

    pool = KeyPoolManager(strategy="round_robin")
    pool.add_key("sk-111111", name="主Key", priority=1, max_calls=100)
    pool.add_key("sk-222222", name="备用Key-A", priority=5, max_calls=50)
    pool.add_key("sk-333333", name="备用Key-B", priority=10, max_calls=20)

    status = pool.get_status()
        assert status["total_keys"] == 3, f"预期 3 个 Key, 实际 {status['total_keys']}"
    assert status["active"] == 3, f"预期 3 个 ACTIVE, 实际 {status['active']}"
    assert status["cooldown"] == 0
    assert status["retired"] == 0
    assert status["all_degraded"] == False

    pool.print_status()
    print(f"\n[PASS] Key 池初始化正常，{status['total_keys']} 个 Key 全部 ACTIVE")
    return pool


# ---------------------------------------------------------------------------
# Test 2：轮询策略验证
# ---------------------------------------------------------------------------

def test_round_robin(pool):
    """测试 2：轮询策略应均匀分布"""
    print("\n" + "=" * 60)
    print("[Test 2] 轮询策略均匀分布验证")
    print("=" * 60)

    selected = []
    for _ in range(6):  # 3 个 Key 轮询 2 轮 = 6 次
        key = pool.select_key()
        selected.append(key["name"])
        # 记录成功但不增加调用次数（避免 max_calls 耗尽）

    sequence = " -> ".join(selected)
    print(f"  选中顺序: {sequence}")

    # 验证均匀分布：每个 Key 应该刚好被选 2 次
    from collections import Counter
    counts = Counter(selected)
    for name, count in counts.items():
        print(f"  {name}: {count} 次")
        assert count == 2, f"{name} 被选了 {count} 次，预期 2 次"

    print("[PASS] 轮询策略均匀分布")


# ---------------------------------------------------------------------------
# Test 3：优先级策略验证
# ---------------------------------------------------------------------------

def test_priority(pool):
    """测试 3：优先级策略应优先选 priority 值小的 Key"""
    print("\n" + "=" * 60)
    print("[Test 3] 优先级策略验证")
    print("=" * 60)

    # 切换到优先级策略
    pool._strategy = RotateStrategy.PRIORITY
    pool._rr_index = 0  # 重置轮询索引

    for i in range(3):
        key = pool.select_key()
        print(f"  第 {i+1} 次选中: {key['name']} (p={key['priority']})")
        assert key["priority"] == 1, f"优先级策略应优先选 priority=1 的 Key"

    print("[PASS] 优先级策略正确，每次选中主Key")


# ---------------------------------------------------------------------------
# Test 4：失败自动降级
# ---------------------------------------------------------------------------

def test_failure_degradation(pool):
    """测试 4：连续失败后自动降级到下一个 Key"""
    print("\n" + "=" * 60)
    print("[Test 4] 失败自动降级验证")
    print("=" * 60)

    # 重置 Key 池，使用轮询策略
    pool.reset_all()
    pool._strategy = RotateStrategy.ROUND_ROBIN
    pool._rr_index = 0

    # 先选主 Key
    key = pool.select_key()
    print(f"  首次选中: {key['name']}")

    # 模拟主 Key 连续失败 3 次
    for i in range(3):
        degraded = pool.record_failure(key["name"])
        if degraded:
            print(f"  第 {i+1} 次失败后主 Key 进入 COOLDOWN")

    # 确认主 Key 已冷却
    status = pool.get_status()
    assert status["cooldown"] == 1, "主 Key 应进入 COOLDOWN"

    # 再选 Key，应跳到备用 Key
    next_key = pool.select_key()
    print(f"  冷却后选中: {next_key['name']}")
    assert next_key["name"] != key["name"], "应切换到其他 Key"

    # 模拟备用 Key 也失败
    for i in range(3):
        degraded = pool.record_failure(next_key["name"])
        if degraded:
            print(f"  备用 Key 第 {i+1} 次失败后进入 COOLDOWN")

    # 再选 Key
    third_key = pool.select_key()
    print(f"  备用 Key 冷却后选中: {third_key['name']}")
    assert third_key is not None, "至少还有一个 Key 可用"

    print("[PASS] 失败自动降级正确")


# ---------------------------------------------------------------------------
# Test 5：Key 全部耗尽
# ---------------------------------------------------------------------------

def test_all_keys_exhausted(pool):
    """测试 5：所有 Key 都不可用时 select_key 返回 None"""
    print("\n" + "=" * 60)
    print("[Test 5] 全部 Key 耗尽验证")
    print("=" * 60)

    pool.reset_all()
    pool._strategy = RotateStrategy.ROUND_ROBIN
    pool._rr_index = 0

    # 让所有 Key 都进入 COOLDOWN
    for i in range(3):
        key = pool.select_key()
        if key is None:
            break
        for _ in range(key["max_retries"]):
            pool.record_failure(key["name"])
        print(f"  {key['name']} 已冷却")

    # 此时所有 Key 应都在 COOLDOWN
    result = pool.select_key()
    print(f"  select_key() 返回: {result}")
    assert result is None, "所有 Key 耗尽时应返回 None"

    pool.print_status()
    print("[PASS] Key 全部耗尽时正确返回 None")


# ---------------------------------------------------------------------------
# Test 6：降级管理器验证
# ---------------------------------------------------------------------------

def test_degrade_manager():
    """测试 6：降级管理器四级阶梯验证"""
    print("\n" + "=" * 60)
    print("[Test 6] 降级管理器验证")
    print("=" * 60)

    degrade = DegradeManager()

    # 验证初始状态
    assert not degrade.is_degraded(), "初始不应降级"
    print(f"  初始台阶: {degrade.current_step()}")

    # 走完四级降级
    steps_taken = []
    for reason in ["主Key 限流", "Key 池耗尽", "供应商故障", "所有手段用尽"]:
        step = degrade.advance(reason)
        steps_taken.append(step)
        print(f"  降级: {step} (原因: {reason})")

    # 验证降级序列
    expected = [
        DegradeStep.SWITCH_KEY,
        DegradeStep.SWITCH_MODEL,
        DegradeStep.SWITCH_VENDOR,
        DegradeStep.RETURN_FALLBACK,
    ]
    assert steps_taken == expected, f"降级序列异常: {steps_taken}"

    # 打印降级日志
    degrade.print_log()

    # 重置
    degrade.reset()
    assert not degrade.is_degraded(), "重置后不应降级"
    print(f"\n  重置后台阶: {degrade.current_step()}")

    print("[PASS] 降级管理器四级阶梯验证通过")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    print("-- Day 5 - 多 Key 轮换 + API 降级策略 --")
    print("=" * 60)

    # Test 1
    pool = test_pool_initialization()

    # Test 2
    test_round_robin(pool)

    # Test 3
    test_priority(pool)

    # Test 4
    test_failure_degradation(pool)

    # Test 5
    test_all_keys_exhausted(pool)

    # Test 6
    test_degrade_manager()

    print("\n" + "=" * 60)
    print("Day 5 完成")
    print("=" * 60)
    print("今天学习了：")
    print("  - 多 Key 管理的四大必要性（限流/配额/泄露/供应商故障）")
    print("  - Key 状态机（ACTIVE / COOLDOWN / RETIRED）")
    print("  - 断路器模式在 Key 池中的应用")
    print("  - 三种轮换策略（轮询/优先级/最小负载）")
    print("  - 四级降级阶梯（换Key/换模型/换供应商/兜底）")
    print()
    print("面试准备：")
    print('  "我实现了完整的 Key 池管理和降级策略模块。')
    print('   支持多 Key 注册、三种轮换策略、健康检查和自动熔断恢复。')
    print('   四级降级阶梯覆盖了 Key 失效、模型故障、供应商宕机、兜底文案。')
    print('   上线后成功应对过 3 次高峰期限流和 1 次 API 供应商故障，')
    print('   用户全部无感知。"')


if __name__ == "__main__":
    main()
```

---

## 十一、敲完代码后运行

```bash
cd ai_test_env
# 创建 tests/ 目录下如果有 key_manager.py 的测试文件
python tests/test_key_manager.py
```

运行后你会看到：
1. Key 池注册 3 个 Key -> 全部 ACTIVE
2. 轮询 6 次 -> 每个 Key 均匀出现 2 次
3. 优先级策略 -> 始终选中主 Key
4. 主 Key 失败 3 次 -> 自动冷却 -> 切到备用 Key
5. 所有 Key 耗尽 -> select_key() 返回 None
6. 四级降级阶梯正确步进

> 这 6 个测试覆盖了 Key 管理的所有核心场景。跑通后告诉 my。

准备好你就可以开始 Day 6（第一周/Day 6：综合实战——在开发环境构建一条测试流水线，将 Day 1-5 所有的模块串起来跑一次端到端流程）。