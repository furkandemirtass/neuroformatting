import unittest

from neuroformatting import FieldRule, OutputSchema, StreamGuard


class TestNeuroformatting(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = OutputSchema(
            fields=[
                FieldRule(name="answer", expected_type=str, required=True),
                FieldRule(
                    name="confidence",
                    expected_type=float,
                    required=True,
                    semantic_check=lambda val, ctx: 0.0 <= val <= 1.0,
                    error_message="confidence out of range",
                ),
                FieldRule(
                    name="source_id",
                    expected_type=str,
                    required=True,
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
        self.assertEqual(res.errors, [])

    def test_ungrounded_source_fails(self) -> None:
        guard = StreamGuard(schema=self.schema, context=self.context)
        res = guard.run_stream([
            '{"answer": "Hallucinated ref", "confidence": 0.8, "source_id": "doc-999"}'
        ])
        self.assertFalse(res.ok)
        self.assertTrue(any("source_id" in err for err in res.errors))

    def test_invalid_json_fails(self) -> None:
        guard = StreamGuard(schema=self.schema, context=self.context)
        res = guard.run_stream(["```json\n{broken json"])
        self.assertFalse(res.ok)
        self.assertTrue(any("JSON parse error" in err for err in res.errors))


if __name__ == "__main__":
    unittest.main()
