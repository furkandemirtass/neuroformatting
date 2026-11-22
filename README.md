# neuroformatting

Commit-point streaming validation and semantic grounding for LLM outputs.

Syntactically valid JSON (`200 OK` from a schema check) can still fail in production: a cited `source_id` may exist in context without supporting the claim (`insufficient_grounding`), fields within the same payload can contradict each other (`reasoning_tokens: 0` alongside non-empty reasoning text), or numeric/time details can drift from the source.

## Quickstart

```bash
pip install -e .
python3 -m neuroformatting.cli --html-out /tmp/neuroformatting-report.html --json-out /tmp/neuroformatting-report.json
PYTHONPATH=. python3 -m unittest discover -s tests -v


#### 2. GitHub Actions CI İş Akışını Ekle (`.github/workflows/semantic-audit.yml`)
```bash
mkdir -p .github/workflows
cat << 'EOF' > .github/workflows/semantic-audit.yml
name: Semantic Audit

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Run unit tests
        run: PYTHONPATH=. python3 -m unittest discover -s tests -v
      - name: Run semantic fixture audit
        run: python3 -m neuroformatting.cli --html-out audit-report.html --json-out audit-report.json
      - name: Upload audit report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: neuroformatting-audit-report
          path: |
            audit-report.html
            audit-report.json
