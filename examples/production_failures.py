import re
from neuroformatting.target_pinning import PinnedTarget, TargetPinningError, guard_side_effect

PLACEHOLDER_RE = re.compile(r"\[PLACEHOLDER\]|\bTBD\b|TODO_", re.IGNORECASE)


def send_customer_email(payload: dict) -> str:
    return f"SENT email to {payload['to']} | subject={payload['subject']}"


def guarded_email_sender(payload: dict) -> dict:
    # 1) Placeholder check
    if PLACEHOLDER_RE.search(payload.get("body", "")) or PLACEHOLDER_RE.search(payload.get("subject", "")):
        return {"status": "blocked", "reason": "PLACEHOLDER_DETECTED"}

    # 2) Cross-field contradiction check
    if payload.get("escalated") is True and payload.get("tier") == "basic":
        return {"status": "blocked", "reason": "CONTRADICTORY_TIER_FOR_ESCALATION"}

    # 3) Grounding check against verified context
    allowed_times = set(payload.get("verified_slots", []))
    claimed_time = payload.get("proposed_slot")
    if claimed_time and claimed_time not in allowed_times:
        return {"status": "blocked", "reason": "UNGROUNDED_TIME_SLOT"}

    # 4) Provenance & target ID pinning before side effect
    @guard_side_effect(
        lambda p: PinnedTarget(
            value=p["to"],
            source=p.get("target_source", "unknown"),
            target_id=p.get("recipient_id"),
        ).__and__ if False else {
            "to": PinnedTarget(
                value=p["to"],
                source=p.get("target_source", "unknown"),
                target_id=p.get("recipient_id"),
            )
        },
        allowed_sources=("user_request", "allowlist"),
        allowed_ids_by_field={"to": set(payload.get("trusted_recipient_ids", []))},
    )
    def _execute(p: dict) -> str:
        return send_customer_email(p)

    try:
        result = _execute(payload)
        return {"status": "ok", "detail": result}
    except TargetPinningError as exc:
        return {"status": "blocked", "reason": exc.rule_code, "message": str(exc)}


if __name__ == "__main__":
    cases = [
        {
            "name": "1. Placeholder leak in outbound email",
            "payload": {
                "to": "ops@client.com",
                "recipient_id": "rec_101",
                "trusted_recipient_ids": ["rec_101"],
                "target_source": "user_request",
                "subject": "Ticket Update",
                "body": "Hello, your invoice [PLACEHOLDER] is ready.",
                "escalated": False,
                "tier": "pro",
                "verified_slots": ["14:00"],
                "proposed_slot": "14:00",
            },
        },
        {
            "name": "2. Cross-field contradiction (escalated=True with tier=basic)",
            "payload": {
                "to": "ops@client.com",
                "recipient_id": "rec_101",
                "trusted_recipient_ids": ["rec_101"],
                "target_source": "user_request",
                "subject": "Urgent Escalation",
                "body": "Escalating ticket now.",
                "escalated": True,
                "tier": "basic",
                "verified_slots": ["14:00"],
                "proposed_slot": "14:00",
            },
        },
        {
            "name": "3. Ungrounded meeting time outside verified context",
            "payload": {
                "to": "ops@client.com",
                "recipient_id": "rec_101",
                "trusted_recipient_ids": ["rec_101"],
                "target_source": "user_request",
                "subject": "Call Slot",
                "body": "Let's meet at 17:30.",
                "escalated": False,
                "tier": "pro",
                "verified_slots": ["14:00", "15:30"],
                "proposed_slot": "17:30",
            },
        },
        {
            "name": "4. Poisoned email target from untrusted retrieved text",
            "payload": {
                "to": "attacker@external-drop.io",
                "recipient_id": "rec_999",
                "trusted_recipient_ids": ["rec_101"],
                "target_source": "retrieved_doc",
                "subject": "Forwarded Summary",
                "body": "Sending summary as requested in thread.",
                "escalated": False,
                "tier": "pro",
                "verified_slots": ["14:00"],
                "proposed_slot": "14:00",
            },
        },
        {
            "name": "5. Clean, grounded, and pinned payload",
            "payload": {
                "to": "ops@client.com",
                "recipient_id": "rec_101",
                "trusted_recipient_ids": ["rec_101"],
                "target_source": "user_request",
                "subject": "Confirmed Slot",
                "body": "Confirmed for 14:00.",
                "escalated": False,
                "tier": "pro",
                "verified_slots": ["14:00", "15:30"],
                "proposed_slot": "14:00",
            },
        },
    ]

    for c in cases:
        outcome = guarded_email_sender(c["payload"])
        print(f"{c['name']} -> {outcome}")
