from __future__ import annotations

import unittest

from usage_widget_common.errors import FetchError


class TestFetchError(unittest.TestCase):
    def test_default_retryable_is_false(self) -> None:
        exc = FetchError("msg")
        self.assertFalse(exc.retryable)

    def test_explicit_retryable_true_and_message(self) -> None:
        exc = FetchError("msg", retryable=True)
        self.assertTrue(exc.retryable)
        self.assertEqual(str(exc), "msg")

    def test_is_subclass_of_runtime_error(self) -> None:
        self.assertTrue(issubclass(FetchError, RuntimeError))


if __name__ == "__main__":
    unittest.main()
