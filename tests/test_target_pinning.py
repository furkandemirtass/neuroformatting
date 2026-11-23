import unittest
from neuroformatting import PinnedTarget, TargetPinningError, guard_side_effect


class TestTargetPinning(unittest.TestCase):
    def test_allows_trusted_source_and_pinned_id(self):
        @guard_side_effect(
            lambda p: {
                "to": PinnedTarget(
                    value=p["to"],
                    source=p["source"],
                    target_id=p["recipient_id"],
                )
            },
            allowed_sources=("user_request",),
            allowed_ids_by_field={"to": {"rec_101"}},
        )
        def send_action(payload: dict) -> str:
            return f"sent:{payload['to']}"

        result = send_action(
            {"to": "ops@client.com", "source": "user_request", "recipient_id": "rec_101"}
        )
        self.assertEqual(result, "sent:ops@client.com")

    def test_blocks_untrusted_retrieved_source(self):
        @guard_side_effect(
            lambda p: {
                "to": PinnedTarget(
                    value=p["to"],
                    source=p["source"],
                    target_id=p["recipient_id"],
                )
            },
            allowed_sources=("user_request",),
            allowed_ids_by_field={"to": {"rec_101"}},
        )
        def send_action(payload: dict) -> str:
            return f"sent:{payload['to']}"

        with self.assertRaises(TargetPinningError) as ctx:
            send_action(
                {"to": "attacker@evil.io", "source": "retrieved_doc", "recipient_id": "rec_101"}
            )
        self.assertEqual(ctx.exception.rule_code, "UNTRUSTED_TARGET_SOURCE")

    def test_blocks_unpinned_target_id(self):
        @guard_side_effect(
            lambda p: {
                "to": PinnedTarget(
                    value=p["to"],
                    source=p["source"],
                    target_id=p["recipient_id"],
                )
            },
            allowed_sources=("user_request",),
            allowed_ids_by_field={"to": {"rec_101"}},
        )
        def send_action(payload: dict) -> str:
            return f"sent:{payload['to']}"

        with self.assertRaises(TargetPinningError) as ctx:
            send_action(
                {"to": "ops@client.com", "source": "user_request", "recipient_id": "rec_999"}
            )
        self.assertEqual(ctx.exception.rule_code, "UNPINNED_TARGET_ID")


if __name__ == "__main__":
    unittest.main()
