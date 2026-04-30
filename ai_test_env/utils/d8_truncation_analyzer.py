"""
AI 回复截断检测与分析模块

功能：分析 API 响应的 finish_reason，区分 stop / length / content_filter，
统计截断率，计算最佳 max_tokens，给出 Token 费用建议。

面试话术：
    "我发现生产环境 30% 的请求被截断了，其中大部分是
    max_tokens 设得太低。通过截断率曲线分析，把常用
    场景的 max_tokens 从 512 调到 1024，截断率从 30%
    降到 2%，用户体验明显改善。"
"""
import statistics
from typing import List, Dict, Optional
from enum import Enum


class FinishReason(str, Enum):
    STOP = "stop"               # 正常结束
    LENGTH = "length"           # 达到 max_tokens 被截断
    CONTENT_FILTER = "content_filter"  # 被内容过滤器截断
    NULL = "null"               # 未指定


# 截断等级（基于截断率）
TRUNCATION_LEVELS = {
    "excellent": {"label": "优秀", "range": (0.0, 0.0199), "action": "无需优化"},
    "good":      {"label": "良好", "range": (0.02, 0.0499), "action": "边缘，可观察"},
    "fair":      {"label": "一般", "range": (0.05, 0.0999), "action": "建议优化 max_tokens"},
    "poor":      {"label": "差",   "range": (0.10, 0.1999), "action": "必须优化 max_tokens"},
    "critical":  {"label": "严重", "range": (0.20, 1.000), "action": "立即调整 max_tokens"},
}


def get_truncation_level(rate: float) -> Dict:
    """根据截断率返回等级描述"""
    for level, info in TRUNCATION_LEVELS.items():
        low, high = info["range"]
        if low <= rate <= high:
            return {"level": level, "label": info["label"], "action": info["action"]}
    return {"level": "unknown", "label": "未知", "action": ""}


class TruncationAnalyzer:
    """
    截断分析器

    分析一组 API 响应的 finish_reason 分布，计算截断率，
    根据截断率给出 max_tokens 调整建议。

    用法：
        analyzer = TruncationAnalyzer()
        result = analyzer.analyze([
            {"prompt": "写首诗", "response_len": 500, "finish_reason": "stop",
             "max_tokens": 1024, "total_tokens": 550},
            {"prompt": "写长文", "response_len": 1024, "finish_reason": "length",
             "max_tokens": 1024, "total_tokens": 1070},
        ])
        print(result.report())
    """

    def __init__(self):
        self._records: List[Dict] = []

    # ------------------------------------------------------------------
    # 分析接口
    # ------------------------------------------------------------------

    def record(
        self,
        prompt: str,
        response_len: int,
        finish_reason: str,
        max_tokens: int,
        total_tokens: int,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> Dict:
        """
        记录一次 API 调用的截断信息

        参数：
            prompt:           提问内容（仅记录）
            response_len:     回复字符长度
            finish_reason:    "stop" / "length" / "content_filter"
            max_tokens:       本次调用的 max_tokens 设置
            total_tokens:     总 Token 消耗
            prompt_tokens:    输入 Token（可选）
            completion_tokens: 输出 Token（可选）
        """
        is_truncated = finish_reason in ("length", "content_filter")
        record = {
            "prompt": prompt[:30],
            "response_len": response_len,
            "finish_reason": finish_reason,
            "max_tokens": max_tokens,
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "is_truncated": is_truncated,
        }
        self._records.append(record)
        return record

    def record_batch(self, records: List[Dict]) -> None:
        """批量记录"""
        for r in records:
            self.record(
                prompt=r.get("prompt", ""),
                response_len=r.get("response_len", 0),
                finish_reason=r.get("finish_reason", "stop"),
                max_tokens=r.get("max_tokens", 1024),
                total_tokens=r.get("total_tokens", 0),
                prompt_tokens=r.get("prompt_tokens", 0),
                completion_tokens=r.get("completion_tokens", 0),
            )

    # ------------------------------------------------------------------
    # 分析计算
    # ------------------------------------------------------------------

    def analyze(self, records: Optional[List[Dict]] = None) -> "TruncationReport":
        """
        分析截断情况

        参数：
            records: 可选，传 None 则用历史记录

        返回：
            TruncationReport 对象
        """
        data = records if records is not None else self._records
        if not data:
            raise ValueError("没有数据可供分析")

        total = len(data)
        truncated = sum(1 for r in data if r["is_truncated"])
        stop_count = sum(1 for r in data if r["finish_reason"] == "stop")
        length_count = sum(1 for r in data if r["finish_reason"] == "length")
        filter_count = sum(1 for r in data if r["finish_reason"] == "content_filter")

        truncation_rate = truncated / total if total > 0 else 0.0

        # 未截断的回复长度分布（用于推荐 max_tokens）
        full_responses = [r["response_len"] for r in data if r["finish_reason"] == "stop"]
        truncated_lengths = [r["response_len"] for r in data if r["finish_reason"] == "length"]

        # 平均回复长度
        all_lengths = [r["response_len"] for r in data]
        avg_response_len = statistics.mean(all_lengths) if all_lengths else 0
        max_response_len = max(all_lengths) if all_lengths else 0

        # 完整回复的平均长度（未截断的）
        avg_full_len = statistics.mean(full_responses) if full_responses else 0
        max_full_len = max(full_responses) if full_responses else 0

        # 被截断的回复长度
        avg_truncated_len = statistics.mean(truncated_lengths) if truncated_lengths else 0

        # Token 实际消耗统计
        all_tokens = [r["total_tokens"] for r in data]
        avg_tokens = statistics.mean(all_tokens) if all_tokens else 0
        max_tokens = max(all_tokens) if all_tokens else 0

        # 推荐的 max_tokens 建议
        recommendation = self._recommend_max_tokens(
            truncation_rate=truncation_rate,
            max_full_len=max_full_len,
            avg_full_len=avg_full_len,
            max_tokens_configs=[r["max_tokens"] for r in data],
        )

        level_info = get_truncation_level(truncation_rate)

        report = TruncationReport(
            total=total,
            truncated=truncated,
            stop_count=stop_count,
            length_count=length_count,
            filter_count=filter_count,
            truncation_rate=truncation_rate,
            avg_response_len=avg_response_len,
            max_response_len=max_response_len,
            avg_full_len=avg_full_len,
            max_full_len=max_full_len,
            avg_truncated_len=avg_truncated_len,
            avg_tokens=avg_tokens,
            max_tokens_used=max_tokens,
            level_info=level_info,
            recommendation=recommendation,
        )

        return report

    def _recommend_max_tokens(
        self,
        truncation_rate: float,
        max_full_len: float,
        avg_full_len: float,
        max_tokens_configs: List[int],
    ) -> Dict:
        """
        根据截断分析和回复长度给出推荐的 max_tokens

        算法：
        1. 如果截断率 < 2%，保持当前配置
        2. 如果有截断，取"完整回复最大长度 × 1.2"作为推荐
        3. 如果连续多档 max_tokens 都截断，推荐增加 50%
        """
        current_max = statistics.mean(max_tokens_configs) if max_tokens_configs else 1024

        if truncation_rate < 0.02:
            return {
                "current": int(current_max),
                "recommended": int(current_max),
                "reason": "截断率低，无需调整",
                "urgency": "none",
            }

        # 推荐使用完整回复最大长度的 1.2 倍
        suggested = int(max_full_len * 1.2)

        # 但不超过当前配置的 4 倍（防止过度推荐）
        suggested = min(suggested, int(current_max * 4))
        # 也不小于当前配置（建议只增不减）
        suggested = max(suggested, int(current_max))

        urgency = "critical" if truncation_rate >= 0.20 else \
                  "high" if truncation_rate >= 0.10 else \
                  "medium" if truncation_rate >= 0.05 else "low"

        return {
            "current": int(current_max),
            "recommended": int(suggested),
            "reason": f"截断率={truncation_rate:.1%}，"
                      f"建议从 {int(current_max)} 调到 {int(suggested)}",
            "urgency": urgency,
        }

    # ------------------------------------------------------------------
    # 高级分析
    # ------------------------------------------------------------------

    def max_tokens_curve(self) -> List[Dict]:
        """
        按 max_tokens 档次分组统计截断率

        返回每条记录按 max_tokens 档次聚合的截断率。
        用于绘制"截断率 - max_tokens"曲线图。
        """
        from collections import defaultdict
        groups = defaultdict(lambda: {"total": 0, "truncated": 0})

        for r in self._records:
            mt = r["max_tokens"]
            groups[mt]["total"] += 1
            if r["is_truncated"]:
                groups[mt]["truncated"] += 1

        curve = []
        for mt in sorted(groups.keys()):
            g = groups[mt]
            rate = g["truncated"] / g["total"] if g["total"] > 0 else 0
            curve.append({
                "max_tokens": mt,
                "total": g["total"],
                "truncated": g["truncated"],
                "rate": round(rate, 4),
            })
        return curve

    def reset(self):
        self._records = []

    @property
    def total_records(self) -> int:
        return len(self._records)


class TruncationReport:
    """截断分析报告"""

    def __init__(self, **kwargs):
        self.total = kwargs["total"]
        self.truncated = kwargs["truncated"]
        self.stop_count = kwargs["stop_count"]
        self.length_count = kwargs["length_count"]
        self.filter_count = kwargs["filter_count"]
        self.truncation_rate = kwargs["truncation_rate"]
        self.avg_response_len = kwargs["avg_response_len"]
        self.max_response_len = kwargs["max_response_len"]
        self.avg_full_len = kwargs["avg_full_len"]
        self.max_full_len = kwargs["max_full_len"]
        self.avg_truncated_len = kwargs["avg_truncated_len"]
        self.avg_tokens = kwargs["avg_tokens"]
        self.max_tokens_used = kwargs["max_tokens_used"]
        self.level_info = kwargs["level_info"]
        self.recommendation = kwargs["recommendation"]

    def to_dict(self) -> Dict:
        return {
            "total": self.total,
            "truncated": self.truncated,
            "truncation_rate": round(self.truncation_rate, 4),
            "level": self.level_info["label"],
            "avg_response_len": round(self.avg_response_len, 1),
            "max_response_len": int(self.max_response_len),
            "avg_full_len": round(self.avg_full_len, 1),
            "avg_truncated_len": round(self.avg_truncated_len, 1),
            "recommended_max_tokens": self.recommendation["recommended"],
            "urgency": self.recommendation["urgency"],
        }

    def report(self) -> str:
        """生成可读报告"""
        lines = []
        lines.append("=" * 50)
        lines.append("截断分析报告")
        lines.append("-" * 50)
        lines.append(f"  总请求数:     {self.total}")
        lines.append(f"  截断数:       {self.truncated}")
        lines.append(f"  截断率:       {self.truncation_rate:.1%}")
        lines.append(f"  截断等级:     {self.level_info['label']}")
        lines.append(f"  建议动作:     {self.level_info['action']}")
        lines.append("-" * 50)

        lines.append(f"  finish_reason 分布：")
        lines.append(f"    stop:           {self.stop_count}")
        lines.append(f"    length:         {self.length_count}")
        lines.append(f"    content_filter: {self.filter_count}")
        lines.append("-" * 50)

        lines.append(f"  回复长度（字符）：")
        lines.append(f"    全部请求：平均 {self.avg_response_len:.0f}, 最大 {self.max_response_len:.0f}")
        lines.append(f"    未截断：  平均 {self.avg_full_len:.0f}, 最大 {self.max_full_len:.0f}")
        if self.truncated > 0:
            lines.append(f"    被截断：  平均 {self.avg_truncated_len:.0f}")
            lines.append(f"    [!!] 被截断的平均长度 < 完整回复平均长度")
            lines.append(f"        → 提高 max_tokens 可以捕获这些截断的回复")
        lines.append("-" * 50)

        lines.append(f"  Token 消耗：")
        lines.append(f"    平均消耗:  {self.avg_tokens:.0f}")
        lines.append(f"    最大消耗:  {self.max_tokens_used:.0f}")
        lines.append("-" * 50)

        rec = self.recommendation
        lines.append(f"  max_tokens 建议：")
        lines.append(f"    当前配置:   {rec['current']}")
        lines.append(f"    推荐配置:   {rec['recommended']}")
        if rec["urgency"] == "critical":
            lines.append(f"    [!!] 紧急等级: 严重 — {rec['reason']}")
        elif rec["urgency"] == "high":
            lines.append(f"    [!!] 紧急等级: 高 — {rec['reason']}")
        elif rec["urgency"] == "medium":
            lines.append(f"    [??] 紧急等级: 中等 — {rec['reason']}")
        else:
            lines.append(f"    [OK] 紧急等级: 低 — {rec['reason']}")

        lines.append("=" * 50)
        return "\n".join(lines)
