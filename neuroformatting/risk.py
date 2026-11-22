from typing import Any, Dict, List


STATUS_RISK_WEIGHTS: Dict[str, int] = {
    "valid": 0,
    "needs_repair": 2,
    "insufficient_grounding": 5,
    "invalid": 4,
}


def compute_audit_risk(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Computes a practical risk score and failure breakdown from an audit summary."""
    cases: List[Dict[str, Any]] = summary.get("cases", [])
    by_status: Dict[str, int] = {}
    total_risk_score = 0
    ungrounded_count = 0

    for case in cases:
        actual = str(case.get("actual", "unknown"))
        by_status[actual] = by_status.get(actual, 0) + 1
        total_risk_score += STATUS_RISK_WEIGHTS.get(actual, 3)
        if actual == "insufficient_grounding":
            ungrounded_count += 1

    return {
        "total_cases": len(cases),
        "risk_score": total_risk_score,
        "ungrounded_count": ungrounded_count,
        "by_status": by_status,
    }
