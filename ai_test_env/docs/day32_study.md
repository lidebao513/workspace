# Day 32 — 质量评估实战

## 学习目标

1. 理解"调用日志回放"的管道模式
2. 掌握 QualityChecker 不同 prompt 设定不同关键词检查
3. 理解 LLMJudge 的离线评分逻辑
4. 学会 SchemaValidator 对代码回复的 JSON 结构验证

---

## 一、今日目标

> 把 D31 真实 API 调用的结果，送入 d6 QualityChecker、d9 LLMJudge、d10 SchemaValidator 做多维质量评估。输出综合质量报告。

- 理解"调用日志回放"的管道模式
- 掌握 QualityChecker 不同 prompt 设定不同关键词检查
- 理解 LLMJudge 的离线评分逻辑
- 学会 SchemaValidator 对代码回复的 JSON 结构验证

---

## 二、管道架构

```
D31 API 调用日志 (run_logs/d31_api_*.json)
  │
  ├── QualityChecker.check()
  │     └── 根据 prompt_label 设定 expected_keywords / forbidden_keywords
  │
  ├── LLMJudge.score_offline()
  │     └── 基于回复长度和词汇多样性打分
  │
  └── SchemaValidator.validate_json_string()
        └── 只对 code_generation 类型的回复做 JSON 校验
  │
  └── 输出: d32_eval_*.json（综合评估报告）
```

---

## 三、QualityChecker 关键词策略

每个 prompt 类型有不同检查标准：

| Label | 期望关键词 | 检查目的 |
|-------|-----------|---------|
| cn_basic | 人工智能, AI, 计算机 | 确保讨论了定义 |
| en_basic | machine learning, data, algorithm | 英文关键词检查 |
| jp_basic | 人工知能, AI | 日语回复检查 |
| code_generation | binary_search, def | 代码必备元素 |
| role_constraint | 导数, 数学 | 数学老师角色保持 |
| multi_turn | 张三 | 上下文记忆检查 |

---

## 四、LLMJudge 离线评分

离线模式不调用真实 API，而是基于回复的**表层特征**估算分数：

```python
relevance    = min(10, len(reply) // 20)       # 回复越长→越相关
completeness = min(10, len(set(reply.split())) // 5)  # 词汇越多→越完整
fluency      = 8.0                              # 默认流畅
weighted     = rel*0.4 + comp*0.3 + fluency*0.3
```

> 实际使用时用 `score_online()` 调用 DeepSeek API 做评委，效果更准确。

---

## 五、SchemaValidator 代码验证

只对 `code_generation` 类型验证：

```python
schema = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "code": {"type": "string"},
    },
    "required": ["content"],
}
```

如果回复不是合法 JSON，标记为 invalid。

---

## 六、测试要点

| 场景 | 测试 | 预期 |
|------|------|------|
| QualityChecker 中文 | 含"人工智能" | passed=True |
| QualityChecker 未知 label | 无关键词要求 | passed=True |
| LLMJudge 中文 | 任意回复 | 返回 overall/relevance/completeness |
| Schema 跳过 | 非代码类型 | checked=False |
| Schema 代码 | 合法 JSON | checked=True |
| 日志加载空目录 | 无日志 | 空列表 |

---

## 面试题

### 题目 1：如何设计多维度的 LLM 输出质量评估系统？

**参考答案：**

**质量评估的核心价值：**

LLM 输出质量不能只靠单一指标判断，需要多维度综合评估：
- **正确性** - 回复是否符合事实
- **相关性** - 回复是否切题
- **完整性** - 回复是否涵盖所有要点
- **格式正确性** - JSON/代码等结构化输出是否合法

**多维度评估框架：**

```python
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from enum import Enum


class QualityDimension(Enum):
    CORRECTNESS = "correctness"
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    FORMAT = "format"


@dataclass
class QualityScore:
    """质量评分"""
    dimension: QualityDimension
    score: float
    details: str


@dataclass
class QualityReport:
    """综合质量报告"""
    overall_score: float
    dimension_scores: List[QualityScore]
    passed: bool
    issues: List[str]


class QualityChecker:
    """质量检查器"""

    KEYWORD_CONFIGS = {
        "cn_basic": {
            "expected": {"人工智能", "AI", "计算机"},
            "forbidden": set()
        },
        "en_basic": {
            "expected": {"machine learning", "data", "algorithm"},
            "forbidden": set()
        },
        "code_generation": {
            "expected": set(),
            "forbidden": {"error", "bug", "wrong"}
        }
    }

    def check(self, prompt_label: str, response: str) -> bool:
        """检查回复质量"""
        config = self.KEYWORD_CONFIGS.get(prompt_label)
        if not config:
            return True

        response_lower = response.lower()

        for keyword in config["expected"]:
            if keyword.lower() not in response_lower:
                return False

        for keyword in config["forbidden"]:
            if keyword.lower() in response_lower:
                return False

        return True


class LLMJudge:
    """LLM 质量评判器（离线）"""

    def __init__(self):
        self.min_response_length = 10
        self.max_response_length = 10000

    def score_offline(self, response: str) -> Dict[str, float]:
        """离线评分"""
        length_score = self._score_length(response)
        diversity_score = self._score_diversity(response)

        overall = 0.6 * length_score + 0.4 * diversity_score

        return {
            "overall": overall,
            "relevance": length_score,
            "completeness": diversity_score
        }

    def _score_length(self, response: str) -> float:
        """长度评分"""
        length = len(response)
        if length < self.min_response_length:
            return 0.0
        if length > self.max_response_length:
            return 0.5
        return min(1.0, length / 500)

    def _score_diversity(self, response: str) -> float:
        """词汇多样性评分"""
        words = response.lower().split()
        if not words:
            return 0.0
        unique_words = set(words)
        diversity = len(unique_words) / len(words)
        return diversity


class SchemaValidator:
    """JSON Schema 验证器"""

    def validate_json_string(self, response: str) -> bool:
        """验证 JSON 字符串格式"""
        import json
        try:
            json.loads(response)
            return True
        except (json.JSONDecodeError, ValueError):
            return False

    def validate_structure(self, response: str, required_keys: Set[str]) -> Dict[str, bool]:
        """验证 JSON 结构"""
        import json
        try:
            data = json.loads(response)
            return {key: key in data for key in required_keys}
        except (json.JSONDecodeError, ValueError):
            return {key: False for key in required_keys}
```

---

### 题目 2：如何在离线环境下评估 LLM 输出质量？

**参考答案：**

**离线评估的局限性：**

真正的 LLM 质量评估需要：
- 人工标注数据
- reference 回复对比
- 语义相似度模型

离线评估只能做基础检查：

```python
class OfflineEvaluator:
    """离线评估器"""

    def __init__(self):
        self.quality_checker = QualityChecker()
        self.llm_judge = LLMJudge()
        self.schema_validator = SchemaValidator()

    def evaluate(
        self,
        prompt_label: str,
        response: str,
        check_json: bool = False
    ) -> QualityReport:
        """综合评估"""
        issues = []

        keyword_pass = self.quality_checker.check(prompt_label, response)
        if not keyword_pass:
            issues.append("Keyword check failed")

        scores = self.llm_judge.score_offline(response)
        if scores["overall"] < 0.3:
            issues.append("Overall quality too low")

        json_valid = True
        if check_json:
            json_valid = self.schema_validator.validate_json_string(response)
            if not json_valid:
                issues.append("Invalid JSON format")

        overall_score = scores["overall"]
        if not json_valid:
            overall_score *= 0.5
        if not keyword_pass:
            overall_score *= 0.7

        return QualityReport(
            overall_score=overall_score,
            dimension_scores=[
                QualityScore(QualityDimension.CORRECTNESS, 1.0 if keyword_pass else 0.0, ""),
                QualityScore(QualityDimension.RELEVANCE, scores["relevance"], ""),
                QualityScore(QualityDimension.COMPLETENESS, scores["completeness"], ""),
                QualityScore(QualityDimension.FORMAT, 1.0 if json_valid else 0.0, ""),
            ],
            passed=len(issues) == 0,
            issues=issues
        )

    def batch_evaluate(self, items: List[Dict]) -> List[QualityReport]:
        """批量评估"""
        return [
            self.evaluate(
                item.get("label", ""),
                item.get("response", ""),
                item.get("check_json", False)
            )
            for item in items
        ]
```

---

## 代码示例

```python
"""
Day 32 代码示例：质量评估实战完整实现
演示多维度质量评估管道
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Set


class QualityChecker:
    KEYWORD_CONFIGS = {
        "cn_basic": {"expected": {"人工智能", "AI", "计算机"}, "forbidden": set()},
        "en_basic": {"expected": {"machine learning", "data"}, "forbidden": set()},
        "code_generation": {"expected": set(), "forbidden": {"error", "bug"}},
    }

    def check(self, prompt_label: str, response: str) -> bool:
        config = self.KEYWORD_CONFIGS.get(prompt_label)
        if not config:
            return True
        response_lower = response.lower()
        for kw in config["expected"]:
            if kw.lower() not in response_lower:
                return False
        for kw in config["forbidden"]:
            if kw.lower() in response_lower:
                return False
        return True


class LLMJudge:
    def score_offline(self, response: str) -> Dict[str, float]:
        length = len(response)
        length_score = min(1.0, length / 500) if length >= 10 else 0.0
        words = response.lower().split()
        diversity = len(set(words)) / len(words) if words else 0.0
        return {
            "overall": 0.6 * length_score + 0.4 * diversity,
            "relevance": length_score,
            "completeness": diversity
        }


class SchemaValidator:
    def validate_json_string(self, response: str) -> bool:
        import json
        try:
            json.loads(response)
            return True
        except Exception:
            return False


class QualityEvaluator:
    def __init__(self):
        self.checker = QualityChecker()
        self.judge = LLMJudge()
        self.validator = SchemaValidator()

    def evaluate(self, label: str, response: str, check_json: bool = False) -> Dict:
        keyword_pass = self.checker.check(label, response)
        scores = self.judge.score_offline(response)
        json_valid = self.validator.validate_json_string(response) if check_json else True

        overall = scores["overall"]
        if not json_valid:
            overall *= 0.5
        if not keyword_pass:
            overall *= 0.7

        return {
            "passed": keyword_pass and json_valid and scores["overall"] >= 0.3,
            "overall_score": overall,
            "keyword_check": keyword_pass,
            "json_valid": json_valid,
            "scores": scores
        }


def demo():
    print("=" * 60)
    print("Day 32 代码示例：质量评估实战演示")
    print("=" * 60)

    evaluator = QualityEvaluator()

    test_cases = [
        {"label": "cn_basic", "response": "人工智能是计算机科学的一个重要分支。"},
        {"label": "en_basic", "response": "Machine learning is a method of data analysis."},
        {"label": "code_generation", "response": '{"result": "success"}'},
    ]

    print("\n[1] 质量评估结果")
    print("-" * 40)
    for case in test_cases:
        result = evaluator.evaluate(case["label"], case["response"])
        status = "✓" if result["passed"] else "✗"
        print(f"  {status} {case['label']}: score={result['overall_score']:.2f}")

    print("\n[2] 评估维度说明")
    print("-" * 40)
    print("  keyword_check: 回复是否包含期望关键词")
    print("  json_valid: JSON 格式是否合法")
    print("  overall_score: 综合质量评分")

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
```

---

## 练习题

### 练习 1：实现多语言质量评估

**要求：**
扩展质量检查器，支持对中英文回复分别进行质量评估。

**提示：**
```python
class MultilingualQualityChecker:
    """多语言质量检查器"""
    def check_chinese(self, response: str) -> bool:
        """检查中文回复"""
        pass

    def check_english(self, response: str) -> bool:
        """检查英文回复"""
        pass
```

**验收标准：**
- 正确识别回复语言
- 根据语言选择对应的检查策略
- 返回统一的检查结果格式

---

### 练习 2：实现质量趋势分析

**要求：**
基于历史评估记录，分析质量趋势（上升/下降/稳定）。

**提示：**
```python
class QualityTrendAnalyzer:
    """质量趋势分析器"""
    def __init__(self):
        self._history: List[Dict] = []

    def record(self, score: float) -> None:
        """记录评估分数"""
        pass

    def analyze(self) -> str:
        """分析趋势"""
        pass
```

**验收标准：**
- 记录历史分数
- 计算移动平均
- 判断趋势方向

---

### 练习 3：实现质量报告生成器

**要求：**
生成格式化的质量评估报告（支持 JSON 和 Markdown 格式）。

**提示：**
```python
class QualityReportGenerator:
    """质量报告生成器"""
    def to_json(self, report: Dict) -> str:
        pass

    def to_markdown(self, report: Dict) -> str:
        pass
```

**验收标准：**
- 生成格式化的 JSON 报告
- 生成 Markdown 表格报告
- 包含统计摘要

---

## 七、产出物

| 文件 | 说明 | 状态 |
|------|------|------|
| `utils/d32_quality_eval.py` | 质量评估实战 | [OK] |
| `tests/d32_test_quality_eval.py` | 9 个测试 | [OK] 9/9 PASS |
| `day32_study.md` | 本文档 | [OK] |
