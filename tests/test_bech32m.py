import unittest

from coinkitty_wallet.bech32m import decode, encode, encode_address, decode_address, is_valid_address, HRP


class DecodeTest(unittest.TestCase):
    def test_official_vectors_ok(self):
        for addr in ("A1LQFN3A", "a1lqfn3a",
                     "abcdef1l7aum6echk45nj3s0wdvt2fg8x9yrzpqzd3ryx"):
            hrp, data5 = decode(addr)
            self.assertIsInstance(hrp, str)
            self.assertIsInstance(data5, list)

    def test_case_insensitive_returns_lowercase(self):
        hrp, _ = decode("A1LQFN3A")
        self.assertEqual(hrp, "a")

    def test_mixed_case_raises(self):
        with self.assertRaises(ValueError):
            decode("A1LqFN3A")

    def test_bad_checksum_raises(self):
        with self.assertRaises(ValueError):
            decode("a1lqfn3b")


class AddressTest(unittest.TestCase):
    def test_round_trip(self):
        payload = bytes(range(20))
        addr = encode_address(payload)
        self.assertEqual(decode_address(addr), payload)
        self.assertTrue(is_valid_address(addr))

    def test_32_byte_round_trip(self):
        payload = bytes(range(32))
        self.assertEqual(decode_address(encode_address(payload)), payload)

    def test_bad_length_raises(self):
        with self.assertRaises(ValueError):
            encode_address(bytes(21))

    def test_wrong_hrp_raises(self):
        other = encode("kittyx", [0, 1, 2])
        with self.assertRaises(ValueError):
            decode_address(other)

    def test_single_char_change_invalid(self):
        addr = encode_address(bytes(range(20)))
        alphabet = "qpzry9x8gf2tvdw0s3jn54khce6mua7l1"
        for index, original in enumerate(addr):
            for repl in alphabet:
                if repl == original:
                    continue
                mutated = addr[:index] + repl + addr[index + 1:]
                self.assertFalse(is_valid_address(mutated))


if __name__ == "__main__":
    unittest.main()
