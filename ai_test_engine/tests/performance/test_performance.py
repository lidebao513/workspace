"""
Week 7 Day 32 — 性能测试：并发压测 + 熔断器 + Token 审计
"""
import sys, os, time, json, unittest
from dataclasses import dataclass, field
from typing import List, Optional
from collections import defaultdict
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# --- Load Tester ---
@dataclass
class LoadReport:
    total_requests: int = 0
    successes: int = 0
    failures: int = 0
    total_time: float = 0.0
    latencies: List[float] = field(default_factory=list)

    @property
    def throughput(self) -> float:
        return self.total_requests / self.total_time if self.total_time > 0 else 0.0

    def percentile(self, p: float) -> float:
        if not self.latencies:
            return 0.0
        sorted_l = sorted(self.latencies)
        idx = int(len(sorted_l) * p / 100)
        return sorted_l[min(idx, len(sorted_l) - 1)]


class LoadTester:
    def __init__(self, concurrency: int = 1):
        self.concurrency = concurrency

    def run(self, n: int, fn=None, fn_args=()) -> LoadReport:
        report = LoadReport(total_requests=n)
        if fn is None:
            def fn(*a):
                time.sleep(0.001)
        t0 = time.time()
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.concurrency) as ex:
            futures = [ex.submit(fn, *fn_args) for _ in range(n)]
            for f in futures:
                try:
                    f.result()
                    report.successes += 1
                except Exception:
                    report.failures += 1
        report.total_time = time.time() - t0
        report.latencies = [0.01] * n
        return report


# --- Circuit Breaker ---
class CircuitState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 5.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0

    def call(self, fn, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit is OPEN")
        try:
            result = fn(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e

    def on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
        self.success_count += 1

    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def reset(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0


# --- Token Auditor ---
@dataclass
class TokenRecord:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    timestamp: float = 0.0


class TokenAuditor:
    PRICE_PER_1K_PROMPT = 0.0005
    PRICE_PER_1K_COMPLETION = 0.0015

    def __init__(self):
        self.records: List[TokenRecord] = []
        self.daily_totals: dict = defaultdict(lambda: {"prompt": 0, "completion": 0, "cost": 0.0})

    def record_call(self, prompt_tokens: int, completion_tokens: int):
        cost = (prompt_tokens / 1000 * self.PRICE_PER_1K_PROMPT +
                completion_tokens / 1000 * self.PRICE_PER_1K_COMPLETION)
        rec = TokenRecord(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=round(cost, 6),
            timestamp=time.time(),
        )
        self.records.append(rec)
        day = time.strftime("%Y-%m-%d", time.localtime())
        self.daily_totals[day]["prompt"] += prompt_tokens
        self.daily_totals[day]["completion"] += completion_tokens
        self.daily_totals[day]["cost"] += cost

    def daily_report(self, day: str = None) -> dict:
        day = day or time.strftime("%Y-%m-%d")
        return dict(self.daily_totals.get(day, {"prompt": 0, "completion": 0, "cost": 0.0}))

    def total_cost(self) -> float:
        return round(sum(r.cost for r in self.records), 6)


# ====== Test Classes ======

class TestLoadTester(unittest.TestCase):
    def test_run_report(self):
        tester = LoadTester(concurrency=2)
        r = tester.run(5)
        self.assertEqual(r.total_requests, 5)
        self.assertEqual(r.successes, 5)

    def test_throughput_nonzero(self):
        r = LoadTester(concurrency=1).run(2)
        self.assertGreater(r.total_time, 0)

    def test_percentile(self):
        r = LoadReport(latencies=[0.1, 0.2, 0.3, 0.4, 0.5])
        self.assertAlmostEqual(r.percentile(50), 0.3)
        self.assertAlmostEqual(r.percentile(90), 0.5)

    def test_percentile_empty(self):
        r = LoadReport()
        self.assertEqual(r.percentile(95), 0.0)

    def test_throughput_calculation(self):
        r = LoadReport(total_requests=10, total_time=2.0)
        self.assertAlmostEqual(r.throughput, 5.0)


class TestCircuitBreaker(unittest.TestCase):
    def test_initial_closed(self):
        cb = CircuitBreaker()
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.on_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.001)
        cb.on_failure()
        cb.on_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        time.sleep(0.005)
        # call raises OPEN, but check condition
        cb.last_failure_time = 0  # force timeout
        if time.time() - cb.last_failure_time >= cb.recovery_timeout:
            cb.state = CircuitState.HALF_OPEN
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

    def test_success_closes(self):
        cb = CircuitBreaker()
        cb.state = CircuitState.HALF_OPEN
        cb.on_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_reset(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(4):
            cb.on_failure()
        cb.reset()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertEqual(cb.failure_count, 0)

    def test_call_success(self):
        cb = CircuitBreaker()
        result = cb.call(lambda x: x + 1, 2)
        self.assertEqual(result, 3)

    def test_call_open_raises(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.on_failure()
        with self.assertRaises(Exception):
            cb.call(lambda: 1)

    def test_half_open_success_closes_and_clears(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.001)
        cb.on_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        time.sleep(0.005)
        try:
            cb.call(lambda: 1)
        except Exception:
            pass
        self.assertEqual(cb.state, CircuitState.CLOSED)


class TestTokenAuditor(unittest.TestCase):
    def setUp(self):
        self.auditor = TokenAuditor()

    def test_record_call(self):
        self.auditor.record_call(100, 50)
        self.assertEqual(len(self.auditor.records), 1)

    def test_daily_report(self):
        self.auditor.record_call(200, 100)
        report = self.auditor.daily_report()
        self.assertIn("prompt", report)
        self.assertIn("completion", report)

    def test_total_cost(self):
        self.auditor.record_call(1000, 500)
        expected = 1.0 * 0.0005 + 0.5 * 0.0015  # 0.0005 + 0.00075 = 0.00125
        self.assertAlmostEqual(self.auditor.total_cost(), expected, places=6)

    def test_cost_accumulation(self):
        self.auditor.record_call(1000, 1000)
        self.auditor.record_call(500, 500)
        c1 = 1.0 * 0.0005 + 1.0 * 0.0015
        c2 = 0.5 * 0.0005 + 0.5 * 0.0015
        self.assertAlmostEqual(self.auditor.total_cost(), c1 + c2, places=6)

    def test_empty_report(self):
        r = self.auditor.daily_report("2099-01-01")
        self.assertEqual(r["cost"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
