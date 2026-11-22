import argparse
import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .guard import StreamGuard
from .regression import compare_audit_runs
from .risk import compute_audit_risk
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


def _default_escalation_tier_consistent(payload: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    if "escalated" in payload and "tier" in payload:
        if bool(payload.get("escalated")) and str(payload.get("tier", "")).lower() == "basic":
            return False
    return True


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
                    CrossFieldRule(
                name="escalation_tier_consistency",
                failure_category="repairable",
                check=_default_escalation_tier_consistent,
                error_message="escalated=true conflicts with tier=basic",
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
                "domain": case.get("domain", "general"),
                "expected": expected,
                "actual": res.status,
                "errors": res.errors,
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


def render_html_report(summary: Dict[str, Any], regression: Optional[Dict[str, Any]] = None) -> str:
    rows_html = []
    for row in summary["cases"]:
        badge_bg = "#dcfce7" if row["matched"] else "#fee2e2"
        badge_fg = "#166534" if row["matched"] else "#991b1b"
        verdict = "PASS" if row["matched"] else "FAIL"
        err_text = "; ".join(row.get("errors", [])) or "-"
        rows_html.append(
            f"""
            <tr>
              <td><code>{html.escape(str(row["id"]))}</code></td>
              <td>{html.escape(str(row["domain"]))}</td>
              <td><code>{html.escape(str(row["actual"]))}</code></td>
              <td><code>{html.escape(str(row["expected"]))}</code></td>
              <td>{html.escape(err_text)}</td>
              <td><span style="background:{badge_bg};color:{badge_fg};padding:2px 8px;border-radius:6px;font-weight:600;">{verdict}</span></td>
            </tr>
            """
        )

    reg_html = ""
    if regression is not None:
        gate_label = "PASSED" if regression["gate_passed"] else "BLOCKED (REGRESSION DETECTED)"
        gate_color = "#4ade80" if regression["gate_passed"] else "#f87171"
        reg_html = f"""
        <div class="summary" style="margin-top:12px;">
          Regression Gate: <strong style="color:{gate_color};">{html.escape(gate_label)}</strong>
          | Regressions: <strong>{regression["regression_count"]}</strong>
          | Improvements: <strong>{regression["improvement_count"]}</strong>
        </div>
        """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>neuroformatting Audit Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 32px; background: #0f172a; color: #e2e8f0; }}
    .card {{ background: #1e293b; border-radius: 12px; padding: 24px; max-width: 1100px; margin: auto; }}
    h1 {{ margin-top: 0; font-size: 22px; }}
    .summary {{ margin-bottom: 20px; color: #94a3b8; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #334155; }}
    th {{ color: #cbd5e1; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>neuroformatting — Semantic Grounding Audit Report</h1>
    <div class="summary">Passed: <strong>{summary["passed"]}/{summary["total"]}</strong> | Failed: <strong>{summary["failed"]}</strong></div>
    {reg_html}
    <table>
      <thead>
        <tr>
          <th>Case ID</th>
          <th>Domain</th>
          <th>Actual Status</th>
          <th>Expected</th>
          <th>Details</th>
          <th>Result</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows_html)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run semantic grounding fixture checks.")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path("fixtures/semantic_cases.json"),
        help="Path to semantic fixtures JSON file.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Optional baseline JSON audit summary to compare against.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional output path to write JSON audit summary.",
    )
    parser.add_argument(
        "--html-out",
        type=Path,
        default=None,
        help="Optional output path to write HTML audit report.",
    )
    args = parser.parse_args()

    summary = run_fixtures(args.fixtures)
    summary["risk"] = compute_audit_risk(summary)
    regression: Optional[Dict[str, Any]] = None
    if args.baseline is not None:
        baseline_data = json.loads(args.baseline.read_text(encoding="utf-8"))
        regression = compare_audit_runs(baseline_data, summary)
        summary["regression"] = regression

    print(f"Fixtures passed: {summary['passed']}/{summary['total']}")
    print(f"Audit risk: score={summary['risk']['risk_score']} ungrounded={summary['risk']['ungrounded_count']}")
    for row in summary["cases"]:
        mark = "PASS" if row["matched"] else "FAIL"
        print(f"  [{mark}] {row['id']}: actual={row['actual']} (expected={row['expected']})")

    if regression is not None:
        print(
            f"Regression gate: {'PASS' if regression['gate_passed'] else 'FAIL'} "
            f"(regressions={regression['regression_count']}, improvements={regression['improvement_count']})"
        )

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if args.html_out is not None:
        args.html_out.parent.mkdir(parents=True, exist_ok=True)
        args.html_out.write_text(render_html_report(summary, regression=regression), encoding="utf-8")

    if summary["failed"] > 0 or (regression is not None and not regression["gate_passed"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
