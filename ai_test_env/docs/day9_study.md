# Day 9（第 2 周 Day 4）：LLM-as-Judge + Schema 验证器

> 对应 8 周计划第 2 周 Day 4
> 目标城市：上海 | 目标岗位：AI 测试工程师
> 学习时间：约 1.5-2 小时

---

## 一、今日学习目标

| 目标 | 说明 |
|:----|:------|
| 理解 LLM-as-Judge 评估范式 | 用大模型评价大模型 |
| 实现 6 维评分引擎 | 准确性/完整性/简洁性/相关性/有用性/安全性 |
| 掌握 A/B 对比测试 | 同一提问，两条回复横向比较 |
| 实现 Schema 验证 | 检查 JSON 响应的字段完整性、类型和值范围 |
| 学会处理评委输出异常 | JSON 解析降级策略 |

**面试对应问题：**
- "怎么评估 AI 回复的质量？"
- "什么是 LLM-as-Judge？有什么优缺点？"
- "A/B 测试在 AI 测试中怎么用？"
- "怎么验证大模型输出是否符合格式要求？"

---

## 二、前置知识讲解

### 2.1 什么是 LLM-as-Judge？

**一句话定义：**
LLM-as-Judge 是一种评估范式——让一个大模型扮演"评委"，给另一个大模型的回复打分。

**类比：**
> 传统考试是老师（人）改卷子。LLM-as-Judge 是让 AI 助教改卷子。你不用改几千份考卷了，但 AI 助教可能自己也会犯错。

**为什么需要它？**
- **没有标准答案**：AI 回复同一问题可以有无数种正确表达方式
- **自动化需求**：人工评估速度慢、成本高、主观偏差大
- **规模化**：一个版本发布前可能有上万条回复需要评估

**业界应用（面试必知）：**
- **MT-Bench**（伯克利 LMSYS 组织）：用 GPT-4 评估其他模型的多轮对话质量
- **AlpacaEval**（斯坦福）：自动评估指令模型的质量
- **Chatbot Arena**（LMSYS）：人工 + LLM 混合评估

| 评估方式 | 优点 | 缺点 |
|:---------|:-----|:-----|
| 人工评估 | 准确度高 | 贵、慢、不可规模 |
| 规则匹配 | 稳定、可重复 | 太死板、假阳性高 |
| LLM-as-Judge | 灵活、可规模 | 有偏差、不自知 |
| 混合评估 | 结合两者优势 | 成本较高 |

**实操关联：**
我们今天实现的 LLMJudge 类，就是一套"自建评委系统"——用 DeepSeek 评 DeepSeek。在实际工作中，你可以让 GPT-4 评自己开源模型的回复，或者交叉评估。

---

### 2.2 为什么需要权重加权？

**一句话定义：**
不同的质量维度对用户体验的影响不同，加权能让评分更贴近实际业务的价值判断。

**类比：**
> 买笔记本电脑，性能占 40%、价格占 30%、外观占 10%、续航占 20%。总分不是简单平均，而是加权平均。不同用户权重不同。

**为什么权重分配重要？**

| 业务场景 | 准确性 | 安全性 | 简洁性 |
|:---------|:------:|:------:|:------:|
| 金融客服 | 0.40 | 0.30 | 0.05 |
| 教育答疑 | 0.35 | 0.10 | 0.15 |
| 闲聊机器人 | 0.15 | 0.05 | 0.25 |

> 面试话术：**"权重不是拍脑袋定的。我会收集 500 条用户反馈，跑回归分析找出哪些维度最影响用户满意度，用数据反推权重。"**

**我们的默认权重：**

| 维度 | 权重 | 为什么？ |
|:----|:----:|:---------|
| 准确性 | 0.30 | AI 最怕胡说，第一优先级 |
| 完整性 | 0.20 | 要回答全，不能漏重点 |
| 相关性 | 0.15 | 别答非所问 |
| 有用性 | 0.15 | 能解决用户实际问题 |
| 简洁性 | 0.10 | 不啰嗦 |
| 安全性 | 0.10 | 底线——不能教人做危险事 |

---

### 2.3 Schema 验证为什么重要？

**一句话定义：**
Schema 验证是检查 JSON 响应的"格式标准"——字段名对不对、类型对不对、值范围对不对。

**类比：**
> 你订了一份"姓名+地址+电话"的快递单，结果对方给了你"名字+备注+手机号"。名字是对的，但字段名不对，系统就解析不了。Schema 验证就是在收到 JSON 后先检查格式有没有问题。

**三类 Schema 检查：**

```
1. 字段存在性   → 该有的字段有没有？
2. 字段类型     → 字符串、数字、数组，对不对？
3. 值范围       → 在不在允许的范围内？（比如 1-10 分）
```

**实战代码：**

```python
# 最基础但最常用的 Schema 检查
def validate_judge_response(data: dict) -> list:
    errors = []
    # 1. 字段存在性
    required_fields = ["accuracy", "completeness", "relevance"]
    for field in required_fields:
        if field not in data:
            errors.append(f"缺少字段: {field}")
    
    # 2. 值范围
    for field in ["accuracy", "completeness", "relevance"]:
        if field in data:
            if not isinstance(data[field], (int, float)):
                errors.append(f"{field} 类型错误")
            elif not 1 <= data[field] <= 10:
                errors.append(f"{field} 超出范围: {data[field]}")
    
    return errors

# 使用
data = {"accuracy": 8, "completeness": "high", "relevance": 9}
print(validate_judge_response(data))
# → ["completeness 类型错误"]
```

> 面试话术：**"Schema 验证虽然简单，但在 AI 联调阶段救过我很多次。有一次大模型更新后输出的 JSON 字段名从 camelCase 变成了 snake_case，我们系统没挂，但后置流水线全乱了。加上格式门禁后，每次上线前都会先过 Schema 检查。"**

---

### 2.4 A/B 对比测试在 AI 测试中的应用

**一句话定义：**
A/B 对比测试是对同一输入，让两个模型（或同一模型的不同配置）各产生回复，然后系统性地比较哪个更好。

**类比：**
> 两个厨师做同一道菜，你盲品尝哪个好吃。A/B 对比就是 AI 界的"盲品"。

**典型场景（面试必知）：**

| 场景 | A | B | 对比目的 |
|:----|:--|:--|:---------|
| 模型更新 | 旧模型 | 新模型 | 新版本有没有变差？ |
| Prompt 优化 | 旧 prompt | 新 prompt | 改写 prompt 后质量是否提升？ |
| Temperature 调优 | temp=0.3 | temp=0.7 | 哪个温度质量更好？ |
| 模型切换 | DeepSeek | GPT-4o | 省钱后质量下降多少？ |

**我们的实现方式：**
不是让 LLM 直接"选 A 还是 B"，而是各自独立评分后再比较。这样能看出各维度的差异：

```
A/B 对比报告
  提问: Python 是什么？
  胜者: B
  分差: 0.15
  ────────────────────
  准确性   A=8.0 > B=7.0   ← A 更准确
  完整性   A=6.0 < B=9.0   ← B 更完整（胜出的关键）
  简洁性   A=9.0 > B=6.0
  相关性   A=8.0 = B=8.0
  ────────────────────
  加权总分: A=0.62 vs B=0.77
```

---

## 三、需求分析

### 3.1 问题

如何自动评估 AI 回复的质量？不仅要打分，还要：
1. **多维度覆盖**：不能只看"对不对"，要看全
2. **可比较性**：两个模型或两个配置，谁更好？
3. **格式保障**：回复必须是合法的结构数据
4. **降级处理**：评委模型如果抽风，不能崩

### 3.2 设计决策

| 决策 | 选择 | 原因 |
|:----|:-----|:------|
| 评分机制 | 加权多维评分 | 比单一分数更精细 |
| 评委模式 | 独立评分后比较 | 和"直接对比"互补 |
| 解析策略 | JSON 多层兜底 | 直解析→代码块→大括号提取 |
| 降级策略 | 默认 5 分 + 错误标记 | 不阻塞流程 |

---

## 四、代码讲解

### 4.1 数据结构

```python
@dataclass
class JudgeResult:
    prompt: str
    response: str
    scores: Dict[str, float]      # 各维度原始分（1-10）
    weighted_score: float         # 加权总分（0-1.0）
    comment: str = ""
    raw_output: str = ""          # 评委原始输出
    error: Optional[str] = None
```

### 4.2 JSON 解析策略（三层兜底）

```python
def _extract_json(self, text: str) -> Optional[Dict]:
    # 第 1 层：直接 json.loads
    try: return json.loads(text)
    except: pass
    
    # 第 2 层：从 ```json ... ``` 代码块提取
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            try: return json.loads(text[start:end].strip())
            except: pass
    
    # 第 3 层：找到第一个 { 和最后一个 }
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        try: return json.loads(text[brace_start:brace_end + 1])
        except: pass
    
    return None  # 全部失败
```

### 4.3 加权分数计算

```python
def _compute_weighted(self, scores: Dict[str, float]) -> float:
    # 每个维度：原始分（1-10）归一化到 0-1.0
    # 归一化公式：(raw - 1) / 9
    #   1 分 → 0.0
    #   10 分 → 1.0
    #   5.5 分 → 0.5
    weighted = 0.0
    for dim, config in self.dimensions.items():
        raw = scores.get(dim, 5)                 # 默认 5 分
        normalized = (raw - 1) / 9               # 归一化
        weighted += normalized * config["weight"] # 乘权重累加
    return round(weighted, 2)
```

> **边界情况**：如果某个维度缺失，scores.get(dim, 5) 给 5 分（中间值），而不是 0 分。因为缺少一个维度不应该直接拉低总分。

---

## 五、实际运行流程

### 离线评分流程

```
接收评委原始输出 text
  │
  ▼
_extract_json(text)
  ├── JSON 合法 → 提取所有维度分数
  ├── 代码块包裹 → 提取 JSON 再解析
  └── 大括号包围 → 最后尝试
      │
      ▼
  解析成功？━━是━━▶ 计算加权分 + 记录 comment
      │
      否
      ▼
  所有维度默认 5 分 + 标记 error
      │
      ▼
  返回 JudgeResult
```

### A/B 对比流程

```
同一 prompt
  │
  ├── 回复 A → 评分 → score_A
  └── 回复 B → 评分 → score_B
      │
      ▼
  winner = A if score_A >= score_B else B
  delta = |score_A - score_B|
      │
      ▼
  各维度对比（accuracy: A=8 > B=7 等）
      │
      ▼
  生成对比报告
```

---

## 六、工作中怎么用

### 场景 1：版本回归检测

```python
# 新模型上线前，和旧模型比 200 条测试用例
judge = LLMJudge(api_func=my_api)
cases = load_test_cases()  # 200 条

fail_count = 0
for case in cases:
    old_reply = old_model(case["prompt"])
    new_reply = new_model(case["prompt"])
    ab_result = judge.ab_compare(case["prompt"], old_reply, new_reply)
    if ab_result.winner == "old":
        fail_count += 1

if fail_count / len(cases) > 0.05:
    print("[!!] 新版本有 5% 以上的回复倒退，阻止上线")
```

### 场景 2：Prompt 改写效果评估

```python
# 比较旧 prompt 和新 prompt 的效果
r1 = judge.score(prompt_old.format(user_query), response)
r2 = judge.score(prompt_new.format(user_query), response)
if r2.weighted_score > r1.weighted_score + 0.05:
    print("[OK] 新 prompt 有效提升")
```

### 场景 3：模型切换的质量监控

```
从 DeepSeek 切换到 GPT-4o mini（省钱）, 跑 100 条
→ 平均分下降 0.08（从 0.72 → 0.64）
→ 但降低成本 60%
→ 决策：高频简单对话用 GPT-4o mini，复杂逻辑用 DeepSeek
```

### 场景 4：Schema 自动门禁

```python
def quality_gate(response: str, schema: dict) -> bool:
    """Schema 门禁：不合 Schema 一律拦截"""
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        return False
    
    for field, field_type in schema["required"].items():
        if field not in data:
            return False
        if not isinstance(data[field], field_type):
            return False
    
    return True
```

---

## 七、面试问题

> **Q1: 什么是 LLM-as-Judge？优点和缺点？**
>
> LLM-as-Judge 是用一个 LLM 评估另一个 LLM 的回复质量。
> 优点：灵活度高、可规模化、比规则更准。
> 缺点：有 self-evaluation bias（LLM 更倾向和自己观点一致的回答）、
> 昂贵（需要额外调用）、自身质量波动会影响评估结果。
> 实际工作中不能完全依赖，需要人工抽样交叉验证。

> **Q2: A/B 测试在 LLM 评估中的价值？**
>
> 和传统 A/B 测试不同，LLM 的 A/B 测试是针对同一输入比较两个回复。
> 核心价值：模型版本对比、prompt 优化验证、temperature 调优。
> 我用过的方法有两种：1）分别评分后比较；
> 2）让 LLM 直接"选 A 还是 B"。前者更精细能看到维度差异，
> 后者更直观但稳定性差。我推荐结合使用。

> **Q3: 怎么处理评委模型的输出异常？**
>
> 三层兜底策略：
> 第 1 层：直接 JSON 解析
> 第 2 层：从代码块中提取
> 第 3 层：找大括号对
> 三层都不行就给默认分（5 分）并标记 error。
> 总比服务挂了好。事后分析 error 率看评委模型本身有没有问题。

> **Q4: 评委模型和被评估模型是同一个，会不会有偏见？**
>
> 会，这叫 self-evaluation bias。同一个模型倾向于给自己的输出
> 打更高分。缓解方法：
> 1. 用更强的模型评弱模型（GPT-4 评 Llama）
> 2. 混合评估（LLM + 规则 + 人工抽样）
> 3. 盲评（不让评委知道是谁生成的）
> 4. 校准（定期用人工标注数据校准评委分数）

> **Q5: 加权评分中权重怎么设定？**
>
> 最佳实践是数据驱动，而不是拍脑袋：
> 1. 收集 500+ 条用户反馈
> 2. 每条让用户打分（满意度 1-5）
> 3. 跑线性回归：满意度 = β1*准确性 + β2*完整性 + ...
> 4. 归一化 β 得到权重
> 如果没数据，先用等权或经验权重，后续迭代。

> **Q6: Schema 验证为什么是测试的一部分？**
>
> 很多测试只关注"回复有没有"或"有没有报错"，但 AI 的输出
> 如果格式不对，下游系统根本无法使用。
> 我遇到过：模型更新后字段名从 camelCase 变 snake_case，
> 系统没报错但数据全丢了。加上 Schema 门禁后，
> 所有结构化输出在上线前都过格式检查。

---

## 八、产出物清单

| 文件 | 说明 |
|:----|:------|
| `utils/llm_judge.py` | LLM-as-Judge 评分引擎（6 维加权 + A/B 对比 + 批量评分） |
| `tests/test_llm_judge.py` | 7 个测试用例覆盖所有功能 + Schema 验证 |

---

## 九、自检清单

- [ ] 能说出 LLM-as-Judge 的优缺点
- [ ] 能默写 JSON 解析的三层兜底策略
- [ ] 能解释加权评分为什么比直接评分好
- [ ] 能说出 A/B 对比的 4 个应用场景
- [ ] 能说出 Schema 验证的三种检查类型
- [ ] 知道 self-evaluation bias 和缓解方法

---

## 十、运行验证

```bash
cd C:\Users\69037\.openclaw\workspace\ai_test_env
python -m tests.test_llm_judge
```

---

## 面试题

### 面试题 1：如何设计一个生产级的 LLM-as-Judge 评估系统？

**参考答案：**

生产级 LLM-as-Judge 系统需要解决评判一致性、偏差校正和降级处理：

1. **多评委集成**：
```python
class MultiJudgeEvaluator:
    """多评委集成评估器"""
    
    def __init__(self):
        self.judges = [
            LLMJudge(model="gpt-4"),
            LLMJudge(model="claude-opus"),
            LLMJudge(model="deepseek-chat")
        ]
        self.weights = [0.4, 0.35, 0.25]
    
    def evaluate(self, prompt, response):
        """多评委独立评分后加权平均"""
        scores = []
        for judge in self.judges:
            score = judge.evaluate(prompt, response)
            scores.append(score)
        
        weighted_score = sum(s * w for s, w in zip(scores, self.weights))
        return {
            "weighted_score": weighted_score,
            "individual_scores": scores,
            "agreement_rate": self._calculate_agreement(scores)
        }
    
    def _calculate_agreement(self, scores):
        """计算评委间一致性"""
        if not scores:
            return 1.0
        variance = np.var(scores)
        return max(0, 1 - variance)
```

2. **偏差校正机制**：
```python
class BiasCorrector:
    """评判偏差校正器"""
    
    def __init__(self):
        self.human_baseline = []  # 人工标定的标准答案
        self.model_predictions = []
    
    def calibrate(self, judge_model):
        """校准评委模型"""
        # 对比人工标定和评委评分
        corrections = []
        for human_score, model_score in zip(self.human_baseline, self.model_predictions):
            correction = human_score - model_score
            corrections.append(correction)
        
        # 计算系统性偏差
        avg_correction = np.mean(corrections)
        return lambda raw_score: raw_score + avg_correction
```

3. **降级兜底策略**：
```python
def safe_evaluate(judge, prompt, response):
    """安全的评估，带降级兜底"""
    try:
        # 优先尝试完整评估
        return judge.evaluate(prompt, response)
    except JSONDecodeError:
        # 降级 1：尝试宽松解析
        result = judge._relaxed_parse(response)
        if result:
            result["fallback"] = True
            return result
        # 降级 2：返回默认值
        return DEFAULT_SCORE.copy()
```

**面试话术：**
> "LLM-as-Judge 不是简单调一个模型打分就完了。我设计了多评委集成降低单点偏差、偏差校正机制校准系统性误差、降级兜底策略确保评估不中断。这套体系在生产环境中稳定运行，每天评估 5000+ 条回复，评委间一致性维持在 85% 以上。"

---

### 面试题 2：如何解决 LLM-as-Judge 的 self-evaluation bias 问题？

**参考答案：**

Self-evaluation bias 是 LLM-as-Judge 的核心挑战，需要多种方法组合应对：

1. **Cross-evaluation 避免自评**：
```python
class CrossEvaluator:
    """交叉评估 - 用其他模型评判"""
    
    def __init__(self):
        self.models = ["gpt-4", "claude-opus", "qwen-plus"]
    
    def evaluate(self, prompt, target_response, judge_model):
        """用指定模型评判"""
        if judge_model == target_model:
            raise ValueError("不能用自己的模型评判自己")
        # 交叉评判逻辑
```

2. **对抗性测试检测偏差**：
```python
def detect_self_preference(judge, test_pairs):
    """检测评委是否对自己的输出有偏好"""
    results = []
    for prompt, response_a, response_b in test_pairs:
        # A 是被测模型输出，B 是其他模型输出
        score_a = judge.evaluate(prompt, response_a)
        score_b = judge.evaluate(prompt, response_b)
        results.append({"a_better": score_a > score_b})
    
    # 如果被测模型输出普遍得分更高，说明有自评偏差
    self_preference_rate = sum(1 for r in results if r["a_better"]) / len(results)
    has_bias = abs(self_preference_rate - 0.5) > 0.15
    
    return {"has_bias": has_bias, "self_preference_rate": self_preference_rate}
```

3. **引入人工标定集**：
```python
CALIBRATION_SET = [
    {"prompt": "...", "response": "...", "expected_score": 0.8},
    {"prompt": "...", "response": "...", "expected_score": 0.3},
]

def validate_judge(judge):
    """验证评委准确性"""
    errors = []
    for item in CALIBRATION_SET:
        predicted = judge.evaluate(item["prompt"], item["response"])
        error = abs(predicted - item["expected_score"])
        errors.append(error)
    
    avg_error = np.mean(errors)
    return {"accurate": avg_error < 0.15, "avg_error": avg_error}
```

**面试话术：**
> "Self-evaluation bias 确实是 LLM-as-Judge 的阿喀琉斯之踵。我的解法是：禁止用自己的模型评判自己、引入对抗性测试检测偏好、用人工标定集持续校准。实践下来，这套机制把评判偏差从 15% 降到了 5% 以内。"

---

## 练习题

### 练习题 1：实现多维度 LLM 质量评估系统

**题目：** 扩展 LLMJudge 类，实现一个更全面的多维度评估系统 `EnhancedLLMJudge`，包含：

1. **维度扩展**：添加更多评估维度（逻辑性、专业性、友好性等）
2. **动态权重**：根据场景自动调整各维度权重
3. **解释生成**：为每个评分维度生成文字解释
4. **改进建议**：基于评分结果给出具体的改进建议

**评估维度扩展：**
```python
ENHANCED_DIMENSIONS = {
    "accuracy": {"weight": 0.20, "description": "回答的事实准确性"},
    "relevance": {"weight": 0.15, "description": "回答与问题的相关性"},
    "completeness": {"weight": 0.15, "description": "回答的完整程度"},
    "conciseness": {"weight": 0.10, "description": "回答的简洁程度"},
    "logicality": {"weight": 0.10, "description": "回答的逻辑性"},
    "professionalism": {"weight": 0.10, "description": "回答的专业性"},
    "friendliness": {"weight": 0.10, "description": "回答的友好程度"},
    "safety": {"weight": 0.10, "description": "回答的安全性"}
}

class EnhancedLLMJudge:
    def evaluate(self, prompt, response):
        """返回多维度评估结果和改进建议"""
        dimension_scores = {}
        for dim, config in ENHANCED_DIMENSIONS.items():
            score = self._evaluate_dimension(prompt, response, dim)
            dimension_scores[dim] = {
                "score": score,
                "weight": config["weight"],
                "description": config["description"]
            }
        
        weighted_total = sum(
            s["score"] * s["weight"] for s in dimension_scores.values()
        )
        
        return EnhancedResult(
            dimensions=dimension_scores,
            total_score=weighted_total,
            suggestions=self._generate_suggestions(dimension_scores)
        )
```

---

### 练习题 2：实现 A/B 对比测试框架

**题目：** 实现一个 A/B 对比测试框架 `ABTestFramework`，包含：

1. **统计显著性检验**：确保对比结果统计上显著
2. **置信区间计算**：给出评分差异的置信区间
3. **多维度对比**：对比各维度的具体差异
4. **自动结论生成**：基于对比结果自动生成结论

**统计检验设计：**
```python
from scipy import stats

class ABTestFramework:
    def __init__(self, significance_level=0.05):
        self.significance_level = significance_level
    
    def compare(self, model_a_results, model_b_results):
        """A/B 对比检验"""
        # 独立 t 检验
        t_stat, p_value = stats.ttest_ind(
            [r["total_score"] for r in model_a_results],
            [r["total_score"] for r in model_b_results]
        )
        
        # 计算效应量
        pooled_std = np.sqrt((
            np.var([r["total_score"] for r in model_a_results]) +
            np.var([r["total_score"] for r in model_b_results])
        ) / 2)
        effect_size = (np.mean([r["total_score"] for r in model_a_results]) -
                      np.mean([r["total_score"] for r in model_b_results])) / pooled_std
        
        return ComparisonResult(
            significant=p_value < self.significance_level,
            p_value=p_value,
            effect_size=effect_size,
            winner="A" if np.mean([r["total_score"] for r in model_a_results]) > 
                          np.mean([r["total_score"] for r in model_b_results]) else "B",
            confidence_interval=self._compute_ci(model_a_results, model_b_results)
        )
```

---

### 练习题 3：实现 Schema 验证与自动修复系统

**题目：** 实现一个 Schema 验证与自动修复系统 `SchemaValidatorWithRepair`，包含：

1. **多层级 Schema 验证**：支持嵌套对象的深度验证
2. **类型自动转换**：尝试自动修复类型错误
3. **默认值填充**：自动填充缺失的默认值
4. **验证报告生成**：生成详细的验证和修复报告

**验证与修复逻辑：**
```python
class SchemaValidatorWithRepair:
    def __init__(self, schema):
        self.schema = schema
        self.repairs = []
    
    def validate_and_repair(self, data):
        """验证并修复数据"""
        original = copy.deepcopy(data)
        errors = []
        warnings = []
        
        # 字段存在性检查
        for field, field_schema in self.schema.get("properties", {}).items():
            if field not in data:
                if field_schema.get("required"):
                    errors.append(f"缺少必需字段: {field}")
                elif "default" in field_schema:
                    data[field] = field_schema["default"]
                    self.repairs.append(f"填充默认值: {field}={field_schema['default']}")
        
        # 类型检查和转换
        for field, value in data.items():
            if field in self.schema.get("properties", {}):
                expected_type = self.schema["properties"][field].get("type")
                if not self._check_type(value, expected_type):
                    converted = self._try_convert(value, expected_type)
                    if converted is not None:
                        data[field] = converted
                        self.repairs.append(f"类型转换: {field}")
                    else:
                        errors.append(f"字段 {field} 类型错误")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            repairs=self.repairs,
            original=original,
            repaired=data
        )
```

**要求：**
- 支持 JSON Schema 规范子集
- 实现常用的类型转换（string→int, string→float等）
- 支持自定义验证规则
- 生成可视化验证报告

期望输出中 6 个测试全部显示 [OK]。
