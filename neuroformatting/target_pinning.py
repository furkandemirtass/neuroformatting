from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class PinnedTarget:
    value: str
    source: str  # e.g. "user_request", "allowlist", "retrieved_doc", "email_body"
    target_id: Optional[str] = None


class TargetPinningError(ValueError):
    def __init__(self, message: str, *, field_name: str, source: str, rule_code: str = "UNTRUSTED_TARGET") -> None:
        super().__init__(message)
        self.field_name = field_name
        self.source = source
        self.rule_code = rule_code


def verify_pinned_targets(
    payload: dict[str, Any],
    targets: dict[str, PinnedTarget],
    *,
    allowed_sources: Iterable[str] = ("user_request", "allowlist"),
    allowed_ids_by_field: Optional[dict[str, set[str]]] = None,
) -> dict[str, Any]:
    """Ensures action targets originate from trusted sources and match pinned IDs."""
    trusted_sources = set(allowed_sources)
    id_allowlists = allowed_ids_by_field or {}

    for field_name, pinned in targets.items():
        if field_name not in payload:
            raise TargetPinningError(
                f"Missing required payload field '{field_name}' for pinned target.",
                field_name=field_name,
                source=pinned.source,
                rule_code="MISSING_PINNED_TARGET_FIELD",
            )

        payload_value = str(payload[field_name])
        if payload_value != pinned.value:
            raise TargetPinningError(
                f"Payload '{field_name}' ('{payload_value}') diverged from pinned target ('{pinned.value}').",
                field_name=field_name,
                source=pinned.source,
                rule_code="TARGET_VALUE_MISMATCH",
            )

        if pinned.source not in trusted_sources:
            raise TargetPinningError(
                f"Blocked side effect: '{field_name}' came from untrusted source '{pinned.source}'.",
                field_name=field_name,
                source=pinned.source,
                rule_code="UNTRUSTED_TARGET_SOURCE",
            )

        required_ids = id_allowlists.get(field_name)
        if required_ids is not None:
            if not pinned.target_id or pinned.target_id not in required_ids:
                raise TargetPinningError(
                    f"Blocked side effect: target_id '{pinned.target_id}' for '{field_name}' is not in trusted request IDs.",
                    field_name=field_name,
                    source=pinned.source,
                    rule_code="UNPINNED_TARGET_ID",
                )

    return payload


def guard_side_effect(
    targets_builder: Callable[[dict[str, Any]], dict[str, PinnedTarget]],
    *,
    allowed_sources: Iterable[str] = ("user_request", "allowlist"),
    allowed_ids_by_field: Optional[dict[str, set[str]]] = None,
) -> Callable[[Callable[[dict[str, Any]], T]], Callable[[dict[str, Any]], T]]:
    """Decorator that enforces target provenance and ID pinning right before a side effect executes."""

    def decorator(action_fn: Callable[[dict[str, Any]], T]) -> Callable[[dict[str, Any]], T]:
        def wrapper(payload: dict[str, Any]) -> T:
            pinned_map = targets_builder(payload)
            verify_pinned_targets(
                payload,
                pinned_map,
                allowed_sources=allowed_sources,
                allowed_ids_by_field=allowed_ids_by_field,
            )
            return action_fn(payload)

        return wrapper

    return decorator
