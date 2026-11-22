import unittest

from neuroformatting.retry_guard import RejectionCode, RetryGuard, TypedRejection


class TestRetryGuard(unittest.TestCase):
    def test_typed_rejection_builds_actionable_message(self) -> None:
        rej = TypedRejection(
            rule_code="ENUM_MISMATCH",
            code=RejectionCode.CONSTRAINT_VIOLATION,
            violated_field="priority",
            actual_summary="'urgent_now'",
            expected_summary="one of ['low', 'medium', 'high']",
            repair_hint="Map urgency to 'high' and keep only allowed enum values.",
        )
        msg = rej.to_correction_message()
        self.assertIn("ENUM_MISMATCH", msg)
        self.assertIn("priority", msg)
        self.assertIn("Map urgency to 'high'", msg)

    def test_retry_guard_stops_repeated_identical_failures(self) -> None:
        guard = RetryGuard(max_attempts=5, max_consecutive_same_error=2)
        rej = TypedRejection(
            rule_code="MISSING_FIELD",
            code=RejectionCode.SCHEMA_MISMATCH,
            violated_field="confidence",
            expected_summary="float between 0.0 and 1.0",
            repair_hint="Include a numeric 'confidence' key in the JSON object.",
        )

        first = guard.record_rejection(rej)
        self.assertTrue(first.allowed)
        self.assertEqual(first.consecutive_same_fingerprint, 1)

        second = guard.record_rejection(rej)
        self.assertFalse(second.allowed)
        self.assertEqual(second.reason, "repeated_identical_rejection")
        self.assertEqual(second.consecutive_same_fingerprint, 2)

    def test_retry_guard_allows_progress_when_error_changes(self) -> None:
        guard = RetryGuard(max_attempts=4, max_consecutive_same_error=2)
        r1 = TypedRejection(rule_code="INVALID_JSON", code=RejectionCode.INVALID_JSON)
        r2 = TypedRejection(
            rule_code="MISSING_FIELD",
            code=RejectionCode.SCHEMA_MISMATCH,
            violated_field="summary",
        )

        self.assertTrue(guard.record_rejection(r1).allowed)
        self.assertTrue(guard.record_rejection(r2).allowed)


if __name__ == "__main__":
    unittest.main()
