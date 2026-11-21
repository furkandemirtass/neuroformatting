# neuroformatting

Lightweight schema enforcement and semantic grounding for structured LLM streams.

## Why `neuroformatting`?

Validating JSON syntax is rarely enough for production LLM pipelines. Models can return syntactically valid JSON that still violates **semantic or grounding rules**—such as citing a `source_id` that does not exist in retrieved context or returning an out-of-range score.

`neuroformatting` gives you a minimal, dependency-free layer to validate streamed outputs against both structural types and context-aware semantic checks.

## Quick Example

```python
from neuroformatting import FieldRule, OutputSchema, StreamGuard

schema = OutputSchema(
    fields=[
        FieldRule(name="answer", expected_type=str),
        FieldRule(
            name="confidence",
            expected_type=float,
            semantic_check=lambda val, ctx: 0.0 <= val <= 1.0,
            error_message="confidence must be between 0.0 and 1.0",
        ),
        FieldRule(
            name="source_id",
            expected_type=str,
            semantic_check=lambda val, ctx: val in ctx.get("allowed_sources", []),
            error_message="source_id must match provided context",
        ),
    ]
)

guard = StreamGuard(schema=schema, context={"allowed_sources": ["doc-101"]})
result = guard.run_stream(['{"answer": "Grounded response", "confidence": 0.88, "source_id": "doc-101"}'])

print(result.ok, result.data)

PYTHONPATH=. python3 examples/demo.py
PYTHONPATH=. python3 -m unittest discover -s tests -v

