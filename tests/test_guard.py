import json
import re
import unittest
from pathlib import Path

from neuroformatting import CrossFieldRule, FieldRule, OutputSchema, StreamGuard


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9:]+", text.lower()) if len(t) > 2}


def supports_claim(payload: dict, ctx: dict) -> bool:
    sources = ctx.get("sources", {})
    source_id = payload.get("source_id")
    if source_id not in sources:
        return False

    source_text = str(sources[source_id]).lower()
    answer_text = str(payload.get("answer", "")).lower()

    for t in re.findall(r"\b\d{1,2}:\d{2}\b", answer_text):
        if t not in source_text:
            return False

    for n in re.findall(r"\b\d+(?:ms)?\b", answer_text):
        if n not in source_text:
            return False

    stopwords = {"your", "with", "from", "that", "this", "have", "been", "into", "after", "all"}
    answer_words = [w for w in _tokens(answer_text) if w not in stopwords]
    if not answer_words:
        return False

    matched = sum(1 for w in answer_words if w in source_text)
    return matched >= min(2, len(answer_words))


def _escalation_tier_consistent(payload: dict, ctx: dict) -> bool:
    if "escalated" in payload and "tier" in payload:
        if bool(payload.get("escalated")) and str(payload.get("tier", "")).lower() == "basic":
            return False
    return True


def _no_unfilled_placeholders(payload: dict, ctx: dict) -> bool:
    combined = " ".join(
        str(payload.get(k, "")) for k in ("answer", "phone", "reasoning_text")
    )
    if re.search(r"\[[A-Z0-9_ -]+\]|\{\{.*?\}\}|\bTBD-[A-Z0-9_-]+\b", combined):
        return False
    return True


def _action_grounded(payload: dict, ctx: dict) -> bool:
    if "action" not in payload:
        return True
    action_name = str(payload.get("action", "")).strip()
    allowed = ctx.get("allowed_actions")
    if isinstance(allowed, list) and action_name not in allowed:
        return False
    source_id = payload.get("source_id")
    sources = ctx.get("sources", {})
    if source_id in sources and action_name not in str(sources[source_id]):
        return False
    return True


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
                        (payload["reasoning_tokens"] == 0 and len(str(payload["reasoning_text"]).strip()) > 0)
                        or (payload["reasoning_tokens"] > 0 and len(str(payload["reasoning_text"]).strip()) == 0)
                    ),
                    error_message="inconsistent reasoning_tokens and reasoning_text",
                ),
                CrossFieldRule(
                    name="escalation_tier_consistency",
                    failure_category="repairable",
                    check=_escalation_tier_consistent,
                    error_message="escalated=true conflicts with tier=basic",
                ),
                CrossFieldRule(
                    name="no_unfilled_placeholders",
                    failure_category="repairable",
                    check=_no_unfilled_placeholders,
                    error_message="unfilled placeholder or TBD value detected",
                ),
                CrossFieldRule(
                    name="action_grounded",
                    failure_category="ungrounded",
                    check=_action_grounded,
                    error_message="action is not grounded in allowed actions/sources",
                ),
            ],
        )

    def test_semantic_fixture_cases(self) -> None:
        fixture_path = Path(__file__).resolve().parent.parent / "fixtures" / "semantic_cases.json"
        spec = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(spec["cases"]), 14)

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
