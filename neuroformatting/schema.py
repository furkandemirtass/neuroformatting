from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class FieldRule:
    name: str
    expected_type: type
    required: bool = True
    semantic_check: Optional[Callable[[Any, Dict[str, Any]], bool]] = None
    error_message: str = "Invalid field value"


@dataclass
class OutputSchema:
    fields: List[FieldRule] = field(default_factory=list)
    allow_extra_fields: bool = False

    def validate(self, payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[str]:
        ctx = context or {}
        errors: List[str] = []

        if not isinstance(payload, dict):
            return ["Payload must be a JSON object (dict)."]

        expected_names = {rule.name for rule in self.fields}
        if not self.allow_extra_fields:
            extra_keys = set(payload.keys()) - expected_names
            if extra_keys:
                errors.append(f"Unexpected extra fields: {sorted(extra_keys)}")

        for rule in self.fields:
            if rule.name not in payload:
                if rule.required:
                    errors.append(f"Missing required field: '{rule.name}'")
                continue

            value = payload[rule.name]
            # bool is a subclass of int in Python; handle carefully
            if rule.expected_type is int and isinstance(value, bool):
                errors.append(f"Field '{rule.name}' expected int, got bool.")
                continue

            if not isinstance(value, rule.expected_type):
                errors.append(
                    f"Field '{rule.name}' expected {rule.expected_type.__name__}, "
                    f"got {type(value).__name__}."
                )
                continue

            if rule.semantic_check is not None:
                try:
                    if not rule.semantic_check(value, ctx):
                        errors.append(f"Semantic check failed for '{rule.name}': {rule.error_message}")
                except Exception as exc:
                    errors.append(f"Semantic check error for '{rule.name}': {exc}")

        return errors
