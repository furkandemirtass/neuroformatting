import unittest

from neuroformatting import CrossFieldRule, FieldRule, OutputSchema, StreamGuard


class TestNeuroformatting(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = OutputSchema(
            fields=[
                FieldRule(name="answer", expected_type=str, required=True),
                FieldRule(
                    name="confidence",
                    expected_type=float,
                    required=True,
                    failure_category="repairable",
                    semantic_check=lambda val, ctx: 0.0 <= val <= 1.0,
                    error_message="confidence out of range",
                ),
                FieldRule(
                    name="source_id",
                    expected_type=str,
                    required=True,
                    failure_category="ungrounded",
                    semantic_check=lambda val, ctx: val in ctx.get("allowed_sources", []),
                    error_message="ungrounded source_id",
                ),
            ]
        )
        self.context = {"allowed_sources": ["doc-101"]}

    def test_valid_stream_passes(self) -> None:
        guard = StreamGuard(schema=self.schema, context=self.context)
        res = guard.run_stream([
            '{"answer": "Grounded", ',
            '"confidence": 0.9, "source_id": "doc-101"}',
        ])
        self.assertTrue(res.ok)
        self.assertEqual(res.status, "valid")

    def test_ungrounded_source_returns_insufficient_grounding(self) -> None:
        guard = StreamGuard(schema=self.schema, context=self.context)
        res = guard.run_stream([
            '{"answer": "Hallucinated ref", "confidence": 0.8, "source_id": "doc-999"}'
        ])
        self.assertFalse(res.ok)
        self.assertEqual(res.status, "insufficient_grounding")

    def test_out_of_bounds_score_marks_needs_repair(self) -> None:
        guard = StreamGuard(schema=self.schema, context=self.context)
        res = guard.run_stream([
            '{"answer": "Overconfident", "confidence": 1.45, "source_id": "doc-101"}'
        ])
        self.assertFalse(res.ok)
        self.assertEqual(res.status, "needs_repair")

    def test_cross_field_contradiction_fixture(self) -> None:
        # Fixture: syntactically valid JSON claiming reasoning_tokens=0 while shipping reasoning_text
        reasoning_schema = OutputSchema(
            fields=[
                FieldRule(name="reasoning_tokens", expected_type=int, required=True),
                FieldRule(name="reasoning_text", expected_type=str, required=True),
            ],
            cross_field_rules=[
                CrossFieldRule(
                    name="reasoning_consistency",
                    failure_category="repairable",
                    check=lambda payload, ctx: not (
                        payload["reasoning_tokens"] == 0 and len(payload["reasoning_text"].strip()) > 0
                    ),
                    error_message="reasoning_tokens cannot be 0 when reasoning_text is non-empty",
                )
            ],
        )
        guard = StreamGuard(schema=reasoning_schema)
        res = guard.run_stream([
            '{"reasoning_tokens": 0, "reasoning_text": "' + ("step " * 60) + '"}'
        ])
        self.assertFalse(res.ok)
        self.assertEqual(res.status, "needs_repair")
        self.assertIn("reasoning_tokens", res.errors[0])

    def test_commit_point_unit_close_streaming(self) -> None:
        guard = StreamGuard(schema=self.schema, context=self.context)
        chunks = [
            '[{"answer": "First", "confidence": 0.9, "source_id": "doc-101"}, ',
            '{"answer": "Second", "confidence": 0.8, "source_id": "doc-999"}]',
        ]
        results = list(guard.iter_validated_units(chunks))
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].status, "valid")
        self.assertEqual(results[1].status, "insufficient_grounding")


if __name__ == "__main__":
    unittest.main()
