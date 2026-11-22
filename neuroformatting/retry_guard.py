from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RejectionCode(str, Enum):
    INVALID_JSON = "INVALID_JSON"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    GUARD_BLOCKED = "GUARD_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TypedRejection:
    rule_code: str
    code: RejectionCode = RejectionCode.UNKNOWN
    violated_field: str | None = None
    actual_summary: str = ""
    expected_summary: str = ""
    repair_hint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        raw = f"{self.rule_code}|{self.code.value}|{self.violated_field or '*'}|{self.expected_summary}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]

    def to_correction_message(self) -> str:
        target = self.violated_field or "payload"
        parts = [f"REJECTED [{self.rule_code}] on '{target}'."]
        if self.expected_summary:
            parts.append(f"Expected: {self.expected_summary}.")
        if self.actual_summary:
            parts.append(f"Observed: {self.actual_summary}.")
        if self.repair_hint:
            parts.append(f"Fix: {self.repair_hint}")
        return " ".join(parts)


@dataclass
class RetryDecision:
    allowed: bool
    reason: str
    attempt: int
    consecutive_same_fingerprint: int
    rejection: TypedRejection | None = None


class RetryGuard:
    def __init__(self, max_attempts: int = 3, max_consecutive_same_error: int = 2) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if max_consecutive_same_error < 1:
            raise ValueError("max_consecutive_same_error must be at least 1")
        self.max_attempts = max_attempts
        self.max_consecutive_same_error = max_consecutive_same_error
        self._attempts = 0
        self._last_fingerprint: str | None = None
        self._consecutive_same = 0
        self._history: list[TypedRejection] = []

    @property
    def attempts(self) -> int:
        return self._attempts

    @property
    def history(self) -> list[TypedRejection]:
        return list(self._history)

    def record_rejection(self, rejection: TypedRejection) -> RetryDecision:
        self._attempts += 1
        self._history.append(rejection)

        fp = rejection.fingerprint
        if fp == self._last_fingerprint:
            self._consecutive_same += 1
        else:
            self._last_fingerprint = fp
            self._consecutive_same = 1

        if self._attempts >= self.max_attempts:
            return RetryDecision(
                allowed=False,
                reason="max_attempts_reached",
                attempt=self._attempts,
                consecutive_same_fingerprint=self._consecutive_same,
                rejection=rejection,
            )

        if self._consecutive_same >= self.max_consecutive_same_error:
            return RetryDecision(
                allowed=False,
                reason="repeated_identical_rejection",
                attempt=self._attempts,
                consecutive_same_fingerprint=self._consecutive_same,
                rejection=rejection,
            )

        return RetryDecision(
            allowed=True,
            reason="retry_with_typed_feedback",
            attempt=self._attempts,
            consecutive_same_fingerprint=self._consecutive_same,
            rejection=rejection,
        )
