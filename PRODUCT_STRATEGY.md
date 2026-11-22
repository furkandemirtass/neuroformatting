# neuroformatting — Product & Monetization Blueprint

## Core Thesis
Syntax/schema validation (`200 OK`) does not guarantee semantic safety. `neuroformatting` catches `insufficient_grounding` ("false passes"), cross-field contradictions, and stream commit-point violations before side effects trigger.

## Open-Core Split
1. **Open Source (`MIT` — Free):**
   - `StreamGuard` commit-point streaming validator
   - Two-stage grounding (`membership` + `support`) and `1..n` index mapping
   - Local CLI fixture runner (`fixtures/semantic_cases.json`) and baseline regression gate (`--baseline`)
2. **Paid B2B / Cloud Audit & CI Gate (Commercial Layer):**
   - **Hosted Audit History & PR Diffs:** Track semantic regressions, `insufficient_grounding` trends, and domain-specific error rates across model/prompt upgrades.
   - **Domain Compliance Packs:** Pre-built semantic rule sets for high-stakes workflows (clinic scheduling/triage, customer support policies, financial/numeric reporting).
   - **Side-Effect Guard & Policy Enforcement:** Block external actions (bookings, refunds, emails, DB writes) until semantic checks pass.

## Immediate Distribution & Traction Loop
- Publish and refine real-world failure fixtures in `fixtures/semantic_cases.json` based on community and production feedback.
- Pair CLI/HTML audit reports with a live interactive browser playground (`neuroformatting.com` / hosted demo) so engineers can test "false pass" cases in seconds.
- Validate willingness to pay with teams running high-stakes agents (e.g., clinics, support desks, vertical SaaS).
