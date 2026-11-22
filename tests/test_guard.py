import json
import re
import unittest
from pathlib import Path

from neuroformatting import CrossFieldRule, FieldRule, OutputSchema, StreamGuard


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9:]+", text.lower()) if len(t) > 2}


def supports_claim(payload: dict, ctx: dict) -> bool:
    """Checks membership + key factual tokens (including times/numbers) in the cited source."""
    sources = ctx.get("sources", {})
    source_id = payload.get("source_id")
    if source_id not in sources:
        return False

    source_text = sources[source_id].lower()
    answer_text = payload.get("answer", "").lower()

    # Check explicit time tokens (e.g. 14:30, 16:00)
    times_in_answer = re.findall(r"\b\d{1,2}:\d{2}\b", answer_text)
    for t in times_in_answer:
        if t not in source_text:
            return False

    # Check numeric tokens (e.g. 120ms, 45ms, 5, 10)
    nums_in_answer = re.findall(r"\b\d+(?:ms)?\b", answer_text)
    for n in nums_in_answer:
        if n not in source_text:
            return False

    # Check content word overlap (excluding generic filler words)
    stopwords = {"your", "with", "from", "that", "this", "have", "been", "into", "after", "all"}
    answer_words = [w for w in _tokens(answer_text) if w not in stopwords]
    if not answer_words:
        return False

    matched = sum(1 for w in answer_words if w in source_text)
    return matched >= min(2, len(answer_words))


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
                    error_message="source_id does not support the claim",
                ),
                CrossFieldRule(
                    name="reasoning_token_consistency",
                    failure_category="repairable",
                    check=lambda payload, ctx: not (
                        (payload["reasoning_tokens"] == 0 and len(payload["reasoning_text"].strip()) > 0)
                        or (payload["reasoning_tokens"] > 0 and len(payload["reasoning_text"].strip()) == 0)
                    ),
                    error_message="inconsistent reasoning_tokens and reasoning_text",
                ),
            ],
        )

    def test_ten_semantic_fixture_cases(self) -> None:
        fixture_path = Path(__file__).resolve().parent.parent / "fixtures" / "semantic_cases.json"
        spec = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.assertEqual(len(spec["cases"]), 10)

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
