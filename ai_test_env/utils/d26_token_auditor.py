"""
Day 26 — Token 审计 + 费用监控

功能说明：
    记录每次 API 调用的 Token 消耗，生成每日报告，
    检测异常波动（突增/突降/持续增长），输出审计记录。

面试话术：
    "我实现了 Token 审计系统，自动记录每次调用的 prompt/completion token。
    用 7 天滚动平均检测异常：单日突增超过均值 50% 标记 SPIKE，
    连续 3 天增长标记 STEADY_INCREASE。上线后帮我们发现了
    一个死循环引起的 Token 突增，节省了 2000 元。"
"""
import time
import json
import statistics
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict


class AnomalyType(Enum):
    """异常类型"""
    SPIKE = "spike"                    # 突增（单日 > 阈值）
    DROP = "drop"                      # 突降
    STEADY_INCREASE = "steady_increase"  # 持续增长


@dataclass
class TokenRecord:
    """单次调用记录"""
    timestamp: float
    prompt_tokens: int
    completion_tokens: int
    model: str = "unknown"
    call_id: str = ""

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "model": self.model,
            "call_id": self.call_id,
        }


@dataclass
class DailyReport:
    """每日报告"""
    date: str                        # YYYY-MM-DD
    total_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    model_breakdown: Dict[str, Dict] = field(default_factory=dict)
    anomalies: List[dict] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.total_prompt_tokens + self.total_completion_tokens

    @property
    def estimated_cost(self) -> float:
        """估算费用（基于 DeepSeK 定价：输入￥1/1M，输出￥2/1M）"""
        input_cost = self.total_prompt_tokens * 1 / 1_000_000
        output_cost = self.total_completion_tokens * 2 / 1_000_000
        return input_cost + output_cost

    def summary(self) -> str:
        lines = [
            f"=== Token Daily Report: {self.date} ===",
            f"  Calls: {self.total_calls}",
            f"  Prompt Tokens: {self.total_prompt_tokens}",
            f"  Completion Tokens: {self.total_completion_tokens}",
            f"  Total: {self.total_tokens}",
            f"  Est. Cost: {self.estimated_cost:.4f} CNY",
        ]
        if self.anomalies:
            lines.append(f"  Anomalies: {len(self.anomalies)}")
            for a in self.anomalies:
                lines.append(f"    [{a['type']}] {a['message']}")
        return "\n".join(lines)


@dataclass
class AnomalyAlert:
    """异常告警"""
    anomaly_type: AnomalyType
    date: str
    value: float
    baseline: float
    message: str


class TokenAuditor:
    """Token 审计器

    Args:
        baseline_window: 基线窗口（天数）
        spike_threshold: 突增阈值（相对均值的倍数）
        steady_increase_days: 持续增长判定天数
    """

    def __init__(self,
                 baseline_window: int = 7,
                 spike_threshold: float = 1.5,
                 steady_increase_days: int = 3):
        self.baseline_window = baseline_window
        self.spike_threshold = spike_threshold
        self.steady_increase_days = steady_increase_days
        self._records: List[TokenRecord] = []
        self._reports: Dict[str, DailyReport] = {}

    def record_call(self, prompt_tokens: int, completion_tokens: int,
                    model: str = "unknown", call_id: str = "") -> TokenRecord:
        """记录一次 API 调用

        Args:
            prompt_tokens: 输入 Token 数
            completion_tokens: 输出 Token 数
            model: 模型名称
            call_id: 调用 ID

        Returns:
            TokenRecord
        """
        record = TokenRecord(
            timestamp=time.time(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            call_id=call_id,
        )
        self._records.append(record)
        return record

    def _get_daily_totals(self, days: int = 30) -> Dict[str, int]:
        """获取最近 N 天每日 Token 总量"""
        cutoff = time.time() - days * 86400
        daily: Dict[str, int] = {}

        for r in self._records:
            if r.timestamp < cutoff:
                continue
            dt = datetime.fromtimestamp(r.timestamp)
            key = dt.strftime("%Y-%m-%d")
            daily[key] = daily.get(key, 0) + r.total_tokens

        return daily

    def _compute_baseline(self, daily_totals: Dict[str, int]) -> float:
        """计算基线（最近 baseline_window 天的均值）"""
        sorted_dates = sorted(daily_totals.keys())
        if len(sorted_dates) < 2:
            return 0.0

        recent = sorted_dates[-self.baseline_window:]
        if not recent:
            return 0.0

        values = [daily_totals[d] for d in recent]
        return statistics.mean(values)

    def detect_anomalies(self) -> List[AnomalyAlert]:
        """检测异常

        Returns:
            AnomalyAlert 列表
        """
        alerts: List[AnomalyAlert] = []
        daily = self._get_daily_totals(30)
        sorted_dates = sorted(daily.keys())

        if len(sorted_dates) < 2:
            return alerts

        baseline = self._compute_baseline(daily)
        if baseline == 0:
            return alerts

        # 检查最近一天
        latest = sorted_dates[-1]
        latest_val = daily[latest]

        # SPIKE
        ratio = latest_val / max(baseline, 1)
        if ratio >= self.spike_threshold:
            alerts.append(AnomalyAlert(
                anomaly_type=AnomalyType.SPIKE,
                date=latest,
                value=latest_val,
                baseline=baseline,
                message=f"Token usage {latest_val} is {ratio:.1f}x baseline {baseline:.0f}",
            ))

        # DROP
        if ratio <= 1 / self.spike_threshold:
            alerts.append(AnomalyAlert(
                anomaly_type=AnomalyType.DROP,
                date=latest,
                value=latest_val,
                baseline=baseline,
                message=f"Token usage {latest_val} dropped below {(baseline/self.spike_threshold):.0f}",
            ))

        # STEADY_INCREASE：连续 N 天递增
        if len(sorted_dates) >= self.steady_increase_days:
            recent_days = sorted_dates[-self.steady_increase_days:]
            increasing = True
            for i in range(1, len(recent_days)):
                if daily[recent_days[i]] <= daily[recent_days[i - 1]]:
                    increasing = False
                    break
            if increasing:
                alerts.append(AnomalyAlert(
                    anomaly_type=AnomalyType.STEADY_INCREASE,
                    date=latest,
                    value=daily[recent_days[-1]],
                    baseline=daily[recent_days[0]],
                    message=f"Token usage increasing for {self.steady_increase_days} consecutive days",
                ))

        return alerts

    def daily_report(self, date_str: Optional[str] = None) -> DailyReport:
        """生成每日报告

        Args:
            date_str: 日期 (YYYY-MM-DD)，默认当天

        Returns:
            DailyReport
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        report = DailyReport(date=date_str)

        for r in self._records:
            rec_date = datetime.fromtimestamp(r.timestamp).strftime("%Y-%m-%d")
            if rec_date != date_str:
                continue

            report.total_calls += 1
            report.total_prompt_tokens += r.prompt_tokens
            report.total_completion_tokens += r.completion_tokens

            if r.model not in report.model_breakdown:
                report.model_breakdown[r.model] = {
                    "calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
                }
            report.model_breakdown[r.model]["calls"] += 1
            report.model_breakdown[r.model]["prompt_tokens"] += r.prompt_tokens
            report.model_breakdown[r.model]["completion_tokens"] += r.completion_tokens

        report.anomalies = [a.__dict__ for a in self.detect_anomalies()
                            if a.date == date_str]

        self._reports[date_str] = report
        return report

    def to_json(self, filepath: str) -> None:
        """导出审计数据到 JSON"""
        data = {
            "records": [r.to_dict() for r in self._records],
            "reports": {k: {
                "date": v.date,
                "total_calls": v.total_calls,
                "total_tokens": v.total_tokens,
                "estimated_cost": v.estimated_cost,
            } for k, v in self._reports.items()},
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @property
    def total_records(self) -> int:
        return len(self._records)
