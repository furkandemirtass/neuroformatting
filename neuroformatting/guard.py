import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional

from .schema import OutputSchema, ValidationIssue


@dataclass
class GuardResult:
    ok: bool
    status: str  # "valid", "needs_repair", "insufficient_grounding", "parse_error"
    data: Optional[Dict[str, Any]]
    issues: List[ValidationIssue]
    errors: List[str]
    raw_text: str


class StreamGuard:
    """Collects streamed chunks, validates at commit points, and classifies failures."""

    def __init__(self, schema: OutputSchema, context: Optional[Dict[str, Any]] = None) -> None:
        self.schema = schema
        self.context = context or {}
        self._chunks: List[str] = []

    def feed(self, chunk: str) -> None:
        if chunk:
            self._chunks.append(chunk)

    def finalize(self) -> GuardResult:
        raw_text = "".join(self._chunks).strip()
        cleaned = self._strip_markdown_fences(raw_text)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            msg = f"JSON parse error: {exc}"
            return GuardResult(
                ok=False,
                status="parse_error",
                data=None,
                issues=[ValidationIssue(field="$root", category="syntax", message=msg)],
                errors=[msg],
                raw_text=raw_text,
            )

        issues = self.schema.validate(parsed, context=self.context)
        if issues:
            has_ungrounded = any(issue.category == "ungrounded" for issue in issues)
            status = "insufficient_grounding" if has_ungrounded else "needs_repair"
            return GuardResult(
                ok=False,
                status=status,
                data=parsed if isinstance(parsed, dict) else None,
                issues=issues,
                errors=[issue.message for issue in issues],
                raw_text=raw_text,
            )

        return GuardResult(
            ok=True,
            status="valid",
            data=parsed,
            issues=[],
            errors=[],
            raw_text=raw_text,
        )

    def run_stream(self, chunks: Iterable[str]) -> GuardResult:
        for chunk in chunks:
            self.feed(chunk)
        return self.finalize()

    def iter_validated_units(self, chunks: Iterable[str]) -> Iterator[GuardResult]:
        """Accumulates streamed deltas and validates only when a top-level JSON object frame closes."""
        buffer: List[str] = []
        depth = 0
        in_string = False
        escape = False

        for chunk in chunks:
            for ch in chunk:
                if escape:
                    if depth > 0:
                        buffer.append(ch)
                    escape = False
                    continue

                if ch == "\\" and in_string:
                    if depth > 0:
                        buffer.append(ch)
                    escape = True
                    continue

                if ch == '"':
                    in_string = not in_string
                    if depth > 0:
                        buffer.append(ch)
                    continue

                if not in_string:
                    if ch == "{":
                        depth += 1
                        buffer.append(ch)
                        continue
                    if ch == "}" and depth > 0:
                        buffer.append(ch)
                        depth -= 1
                        if depth == 0:
                            unit_guard = StreamGuard(schema=self.schema, context=self.context)
                            yield unit_guard.run_stream(["".join(buffer)])
                            buffer.clear()
                        continue

                if depth > 0:
                    buffer.append(ch)

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        trimmed = text.strip()
        if trimmed.startswith("```"):
            lines = trimmed.splitlines()
            if len(lines) >= 2:
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                return "\n".join(lines).strip()
        return trimmed
