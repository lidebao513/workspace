"""
D28 — 报告聚合器测试
"""
import sys, os, json, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.d28_report_aggregator import (
    AggregatedReport, ModuleStability, ReportAggregator,
)


def _write_log(log_dir: str, filename: str, data: dict):
    with open(os.path.join(log_dir, filename), "w") as f:
        json.dump(data, f, ensure_ascii=False)


def _make_entry(module, passed, failed, dur=0.5):
    return {"module": module, "passed": passed, "failed": failed, "duration_s": dur}


def test_module_stability():
    s = ModuleStability("d6_test_quality.py", runs=10, failures=1,
                         total_passed=150, total_failed=2)
    assert s.pass_rate == 0.9
    assert s.grade == "B"


def test_module_stability_grade_a():
    s = ModuleStability("d6_test_quality.py", runs=10, failures=0,
                         total_passed=150, total_failed=0)
    assert s.grade == "A"


def test_module_stability_grade_c():
    s = ModuleStability("d6_test_quality.py", runs=10, failures=5,
                         total_passed=100, total_failed=50)
    assert s.grade == "C"


def test_aggregated_report_empty():
    r = AggregatedReport(total_runs=0, date_range="N/A",
                          overall_pass_rate=1.0,
                          module_stabilities=[], level_stats={})
    assert r.total_runs == 0


def test_aggregator_no_logs():
    agg = ReportAggregator(log_dir="_nonexistent_dir_12345")
    report = agg.aggregate()
    assert report.total_runs == 0
    assert "No run logs" in report.summary


def test_aggregator_empty_log_dir():
    with tempfile.TemporaryDirectory() as tmp:
        agg = ReportAggregator(log_dir=tmp)
        report = agg.aggregate()
        assert report.total_runs == 0


def test_aggregator_single_run():
    with tempfile.TemporaryDirectory() as tmp:
        _write_log(tmp, "run_2026-04-30T19-00-00.json", {
            "timestamp": "2026-04-30T19:00:00",
            "level": "full",
            "total_passed": 50,
            "total_failed": 2,
            "modules": [
                _make_entry("d6_test_quality.py", 15, 0),
                _make_entry("d12_test_injection.py", 12, 2),
            ],
        })
        agg = ReportAggregator(log_dir=tmp)
        report = agg.aggregate(days=365)
        assert report.total_runs == 1
        assert report.overall_pass_rate < 1.0
        assert len(report.module_stabilities) == 2


def test_aggregator_all_pass():
    with tempfile.TemporaryDirectory() as tmp:
        _write_log(tmp, "run_pass.json", {
            "timestamp": "2026-04-30T19:00:00",
            "level": "smoke",
            "total_passed": 50,
            "total_failed": 0,
            "modules": [
                _make_entry("d1_test.py", 10, 0),
                _make_entry("d2_test.py", 40, 0),
            ],
        })
        agg = ReportAggregator(log_dir=tmp)
        report = agg.aggregate(days=365)
        assert report.overall_pass_rate == 1.0


def test_aggregator_invalid_json():
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "bad.json"), "w") as f:
            f.write("{invalid")
        agg = ReportAggregator(log_dir=tmp)
        report = agg.aggregate(days=365)
        assert report.total_runs == 0


def test_troubleshoot_module_found():
    with tempfile.TemporaryDirectory() as tmp:
        _write_log(tmp, "run_1.json", {
            "timestamp": "2026-04-30T19:00:00",
            "level": "full",
            "total_passed": 50,
            "total_failed": 2,
            "modules": [
                _make_entry("d6_test_quality.py", 15, 0),
            ],
        })
        agg = ReportAggregator(log_dir=tmp)
        result = agg.troubleshoot("d6_test_quality")
        assert "d6_test_quality" in result
        assert "15p/0f" in result


def test_troubleshoot_module_not_found():
    agg = ReportAggregator(log_dir="_nonexistent_")
    result = agg.troubleshoot("nonexistent.py")
    assert "无记录" in result or "无运行记录" in result


def test_generate_report():
    with tempfile.TemporaryDirectory() as tmp:
        _write_log(tmp, "run_1.json", {
            "timestamp": "2026-04-30T19:00:00",
            "level": "full",
            "total_passed": 50,
            "total_failed": 0,
            "modules": [
                _make_entry("d6_test_quality.py", 15, 0),
                _make_entry("d12_test_injection.py", 25, 0),
            ],
        })
        agg = ReportAggregator(log_dir=tmp)
        report_str = agg.generate_report(days=365)
        assert "通过率" in report_str
        assert "Grade" in report_str


def test_generate_report_empty():
    agg = ReportAggregator(log_dir="_empty_")
    report_str = agg.generate_report()
    assert "report" not in report_str.lower() or report_str


def test_module_stability_last_failed():
    s = ModuleStability("test.py", runs=5, failures=2,
                         total_passed=50, total_failed=10,
                         last_failed="2026-04-29T19:00:00")
    assert s.last_failed == "2026-04-29T19:00:00"


def test_level_stats():
    with tempfile.TemporaryDirectory() as tmp:
        for i, lvl in enumerate(["smoke", "smoke", "full"]):
            _write_log(tmp, f"run_{i}_{lvl}.json", {
                "timestamp": "2026-04-30T19:00:00",
                "level": lvl,
                "total_passed": 10,
                "total_failed": 0,
                "modules": [_make_entry("test.py", 10, 0)],
            })
        agg = ReportAggregator(log_dir=tmp)
        report = agg.aggregate(days=365)
        assert report.total_runs == 3
        assert report.level_stats.get("smoke", 0) == 2
        assert report.level_stats.get("full", 0) == 1


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])

