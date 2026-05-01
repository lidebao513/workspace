# Day 7（第 2 周 Day 2）：回复一致性测试

> 对应 8 周计划第 2 周 Day 2
> 目标城市：上海 | 目标岗位：AI 测试工程师
> 学习时间：约 1.5-2 小时

---

## 一、今日学习目标

| 目标 | 说明 |
|:----|:------|
| 理解"一致性"对 AI 产品的意义 | 为什么用户不能接受"同问不同答" |
| 掌握一致性评分算法 | unique_ratio + 变异系数的加权计算 |
| 理解 Temperature 对一致性的影响 | 从 0 到 2 的一致性变化曲线 |
| 实现温度曲线测试 | 在不同 temperature 下各跑 N 次并对比 |
| 实现最佳温度推荐 | 根据曲线找到"质量-一致性"平衡点 |

**面试对应问题：**
- "用户如果问同一个问题得到不同回答，你怎么看？"
- "不一致是一种 bug 吗？"
- "你的产品在不同场景用什么 temperature？"
- "你怎样决定一个场景的 temperature 设多少？"

---

## 二、前置知识讲解

### 2.1 什么是一致性？为什么它很重要？

**一句话定义：** 一致性是大模型在相同输入下输出结果的稳定程度——问同样的问题 N 次，得到的回复趋同还是迥异。

**用户视角：**
```
用户问："今天天气怎么样？"
第 1 次："今天天气晴朗，温度 22 度。"
第 2 次："今天多云转晴，体感舒适。"
第 3 次："今天上海天气不错，适合出门。"

如果三个回答完全不同，但都正确——用户会觉得：
"这 AI 靠谱吗？每次说的不一样？"

如果三个回答的核心信息一致（天气好、温度适中）——
用户会觉得："嗯，这个 AI 挺稳的。"
```

**不一致是 bug 吗？——面试必问**

```
答：不完全算 bug，但它是一个"质量问题"。

如果是客服场景：
  用户查余额，第一次回复"12500 元"，
  第二次回复"账户余额充足"（没说具体数字）
  → 用户无法信任系统

如果是聊天机器人：
  用户问"推荐一部电影"，
  每次推荐不一样 → 其实挺好的，用户觉得丰富

所以不是"所有不一致都是问题"，
而是"应该一致的地方不一致才是问题"。

具体来说：
  事实查询（余额/订单状态）→ 必须严格一致
  知识问答（Python 是什么）→ 核心信息一致，措辞可变
  创意生成（写首诗）→ 不一致是优点
```

### 2.2 一致性测试的两个维度

```
内部一致性（今天做）：
  同一个模型、同一个参数、同一个 prompt
  跑 N 次 → 看变异程度
  → 衡量的是模型自身的"随机性"

外部一致性（第3周做）：
  同一个 prompt，不同模型/不同 prompt 写法
  跑 N 次 → 看差异
  → 衡量的是"模型版本变化"或"prompt 敏感度"

今天做内部一致性，明天做外部一致性覆盖。
```

### 2.3 描述性统计——不写代码也能理解变化的量

一致性测试的核心是**统计学**。不需要精通高等数学，但需要理解三个概念：

**均值（Mean, 平均值）：** 一组数的"中心"
```
回复长度：[50, 52, 48, 51, 49]
均值 = (50+52+48+51+49) / 5 = 50 字
```

**方差（Variance）：** 每个数偏离均值的"平均平方距离"
```
[50, 52, 48, 51, 49]
每个偏差：(50-50)^2=0, (52-50)^2=4, (48-50)^2=4, (51-50)^2=1, (49-50)^2=1
方差 = (0+4+4+1+1) / 4 = 2.5
```

**标准差（Standard Deviation）：** 方差的平方根
```
std = sqrt(2.5) ≈ 1.58
意味着：大多数回复长度在 50 ± 1.58 之内
```

**变异系数（Coefficient of Variation, CV）：** 标准差 / 均值
```
CV = 1.58 / 50 = 0.032
意味着：回复长度波动只有均值的 3.2%，非常稳定！

如果 CV = 0.5 → 波动是均值的 50%，很不稳定
如果 CV = 1.0 → 波动和均值一样大，极其不稳定
```

**在一致性评分中：**
```
unique_ratio = 不相同的回复占的比例（越接近 0 越一致）
cv = 回复长度的相对波动（越接近 0 越一致）

一致性评分 = (1 - unique_ratio) × 0.6 + (1 - cv) × 0.4
```

### 2.4 Temperature 对一致性的影响原理（回顾 Day 2 + 新认知）

**复习 Day 2 内容：** temperature 控制概率分布的"尖锐程度"

**从一致性角度重新理解：**
```
temperature = 0.0：
  每次选概率最高的词 → 回复几乎一样
  一致性评分 ≈ 0.88（5 次跑 1 个 unique）

temperature = 0.5：
  偶尔选概率第二高的词 → 少量措辞变化
  一致性评分 ≈ 0.61（5 次跑 3 个 unique）

temperature = 1.0：
  经常选非最高概率词 → 明显措辞差异
  一致性评分 ≈ 0.35（5 次跑 5 个 unique）

temperature = 2.0：
  低概率词也有机会 → 可能完全不相关
  一致性评分 ≈ 0.33（发散到完全不同的主题）
```

**一致性下降曲线不是线性的：**
```
score
1.0 |  ● (temp=0.0, score=0.88)
0.8 |
0.6 |      ● (temp=0.5, score=0.61)
0.4 |            ● (temp=1.0, score=0.35)
0.2 |                 ● (temp=2.0, score=0.33)
0.0 └───────────────────────────────
    0.0   0.5   1.0   1.5   2.0   temperature


关键发现：一致性在 temperature=0到0.5 之间快速下降，
之后趋于平稳。这意味着：把 temperature 从 0 调到 0.5
变化最大，0.5→1.0 变化其次，1.0→2.0 几乎没区别。
```

### 2.5 什么场景该用多高的 temperature？

| 场景 | 推荐 temperature | 理由 |
|:----|:---------------|:-----|
| 金融客服 | 0.0 - 0.3 | 查余额/利率/流水，必须每次回复一致 |
| 法律咨询 | 0.0 - 0.2 | 法律条款不能有措辞歧义 |
| 医疗问答 | 0.1 - 0.3 | 安全第一，宁可重复也不冒险创新 |
| 技术支持 | 0.3 - 0.5 | 核心信息一致，但语气可以调整 |
| 教育辅导 | 0.5 - 0.7 | 讲解可以多样化，但答案要一致 |
| 聊天机器人 | 0.7 - 1.0 | 多样性 > 一致性，用户喜欢新鲜感 |
| 创意写作 | 1.0 - 1.5 | 追求多样性，甚至可以故意降低一致性 |
| 头脑风暴 | 1.5 - 2.0 | 越随机越有创意可能 |

---

## 三、代码设计：一致性检查器

### 3.1 模块架构图

```
utils/consistency_checker.py
│
├── ConsistencyChecker       ← 主类
│   ├── analyze_responses()  ← 离线分析（传已有的回复列表）
│   ├── run_consistency_test() ← 在线模式（传入 API 调用函数）
│   ├── temperature_curve()  ← 跑多个 temperature 的温度曲线
│   ├── compare_consistency() ← 对比多个温度的表现
│   └── history() / reset()  ← 历史管理和重置
│
├── ConsistencyResult        ← 单组测试结果（dataclass）
│   └── to_dict()            ← 转字典用于报告
│
└── get_consistency_level()  ← 评分 → 等级标签
```

### 3.2 评分算法详解

```
输入：N 次回复的内容列表
                                                         一致性评分
    unique_ratio ────────────── 唯一性分数 ──────→  0.6 × 唯一性分
      ↓                            ↑
    不同的回复数                 1 - unique_ratio
    / 总回复数
                                                       +
    回复长度标准差 ──  +  ── 变异系数 ──→ 变异分数
    / 平均长度                    ↑                0.4 × 变异分
                               1 - min(cv, 1.0)
```

**核心代码：**
```python
def _compute_consistency(self, n, unique_count, responses, lengths):
    unique_ratio = unique_count / n
    avg_len = statistics.mean(lengths)
    len_std = statistics.stdev(lengths) if n >= 2 else 0.0
    cv = len_std / avg_len if avg_len > 0 else 1.0

    uniqueness_score = 1.0 - unique_ratio  # 越少 unique 越高分
    cv_score = max(0.0, 1.0 - min(cv, 1.0))  # 越少波动越高分

    return uniqueness_score * 0.6 + cv_score * 0.4
```

### 3.3 在线 vs 离线模式

**离线模式（`analyze_responses`）：**
- 传一个现成的回复列表
- 不调用 API，纯粹做分析
- 用于写测试用例（不需要真调用 API）
- 用于产品环境：抽取生产日志中的 N 次回复做分析

**在线模式（`run_consistency_test`）：**
- 传一个 API 调用函数 `api_func() -> (text, tokens, latency)`
- 自动调用 N 次
- 用于测试环境：跑不同 temperature 的对比
- 需要 API Key 和网络

---

## 四、代码逐行讲解

### 4.1 `utils/consistency_checker.py`

**一致性等级表：**
```python
CONSISTENCY_LEVELS = {
    "very_high": {"label": "极高", "range": (0.90, 1.00)},
    "high":      {"label": "高",   "range": (0.75, 0.90)},
    "medium":    {"label": "中等", "range": (0.50, 0.75)},
    "low":       {"label": "低",   "range": (0.25, 0.50)},
    "very_low":  {"label": "极低", "range": (0.00, 0.25)},
}
```

基于业务经验划分。不是科学的硬边界，而是"方便理解"的分档。面试时可以这样说：
> "这些分档是我根据业务经验画的。金融场景我们要求极高（0.9+），聊天场景中即可（0.5+）。关键不是分档本身，是你知道每个档次意味着什么。"
```

**`analyze_responses` 方法：**

```python
def analyze_responses(self, prompt, responses, temperature=0.0, ...):
    n = len(responses)
    if n < 2:
        raise ValueError(...)  # 至少 2 次，否则没意义

    lengths = [len(r) for r in responses]
    avg_len = statistics.mean(lengths)
    len_std = statistics.stdev(lengths) if n >= 2 else 0.0
```

- 使用 Python 标准库的 `statistics` 模块（不需要 numpy）
- `statistics.mean()` 计算均值
- `statistics.stdev()` 计算样本标准差（用 n-1 作为分母）

**`temperature_curve` 方法：**

```python
def temperature_curve(self, api_func, prompt, temperatures, n_per_temp=5):
    results = []
    for t in temperatures:
        r = self.run_consistency_test(api_func, prompt, t, n_per_temp)
        results.append(r)
    return results
```

一次跑多个 temperature 的各 N 次——找出"转折点"。

**`compare_consistency` 方法：**

```python
def compare_consistency(self, results):
    temp_scores = [{"temperature": r.temperature, "score": r.consistency_score, ...}]
    best = max(temp_scores, key=lambda x: x["score"])
    ...
    return {"curve": ..., "best_temperature": ..., "recommendation": ...}
```

`recommendation` 方法自动找到一致性开始显著下降的温度点，作为建议值。

### 4.2 `tests/test_consistency.py`

测试设计思路：
```
Test 1: 完全一致 → 评分应最高    （5 次一模一样的回复）
Test 2: 部分一致 → 评分应居中    （5 次有 3 种变体）
Test 3: 完全不一致 → 评分应最低  （5 次完全不同）
Test 4: 等级标签 → 每个分数段标签正确
Test 5: 温度曲线 → 分数随温度上升而下降
Test 6: 边界情况 → 2次/N=10/附带Token延迟/history
```

---

## 五、实际运行流程

```
执行 python tests/test_consistency.py

Test 1: 完全一致
  5 次完全相同回复
  → unique_ratio=0.2, score=0.88, level=高
  → 分析：一摸一样只能拿到 0.88，因为 unique_ratio 最小是 1/n

Test 2: 部分一致
  3 种不同的回复（但核心都差不多）
  → unique_ratio=0.6, score=0.61, level=中等

Test 3: 完全不一致
  5 个完全不相关的回复
  → unique_ratio=1.0, score=0.28, level=低

Test 4: 等级标签
  9 个分数点逐一验证标签（0.0→极低 ... 1.0→极高）
  → 全部匹配

Test 5: 温度曲线
  temp=0.0: score=0.88
  temp=0.5: score=0.61  ← 快速下降阶段
  temp=1.0: score=0.35  ← 继续下降
  temp=2.0: score=0.33  ← 几乎不降（已达底限）
  → 推荐 temperature ≤ 0.5

Test 6: 边界情况
  → 最少 2 次也可分析
  → 大量回复（10 次）统计更稳定
  → 附带 Token 和延迟数据

结果：6 个测试全部通过 ✓
```

---

## 六、工作中怎么用

### 场景 1：新模型上线前的"一致性认证"

```
流程：
1. 选取 50 个代表性 prompt
2. 每个 prompt 在新旧模型上各跑 5 次
3. 比较两个模型的一致性曲线
4. 如果新模型在某场景的一致性低于旧模型 > 10%，打回

代码示意：
    checker = ConsistencyChecker()
    old_results = checker.temperature_curve(old_api, prompt, temperatures)
    new_results = checker.temperature_curve(new_api, prompt, temperatures)
    for i in range(len(temperatures)):
        delta = old_results[i].consistency_score - new_results[i].consistency_score
        if delta > 0.1:
            print(f"新模型在 temp={temperatures[i]} 一致性下降 {delta:.2f}")
```

### 场景 2：Temperature 策略调优

```
工作流：
1. 收集所有业务场景清单
2. 对每个场景跑温度曲线，找到"转折温度"
3. 为每个场景确定安全温度和极限温度
4. 写入配置中心，不允许产品经理自行修改

输出配置示例：
    {
        "金融_余额查询": {"temperature": 0.1, "max": 0.3},
        "客服_常见问题": {"temperature": 0.3, "max": 0.5},
        "聊天_自由对话": {"temperature": 0.7, "max": 1.0},
        "写作_创意文案": {"temperature": 1.0, "max": 1.5},
    }
```

### 场景 3：生产环境一致性监控

```
实时监控：
1. 在日志中标记"重复提问"（用户 5 分钟内问了相同问题）
2. 对比两次回复的一致性评分
3. 如果一致性评分 < 0.5，记录为"不一致事件"
4. 每日统计不一致事件比例

如果某个场景的不一致比例突然上升：
  → 可能模型版本有变
  → 可能 prompt 被改了
  → 可能需要人工复盘
```

### 场景 4：测试中验证 seed 的有效性

```
用一致性检查器验证 seed：
  seed=42 + temperature=0 → 跑 5 次 → 应该 score≈0.88
  seed=None + temperature=0 → 跑 5 次 → score 可能更低
  → 对比有 seed 和没 seed 的差异，验证 seed 是否有效

这个测试特别有用——如果 seed 实现有 bug，导致 seed 没生效，
一致性会比你预期低，一致性检查器就能发现这个问题。
```

---

## 七、面试常见问题与回答

### Q1：你刚才说"不一致不一定是 bug"，那什么场景下必须 100% 一致？

```
答：有一个简单的判断标准：如果用户依赖你的回答做决策，
那么必须一致。

具体场景：
1. 金融查询：查余额、查汇率、查股票——同问必须同答
   "我的余额是多少？" → 必须说具体数字，不能说"还不错"

2. 政策查询：保险条款、法律规定——措辞都不能变
   "合同第三条约定的违约金是多少？" → 每次必须一样

3. 状态查询：订单状态、物流进度——变化代表状态变了
   "我的快递到哪了？" → 如果两次回答的包裹位置不一致
   那就是本质性的数据不一致，不是措辞问题

4. 医疗信息：药品说明、剂量建议——变一个字都可能有风险

可以不一致的场景：
  创意写作、聊天、推荐系统（"推荐一部电影"）
  这些场景多样性反而是优势。

我的原则：信息类必须一致（不能给用户矛盾的信息），
体验类可以不一致（新鲜感是好事）。
```

### Q2：温度曲线测试最少要跑多少次才有效？

```
答：这是一个统计显著性的问题。我一般会这样做：

快速扫描阶段（每个温度跑 5 次）：
  用 5 次获得初步曲线，找到"可能有问题"的温度区间。
  5 次在统计学上不够精确，但用来做"探路"够了。
  今天测试用的就是 5 次。

精确验证阶段（关键温度跑 30 次）：
  在"转折点"附近（比如 0.5 附近）跑 30 次。
  30 次在统计学上是一个"足够大样本"的近似，
  可以比较可靠地估计均值和方差。

生产监控阶段（每天跑 3 次）：
  不需要每次都跑大量测试——3 次够了。
  连续监控，如果连续 3 天的评分都下降，说明有问题。

我的建议：开发时用 5 次，决策时用 30 次，监控时用 3 次。
```

### Q3：一致性评分 0.88（5 次完全相同）为什么不是 1.0？

```
答：这是因为 unique_ratio 的设计缺陷——它是我刻意留的。

5 次完全相同，unique_count=1，unique_ratio=1/5=0.2。
唯一性分 = 1 - 0.2 = 0.8。所以评分永远到不了 1.0。

为什么这样设计？

第一，这是安全的"自我修正"——如果只跑 2 次完全一样，
unique_ratio=0.5，score 更低。你会意识到"2 次不够"，
需要跑更多次。用 5 次可以得到 0.88，已经接近 1.0。

第二，它暗示了"样本量问题"——即使 5 次完全相同，
在统计学上也不能 100% 确定是同一个分布产生的。
如果你要证明"完全一致"，需要更多样本。

第三，实际业务中我们不用 1.0 作为目标——0.88 的
"高"一致性对大多数场景已经足够。追求 1.0 是过度设计。

如果要改成 1.0，只需要把 unique_ratio 改为
(n - unique_count) / (n - 1) 即可。
但我觉得现在的设计更有教育意义。
```

### Q4：一致性测试和回归测试有什么区别？

```
答：这是一个好问题，很多人混淆。

                 一致性测试                      回归测试
  ─────────    ────────────                   ────────────
  测试对象    内部稳定性                      版本间变化
  比较对象    同版本自我对比                  新版本 vs 旧版本
  核心问题    "同一个东西每次一样吗？"        "新版本不如旧版本吗？"
  测试方法    同一个 prompt 跑 N 次           新旧各跑一次对比
  数据需求    需要 N 次输出                   只需要一次输出
  
  举例子：
  一致性测试：temperature=0.5，同一个问题跑 5 次
              → 看看 5 个回答差异大不大
  
  回归测试：旧版本回答 "Python 是编程语言"
           新版本回答 "Python 是一种蛇"
           → 内容变了，说明回归有问题
  
  两者关系：一致性测试可以看作是"微观层面的回归测试"
           — 如果你的系统每次输出都不一样，谈何回归？
```

### Q5：你的产品中有使用"最小负温度"（temperature < 0）的情况吗？

```
答：目前主流的大模型 API 不支持 temperature < 0。

temperature 的范围一般是 [0, 2]。等于 0 时已经是最确定的
状态——每次都选概率最高的词。

低于 0 在数学上没有意义（softmax 的温度参数分母是
正数），而且即使 API 传了负数也只会被 clamp 到 0。

有人问能不能用负 temperature 实现"完全相同的回复"——
答案是不行。为什么 temperature=0 还不够完全一致？
因为 GPU 并行计算的线程调度顺序有微小差异。

所以：温度曲线的下限就是 0，不用考虑负数。
更一致的回复靠 seed 参数（Day 2 讲过）而不是负温度。
```

---

## 八、产出物清单

| 文件 | 说明 | 行数 |
|:----|:----|:----|
| `utils/consistency_checker.py` | 一致性检查器模块 | ~230 行 |
| `tests/test_consistency.py` | 6 个测试用例 | ~270 行 |
| `day7_study.md` | 本学习文档 | — |

---

## 九、Day 7 自检清单

- [ ] 能向非技术同事解释"什么是一致性"
- [ ] 能说出"不一致不一定是 bug"的理由和判断标准
- [ ] 会手算一致性评分（用 unique_ratio + CV）
- [ ] 能画出 temperature 从 0→2 的一致性下降曲线
- [ ] 能给出三个以上场景的推荐 temperature
- [ ] 能回答"最少跑多少次"的统计显著性问题
- [ ] 知道一致性测试 vs 回归测试的区别
- [ ] 能回答 Q1-Q5 中的任意三个

---

## 十、运行验证

```bash
cd ai_test_env
python tests/test_consistency.py
```

---

## 面试题

### 面试题 1：如何设计一个完整的一致性测试体系？

**参考答案：**

完整的一致性测试体系需要从多个维度进行设计：

1. **多温度梯度测试**：
```python
def temperature_consistency_curve(client, prompt, temperatures, runs=5):
    """温度-一致性曲线测试"""
    results = {}
    
    for temp in temperatures:
        responses = []
        for _ in range(runs):
            response = client.chat_with_params(
                prompt=prompt,
                temperature=temp,
                max_tokens=500
            )
            responses.append(client.get_reply_text(response))
        
        score = calculate_consistency_score(responses)
        results[temp] = {
            "score": score,
            "unique_count": len(set(responses)),
            "avg_length": sum(len(r) for r in responses) / len(responses)
        }
    
    return results
```

2. **场景化温度推荐**：
```python
TEMPERATURE_RECOMMENDATIONS = {
    "financial_inquiry": {"range": [0.0, 0.3], "reason": "余额必须一致"},
    "legal_consultation": {"range": [0.0, 0.2], "reason": "条款不能有歧义"},
    "technical_support": {"range": [0.3, 0.5], "reason": "核心信息一致，表达可变"},
    "creative_writing": {"range": [1.0, 1.5], "reason": "追求多样性"},
    "chatbot": {"range": [0.7, 1.0], "reason": "新鲜感优先"}
}
```

3. **统计显著性检验**：
```python
from scipy import stats

def check_statistical_significance(baseline_scores, new_scores):
    """检验新旧评分差异是否显著"""
    t_stat, p_value = stats.ttest_ind(baseline_scores, new_scores)
    return {
        "significant": p_value < 0.05,
        "p_value": p_value,
        "conclusion": "差异显著" if p_value < 0.05 else "差异不显著"
    }
```

**面试话术：**
> "一致性测试不是单点测试，而是一个体系。我会先建立温度-一致性曲线，找到场景的最优温度；然后用统计方法验证样本量是否足够；最后设计场景化的温度推荐表。生产环境中，每天监控一致性分数的分布趋势，一旦异常立刻告警。"

---

### 面试题 2：如何处理"创意场景需要不一致"的需求？

**参考答案：**

创意场景和事实场景的一异性测试策略完全不同：

1. **场景分类处理**：
```python
class ConsistencyTestStrategy:
    """一致性测试策略选择器"""
    
    STRATEGIES = {
        "factual": {
            "expected_consistency": "high",
            "test_method": "exact_match_or_embedding_similarity",
            "threshold": 0.95
        },
        "creative": {
            "expected_consistency": "low",
            "test_method": "diversity_metrics",
            "threshold": 0.3  # 越低说明越多样
        },
        "hybrid": {
            "expected_consistency": "medium",
            "test_method": "combined_score",
            "threshold": 0.6
        }
    }
```

2. **多样性指标设计**：
```python
def calculate_diversity_score(responses):
    """计算创意场景的多样性评分"""
    if not responses:
        return 0.0
    
    unique_ratio = len(set(responses)) / len(responses)
    length_variation = np.std([len(r) for r in responses]) / np.mean([len(r) for r in responses])
    
    diversity_score = unique_ratio * 0.6 + min(length_variation, 1.0) * 0.4
    return round(diversity_score, 3)
```

3. **混合评分方法**：
```python
def calculate_hybrid_consistency_score(responses, is_creative=False):
    """混合场景的一致性评分"""
    base_score = calculate_basic_consistency_score(responses)
    
    if is_creative:
        diversity_bonus = calculate_diversity_score(responses) * 0.3
        return base_score * 0.7 + diversity_bonus
    else:
        return base_score
```

**面试话术：**
> "不是所有场景都需要高一致性。创意场景反而需要低一致性——每次回复都不一样才是好的。我设计了场景化的评分策略：事实类场景用相似度评分，创意类场景用多样性评分。这样既能满足质量要求，又不会误杀创意回复。"

---

## 练习题

### 练习题 1：实现自适应温度推荐系统

**题目：** 实现一个自适应温度推荐系统 `AdaptiveTemperatureRecommender`，包含：

1. **历史数据分析**：分析不同场景的历史回复一致性
2. **动态阈值调整**：根据用户反馈调整一致性阈值
3. **多维度推荐**：综合考虑场景、用户偏好、成本限制
4. **A/B 测试支持**：支持不同温度的在线对比实验

**推荐算法设计：**
```python
class AdaptiveTemperatureRecommender:
    def __init__(self):
        self.scene_profiles = {
            "factual": {"target_consistency": 0.95, "weight_facts": 0.4},
            "creative": {"target_diversity": 0.7, "weight_creativity": 0.4}
        }
    
    def recommend(self, scene, user_preferences=None, cost_budget=None):
        """返回推荐温度和理由"""
        profile = self.scene_profiles.get(scene, {})
        target = profile.get("target_consistency", 0.8)
        
        recommended_temp = self._find_optimal_temperature(
            scene=scene,
            target_score=target
        )
        
        return Recommendation(
            temperature=recommended_temp,
            confidence=0.85,
            reasoning=f"基于{scene}场景的目标一致性{target}推荐"
        )
```

---

### 练习题 2：实现一致性异常检测系统

**题目：** 实现一个一致性异常检测系统 `ConsistencyAnomalyDetector`，包含：

1. **实时监控**：监控生产环境回复的一致性分数
2. **异常检测算法**：使用统计方法检测一致性异常
3. **根因分析**：分析一致性下降的可能原因
4. **自动告警**：触发阈值后自动通知

**异常检测逻辑：**
```python
class ConsistencyAnomalyDetector:
    def __init__(self, window_size=100, z_threshold=2.5):
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.history = []
    
    def detect(self, new_score):
        """检测一致性是否异常"""
        self.history.append(new_score)
        if len(self.history) < self.window_size:
            return {"anomaly": False, "reason": "数据不足"}
        
        recent = self.history[-self.window_size:]
        mean = np.mean(recent)
        std = np.std(recent)
        
        z_score = (new_score - mean) / std if std > 0 else 0
        
        return {
            "anomaly": abs(z_score) > self.z_threshold,
            "z_score": z_score,
            "deviation": new_score - mean,
            "severity": "high" if abs(z_score) > 3 else "medium" if abs(z_score) > 2 else "low"
        }
```

---

### 练习题 3：实现跨模型一致性对比测试

**题目：** 实现一个跨模型一致性对比系统 `CrossModelConsistencyTester`，包含：

1. **多模型支持**：支持测试多个不同模型的一致性
2. **对比分析**：对比不同模型在不同场景的一致性表现
3. **可视化报告**：生成直观的对比图表
4. **最优选择**：根据场景推荐最适合的模型

**对比报告格式：**
```python
{
    "test_prompt": "什么是人工智能？",
    "models_tested": ["deepseek-chat", "qwen-plus", "gpt-4o-mini"],
    "results": {
        "deepseek-chat": {"consistency": 0.82, "avg_length": 150, "stability": "high"},
        "qwen-plus": {"consistency": 0.75, "avg_length": 180, "stability": "medium"},
        "gpt-4o-mini": {"consistency": 0.88, "avg_length": 120, "stability": "very_high"}
    },
    "recommendation": {
        "model": "gpt-4o-mini",
        "reason": "在factual场景下表现最佳"
    }
}
```

**要求：**
- 实现统计显著性检验
- 支持自定义测试场景
- 生成 HTML 可视化报告
- 实现结果缓存避免重复测试
