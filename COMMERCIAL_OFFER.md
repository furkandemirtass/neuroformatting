# neuroformatting — Commercial & Pilot Offering

## Who Pays and Why
Teams running LLM agents in production lose money and trust when **syntactically valid JSON** passes schema checks while containing semantic contradictions, ungrounded citations (`insufficient_grounding`), or silent routing/side-effect bugs.

High-priority buyers:
- **Customer Support & Routing Teams:** Prevent silent contradictions (such as `escalated: true` paired with `tier: "basic"`) or policy/refund window drift.
- **Healthcare / Clinic & Scheduling Workflows:** Block wrong time slots or ungrounded instructions before bookings or messages go out.
- **RAG & Reporting Pipelines:** Catch false-pass source IDs and numeric/latency drift before downstream actions execute.

## Tiers
1. **Open Source (`MIT` — Free):**
   - `StreamGuard` commit-point streaming validation
   - Grounding helpers (`1..n` index mapping) and fixture suite (`fixtures/semantic_cases.json`)
   - Local CLI runner, HTML/JSON reports, baseline regression check (`--baseline`), and risk scoring
2. **Team / CI Semantic Gate (Paid Tier):**
   - Automated PR/CI regression blocking when `insufficient_grounding` or `risk_score` rises after prompt or model changes
   - Custom domain rule packs & team-shared fixture libraries
   - Audit history and side-effect guard policies for production agents

## Pilot Validation Loop
- Collect real failure payloads from active agent teams and turn them into reproducible fixture cases.
- Run baseline vs. candidate checks on real prompts/models to quantify blocked semantic regressions before production rollout.
