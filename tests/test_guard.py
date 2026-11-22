import json
import unittest
from pathlib import Path

from neuroformatting import CrossFieldRule, FieldRule, OutputSchema, StreamGuard


def supports_claim(payload: dict, ctx: dict) -> bool:
    """Two-stage check: membership (id exists) + support (cited source backs the claim)."""
    sources = ctx.get("sources", {})
    source_id = payload.get("source_id")
    if source_id not in sources:
        return False
    source_text = sources[source_id].lower()
    keywords = [w.strip(".,") for w in payload.get("answer", "").lower().split() if len(w.strip(".,")) > 5]
    return any(kw in source_text for kw in keywords)


class TestNeuroformatting(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = OutputSchema(
            fields=[
                FieldRule(name="answer", expected_type=str, required=True),
                FieldRule(
                    name="source_id",
                    expected_type=str,
                    required=True,
                    failure_category="ungrounded",
                    semantic_check=lambda val, ctx: val in ctx.get("sources", {}),
                    error_message="source_id not found in retrieved sources",
                ),
                FieldRule(name="reasoning_tokens", expected_type=int, required=True),
                FieldRule(name="reasoning_text", expected_type=str, required=True),
            ],
            cross_field_rules=[
                CrossFieldRule(
                    name="source_claim_support",
                    failure_category="ungrounded",
                    check=supports_claim,
                    error_message="source_id exists in context but does not support the claim",
                ),
                CrossFieldRule(
                    name="reasoning_token_consistency",
                    failure_category="repairable",
                    check=lambda payload, ctx: not (
                        payload["reasoning_tokens"] == 0 and len(payload["reasoning_text"].strip()) > 0
                    ),
                    error_message="reasoning_tokens cannot be 0 when reasoning_text is non-empty",
                ),
            ],
        )

    def test_semantic_fixture_spec(self) -> None:
        fixture_path = Path(__file__).resolve().parent.parent / "fixtures" / "semantic_cases.json"
        spec = json.loads(fixture_path.read_text(encoding="utf-8"))

        for case in spec["cases"]:
            with self.subTest(case=case["id"]):
                guard = StreamGuard(schema=self.schema, context=case["context"])
                res = guard.run_stream([json.dumps(case["payload"])])
                self.assertEqual(res.status, case["expected_status"])

    def test_commit_point_unit_close_streaming(self) -> None:
        ctx = {
            "sources": {
                "doc-101": "Stream validation runs at commit points when a JSON object closes.",
                "doc-202": "Retry prompts should carry the exact violated rule.",
            }
        }
        guard = StreamGuard(schema=self.schema, context=ctx)
        chunks = [
            '[{"answer": "Validation runs at commit points.", "source_id": "doc-101", "reasoning_tokens": 12, "reasoning_text": "ok"}, ',
            '{"answer": "Validation runs at commit points.", "source_id": "doc-202", "reasoning_tokens": 12, "reasoning_text": "wrong source"}]',
        ]
        results = list(guard.iter_validated_units(chunks))
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].status, "valid")
        self.assertEqual(results[1].status, "insufficient_grounding")


if __name__ == "__main__":
    unittest.main()
