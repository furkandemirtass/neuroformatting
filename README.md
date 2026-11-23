# neuroformatting

Deterministic output validation, grounding checks, and **pre-side-effect target pinning** for LLM & AI agent workflows in Python.

### What It Catches Before Execution (`200 OK` Is Not Enough)
Run `PYTHONPATH=. python3 examples/production_failures.py` to reproduce all 5 cases locally:

```text
1. Placeholder leak in outbound email -> {'status': 'blocked', 'reason': 'PLACEHOLDER_DETECTED'}
2. Cross-field contradiction (escalated=True with tier=basic) -> {'status': 'blocked', 'reason': 'CONTRADICTORY_TIER_FOR_ESCALATION'}
3. Ungrounded meeting time outside verified context -> {'status': 'blocked', 'reason': 'UNGROUNDED_TIME_SLOT'}
4. Poisoned email target from untrusted retrieved text -> {'status': 'blocked', 'reason': 'UNTRUSTED_TARGET_SOURCE', 'message': "Blocked side effect: 'to' came from untrusted source 'retrieved_doc'."}
5. Clean, grounded, and pinned payload -> {'status': 'ok', 'detail': 'SENT email to ops@client.com | subject=Confirmed Slot'}

### Commercial & Freelance Implementation
Need deterministic guardrails, Pydantic validation, or side-effect safety wired into an existing Python agent/API? Available for fixed-scope guardrail audits and production integrations.

---

# neuroformatting

Commit-point streaming validation and semantic grounding for LLM outputs.

Syntactically valid JSON (`200 OK` from a schema check) can still fail in production: a cited `source_id` may exist in context without supporting the claim (`insufficient_grounding`), fields within the same payload can contradict each other (`reasoning_tokens: 0` alongside non-empty reasoning text), or numeric/time details can drift from the source.

## Interactive Demo & Audit Report

Open the interactive browser playground locally:

```bash
open demo/index.html

pip install -e .
python3 -m neuroformatting.cli --html-out /tmp/neuroformatting-report.html --json-out /tmp/neuroformatting-report.json
PYTHONPATH=. python3 -m unittest discover -s tests -v


### 2. Testleri Çalıştır ve `v0.2.2` Olarak Gönder
```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
git add .
git commit -m "docs(readme): link interactive browser demo and regression/risk capabilities"
git tag v0.2.2
git push && git push --tags

cat << 'EOF' > README.md
# neuroformatting

Commit-point streaming validation and semantic grounding for LLM outputs.

Syntactically valid JSON (200 OK from a schema check) can still fail in production: a cited `source_id` may exist in context without supporting the claim (`insufficient_grounding`), fields within the same payload can contradict each other (`reasoning_tokens: 0` alongside non-empty reasoning text), or numeric/time details can drift from the source.

## Interactive Demo & Audit Report

Open the interactive browser playground locally:

`open demo/index.html`

Or generate a standalone HTML/JSON audit report from the 10-case semantic fixture suite:

`pip install -e .`
`python3 -m neuroformatting.cli --html-out /tmp/neuroformatting-report.html --json-out /tmp/neuroformatting-report.json`
`PYTHONPATH=. python3 -m unittest discover -s tests -v`

## Key Capabilities

- **Commit-point streaming (`StreamGuard`):** Validates structured units as objects/frames close rather than on raw mid-token deltas.
- **Two-stage grounding (`membership` + `support`):** Separates whether a referenced source exists from whether the cited content actually supports the claim.
- **1..n index mapping (`build_indexed_sources`, `resolve_source_index`):** Lets models pick from a bounded integer index while mapping back to real IDs in application code.
- **Versioned semantic fixtures (`fixtures/semantic_cases.json`):** 10 real-world failure and valid cases across RAG, clinic scheduling, support policy, and telemetry.
- **Regression gate & risk scoring (`compare_audit_runs`, `compute_audit_risk`):** Compares baseline vs. candidate runs in CLI/CI and scores ungrounded/contradictory outputs.

## License

MIT

## Custom Schemas & Production Guardrails

Need strict Pydantic v2 validation, deterministic output rules, or reliability guardrails for your LLM workflows?

I build production-ready Python validation layers for structured outputs, tool/API safety checks, and retry/error handling.

- **Fiverr Gig:** https://www.fiverr.com/demirtasfurkan/create-python-guardrails-for-ai
- Feel free to reach out with your schema requirements, sample payloads, or target LLM stack before ordering.
