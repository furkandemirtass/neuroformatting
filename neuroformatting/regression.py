from typing import Any, Dict, List


def compare_audit_runs(baseline: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two fixture/audit summaries to detect semantic regressions."""
    base_cases = {c["id"]: c for c in baseline.get("cases", [])}
    cand_cases = {c["id"]: c for c in candidate.get("cases", [])}

    regressions: List[Dict[str, Any]] = []
    improvements: List[Dict[str, Any]] = []

    for case_id, cand_row in cand_cases.items():
        base_row = base_cases.get(case_id)
        if not base_row:
            continue
        was_ok = bool(base_row.get("matched"))
        now_ok = bool(cand_row.get("matched"))

        if was_ok and not now_ok:
            regressions.append(
                {
                    "id": case_id,
                    "domain": cand_row.get("domain", "general"),
                    "baseline_status": base_row.get("actual"),
                    "candidate_status": cand_row.get("actual"),
                    "expected": cand_row.get("expected"),
                }
            )
        elif not was_ok and now_ok:
            improvements.append(
                {
                    "id": case_id,
                    "domain": cand_row.get("domain", "general"),
                    "candidate_status": cand_row.get("actual"),
                }
            )

    return {
        "baseline_passed": baseline.get("passed", 0),
        "candidate_passed": candidate.get("passed", 0),
        "total": candidate.get("total", 0),
        "regression_count": len(regressions),
        "improvement_count": len(improvements),
        "regressions": regressions,
        "improvements": improvements,
        "gate_passed": len(regressions) == 0,
    }
