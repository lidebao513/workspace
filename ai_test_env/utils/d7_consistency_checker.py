"""
AI 回复一致性检查器模块

功能：多轮重复提问，分析同一问题的回复一致性（方差）。
覆盖 temperature 从 0 到 2 的各档位一致性表现。

面试话术：
    "一致性测试是我在做 AI 质量评估时发现的重灾区。
    temperature=0 时回复几乎完全一致，temperature=0.8
    时方差大到不可接受。我们根据测试结果把金融场景
    的 temperature 锁定在 0.3 以下，聊天场景用 0.7。
    用数据说话。"
"""
import time
import statistics
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass, field


# 一致性等级
CONSISTENCY_LEVELS = {
    "very_high": {"label": "极高", "range": (0.90, 1.00)},
    "high":      {"label": "高",   "range": (0.75, 0.90)},
    "medium":    {"label": "中等", "range": (0.50, 0.75)},
    "low":       {"label": "低",   "range": (0.25, 0.50)},
    "very_low":  {"label": "极低", "range": (0.00, 0.25)},
}


def get_consistency_level(score: float) -> str:
    """根据一致性分数返回等级标签"""
    for level, info in CONSISTENCY_LEVELS.items():
        low, high = info["range"]
        if low <= score <= high:
            return info["label"]
    return "未知"


@dataclass
class ConsistencyResult:
    """单组一致性测试结果"""
    prompt: str
    temperature: float
    n_runs: int
    responses: List[str] = field(default_factory=list)
    tokens_used: List[int] = field(default_factory=list)
    latencies_ms: List[float] = field(default_factory=list)
    # 以下是动态计算字段
    avg_length: float = 0.0
    length_std: float = 0.0
    length_variance: float = 0.0
    unique_count: int = 0
    unique_ratio: float = 0.0
    consistency_score: float = 0.0
    level: str = ""
    avg_tokens: float = 0.0
    avg_latency_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "prompt": self.prompt[:30],
            "temperature": self.temperature,
            "n_runs": self.n_runs,
            "unique_count": self.unique_count,
            "unique_ratio": round(self.unique_ratio, 2),
            "consistency_score": round(self.consistency_score, 2),
            "level": self.level,
            "avg_length": round(self.avg_length, 1),
            "length_std": round(self.length_std, 2),
            "avg_tokens": round(self.avg_tokens, 1),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
        }


class ConsistencyChecker:
    """
    一致性检查器

    对同一 prompt 在相同参数下跑 N 次，分析回复的变异程度。
    支持离线和在线两种模式：
      - 在线：传入一个 callable（API 调用函数），自动调用 N 次
      - 离线：传入已有的一组回复，直接分析

    用法：
        checker = ConsistencyChecker()
        result = checker.analyze_responses(
            prompt="Python 是什么？",
            responses=["编程语言", "编程语言", "编程语言", "脚本语言"],
            temperature=0.0,
        )
        print(f"一致性评分: {result.consistency_score}")
        print(f"等级: {result.level}")
    """

    def __init__(self):
        self._history: List[Dict] = []

    # ------------------------------------------------------------------
    # 离线分析：直接传回复列表
    # ------------------------------------------------------------------

    def analyze_responses(
        self,
        prompt: str,
        responses: List[str],
        temperature: float = 0.0,
        tokens_used: Optional[List[int]] = None,
        latencies_ms: Optional[List[float]] = None,
    ) -> ConsistencyResult:
        """
        离线分析一组回复的一致性。

        参数：
            prompt:      原始提问
            responses:   N 次回复的内容列表
            temperature: 本次测试的 temperature 值
            tokens_used: 每次消耗的 Token 数（可选）
            latencies_ms: 每次的响应延迟（可选）

        返回：
            ConsistencyResult 对象
        """
        n = len(responses)
        if n < 2:
            raise ValueError(f"至少需要 2 次回复才能分析一致性，当前={n}")

        tokens = tokens_used or [0] * n
        latencies = latencies_ms or [0.0] * n

        # 计算各统计量
        lengths = [len(r) for r in responses]
        avg_len = statistics.mean(lengths)
        len_std = statistics.stdev(lengths) if n >= 2 else 0.0
        len_var = statistics.variance(lengths) if n >= 2 else 0.0

        unique_responses = set(responses)
        unique_count = len(unique_responses)
        unique_ratio = unique_count / n

        # 一致性评分核心计算
        consistency_score = self._compute_consistency(
            n=n,
            unique_count=unique_count,
            responses=responses,
            lengths=lengths,
        )

        result = ConsistencyResult(
            prompt=prompt,
            temperature=temperature,
            n_runs=n,
            responses=responses,
            tokens_used=tokens,
            latencies_ms=latencies,
            avg_length=avg_len,
            length_std=len_std,
            length_variance=len_var,
            unique_count=unique_count,
            unique_ratio=unique_ratio,
            consistency_score=consistency_score,
            level=get_consistency_level(consistency_score),
            avg_tokens=statistics.mean(tokens),
            avg_latency_ms=statistics.mean(latencies),
        )

        self._history.append(result.to_dict())
        return result

    # ------------------------------------------------------------------
    # 在线模式：传一个 API 调用函数
    # ------------------------------------------------------------------

    def run_consistency_test(
        self,
        api_func: Callable[[], Tuple[str, int, float]],
        prompt: str,
        temperature: float,
        n_runs: int = 5,
    ) -> ConsistencyResult:
        """
        在线模式：传入 API 调用函数，自动跑 N 次。

        api_func 签名:
            def my_call() -> Tuple[str, int, float]:
                # 调用 API
                return reply_text, total_tokens, latency_ms

        返回：
            ConsistencyResult 对象
        """
        responses = []
        tokens = []
        latencies = []

        print(f"  开始一致性测试: temperature={temperature}, n={n_runs}")
        for i in range(n_runs):
            try:
                text, t, l = api_func()
                responses.append(text)
                tokens.append(t)
                latencies.append(l)
                print(f"    第 {i+1}/{n_runs} 次: {len(text)} 字, {t} tokens, {l:.0f}ms")
            except Exception as e:
                print(f"    第 {i+1}/{n_runs} 次失败: {e}")
                continue

        if len(responses) < 2:
            raise RuntimeError(f"成功率太低，只获取了 {len(responses)} 次有效回复")

        return self.analyze_responses(
            prompt=prompt,
            responses=responses,
            temperature=temperature,
            tokens_used=tokens,
            latencies_ms=latencies,
        )

    # ------------------------------------------------------------------
    # 温度曲线测试
    # ------------------------------------------------------------------

    def temperature_curve(
        self,
        api_func: Callable,
        prompt: str,
        temperatures: List[float],
        n_per_temp: int = 5,
    ) -> List[ConsistencyResult]:
        """
        在不同 temperature 下各跑 N 次，观察一致性变化曲线。

        返回：
            每个 temperature 的 ConsistencyResult 列表
        """
        results = []
        for t in temperatures:
            r = self.run_consistency_test(
                api_func=api_func,
                prompt=prompt,
                temperature=t,
                n_runs=n_per_temp,
            )
            results.append(r)
        return results

    # ------------------------------------------------------------------
    # 统计接口
    # ------------------------------------------------------------------

    def history(self) -> List[Dict]:
        return list(self._history)

    def reset(self):
        self._history = []

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _compute_consistency(
        self,
        n: int,
        unique_count: int,
        responses: List[str],
        lengths: List[int],
    ) -> float:
        """
        一致性评分计算（0.0 - 1.0）

        算法三要素：
        1. 唯一性比例：unique_count / n（越低越一致）
        2. 长度变异系数：std / mean（CV 越小越一致）
        3. 编辑距离：平均两两之间的差异（扩展版用）

        简化版只用了前两个要素：
        score = (1 - unique_ratio) × 0.5 + (1 - cv) × 0.5

        其中 cv = length_std / avg_length（变异系数）
        """
        unique_ratio = unique_count / n
        avg_len = statistics.mean(lengths) if lengths else 1
        len_std = statistics.stdev(lengths) if n >= 2 else 0.0
        cv = len_std / avg_len if avg_len > 0 else 1.0  # 变异系数

        # unique_ratio: 0.0（全相同）= 满分，1.0（全不同）= 0 分
        uniqueness_score = 1.0 - unique_ratio
        # cv: 0.0（长度完全一致）= 满分，1.0+ ≈ 0 分
        cv_score = max(0.0, 1.0 - min(cv, 1.0))

        score = uniqueness_score * 0.6 + cv_score * 0.4
        return round(score, 2)

    def compare_consistency(
        self,
        results: List[ConsistencyResult],
    ) -> Dict:
        """
        比较多个温度设置下的一致性表现。
        results 来自 temperature_curve() 的输出。
        """
        if not results:
            return {}

        temp_scores = []
        for r in results:
            temp_scores.append({
                "temperature": r.temperature,
                "score": r.consistency_score,
                "level": r.level,
                "unique_ratio": r.unique_ratio,
            })

        # 找出最佳温度
        best = max(temp_scores, key=lambda x: x["score"])

        return {
            "curve": temp_scores,
            "best_temperature": best["temperature"],
            "best_score": best["score"],
            "recommendation": self._recommend_temperature(temp_scores),
        }

    def _recommend_temperature(self, curve: List[Dict]) -> str:
        """根据温度曲线给出建议"""
        if not curve:
            return "数据不足，无法建议"

        # 找出转折点（分数开始明显下降的温度）
        curve_sorted = sorted(curve, key=lambda x: x["temperature"])
        drop_point = None
        for i in range(1, len(curve_sorted)):
            drop = curve_sorted[i - 1]["score"] - curve_sorted[i]["score"]
            if drop > 0.15:
                drop_point = curve_sorted[i]["temperature"]
                break

        if drop_point is not None:
            return f"推荐 temperature ≤ {drop_point:.1f}，超过后一致性明显下降"
        else:
            return f"所有温度的一致性相对稳定，可根据业务需求选择"
