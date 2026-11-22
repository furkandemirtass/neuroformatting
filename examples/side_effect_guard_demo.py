import json

from neuroformatting import CrossFieldRule, FieldRule, OutputSchema, StreamGuard, compute_audit_risk


def _escalation_tier_consistent(payload: dict, ctx: dict) -> bool:
    if "escalated" in payload and "tier" in payload:
        if bool(payload.get("escalated")) and str(payload.get("tier", "")).lower() == "basic":
            return False
    return True


def main() -> None:
    schema = OutputSchema(
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
                name="escalation_tier_consistency",
                failure_category="repairable",
                check=_escalation_tier_consistent,
                error_message="escalated=true conflicts with tier=basic",
            ),
        ],
    )

    ctx = {
        "sources": {
            "routing-policy-1": "Basic tier tickets require manual escalation review when escalated is true."
        }
    }

    candidate_payload = {
        "answer": "Ticket routed automatically without escalation review.",
        "source_id": "routing-policy-1",
        "escalated": True,
        "tier": "basic",
        "reasoning_tokens": 16,
        "reasoning_text": "Marked escalated=true while keeping basic tier routing.",
    }

    guard = StreamGuard(schema=schema, context=ctx)
    res = guard.run_stream([json.dumps(candidate_payload)])

    summary = {
        "cases": [
            {
                "id": "support_routing_check",
                "actual": res.status,
                "expected": "valid",
                "matched": res.status == "valid",
            }
        ]
    }
    risk = compute_audit_risk(summary)

    print("Guard status:", res.status)
    print("Errors:", res.errors)
    print("Risk summary:", risk)

    if res.status != "valid":
        print("SIDE EFFECT BLOCKED: Do not execute ticket routing or external action.")
    else:
        print("SIDE EFFECT ALLOWED: Safe to proceed.")


if __name__ == "__main__":
    main()
