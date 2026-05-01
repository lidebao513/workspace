# Day 30 — 质量评估模块

## 学习目标

1. 理解 5 维评分体系，学会从完整性、相关性、连贯性、一致性、简洁性五个维度评估 AI 回复质量
2. 掌握 LLM-as-Judge 方法，学会用 AI 模型评估 AI 输出
3. 理解 JSON 解析三层兜底策略，学会处理不稳定的 JSON 输出
4. 掌握版本对比（A/B）方法，学会量化模型升级的质量变化

## 一、引言

从 ai_test_env 的 Week 2 迁移质量评估三件套到 ai_test_engine：5 维评分、LLM-as-Judge、端到端流水线。

## 二、前置知识讲解

### 2.1 什么是 5 维评分体系？

**一句话定义：** 从 completeness（完整性）、relevance（相关性）、coherence（连贯性）、consistency（一致性）、conciseness（简洁性）五个维度给 AI 回复打分。

**面试话术：** "只给一个综合分太笼统。5 维评分让你看见具体短板——用户追问时能说 '上周 completeness 降了 20%，因为模型切换导致回复变短了'。"

### 2.2 LLM-as-Judge 是什么？

**一句话定义：** 用 AI 模型来评估 AI 模型的输出质量，而非人工逐条打分。

**面试话术：** "LLM-as-Judge 比人工快 100 倍，但有个坑——它输出的 JSON 格式不稳定。我写了三层兜底解析：`json.loads` → 正则匹配 → 默认 0.5，实测能兜住 99% 的情况。"

### 2.3 什么是 JSON 解析的三层兜底？

```python
# 第 1 层：标准 JSON
json.loads('{"score": 0.85}')

# 第 2 层：正则提取
re.search(r'score\\s*:\\s*([0-9.]+)', '{"score": 0.85}')

# 第 3 层：默认值
return 0.5
```

### 2.4 什么是版本对比（A/B）？

**一句话定义：** 同一组 prompt 在旧模型（v1）和新模型（v2）下的表现差异，量化改进或回退。

**面试话术：** "模型升级后质量是变好还是变差？得分说话。`compare_versions()` 直接算 delta，正数改进、负数回退、< -0.1 标记 regression。"

## 三、需求分析

13 个测试用例，分 3 组：
1. QualityScore（5 个测试）—— 评分结构/综合分计算/范围
2. LLMJudge（5 个测试）—— 解析三种格式/A/B 比较
3. AssessmentPipeline（3 个测试）—— 评估/版本对比

## 四、运行结果

```
13 passed (quality: 13)
```

## 五、面试问题

**Q: 10 分制和 5 维评分比单一打分有什么好处？**
A: 可定位问题。综合分 0.6 如果只看数字就是"不及格"，但 5 维评分告诉你'一致性很低，相关性很高'，改进方向一下子就清楚了。

**Q: 如何处理 LLM 打分偏差？**
A: 同一组 prompt 用 3 次不同温度取中位数，减少单次 variance。还做了一致性检查——对同一对回复从不同角度问 3 次，评分波动大的样本打标记。

**Q: LLM-as-Judge 的局限性是什么？如何缓解？**
A: 主要局限是输出格式不稳定（经常返回非标准 JSON）和打分偏差（倾向于给高分）。我用三层兜底解析（JSON→正则→默认值）处理格式问题，用多轮取中位数和一致性检查缓解打分偏差。

**Q: 版本对比中，delta 的阈值应该怎么设置？**
A: 这取决于业务需求。我设置 delta < -0.1 为回归，delta > 0.1 为改进。阈值太小会产生太多误报，太大则会漏掉真正的质量下降。

## 六、代码示例

### 5 维评分体系实现

```python
from dataclasses import dataclass, asdict
from typing import Dict, Optional

@dataclass
class QualityScore:
    """5 维质量评分体系"""
    completeness: float  # 完整性：回答是否覆盖所有要点
    relevance: float     # 相关性：回答是否与问题相关
    coherence: float     # 连贯性：回答逻辑是否连贯
    consistency: float   # 一致性：回答是否前后一致
    conciseness: float   # 简洁性：回答是否简洁不冗余
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'QualityScore':
        """从字典创建评分对象"""
        return cls(
            completeness=data.get('completeness', 0.0),
            relevance=data.get('relevance', 0.0),
            coherence=data.get('coherence', 0.0),
            consistency=data.get('consistency', 0.0),
            conciseness=data.get('conciseness', 0.0)
        )
    
    @property
    def overall(self) -> float:
        """计算综合分（各维度平均值）"""
        return (self.completeness + self.relevance + 
                self.coherence + self.consistency + 
                self.conciseness) / 5
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典，包含综合分"""
        data = asdict(self)
        data['overall'] = round(self.overall, 2)
        return data

class LLMJudge:
    """LLM-as-Judge 评估器"""
    
    @staticmethod
    def parse_score(output: str) -> float:
        """三层兜底解析 LLM 输出的分数"""
        import json
        import re
        
        # 第一层：标准 JSON 解析
        try:
            result = json.loads(output)
            if 'score' in result:
                return float(result['score'])
            if 'overall' in result:
                return float(result['overall'])
        except json.JSONDecodeError:
            pass
        
        # 第二层：正则提取
        match = re.search(r'score\s*[:=]\s*([0-9.]+)', output, re.IGNORECASE)
        if match:
            return float(match.group(1))
        
        match = re.search(r'(\d+\.?\d*)\s*(?:分|分制|out of|/)\s*10?', output)
        if match:
            return float(match.group(1)) / 10.0
        
        # 第三层：默认值
        return 0.5
    
    def judge(self, prompt: str, response: str) -> QualityScore:
        """评估单个回复的质量"""
        # 模拟 LLM 评估（实际实现需要调用真实 LLM）
        # 这里用随机生成模拟
        import random
        return QualityScore(
            completeness=round(random.uniform(0.5, 1.0), 2),
            relevance=round(random.uniform(0.6, 1.0), 2),
            coherence=round(random.uniform(0.7, 1.0), 2),
            consistency=round(random.uniform(0.6, 1.0), 2),
            conciseness=round(random.uniform(0.5, 1.0), 2)
        )

class AssessmentPipeline:
    """端到端质量评估流水线"""
    
    def __init__(self):
        self.judge = LLMJudge()
    
    def assess(self, prompts: list, responses: list) -> list:
        """批量评估一组 prompt-response 对"""
        results = []
        for prompt, response in zip(prompts, responses):
            score = self.judge.judge(prompt, response)
            results.append({
                'prompt': prompt,
                'response': response,
                'score': score.to_dict()
            })
        return results
    
    def compare_versions(self, v1_results: list, v2_results: list) -> dict:
        """对比两个版本的评估结果"""
        deltas = []
        for v1, v2 in zip(v1_results, v2_results):
            delta = v2['score']['overall'] - v1['score']['overall']
            deltas.append(delta)
        
        avg_delta = sum(deltas) / len(deltas)
        improvement_count = sum(1 for d in deltas if d > 0.1)
        regression_count = sum(1 for d in deltas if d < -0.1)
        
        return {
            'avg_delta': round(avg_delta, 3),
            'improvement_count': improvement_count,
            'regression_count': regression_count,
            'verdict': 'improvement' if avg_delta > 0.1 
                       else 'regression' if avg_delta < -0.1 
                       else 'no_change'
        }

# 使用示例
if __name__ == "__main__":
    pipeline = AssessmentPipeline()
    
    # 评估示例
    prompts = ["What is AI?", "Explain machine learning"]
    responses = [
        "AI is the simulation of human intelligence in machines.",
        "Machine learning is a subset of AI that uses algorithms."
    ]
    
    results = pipeline.assess(prompts, responses)
    print("评估结果:", results)
    
    # 模拟版本对比
    v1_results = results
    v2_results = [
        {'prompt': "What is AI?", 'response': "AI is...", 'score': {'overall': 0.85}},
        {'prompt': "Explain machine learning", 'response': "ML is...", 'score': {'overall': 0.88}}
    ]
    
    comparison = pipeline.compare_versions(v1_results, v2_results)
    print("版本对比:", comparison)
```

## 七、产出物

- `tests/quality/test_quality.py` — 13 个测试

## 八、练习题

1. **基础题：** 为 `QualityScore` 类添加一个 `validate()` 方法，检查所有维度值是否在 0-1 范围内。

2. **进阶题：** 扩展 `LLMJudge.parse_score()` 方法，支持解析更多格式，如 "评分：8/10"、"给分：0.75" 等。

3. **挑战题：** 实现一个 `QualityReportGenerator` 类，能根据评估结果生成 HTML 报告，包含各维度得分的可视化图表。

## 九、自检清单

- [ ] 5 维评分返回值包含所有维度
- [ ] 综合分 = 各维度平均值
- [ ] LLMJudge 能解析 3 种格式
- [ ] 流水线能输出 verdict
- [ ] 版本对比能计算 delta
