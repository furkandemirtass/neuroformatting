import unittest

from neuroformatting import compute_audit_risk


class TestAuditRisk(unittest.TestCase):
    def test_risk_score_and_ungrounded_count(self) -> None:
        summary = {
            "cases": [
                {"id": "1", "actual": "valid"},
                {"id": "2", "actual": "insufficient_grounding"},
                {"id": "3", "actual": "needs_repair"},
            ]
        }
        risk = compute_audit_risk(summary)
        self.assertEqual(risk["total_cases"], 3)
        self.assertEqual(risk["ungrounded_count"], 1)
        self.assertEqual(risk["risk_score"], 7)


if __name__ == "__main__":
    unittest.main()
