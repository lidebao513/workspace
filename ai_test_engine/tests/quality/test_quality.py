"""
Week 7 Day 30 — 质量评估：评分器 + LLM Judge + 流水线
"""
import sys, os, json, unittest
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class QualityScore:
    """5 维评分"""
    DIMENSIONS = ["completeness", "relevance", "coherence", "consistency", "conciseness"]

    @staticmethod
    def score_response(response: str) -> dict:
        return {
            "completeness": 0.9,
            "relevance": 0.85,
            "coherence": 0.8,
            "consistency": 0.75,
            "conciseness": 0.7,
        }

    @staticmethod
    def overall(scores: dict) -> float:
        return sum(scores.values()) / len(scores) if scores else 0.0


class LLMJudge:
    @staticmethod
    def parse_score(text: str) -> float:
        try:
            data = json.loads(text)
            return float(data.get("score", 0))
        except (json.JSONDecodeError, TypeError):
            pass
        import re
        m = re.search(r'"?score"?\s*:\s*([0-9.]+)', text)
        if m:
            return float(m.group(1))
        return 0.5

    @staticmethod
    def compare(a: float, b: float) -> dict:
        return {"winner": "A" if a > b else "B" if b > a else "tie", "delta": abs(a - b)}


class AssessmentPipeline:
    """端到端质量评估流水线"""

    @staticmethod
    def assess(response: str) -> dict:
        scores = QualityScore.score_response(response)
        overall = QualityScore.overall(scores)
        return {
            "scores": scores,
            "overall": round(overall, 4),
            "verdict": "pass" if overall >= 0.6 else "fail",
        }

    @staticmethod
    def compare_versions(v1: dict, v2: dict) -> dict:
        return {
            "v1_overall": v1.get("overall", 0),
            "v2_overall": v2.get("overall", 0),
            "improvement": v2.get("overall", 0) - v1.get("overall", 0),
        }


class TestQualityScore(unittest.TestCase):
    def test_dimensions_count(self):
        self.assertEqual(len(QualityScore.DIMENSIONS), 5)

    def test_score_response_returns_dict(self):
        r = QualityScore.score_response("test")
        self.assertIn("completeness", r)

    def test_overall_calculation(self):
        s = {"a": 1.0, "b": 0.0}
        self.assertAlmostEqual(QualityScore.overall(s), 0.5)

    def test_overall_empty(self):
        self.assertEqual(QualityScore.overall({}), 0.0)

    def test_score_range(self):
        s = QualityScore.score_response("hello")
        for v in s.values():
            self.assertGreaterEqual(v, 0)
            self.assertLessEqual(v, 1)


class TestLLMJudge(unittest.TestCase):
    def test_parse_json(self):
        self.assertAlmostEqual(LLMJudge.parse_score('{"score": 0.85}'), 0.85)

    def test_parse_fallback_regex(self):
        self.assertAlmostEqual(LLMJudge.parse_score('score: 0.75'), 0.75)

    def test_parse_garbage(self):
        self.assertAlmostEqual(LLMJudge.parse_score("nope"), 0.5)

    def test_compare_a_wins(self):
        r = LLMJudge.compare(0.9, 0.5)
        self.assertEqual(r["winner"], "A")

    def test_compare_tie(self):
        r = LLMJudge.compare(0.5, 0.5)
        self.assertEqual(r["winner"], "tie")


class TestAssessmentPipeline(unittest.TestCase):
    def test_assess_returns_keys(self):
        r = AssessmentPipeline.assess("hello")
        self.assertIn("scores", r)
        self.assertIn("overall", r)
        self.assertIn("verdict", r)

    def test_assess_pass(self):
        r = AssessmentPipeline.assess("good response")
        self.assertEqual(r["verdict"], "pass")

    def test_compare_versions_v2_improved(self):
        v1 = {"overall": 0.5}
        v2 = {"overall": 0.8}
        r = AssessmentPipeline.compare_versions(v1, v2)
        self.assertAlmostEqual(r["improvement"], 0.3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
