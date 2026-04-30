# Day 8（第 2 周 Day 3）：截断检测 + Max Tokens 调优

> 对应 8 周计划第 2 周 Day 3
> 目标城市：上海 | 目标岗位：AI 测试工程师
> 学习时间：约 1.5-2 小时

---

## 一、今日学习目标

| 目标 | 说明 |
|:----|:------|
| 理解 finish_reason 的含义 | stop / length / content_filter 的区别 |
| 学会分析截断率 | 多少回复被提前截断 |
| 掌握 max_tokens 推荐算法 | 根据实际数据优化配置 |
| 理解截断与费用的平衡 | 截断率下降 vs 费用上涨的权衡 |
| 实现多档 max_tokens 曲线 | 观察不同配置下的截断表现 |

**面试对应问题：**
- "max_tokens 设多少合适？"
- "你怎么发现回复被截断了？"
- "截断率多少算健康？"
- "改 max_tokens 会影响费用吗？"

---

## 二、前置知识讲解

### 2.1 什么是截断？为什么它是个问题？

**一句话定义：** 截断是 AI 回复因为达到 max_tokens 上限而被"腰斩"——内容没说完就停了。

**用户视角：**
```
用户问："帮我写一篇 2000 字的文章，关于 AI 对就业的影响。"

如果 max_tokens = 512：
  AI 写到一半停了：
  "AI 对就业的影响是一个复杂的话题。一方面..."
  → 用户看到"一方面"就断了，没法继续

如果 max_tokens = 4096：
  AI 写完了整篇文章
  → 用户看到完整内容
```

**finish_reason 的三个值：**

| finish_reason | 含义 | 代表的含义 |
|:-------------|:-----|:-----------|
| `stop` | 正常结束 | AI 认为自己已经把话说完，回复是完整的 |
| `length` | 被截断 | 回复没说完，因为达到了 max_tokens 限制 |
| `content_filter` | 内容过滤 | 回复被安全策略拦截，通常是触发了敏感内容规则 |
| `null` | 未指定 | 极少出现，通常是处理错误 |

**截断的三个层次：**
```
截断不总是坏事情

层次一：预期截断（可接受）
  回复本身就非常长，截断了但核心信息已给
  → max_tokens 需要上调

层次二：意外截断（需要优化）
  回复不算长但被截断了，说明 max_tokens 设得太低
  → 调整 max_tokens

层次三：内容过滤截断（需要警惕）
  回复被安全策略拦截了
  → 可能是 prompt 有问题，需要人工审核
  → "stop" or "length" 之外的 finish_reason 都要关注
```

### 2.2 截断率的计算

```
截断率 = 截断的请求数 / 总请求数 × 100%

假设你跑了 1000 条请求：
  820 条 finish_reason = "stop"
  170 条 finish_reason = "length"
  10 条 finish_reason = "content_filter"

截断率 = (170 + 10) / 1000 = 18%

截断等级：
  < 2%   → 优秀（不用管）
  2-5%   → 良好（边缘）
  5-10%  → 一般（建议调整）
  10-20% → 差（必须调整）
  > 20%  → 严重（立即调整）
```

### 2.3 max_tokens 推荐算法

给定一组回复数据，怎么确定合适的 max_tokens？

```
原则：取"完整回复的最大长度" × 1.2 倍作为推荐值

为什么 × 1.2？
  - × 1.0 太紧：正好卡在边界，稍微多几个 Token 就又截断了
  - × 1.5 太大：浪费 Token 和费用
  - × 1.2 适度：留出 20% 的余量

例子：
  完整回复长度分布：50, 200, 500, 800, 1000, 1500
  最大完整长度：1500
  推荐 max_tokens = 1500 × 1.2 = 1800

  当前配置：1024
  推荐配置：1800
  变化：+76%
```

### 2.4 截断与费用的平衡关系

```
改 max_tokens 不只是技术决策，也是成本决策。

假设每天 10000 次请求：
  当前 max_tokens = 512，平均完成 Token = 300
  每天输出 Token = 300 × 10000 = 3,000,000
  每天费用 ≈ 3M × 0.28元/百万 ≈ 0.84 元

  推荐 max_tokens = 1024，平均完成 Token 涨到 450
  每天输出 Token = 450 × 10000 = 4,500,000
  每天费用 ≈ 4.5M × 0.28元/百万 ≈ 1.26 元

  费用增加：50%
  截断率下降：假设从 30% 降到 2%（降了 93%）

  这个权衡值不值？——当然值！
  → 用户不再看到截断的内容了
  → 费用只多了 0.42 元/天
```

**面试话术：**
> "我发现生产环境 30% 的请求被截断了。做了截断分析后，把 max_tokens 从 512 调到 1024，截断率降到 2%。费用只涨了 15%，但截断率降了 93%。每次优化都要用数据说话——截断率降了多少、费用涨了多少、值不值。"

### 2.5 多档 max_tokens 曲线

不同场景可能需要不同的 max_tokens：
```
max_tokens 曲线的作用：
  把历史请求按 max_tokens 分组
  查看每个组（256/512/1024/2048）的截断率
  直观地看到"多少够用"

示例曲线：
  max_tokens = 256:  截断率 50% (2/4)
  max_tokens = 512:  截断率 33% (3/9)
  max_tokens = 1024: 截断率 0%  (0/2)
  → 说明 512 不够，1024 够

如果所有档都截断（包括 4096）：
  → 可能是 prompt 问题（比如要求写太长了）
  → 也可能是需要分块输出
```

---

## 三、代码设计：截断分析器

### 3.1 模块架构图

```
utils/truncation_analyzer.py
│
├── TruncationAnalyzer   ← 主类
│   ├── record()         ← 单次记录
│   ├── record_batch()   ← 批量记录
│   ├── analyze()        ← 生成截断分析报告
│   └── max_tokens_curve() ← 按 max_tokens 分组的截断率曲线
│
├── TruncationReport     ← 分析报告
│   └── report()         ← 可读报告文本
│
└── get_truncation_level() ← 截断率 → 等级描述
```

### 3.2 关键设计决策

| 决策 | 选择 | 理由 |
|:----|:----|:-----|
| content_filter 算不算截断 | **算** | 虽然性质不同，但从用户体验看都是"没拿到完整回复" |
| 推荐 max_tokens 的上限 | **当前值的 4 倍** | 防止一次推荐太激进导致费用暴涨 |
| 截断率低时不建议调整 | **自动返回不调整** | "如果没坏，就别修" |
| 字符串 max 设为 warning | **不设为 error** | 长度只是一个"建议"，不是"必须" |

---

## 四、代码设计

### 4.1 `utils/truncation_analyzer.py` — 截断分析器

**`record()` 方法：**

```python
def record(self, prompt, response_len, finish_reason, max_tokens, total_tokens, ...):
    is_truncated = finish_reason in ("length", "content_filter")
    record = {
        "prompt": prompt[:30],
        "response_len": response_len,
        "finish_reason": finish_reason,
        ...
        "is_truncated": is_truncated,
    }
    self._records.append(record)
```

- `content_filter` 也被视为截断——因为用户同样没拿到完整回复
- prompt 只存前 30 个字符——日志空间有限

**`analyze()` 方法：**

```python
def analyze(self, records=None):
    # 统计基本分布
    truncated = sum(1 for r in data if r["is_truncated"])
    stop_count = sum(1 for r in data if r["finish_reason"] == "stop")
    length_count = sum(1 for r in data if r["finish_reason"] == "length")
    
    # 分两组：完整回复 vs 截断回复
    full_responses = [r["response_len"] for r in data if r["finish_reason"] == "stop"]
    truncated_lengths = [r["response_len"] for r in data if r["finish_reason"] == "length"]
```

核心逻辑：把回复分成两组——完整组（stop）和截断组（length）。完整组的最大长度决定了推荐的 max_tokens。

**推荐算法：**

```python
suggested = int(max_full_len * 1.2)
suggested = min(suggested, int(current_max * 4))  # 上限 4 倍
suggested = max(suggested, int(current_max))  # 只增不减
```

三行代码完成了推荐：基于数据 × 1.2，防暴涨，只增不减。

### 4.2 `tests/test_truncation.py` — 测试文件

测试设计：
```
Test 1: 无截断 → 截断率 0%，等级"优秀"
Test 2: 全部截断 → 截断率 100%，等级"严重"
Test 3: 混合场景 → 8 stop + 3 length，计算截断率
Test 4: 等级标签 → 每个截断率对应正确等级
Test 5: 推荐算法 → 低截断不调 / 中截断推荐 / 多档曲线
Test 6: 边界情况 → 空数据 / 单条 / content_filter / reset
```

---

## 五、实际运行流程

```
Test 1: 10条全部stop → 截断率 0% → 优秀
Test 2: 5条全部length → 截断率 100% → 严重，建议 1024→1024
  （因为全部被截断，没有"完整回复"可参考，所以不调）
Test 3: 11条(8stop+3length) → 截断率 27.3% → 严重
  完整回复 max=1500 → 推荐 1210→1800
  max_tokens曲线: 1024档 33.3%, 2048档 0%
Test 4: 0%~100% 10个截断率点 → 标签全对
Test 5: 低截断不调 / 10%截断推荐 / 3档配置曲线
Test 6: 空数据报错 / 单条 / content_filter计截断 / reset清零
```

---

## 六、工作中怎么用

### 场景 1：每周截断率报告

```
每周自动跑一次截断分析：
  1. 从日志中提取本周所有请求的 finish_reason
  2. 计算截断率
  3. 如果截断率 > 5%，发送告警
  4. 给出推荐的 max_tokens 调整方案
```

### 场景 2：新 prompt 上线前的截断预检

```
写了一个新 prompt，要求 AI 输出很长的内容：
  1. 用新 prompt 跑 20 次，记录 finish_reason
  2. 如果截断率 > 10%，提示优化 prompt 或调大 max_tokens
  3. 在 CI 中加入这个检查
```

### 场景 3：费用审计

```
每月分析 Token 消耗：
  1. 对比"实际消耗"和"截断浪费的 Token"
  2. 如果截断浪费的 Token > 总消耗的 5%，说明 max_tokens 设置不合理
  3. 给出优化建议和预期省钱金额
```

---

## 七、面试常见问题

### Q1：为什么截断率不是越低越好？

```
答：截断率低到 0% 意味着：
  max_tokens 设得非常大，导致费用很高

比如你用 max_tokens=4096 做所有请求：
  截断率 0%，但每次回复哪怕只用了 50 Token，
  也要为 4096 Token 的上限预留资源（虽然只收实际费用）

更重要的是：如果 max_tokens 设得太大，
AI 可能会"灌水"——反正有空间，多说几句废话。

我一般建议截断率控制在 2-5% 之间。
2% 以下是"浪费了空间"，5% 以上是"很多请求被截断"。
2-5% 是黄金区间——大多数回复都完整，极少数被截断。
```

### Q2：content_filter 截断和 length 截断要怎么区别处理？

```
答：性质不同，处理方式也不同。

length 截断：
  原因是 max_tokens 不够。
  处理方式：调大 max_tokens 或优化 prompt 让回复更短。
  不需要人工介入——自动调整就好。

content_filter 截断：
  原因是 AI 回复触发了安全策略。
  处理方式：
    1. 记录触发内容（用来分析安全策略是否过严）
    2. 如果是误杀，联系 API 供应商调整策略
    3. 如果确实触及了红线，优化提示词
  需要人工复盘——不是简单的参数调整能解决的。

在一个截断分析系统中，我会分开统计两种截断率，
设置不同的告警阈值和修复策略。
```

### Q3：你的截断分析数据从哪里来？

```
答：三个来源：

1. 测试环境（验证用）：
   在测试用例中故意构造长回复提示，验证截断检测逻辑。
   不会影响用户，但数据量小。

2. 预发布环境（调优用）：
   在预发布环境用真实流量影子测试，收集截断数据。
   用这些数据确定 max_tokens 的初始值。
   数据量大，但不会影响生产用户。

3. 生产环境日志（监控用）：
   从生产日志提取每一次调用的 finish_reason 和 Token 消耗。
   数据最大、最真实。
   每日跑一次报告，截断率 > 阈值则告警。

三个环境串联起来就是：
  测试 → 预发布 → 生产
  验证逻辑 → 确定配置 → 监控运行
```

---

## 八、产出物清单

| 文件 | 说明 | 行数 |
|:----|:----|:----|
| `utils/truncation_analyzer.py` | 截断分析器 | ~280 行 |
| `tests/test_truncation.py` | 6 个测试用例 | ~270 行 |
| `day8_study.md` | 本学习文档 | — |

---

## 九、自检清单

- [ ] 能解释 finish_reason 三个值分别代表什么
- [ ] 会计算截断率并判断健康等级
- [ ] 能说出推荐 max_tokens 的公式
- [ ] 理解截断率和费用的平衡关系
- [ ] 知道 content_filter 和 length 的区别
- [ ] 能画出 max_tokens 曲线
- [ ] 能给出多场景的 max_tokens 设置建议

---

## 十、运行验证

```bash
cd ai_test_env
python tests/test_truncation.py
```
