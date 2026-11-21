from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ValidationIssue:
    field: str
    category: str  # "syntax", "type", "repairable", "ungrounded"
    message: str


@dataclass
class FieldRule:
    name: str
    expected_type: type
    required: bool = True
    semantic_check: Optional[Callable[[Any, Dict[str, Any]], bool]] = None
    failure_category: str = "repairable"  # "repairable" or "ungrounded"
    error_message: str = "Invalid field value"


@dataclass
class CrossFieldRule:
    name: str
    check: Callable[[Dict[str, Any], Dict[str, Any]], bool]
    failure_category: str = "repairable"
    error_message: str = "Cross-field semantic check failed"


@dataclass
class OutputSchema:
    fields: List[FieldRule] = field(default_factory=list)
    cross_field_rules: List[CrossFieldRule] = field(default_factory=list)
    allow_extra_fields: bool = False

    def validate(self, payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[ValidationIssue]:
        ctx = context or {}
        issues: List[ValidationIssue] = []

        if not isinstance(payload, dict):
            return [ValidationIssue(field="$root", category="type", message="Payload must be a JSON object (dict).")]

        expected_names = {rule.name for rule in self.fields}
        if not self.allow_extra_fields:
            extra_keys = set(payload.keys()) - expected_names
            if extra_keys:
                issues.append(
                    ValidationIssue(
                        field="$root",
                        category="repairable",
                        message=f"Unexpected extra fields: {sorted(extra_keys)}",
                    )
                )

        for rule in self.fields:
            if rule.name not in payload:
                if rule.required:
                    issues.append(
                        ValidationIssue(
                            field=rule.name,
                            category="repairable",
                            message=f"Missing required field: '{rule.name}'",
                        )
                    )
                continue

            value = payload[rule.name]
            if rule.expected_type is int and isinstance(value, bool):
                issues.append(
                    ValidationIssue(
                        field=rule.name,
                        category="type",
                        message=f"Field '{rule.name}' expected int, got bool.",
                    )
                )
                continue

            if not isinstance(value, rule.expected_type):
                issues.append(
                    ValidationIssue(
                        field=rule.name,
                        category="type",
                        message=f"Field '{rule.name}' expected {rule.expected_type.__name__}, got {type(value).__name__}.",
                    )
                )
                continue

            if rule.semantic_check is not None:
                try:
                    if not rule.semantic_check(value, ctx):
                        issues.append(
                            ValidationIssue(
                                field=rule.name,
                                category=rule.failure_category,
                                message=f"Semantic check failed for '{rule.name}': {rule.error_message}",
                            )
                        )
                except Exception as exc:
                    issues.append(
                        ValidationIssue(
                            field=rule.name,
                            category=rule.failure_category,
                            message=f"Semantic check error for '{rule.name}': {exc}",
                        )
                    )

        if not issues:
            for cf_rule in self.cross_field_rules:
                try:
                    if not cf_rule.check(payload, ctx):
                        issues.append(
                            ValidationIssue(
                                field=cf_rule.name,
                                category=cf_rule.failure_category,
                                message=cf_rule.error_message,
                            )
                        )
                except Exception as exc:
                    issues.append(
                        ValidationIssue(
                            field=cf_rule.name,
                            category=cf_rule.failure_category,
                            message=f"Cross-field rule error '{cf_rule.name}': {exc}",
                        )
                    )

        return issues
