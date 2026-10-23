"""Tests for the send-screen logic: ranking, search, payment-request URIs."""

import unittest
from urllib.parse import urlencode

from coinkitty_wallet.bech32m import encode_address
from coinkitty_wallet.models import Contact, Transaction
from coinkitty_wallet.send_logic import top_contacts, search_contacts, PaymentRequest

ADDRESS = encode_address(bytes(range(20)))


class TopContactsTest(unittest.TestCase):
    def setUp(self):
        self.contacts = [
            Contact(id="1", name="Ada", address=ADDRESS),
            Contact(id="2", name="Ben", address=ADDRESS, favorite=True),
            Contact(id="3", name="Cai", address=ADDRESS),
            Contact(id="4", name="Dot", address=ADDRESS),
            Contact(id="5", name="Eve", address=ADDRESS),
            Contact(id="6", name="Fred", address=ADDRESS),
        ]
        self.transactions = [
            Transaction(id="a", kind="send", asset="KITTY", amount=1, counterparty="Cai", memo="", timestamp=1),
            Transaction(id="b", kind="send", asset="KITTY", amount=2, counterparty="Cai", memo="", timestamp=2),
            Transaction(id="c", kind="send", asset="KITTY", amount=3, counterparty="Ada", memo="", timestamp=3),
            Transaction(id="d", kind="receive", asset="KITTY", amount=9, counterparty="Dot", memo="", timestamp=4),
            Transaction(id="e", kind="rain", asset="KITTY", amount=4, counterparty="Eve", memo="", timestamp=5),
        ]

    def test_favorites_first(self):
        ranked = top_contacts(self.contacts, self.transactions)
        self.assertEqual(ranked[0].name, "Ben")

    def test_send_counts_order(self):
        ranked = top_contacts(self.contacts, self.transactions)
        self.assertEqual([c.name for c in ranked], ["Ben", "Cai", "Ada", "Dot", "Eve"])

    def test_name_tie_break(self):
        ranked = top_contacts(self.contacts, self.transactions)
        self.assertEqual([c.name for c in ranked[3:]], ["Dot", "Eve"])

    def test_at_most_n(self):
        ranked = top_contacts(self.contacts, self.transactions, n=2)
        self.assertEqual([c.name for c in ranked], ["Ben", "Cai"])

    def test_limit_larger_than_contacts(self):
        ranked = top_contacts(self.contacts, self.transactions, n=99)
        self.assertEqual(len(ranked), len(self.contacts))


class SearchContactsTest(unittest.TestCase):
    def setUp(self):
        self.contacts = [
            Contact(id="1", name="Zoe", address=ADDRESS),
            Contact(id="2", name="ada", address=ADDRESS),
            Contact(id="3", name="Adrian", address=ADDRESS),
        ]

    def test_empty_query_all_sorted(self):
        found = search_contacts(self.contacts, "")
        self.assertEqual([c.name for c in found], ["Adrian", "Zoe", "ada"])

    def test_case_insensitive_substring(self):
        found = search_contacts(self.contacts, "AD")
        self.assertEqual([c.name for c in found], ["Adrian", "ada"])

    def test_no_match(self):
        self.assertEqual(search_contacts(self.contacts, "zzz"), [])


class PaymentRequestTest(unittest.TestCase):
    def test_round_trip_plain(self):
        request = PaymentRequest(address=ADDRESS, asset="KITTY", amount=10**24, memo="hi")
        self.assertEqual(PaymentRequest.from_uri(request.to_uri()), request)

    def test_round_trip_tricky_memo(self):
        memo = "lunch & tea 3pm +tip"
        request = PaymentRequest(address=ADDRESS, asset="BTC", amount=0, memo=memo)
        uri = request.to_uri()
        expected = urlencode({"memo": memo})[len("memo="):]
        self.assertIn(f"memo={expected}", uri)
        self.assertEqual(PaymentRequest.from_uri(uri), request)

    def test_wrong_scheme(self):
        with self.assertRaises(ValueError):
            PaymentRequest.from_uri("bitcoin:" + ADDRESS + "?asset=KITTY&amount=1&memo=")

    def test_invalid_address(self):
        with self.assertRaises(ValueError):
            PaymentRequest.from_uri("coinkitty:not-an-address?asset=KITTY&amount=1&memo=")

    def test_non_integer_amount(self):
        with self.assertRaises(ValueError):
            PaymentRequest.from_uri("coinkitty:" + ADDRESS + "?asset=KITTY&amount=1.5&memo=")

    def test_negative_amount(self):
        with self.assertRaises(ValueError):
            PaymentRequest.from_uri("coinkitty:" + ADDRESS + "?asset=KITTY&amount=-5&memo=")

    def test_unknown_asset(self):
        with self.assertRaises(ValueError):
            PaymentRequest.from_uri("coinkitty:" + ADDRESS + "?asset=DOGE&amount=1&memo=")

    def test_missing_field(self):
        with self.assertRaises(ValueError):
            PaymentRequest.from_uri("coinkitty:" + ADDRESS + "?asset=KITTY&amount=1")


if __name__ == "__main__":
    unittest.main()
