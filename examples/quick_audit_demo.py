from neuroformatting import PinnedTarget, TargetPinningError, guard_side_effect


@guard_side_effect(
    lambda payload: {
        "to": PinnedTarget(
            value=payload["to"],
            source=payload["source"],
            target_id=payload["recipient_id"],
        )
    },
    allowed_sources=("verified_crm",),
    allowed_ids_by_field={"to": {"acct_01"}},
)
def dispatch_notification(payload: dict) -> str:
    return f"DISPATCHED -> {payload['to']} (id={payload['recipient_id']})"


def run_demo() -> None:
    cases = [
        {"to": "cfo@company.com", "source": "verified_crm", "recipient_id": "acct_01"},
        {"to": "outside@malicious.org", "source": "rag_snippet", "recipient_id": "acct_01"},
        {"to": "cfo@company.com", "source": "verified_crm", "recipient_id": "acct_99"},
    ]
    for idx, item in enumerate(cases, start=1):
        try:
            res = dispatch_notification(item)
            print(f"Case {idx}: ALLOWED -> {res}")
        except TargetPinningError as err:
            print(f"Case {idx}: BLOCKED [{err.rule_code}] -> {err}")


if __name__ == "__main__":
    run_demo()
