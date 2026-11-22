import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from .guard import StreamGuard
from .schema import CrossFieldRule, FieldRule, OutputSchema


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9:]+", text.lower()) if len(t) > 2}


def _default_supports_claim(payload: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
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


def build_default_schema() -> OutputSchema:
    return OutputSchema(
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
                check=_default_supports_claim,
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
        ],
    )


def run_fixtures(fixture_path: Path) -> Dict[str, Any]:
    spec = json.loads(fixture_path.read_text(encoding="utf-8"))
    schema = build_default_schema()
    results: List[Dict[str, Any]] = []

    passed = 0
    for case in spec.get("cases", []):
        guard = StreamGuard(schema=schema, context=case.get("context", {}))
        res = guard.run_stream([json.dumps(case.get("payload", {}))])
        expected = case.get("expected_status")
        matched = res.status == expected
        if matched:
            passed += 1
        results.append(
            {
                "id": case.get("id"),
                "expected": expected,
                "actual": res.status,
                "matched": matched,
            }
        )

    total = len(results)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "cases": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run semantic grounding fixture checks.")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path("fixtures/semantic_cases.json"),
        help="Path to semantic fixtures JSON file.",
    )
    args = parser.parse_args()

    summary = run_fixtures(args.fixtures)
    print(f"Fixtures passed: {summary['passed']}/{summary['total']}")
    for row in summary["cases"]:
        mark = "PASS" if row["matched"] else "FAIL"
        print(f"  [{mark}] {row['id']}: actual={row['actual']} (expected={row['expected']})")

    if summary["failed"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
