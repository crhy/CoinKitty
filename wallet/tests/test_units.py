import unittest

from coinkitty_wallet.units import parse_amount, format_amount, KITTY, BTC


class ParseTest(unittest.TestCase):
    def test_one_and_a_half_both_ways(self):
        self.assertEqual(parse_amount("1.5", KITTY), 1_500_000_000_000_000_000_000_000)
        self.assertEqual(format_amount(1_500_000_000_000_000_000_000_000, KITTY), "1.5")

    def test_smallest_unit(self):
        self.assertEqual(parse_amount("0.000000000000000000000001", KITTY), 1)

    def test_too_many_fraction_digits(self):
        with self.assertRaises(ValueError):
            parse_amount("0.0000000000000000000000001", KITTY)  # 25 digits

    def test_rejects_garbage(self):
        for bad in ("1e5", "-1", "", "abc"):
            with self.assertRaises(ValueError):
                parse_amount(bad, KITTY)

    def test_thousands_separator(self):
        self.assertEqual(parse_amount("1,000.25", KITTY), 1000 * 10**24 + 25 * 10**22)

    def test_btc(self):
        self.assertEqual(parse_amount("1.5", BTC), 150_000_000)


class FormatTest(unittest.TestCase):
    def test_one_kitoshi(self):
        self.assertEqual(format_amount(1, KITTY), "<0.00000001")

    def test_thousands(self):
        self.assertEqual(format_amount(12345 * 10**24 + 6 * 10**23, KITTY), "12,345.6")

    def test_zero(self):
        self.assertEqual(format_amount(0, KITTY), "0")

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            format_amount(-1, KITTY)

    def test_truncates_down(self):
        # 1 KITTY + 1 kitoshi truncates to "1" at 8 decimals.
        self.assertEqual(format_amount(10**24 + 1, KITTY), "1")

    def test_full_precision(self):
        self.assertEqual(format_amount(1, KITTY, max_decimals=24),
                         "0.000000000000000000000001")


if __name__ == "__main__":
    unittest.main()
