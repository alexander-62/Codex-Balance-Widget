from __future__ import annotations

import copy
import unittest

from usage_widget_common.redaction import redact, redaction_clean


class TestRedact(unittest.TestCase):
    def test_redacts_denylisted_keys_and_token_substring_without_mutating_input(self) -> None:
        original = {
            "email": "e@x.com",
            "user_id": "u1",
            "access_token": "tok",
            "nested": {"email": "y@x.com"},
        }
        original_copy = copy.deepcopy(original)

        result = redact(original, keys=frozenset({"email", "user_id"}))

        self.assertEqual(result["email"], "<redacted>")
        self.assertEqual(result["user_id"], "<redacted>")
        # access_token is redacted via the "token" substring rule, not via `keys`
        self.assertEqual(result["access_token"], "<redacted>")
        self.assertEqual(result["nested"]["email"], "<redacted>")

        # original dict must be untouched after the call
        self.assertEqual(original, original_copy)

    def test_recurses_into_lists(self) -> None:
        result = redact(
            [{"email": "e@x.com"}, {"other": "value"}],
            keys=frozenset({"email"}),
        )
        self.assertEqual(result, [{"email": "<redacted>"}, {"other": "value"}])

    def test_non_dict_non_list_values_returned_unchanged(self) -> None:
        self.assertEqual(redact("plain string", keys=frozenset()), "plain string")
        self.assertEqual(redact(42, keys=frozenset()), 42)
        self.assertIsNone(redact(None, keys=frozenset()))


class TestRedactionClean(unittest.TestCase):
    def test_jwt_prefix_is_not_clean(self) -> None:
        self.assertFalse(redaction_clean("token eyJhbGci"))

    def test_email_is_not_clean(self) -> None:
        self.assertFalse(redaction_clean("user@example.com"))

    def test_plain_text_is_clean(self) -> None:
        self.assertTrue(redaction_clean("clean text"))


if __name__ == "__main__":
    unittest.main()
