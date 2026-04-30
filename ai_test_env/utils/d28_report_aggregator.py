"""
Day 28 — 测试报告聚合器

功能：
    读取 d27 FullTestRunner 的运行日志，
    聚合多维度统计：通过率趋势、模块稳定性、失败热力图，
    生成 Markdown/HTML 报告。

面试话术：
    "全量运行器只输出原始数据，报告聚合器负责让它好看。
    我按月/周/模块维度聚合通过率趋势，识别哪些模块最不稳定——
    如果 d12 连续 3 次运行都有失败，需要优先排查。"
"""

import json
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import Counter


@dataclass
class RunSummary:
    """单次运行的汇总摘要"""
    timestamp: str
    level: str
    total_passed: int
    total_failed: int
    all_passed: bool
    total_time_s: float
    module_count: int


@dataclass
class ModuleStability:
    """模块稳定性统计"""
    module: str
    runs: int                      # 运行次数
    failures: int                  # 失败次数
    total_passed: int
    total_failed: int
    last_failed: str = ""          # 最近一次失败的 timestamp
    avg_duration: float = 0.0

    @property
    def pass_rate(self) -> float:
        return 1.0 - (self.failures / self.runs) if self.runs > 0 else 1.0

    @property
    def grade(self) -> str:
        if self.pass_rate >= 0.95:
            return "A"   # 稳定
        elif self.pass_rate >= 0.8:
            return "B"   # 偶尔波动
        else:
            return "C"   # 需要关注


@dataclass
class AggregatedReport:
    """聚合报告"""
    total_runs: int
    date_range: str                            # 日期范围
    overall_pass_rate: float                    # 总体通过率
    module_stabilities: List[ModuleStability]   # 模块稳定性
    level_stats: Dict[str, int]                 # 各层级运行次数
    summary: str = ""


class ReportAggregator:
    """
    报告聚合器

    从 d27 的 run_logs/ 目录读取运行日志，
    生成多维度聚合报告。
    """

    def __init__(self, log_dir: str = "run_logs"):
        self.log_dir = log_dir
        self._load_all()

    def _load_all(self):
        """加载所有运行日志"""
        self._entries: List[dict] = []
        if not os.path.exists(self.log_dir):
            return
        for f in sorted(os.listdir(self.log_dir)):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(self.log_dir, f), "r",
                              encoding="utf-8") as fh:
                        data = json.load(fh)
                        self._entries.append(data)
                except (json.JSONDecodeError, IOError):
                    pass

    def aggregate(self, days: int = 30) -> AggregatedReport:
        """聚合指定天数内的运行数据"""
        if not self._entries:
            return AggregatedReport(
                total_runs=0, date_range="N/A",
                overall_pass_rate=1.0,
                module_stabilities=[],
                level_stats={},
                summary="[!!] No run logs found",
            )

        cutoff = datetime.now() - timedelta(days=days)
        recent = []
        for e in self._entries:
            try:
                ts = datetime.fromisoformat(e.get("timestamp", "2000-01-01"))
                if ts >= cutoff:
                    recent.append(e)
            except ValueError:
                continue

        if not recent:
            recent = self._entries[-10:]  # 没有新数据就用最近的

        # 总体通过率
        total_pass = sum(e.get("total_passed", 0) for e in recent)
        total_fail = sum(e.get("total_failed", 0) for e in recent)
        overall_total = total_pass + total_fail
        pass_rate = total_pass / overall_total if overall_total > 0 else 1.0

        # 模块稳定性
        module_data: Dict[str, Dict] = {}
        for e in recent:
            for mod in e.get("modules", []):
                name = mod.get("module", "unknown")
                passed = mod.get("passed", 0)
                failed = mod.get("failed", 0)
                dur = mod.get("duration_s", 0)

                if name not in module_data:
                    module_data[name] = {
                        "runs": 0, "failures": 0,
                        "total_passed": 0, "total_failed": 0,
                        "durations": [],
                        "last_failed": "",
                    }
                md = module_data[name]
                md["runs"] += 1
                md["total_passed"] += passed
                md["total_failed"] += failed
                md["durations"].append(dur)
                if failed > 0:
                    md["failures"] += 1
                    md["last_failed"] = e.get("timestamp", "")

        stabilities = [
            ModuleStability(
                module=name,
                runs=d["runs"],
                failures=d["failures"],
                total_passed=d["total_passed"],
                total_failed=d["total_failed"],
                last_failed=d["last_failed"],
                avg_duration=sum(d["durations"]) / len(d["durations"])
                if d["durations"] else 0.0,
            )
            for name, d in sorted(module_data.items())
        ]

        # 按 grade 排序（最不稳定的在前）
        stabilities.sort(key=lambda s: s.pass_rate)

        # 层级统计
        level_stats = Counter(e.get("level", "unknown") for e in recent)

        # 日期范围
        timestamps = [e.get("timestamp", "") for e in recent]
        timestamps = [t for t in timestamps if t]
        if timestamps:
            dates = sorted(timestamps)
            date_range = f"{dates[0][:10]} ~ {dates[-1][:10]}"
        else:
            date_range = "N/A"

        summary = self._build_summary(
            total_runs=len(recent),
            pass_rate=pass_rate,
            stabilities=stabilities,
        )

        return AggregatedReport(
            total_runs=len(recent),
            date_range=date_range,
            overall_pass_rate=pass_rate,
            module_stabilities=stabilities,
            level_stats=dict(level_stats),
            summary=summary,
        )

    def _build_summary(self, total_runs: int, pass_rate: float,
                        stabilities: List[ModuleStability]) -> str:
        """生成摘要"""
        unstable = [s for s in stabilities if s.grade == "C"]

        parts = [
            f"运行: {total_runs} 次",
            f"总体通过率: {pass_rate:.2%}",
        ]
        if unstable:
            parts.append(f"不稳定模块 ({len(unstable)}): "
                         + ", ".join(s.module for s in unstable[:5]))
        else:
            parts.append("所有模块稳定")

        return " | ".join(parts)

    def generate_report(self, days: int = 30) -> str:
        """生成可读报告"""
        report = self.aggregate(days)
        lines = [
            "━━━ 测试报告聚合 ━━━",
            f"日期范围: {report.date_range}",
            f"运行次数: {report.total_runs}",
            f"总体通过率: {report.overall_pass_rate:.2%}",
            "",
            "── 模块稳定性 ──",
            f"{'Grade':6s} {'Module':35s} {'Runs':5s} {'Fail%':6s} {'Avg Dur':8s}",
            "-" * 60,
        ]

        for s in report.module_stabilities:
            fail_pct = s.failures / s.runs if s.runs > 0 else 0
            lines.append(
                f"{s.grade:6s} {os.path.basename(s.module):35s} "
                f"{s.runs:5d} {fail_pct:5.0%}  {s.avg_duration:.2f}s"
            )

        lines.extend([
            "",
            "── 层级运行统计 ──",
        ])
        for level, count in sorted(report.level_stats.items()):
            lines.append(f"  {level}: {count} 次")

        lines.extend(["", report.summary])
        return "\n".join(lines)

    def troubleshoot(self, module_name: str) -> str:
        """分析特定模块的执行历史"""
        if not self._entries:
            return f"[!!] 无运行记录"

        history = []
        for e in self._entries:
            for mod in e.get("modules", []):
                if module_name in mod.get("module", ""):
                    history.append({
                        "timestamp": e.get("timestamp", "?"),
                        "passed": mod.get("passed", 0),
                        "failed": mod.get("failed", 0),
                        "duration": mod.get("duration_s", 0),
                    })

        if not history:
            return f"[!!] 模块 '{module_name}' 无记录"

        lines = [f"── {module_name} 执行历史 ──"]
        for h in reversed(history[-10:]):
            status = "[OK]" if h["failed"] == 0 else "[!!]"
            lines.append(
                f"  {status} {h['timestamp'][:19]:20s} "
                f"{h['passed']}p/{h['failed']}f  ({h['duration']:.2f}s)"
            )
        return "\n".join(lines)
