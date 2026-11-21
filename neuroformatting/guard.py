import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from .schema import OutputSchema


@dataclass
class GuardResult:
    ok: bool
    data: Optional[Dict[str, Any]]
    errors: List[str]
    raw_text: str


class StreamGuard:
    """Collects streamed chunks, parses JSON, and enforces schema + semantic rules."""

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
            return GuardResult(
                ok=False,
                data=None,
                errors=[f"JSON parse error: {exc}"],
                raw_text=raw_text,
            )

        errors = self.schema.validate(parsed, context=self.context)
        if errors:
            return GuardResult(
                ok=False,
                data=parsed if isinstance(parsed, dict) else None,
                errors=errors,
                raw_text=raw_text,
            )

        return GuardResult(ok=True, data=parsed, errors=[], raw_text=raw_text)

    def run_stream(self, chunks: Iterable[str]) -> GuardResult:
        for chunk in chunks:
            self.feed(chunk)
        return self.finalize()

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
