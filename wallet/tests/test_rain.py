import unittest

from coinkitty_wallet.rain import split_equal, validate_custom


class SplitTest(unittest.TestCase):
    def test_100_among_3(self):
        self.assertEqual(split_equal(100, ["a", "b", "c"]), {"a": 34, "b": 33, "c": 33})

    def test_sums_exactly(self):
        total = 10**24 + 7
        for n in range(1, 51):
            members = [f"m{i}" for i in range(n)]
            result = split_equal(total, members)
            self.assertEqual(len(result), n)
            self.assertEqual(sum(result.values()), total)

    def test_no_members(self):
        with self.assertRaises(ValueError):
            split_equal(10, [])

    def test_duplicate_ids(self):
        with self.assertRaises(ValueError):
            split_equal(10, ["a", "a"])

    def test_non_positive_total(self):
        with self.assertRaises(ValueError):
            split_equal(0, ["a"])
        with self.assertRaises(ValueError):
            split_equal(-5, ["a"])


class ValidateTest(unittest.TestCase):
    def test_valid(self):
        self.assertIs(validate_custom(10, {"a": 4, "b": 6}), None)

    def test_sum_mismatch(self):
        with self.assertRaises(ValueError):
            validate_custom(10, {"a": 4, "b": 5})

    def test_non_positive(self):
        with self.assertRaises(ValueError):
            validate_custom(10, {"a": 0, "b": 10})
        with self.assertRaises(ValueError):
            validate_custom(10, {"a": -1, "b": 11})

    def test_empty(self):
        with self.assertRaises(ValueError):
            validate_custom(10, {})


if __name__ == "__main__":
    unittest.main()
