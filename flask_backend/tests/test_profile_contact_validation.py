import os
import sys
import unittest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIn0."
    "test-signature",
)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.routes.core import normalize_philippine_mobile_number


class ProfileContactValidationTest(unittest.TestCase):
    def test_normalizes_local_mobile_to_e164(self):
        self.assertEqual(
            normalize_philippine_mobile_number("09270292527"),
            "+639270292527",
        )

    def test_keeps_normalized_mobile(self):
        self.assertEqual(
            normalize_philippine_mobile_number("+639270292527"),
            "+639270292527",
        )

    def test_trims_surrounding_whitespace(self):
        self.assertEqual(
            normalize_philippine_mobile_number("  09270292527  "),
            "+639270292527",
        )

    def test_rejects_invalid_prefix(self):
        with self.assertRaisesRegex(ValueError, "Invalid phone number."):
            normalize_philippine_mobile_number("09110292527")

    def test_rejects_wrong_start(self):
        with self.assertRaisesRegex(ValueError, "Phone number must start with 09."):
            normalize_philippine_mobile_number("639270292527")

    def test_rejects_wrong_local_length(self):
        with self.assertRaisesRegex(ValueError, "Phone number must contain exactly 11 digits."):
            normalize_philippine_mobile_number("0927029252")

    def test_rejects_letters_and_spaces(self):
        with self.assertRaisesRegex(ValueError, "Invalid phone number."):
            normalize_philippine_mobile_number("09270A92527")

        with self.assertRaisesRegex(ValueError, "Invalid phone number."):
            normalize_philippine_mobile_number("0927 029 2527")


if __name__ == "__main__":
    unittest.main()
