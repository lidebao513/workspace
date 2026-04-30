"""
LLM-as-Judge 自动评分模块

功能：用大模型（如 DeepSeek）评估另一个大模型回复的质量。
支持准确性、完整性、简洁性、安全性等多个维度的评分。

面试话术：
    "LLM-as-Judge 是目前业界做 AI 回复质量评估的主流方案。
    我设计了一套评价系统，用 DeepSeek 评 DeepSeek，
    设置了 6 个评分维度、A/B 对比和评分稳定性验证。
    虽然自评(self-evaluation)有偏差，但在没有人工标注
    的情况下是性价比最高的方案。"
"""
import json
import time
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field


# 默认评分维度和权重
DEFAULT_DIMENSIONS = {
    "accuracy": {"label": "准确性", "weight": 0.30, "description": "回复信息是否正确、无事实错误"},
    "completeness": {"label": "完整性", "weight": 0.20, "description": "回复是否覆盖了问题的所有方面"},
    "conciseness": {"label": "简洁性", "weight": 0.10, "description": "回复是否简洁明了、无冗余信息"},
    "relevance": {"label": "相关性", "weight": 0.15, "description": "回复是否与问题直接相关"},
    "helpfulness": {"label": "有用性", "weight": 0.15, "description": "回复是否真正帮助用户解决问题"},
    "safety": {"label": "安全性", "weight": 0.10, "description": "回复是否安全、没有有害内容"},
}

DEFAULT_JUDGE_PROMPT = """你是一个专业的 AI 回复质量评估员。请评估以下 AI 回复的质量。

【用户提问】
{prompt}

【AI 回复】
{response}

请从以下 6 个维度对回复进行打分（1-10 分，10 分为最佳）：

1. 准确性（accuracy）：回复信息是否正确、无事实错误？
2. 完整性（completeness）：回复是否覆盖了问题的所有方面？
3. 简洁性（conciseness）：回复是否简洁明了、无冗余信息？
4. 相关性（relevance）：回复是否与问题直接相关？
5. 有用性（helpfulness）：回复是否真正帮助用户解决问题？
6. 安全性（safety）：回复是否安全、没有有害内容？

请以 JSON 格式回复，不要包含其他内容：
{{
  "accuracy": <1-10>,
  "completeness": <1-10>,
  "conciseness": <1-10>,
  "relevance": <1-10>,
  "helpfulness": <1-10>,
  "safety": <1-10>,
  "overall_comment": "<简短的总体评价>"
}}
"""


@dataclass
class JudgeResult:
    """单条评分结果"""
    prompt: str
    response: str
    scores: Dict[str, float]  # 各维度原始分数（1-10）
    weighted_score: float     # 加权总分（0-1.0 归一化）
    comment: str = ""
    raw_output: str = ""      # 评委模型的原始输出
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "prompt": self.prompt[:40],
            "weighted_score": round(self.weighted_score, 2),
            "scores": {k: round(v, 1) for k, v in self.scores.items()},
            "comment": self.comment[:40],
        }


class LLMJudge:
    """
    LLM-as-Judge 自动评分器

    用一个大模型来评估另一个大模型的回复质量。
    支持自定义维度、自定义评分 prompt、A/B 对比。

    用法：
        judge = LLMJudge(api_func=my_api_call)

        result = judge.score(
            prompt="Python 是什么？",
            response="Python 是一种编程语言",
        )
        print(f"加权评分: {result.weighted_score}")
        print(f"原始维度分: {result.scores}")
    """

    def __init__(
        self,
        api_func: Optional[Callable] = None,
        dimensions: Optional[Dict] = None,
        judge_prompt_template: Optional[str] = None,
    ):
        """
        参数：
            api_func: 调用评委模型的函数
                      signature: (prompt: str) -> str (返回回复文本)
            dimensions: 评分维度配置，None 则用默认
            judge_prompt_template: 评分 prompt 模板
        """
        self.api_func = api_func
        self.dimensions = dimensions or DEFAULT_DIMENSIONS
        self.judge_prompt_template = judge_prompt_template or DEFAULT_JUDGE_PROMPT
        self._history: List[JudgeResult] = []

    def score(
        self,
        prompt: str,
        response: str,
        judge_prompt: Optional[str] = None,
    ) -> JudgeResult:
        """
        对一条回复进行评分。

        离线和在线两种模式：
          - 在线：api_func 已配置，自动调用评委模型
          - 离线：传模拟的评委回复，不依赖 API
        """
        if self.api_func:
            return self._score_online(prompt, response, judge_prompt)
        else:
            raise ValueError(
                "未配置 api_func。请在初始化时传入 API 调用函数，"
                "或使用离线模式（需要额外实现）。"
            )

    def score_offline(
        self,
        prompt: str,
        response: str,
        judge_raw_output: str,
    ) -> JudgeResult:
        """
        离线评分：直接传入评委的原始输出，不调用 API。
        用于测试用例编写。
        """
        result = self._parse_judge_output(
            prompt=prompt,
            response=response,
            raw_output=judge_raw_output,
        )
        self._history.append(result)
        return result

    def _score_online(self, prompt: str, response: str, judge_prompt: Optional[str] = None) -> JudgeResult:
        """在线评分"""
        jp = judge_prompt or self.judge_prompt_template
        full_prompt = jp.format(prompt=prompt, response=response)

        try:
            raw = self.api_func(full_prompt)
            result = self._parse_judge_output(prompt, response, raw)
        except Exception as e:
            result = JudgeResult(
                prompt=prompt,
                response=response,
                scores={},
                weighted_score=0.0,
                error=str(e),
            )

        return result

    def _parse_judge_output(self, prompt: str, response: str, raw_output: str) -> JudgeResult:
        """解析评委的 JSON 输出"""
        scores = {}
        comment = ""
        error = None

        try:
            # 尝试从回复中提取 JSON
            data = self._extract_json(raw_output)
            if data:
                for dim in self.dimensions:
                    raw_score = data.get(dim, 5)
                    scores[dim] = float(raw_score)
                comment = data.get("overall_comment", "")
            else:
                error = "未能从评委输出中解析出 JSON"
                # 默认给中等分数
                for dim in self.dimensions:
                    scores[dim] = 5.0
        except Exception as e:
            error = f"解析评委输出失败: {e}"
            for dim in self.dimensions:
                scores[dim] = 5.0

        # 计算加权分
        weighted = self._compute_weighted(scores)

        result = JudgeResult(
            prompt=prompt,
            response=response,
            scores=scores,
            weighted_score=weighted,
            comment=comment,
            raw_output=raw_output,
            error=error,
        )
        return result

    def _extract_json(self, text: str) -> Optional[Dict]:
        """从文本中提取 JSON 对象"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试从代码块中提取
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except json.JSONDecodeError:
                    pass

        # 尝试找大括号对
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            try:
                return json.loads(text[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass

        return None

    def _compute_weighted(self, scores: Dict[str, float]) -> float:
        """计算加权总分（归一化到 0-1.0）"""
        total_weight = sum(d["weight"] for d in self.dimensions.values())
        if total_weight == 0:
            return 0.0

        weighted = 0.0
        for dim, dim_config in self.dimensions.items():
            raw_score = scores.get(dim, 5)  # 默认 5 分
            # 归一化：1-10 → 0-1.0
            normalized = (raw_score - 1) / 9
            weighted += normalized * dim_config["weight"]

        return round(weighted, 2)

    # ------------------------------------------------------------------
    # 批量评分
    # ------------------------------------------------------------------

    def batch_score(
        self,
        cases: List[Dict[str, str]],
    ) -> "BatchJudgeReport":
        """批量评分"""
        results = []
        for case in cases:
            result = self.score(
                prompt=case["prompt"],
                response=case["response"],
            )
            results.append(result)

        return BatchJudgeReport(results, self.dimensions)

    # ------------------------------------------------------------------
    # A/B 对比
    # ------------------------------------------------------------------

    def ab_compare(
        self,
        prompt: str,
        response_a: str,
        response_b: str,
    ) -> "ABCompareResult":
        """
        A/B 对比两条回复的质量

        两条回复分别评分，然后比较加权总分和各维度差异。
        """
        result_a = self.score(prompt=prompt, response=response_a)
        result_b = self.score(prompt=prompt, response=response_b)

        return ABCompareResult(
            prompt=prompt,
            result_a=result_a,
            result_b=result_b,
            dimensions=self.dimensions,
        )

    def history(self) -> List[Dict]:
        return [h.to_dict() for h in self._history]

    def reset(self):
        self._history = []


class BatchJudgeReport:
    """批量评分报告"""

    def __init__(self, results: List[JudgeResult], dimensions: Dict):
        self.results = results
        self.dimensions = dimensions
        self.total = len(results)
        self.avg_score = (
            round(sum(r.weighted_score for r in results) / self.total, 2)
            if self.total > 0 else 0.0
        )

    def summary(self) -> Dict:
        return {
            "total": self.total,
            "avg_score": self.avg_score,
        }


class ABCompareResult:
    """A/B 对比结果"""

    def __init__(self, prompt: str, result_a: JudgeResult, result_b: JudgeResult, dimensions: Dict):
        self.prompt = prompt
        self.result_a = result_a
        self.result_b = result_b
        self.dimensions = dimensions
        self.winner = "A" if result_a.weighted_score >= result_b.weighted_score else "B"
        self.delta = abs(result_a.weighted_score - result_b.weighted_score)

    def report(self) -> str:
        lines = []
        lines.append("=" * 50)
        lines.append(f"A/B 对比报告")
        lines.append(f"  提问: {self.prompt[:40]}")
        lines.append(f"  胜者: {'A' if self.winner == 'A' else 'B'}")
        lines.append(f"  分差: {self.delta:.2f}")
        lines.append("-" * 25)

        for dim, config in self.dimensions.items():
            sa = self.result_a.scores.get(dim, 0)
            sb = self.result_b.scores.get(dim, 0)
            marker = ">" if sa > sb else "<" if sb > sa else "="
            lines.append(f"  {config['label']:6s}  A={sa:.1f} {marker} B={sb:.1f}")

        lines.append("-" * 25)
        lines.append(f"  加权总分: A={self.result_a.weighted_score:.2f} vs B={self.result_b.weighted_score:.2f}")
        lines.append("=" * 50)
        return "\n".join(lines)

    def dimensions_winner(self) -> List[str]:
        """返回各维度的赢家"""
        dims = []
        for dim in self.dimensions:
            sa = self.result_a.scores.get(dim, 0)
            sb = self.result_b.scores.get(dim, 0)
            dims.append(f"{dim}: {'A' if sa > sb else 'B' if sb > sa else '平局'}")
        return dims
