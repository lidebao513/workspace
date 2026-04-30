# Day 10（第 2 周 Day 5）：Week 2 收尾 — 统一质量评估流水线

> 对应 8 周计划第 2 周 Day 5
> 目标城市：上海 | 目标岗位：AI 测试工程师
> 学习时间：约 1.5-2 小时

---

## 一、今日学习目标

| 目标 | 说明 |
|:----|:------|
| 整合 Week 2 四个工具 | QualityChecker + ConsistencyChecker + TruncationAnalyzer + LLMJudge |
| 实现端到端评估流水线 | 一条命令跑完整套质量评估 |
| 掌握综合评分算法 | 四模块权重归一化 |
| 实现版本对比 | 模型更新前后的质量回归检测 |
| 学会自动生成报告 | 将结果格式化为可读报告 + 自动改进建议 |

**面试对应问题：**
- "你怎么保证模型上线前的质量？"
- "你们的质量评估流程是什么样的？"
- "怎么判断新模型比旧模型好？"
- "一次评估需要多久？怎么从几天缩短到几十分钟？"

---

## 二、前置知识讲解

### 2.1 什么是评估流水线（Pipeline）？

**一句话定义：**
评估流水线是把多个独立的检查步骤按顺序串起来，自动完成整个评估过程——输入测试用例 → 按步骤跑各检查 → 输出综合报告。

**类比：**
> 造一辆车不是一次检查就搞定的。先检查发动机 → 再检查轮胎 → 再检查刹车 → 最后综合评价。每个步骤由不同的人（模块）负责，最后汇总成一份质检报告。评估流水线就是这个流程的自动化版本。

**为什么需要流水线？**
- **替代手动步骤**：不用一个模块一个模块手动跑
- **标准化流程**：每次评估都走同样的流程，不会漏步骤
- **可复现性**：同一批测试用例每次跑的结果理论上一致
- **可对比性**：流水线输出的报告格式统一，可以直接对比

**Week 2 流水线架构图：**

```
        ┌─────────────┐
        │  Test Cases  │  (N 条测试用例)
        └──────┬──────┘
               │
       ┌───────▼────────┐
       │  Step 1        │
       │  Quality Check │  ← Day 6: 关键词覆盖 + 否定检测
       │  (QualityCheck)│
       └───────┬────────┘
               │
       ┌───────▼────────┐
       │  Step 2        │
       │  Consistency   │  ← Day 7: 多轮回复一致性
       │  (Consistency) │
       └───────┬────────┘
               │
       ┌───────▼────────┐
       │  Step 3        │
       │  Truncation    │  ← Day 8: 截断率 + max_tokens
       │  (Truncation)  │
       └───────┬────────┘
               │
       ┌───────▼────────┐
       │  Step 4        │
       │  LLM-as-Judge  │  ← Day 9: 6 维评分引擎
       │  (LLMJudge)    │
       └───────┬────────┘
               │
       ┌───────▼────────┐
       │  QualityReport │  ← 综合评分 + 问题列表 + 改进建议
       └────────────────┘
```

---

### 2.2 归一化评分（Normalization）

**一句话定义：**
归一化是把不同尺度的分数映射到统一范围，让它们可以公平地合并计算。

**类比：**
> 考试中，数学满分 150 分，英语满分 100 分。总成绩不能直接 120 + 90 = 210，因为两科满分不一样。归一化就是先把数学 120 转换成 80%（120/150），再把英语 90 转换成 90%（90/100），然后才能加权平均。

**我们遇到的具体问题：**

四个模块的分数含义完全不同：

| 模块 | 原始分数含义 | 范围 | 问题 |
|:----|:-------------|:----:|:-----|
| QualityChecker | 关键词覆盖 + 否定检查 | 0-1.0 | 分数含义明确 |
| ConsistencyChecker | 多轮一致程度 | 0-1.0 | 越高越一致 |
| TruncationAnalyzer | 截断率 | 0-100% | **越低越好** |
| LLMJudge | 加权评分 | 0-1.0 | 分数含义明确 |

截断率是唯一一个"越低越好"的指标。所以需要转换：

```
截断得分 = 1.0 - min(截断率, 1.0)

截断率 0%  → 得分 1.0（完美）
截断率 10% → 得分 0.9
截断率 50% → 得分 0.5
截断率 100%→ 得分 0.0（灾难）
```

**我们的归一化策略（面试亮点）：**

不仅仅是固定权重。当一个模块没有数据时，它的权重自动分配到其他有数据的模块：

```python
# 只有 3 个模块有数据
active_weights = 0.25 (quality) + 0.15 (consistency) + 0.50 (judge)
# 合计活动权重 = 0.90
# 综合分 = (quality*0.25 + consistency*0.15 + judge*0.50) / 0.90
```

这种设计就是**自适应权重归一化**。面试时可以说：
> **"我设计了一套自适应权重的归一化方案。当某个模块没有数据时，权重自动重新分配，不会因为缺少模块而整体偏分。"**

---

### 2.3 版本对比（Regression Testing）

**一句话定义：**
版本对比是分别对旧模型和新模型跑同一套评估流水线，比较两次的综合评分和各维度变化，判断新版本是否退化。

**类比：**
> 你的手机从 iOS 16 升级到 iOS 17。你希望它更快、更省电、新功能更好用。但如果升级后电池耗电更快了，这就是退化（regression）。版本对比就是在上线前系统性地检查"新版本有没有把旧版本好的地方弄坏了"。

**核心指标对比：**

```
             旧版 (v1) → 新版 (v2)  变化方向
综合评分     0.75    → 0.82         ↑ 更好
质量检查分   0.80    → 0.85         ↑ 更好
一致性分     0.72    → 0.65         ↓ 变差（⚠️ 关注！）
截断率       8%      → 3%           ↑ 更好
LLM 评分     0.70    → 0.78         ↑ 更好
新发现问题   3 个    → 1 个         ↓ 更少
```

**门禁决策逻辑：**

```python
def gating_decision(comparison: Dict) -> str:
    """根据版本对比结果判断是否允许上线"""
    if comparison["deltas"]["overall"] < -0.05:
        return "BLOCKED"  # 综合分下降 > 5%，阻止上线
    if comparison["deltas"]["judge"] < -0.10:
        return "BLOCKED"  # LLM 评分下降 > 10%，阻止上线
    if comparison["new_issues"] > 3:
        return "REVIEW"   # 新增问题 > 3 个，需人工审查
    return "APPROVED"
```

> 面试话术：**"我们每个模型版本上线前，跑 500 条质量评估用例，自动对比新旧版本。综合评分降 5% 以上直接阻止上线，省去了一堆扯皮。"**

---

## 三、需求分析

### 3.1 问题

有了四个独立工具后，还需要：
1. **整合**：不能每次手动跑四个模块
2. **自动报告**：评估结果要有统一格式
3. **可比较**：多次评估能对比
4. **可扩展**：未来加新模块不会破坏现有逻辑

### 3.2 设计决策

| 决策 | 选择 | 原因 |
|:----|:-----|:------|
| 流水线模式 | 离线全量 + 可传部分模块 | 灵活，适应不同场景 |
| 评分算法 | 自适应权重归一化 | 模块缺失不影响总分尺度 |
| 报告格式 | dataclass + to_dict + 控制台格式化 | 既适合编程处理也适合阅读 |
| 版本对比 | 基于 QualityReport 的 Delta 计算 | 可扩展，新模块加字段就行 |

---

## 四、代码讲解

### 4.1 综合评分核心算法

```python
def compute_overall_score(quality, consistency, truncation, judge):
    # 截断分转换（越低越好）
    truncation_score = max(0.0, 1.0 - min(truncation, 1.0))
    
    # 自适应权重：只统计有数据的模块
    weighted_sum = 0.0
    total_weight = 0.0
    
    if quality > 0:
        weighted_sum += quality * 0.25
        total_weight += 0.25
    if consistency > 0:
        weighted_sum += consistency * 0.15
        total_weight += 0.15
    if truncation > 0:
        weighted_sum += truncation_score * 0.10
        total_weight += 0.10
    if judge > 0:
        weighted_sum += judge * 0.50
        total_weight += 0.50
    
    if total_weight == 0:
        return 0.0
    
    return weighted_sum / total_weight  # 归一化
```

### 4.2 版本对比核心算法

```python
def compare_versions(report_v1, report_v2):
    deltas = {
        "overall":     report_v2.overall_score - report_v1.overall_score,
        "quality":     report_v2.quality_score - report_v1.quality_score,
        "consistency": report_v2.consistency_score - report_v1.consistency_score,
        "truncation":  report_v2.truncation_rate - report_v1.truncation_rate,
        "judge":       report_v2.judge_avg_score - report_v1.judge_avg_score,
    }
    status = "PASS" if deltas["overall"] >= 0 else "WARN"
    return {
        "version_a": report_v1.model_name,
        "version_b": report_v2.model_name,
        "status": status,
        "deltas": deltas,
        "v1_grade": report_v1.overall_grade,
        "v2_grade": report_v2.overall_grade,
    }
```

### 4.3 自动改进建议生成

```python
def _generate_recommendations(report):
    recs = []
    
    if report.quality_score < 0.7:
        recs.append("质量分偏低：检查关键词覆盖率是否合理")
    
    if report.consistency_score < 0.5:
        recs.append(f"一致性不足（{report.consistency_score}）："
                    "考虑降低 temperature 到 0.3 以下")
    
    if report.truncation_rate > 0.10:
        recs.append(f"截断率偏高（{report.truncation_rate:.1%}）："
                    f"建议 max_tokens 调至 {report.max_tokens_advice}")
    
    if report.judge_avg_score < 0.6:
        recs.append(f"LLM 评分偏低（{report.judge_avg_score:.2f}）：需排查")
    
    if not recs:
        recs.append("所有指标在健康范围内")
    
    return recs
```

---

## 五、实际运行流程

### 运行 `run_offline` 后的完整流程

```
run_offline(quality_cases, consistency_cases, truncation_records, judge_cases)
  │
  ├─ Step 1: QualityChecker.batch_check(quality_cases)
  │    → 每条用例检查关键词 + 否定词
  │    → 计算通过率和平均分
  │    → 检查低分项（score < 0.5 → 记录 issue）
  │
  ├─ Step 2: ConsistencyChecker.analyze_responses(...)
  │    → 每组多轮回复计算一致性分
  │    → 取平均作为最终一致性分
  │    → 检查低一致性（score < 0.5 → 记录 issue）
  │
  ├─ Step 3: TruncationAnalyzer.record_batch → analyze()
  │    → 统计截断率
  │    → 检查高截断（rate > 10% → 记录 issue）
  │    → 给出 max_tokens 推荐
  │
  ├─ Step 4: LLMJudge.score_offline(...) × N
  │    → 每条用例让评委模型打分
  │    → 计算平均分
  │    → 检查低分（score < 0.5 → 记录 issue）
  │
  ├─ 综合计算
  │    → compute_overall_score()
  │    → compute_overall_grade()
  │
  └─ 输出 QualityReport
       → to_dict()（给程序用）
       → format_report_console()（给人看）
```

---

## 六、工作中怎么用

### 场景 1：模型上线门禁

```python
pipeline = AssessmentPipeline()

# 旧版本评估
report_old = pipeline.run_offline(
    model_name="v1.0",
    quality_cases=load_test_cases("quality"),
    consistency_cases=load_test_cases("consistency"),
    truncation_records=load_logs("production"),
    judge_cases=load_test_cases("judge"),
)

# 新版本评估
pipeline.reset()
report_new = pipeline.run_offline(
    model_name="v2.0",
    # 用同一套测试用例
    quality_cases=load_test_cases("quality"),
    consistency_cases=load_test_cases("consistency"),
    truncation_records=load_logs("production"),
    judge_cases=load_test_cases("judge"),
)

# 自动对比 + 门禁
comparison = pipeline.compare_versions(report_old, report_new)
if comparison["status"] == "WARN":
    send_alert("阻止上线：新版本综合评分下降")
else:
    approve_deployment()
```

### 场景 2：每日质量监控

```
每天早上 8:00 定时跑评估流水线
→ 和昨天的报告对比
→ 如果质量下降超 5%，发告警
→ 趋势图：综合评分 7 天曲线
```

### 场景 3：Prompt 优化效果追踪

```
优化前 prompt → 评估得 0.72
优化后 prompt → 评估得 0.81
提升 0.09，决定全量上线新 prompt
```

### 场景 4：供应商模型评估

```
A 模型（0.85 分, $10/百万Token）
B 模型（0.82 分, $3/百万Token）
C 模型（0.79 分, $0.5/百万Token）

权衡：B 模型性价比最高，选 B
质量下降可以接受，成本降 70%
```

---

## 七、面试问题

> **Q1: 怎么设计一套 AI 回复质量评估流程？**
>
> 我的方案分四层：
> 1. 规则层（关键词覆盖 + 否定检测）— 快速排除明显问题
> 2. 统计层（一致性检查）— 看回复是否稳定
> 3. 指标层（截断率 + max_tokens）— 基础设施维度
> 4. 语义层（LLM-as-Judge）— 最核心的语义质量评估
>
> 四层串成一条流水线，30 分钟跑完 500 条用例，自动出报告。
> 每层产出归一化到 0-1 后按自适应权重合并。

> **Q2: 版本对比中怎么判断"是否退化"？**
>
> 我设置了三道防线：
> 1. 综合分下降 5% → 直接阻止上线
> 2. LLM 评分下降 10% 或截断率上升 10% → 阻止上线
> 3. 新增问题超过 3 个 → 需人工审查
>
> 这三道防线拦截过 3 次问题版本。

> **Q3: 如果四个模块有些有数据有些没有，综合分怎么算？**
>
> 用自适应权重归一化。假设只有质量检查（权重 0.25）和
> LLM 评分（权重 0.50）有数据，活动权重合计 0.75。
> 综合分 = (质量分×0.25 + LLM 分×0.50) / 0.75。
> 这样不管传几个模块，总分都在 0-1 的稳定范围内。

> **Q4: 流水线中的各个模块可以替换吗？**
>
> 可以。每个模块都是独立类，有统一的输入输出接口。
> 如果将来有更好的质量检查方法，替换 QualityChecker
> 即可，不需要改流水线代码。这就是组合优于继承。

> **Q5: 评估一次需要多少测试用例？**
>
> 最少 20 条能看到趋势，稳定评估需要 200-500 条。
> 我们的生产环境固定 500 条回归用例，来自三个来源：
> 1. 线上用户真实请求（去隐私后的）
> 2. 边界情况（特意构造的刁钻问题）
> 3. 历史故障和修复验证

> **Q6: 如果某个模块运行失败怎么办？**
>
> 设计上我做了容错：模块失败不影响其他模块。
> 比如 LLM-as-Judge 调用超时了，质量检查和截断分析
> 的结果还在。最终报告会标记哪些模块有数据、哪些缺失。
> 但不会让整个流程崩掉。

---

## 八、产出物清单

| 文件 | 说明 |
|:----|:------|
| `utils/pipeline_assessment.py` | AssessmentPipeline 主类 + QualityReport + 格式化输出 |
| `tests/test_pipeline_assessment.py` | 6 个测试用例覆盖全量/部分/边界/版本对比 |

---

## 九、自检清单

- [ ] 能画出 Week 2 流水线的四步架构图
- [ ] 能解释自适应权重归一化的原理和必要性
- [ ] 能说出版本对比的三道防线门禁规则
- [ ] 知道截断率和其他三个指标的方向差异（越低越好 vs 越高越好）
- [ ] 能说出自动改进建议触发的条件（质量<0.7/一致性<0.5/截断>10%/LLM<0.6）
- [ ] 知道实际工作中的一个"版前评估→发现问题→阻止上线"的实战案例

---

## 十、运行验证

```bash
cd C:\Users\69037\.openclaw\workspace\ai_test_env
python -m tests.test_pipeline_assessment
```

期望输出中 6 个测试全部显示 [OK]。

## 十一、Week 2 总结

| 天数 | 主题 | 核心产出 |
|:----|:-----|:---------|
| Day 6 | 回复质量检查器 | QualityChecker（关键词+否定检测） |
| Day 7 | 一致性检查器 | ConsistencyChecker（多轮回复稳定性） |
| Day 8 | 截断检测 + Max Tokens | TruncationAnalyzer（截断率+费用分析） |
| Day 9 | LLM-as-Judge + Schema | LLMJudge（6 维评分+A/B对比） |
| Day 10 | 统一评估流水线 | AssessmentPipeline（四合一+版本对比+自动报告） |

**Week 2 的实战价值：**
你现在有一整套自动化质量评估工具。拿到一个 AI 模型后，你可以：

1. **快速评估**：跑 500 条用例，30 分钟出报告
2. **发现隐患**：低一致性、高截断、低分回复一网打尽
3. **回归检测**：新版本上线前自动对比旧版本
4. **数据说话**：质量评估不再靠感觉，每个决策有数据支撑
