import unittest

from neuroformatting import compare_audit_runs


class TestRegressionGate(unittest.TestCase):
    def test_detects_new_semantic_regression(self) -> None:
        baseline = {
            "total": 2,
            "passed": 2,
            "cases": [
                {"id": "c1", "domain": "rag", "actual": "valid", "expected": "valid", "matched": True},
                {"id": "c2", "domain": "clinic", "actual": "insufficient_grounding", "expected": "insufficient_grounding", "matched": True},
            ],
        }
        candidate = {
            "total": 2,
            "passed": 1,
            "cases": [
                {"id": "c1", "domain": "rag", "actual": "valid", "expected": "valid", "matched": True},
                {"id": "c2", "domain": "clinic", "actual": "valid", "expected": "insufficient_grounding", "matched": False},
            ],
        }
        diff = compare_audit_runs(baseline, candidate)
        self.assertFalse(diff["gate_passed"])
        self.assertEqual(diff["regression_count"], 1)
        self.assertEqual(diff["regressions"][0]["id"], "c2")


if __name__ == "__main__":
    unittest.main()
