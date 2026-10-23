import os
import unittest

import random
import tempfile

from coinkitty_wallet.demo_backend import DemoBackend
from coinkitty_wallet.models import Contact, RainGroup


class DemoBackendTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "wallet.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_round_trip_keeps_big_ints(self):
        wallet = DemoBackend.create(self.path, random.Random(42))
        reloaded = DemoBackend.load(self.path)
        self.assertEqual(reloaded.balance("KITTY"), 25 * 10**24)
        self.assertEqual(reloaded.balance("BTC"), 150_000)
        self.assertEqual(reloaded.address(), wallet.address())
        self.assertEqual(len(reloaded.contacts()), 5)
        self.assertEqual(len(reloaded.rain_groups()), 2)
        favorites = {c.name for c in reloaded.contacts() if c.favorite}
        self.assertEqual(favorites, {"Babysitter", "Julie"})

    def test_send_reduces_and_records(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        target = wallet.contacts()[0]
        txn = wallet.send("KITTY", 10**24, target.id, "thanks")
        self.assertEqual(wallet.balance("KITTY"), 24 * 10**24)
        self.assertEqual(txn.kind, "send")
        self.assertEqual(txn.counterparty, target.name)
        self.assertEqual(len(wallet.transactions()), 1)
        self.assertEqual(wallet.transactions()[0].id, txn.id)

    def test_send_over_balance_changes_nothing(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        before = wallet.balance("BTC")
        with self.assertRaises(ValueError):
            wallet.send("BTC", before + 1, wallet.contacts()[0].id)
        self.assertEqual(wallet.balance("BTC"), before)
        self.assertEqual(wallet.transactions(), [])

    def test_send_non_positive_raises(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        with self.assertRaises(ValueError):
            wallet.send("BTC", 0, wallet.contacts()[0].id)

    def test_rain_all_or_nothing(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        group = wallet.rain_groups()[0]  # "Band": 3 members
        too_much = wallet.balance("KITTY") + 1
        with self.assertRaises(ValueError):
            wallet.rain("KITTY", too_much, group.member_ids)
        self.assertEqual(wallet.balance("KITTY"), 25 * 10**24)
        self.assertEqual(wallet.transactions(), [])

    def test_rain_success(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        group = wallet.rain_groups()[0]
        total = 15 * 10**24
        txns = wallet.rain("KITTY", total, group.member_ids)
        self.assertEqual(wallet.balance("KITTY"), 10 * 10**24)
        self.assertEqual(len(txns), 3)
        self.assertEqual(sum(t.amount for t in txns), total)
        self.assertTrue(all(t.kind == "rain" for t in txns))

    def test_delete_contact_removes_from_groups(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        maya = next(c for c in wallet.contacts() if c.name == "Maya")
        wallet.delete_contact(maya.id)
        for group in wallet.rain_groups():
            self.assertNotIn(maya.id, group.member_ids)

    def test_pick_luck_deterministic(self):
        wallet = DemoBackend.create(self.path, random.Random(7))
        first = wallet.pick_luck(random.Random(1))
        second = wallet.pick_luck(random.Random(1))
        self.assertEqual(first.name, second.name)

    def test_pick_luck_no_contacts(self):
        wallet = DemoBackend.create(self.path, random.Random(7))
        for contact in wallet.contacts():
            wallet.delete_contact(contact.id)
        with self.assertRaises(ValueError):
            wallet.pick_luck(random.Random(1))

    def test_add_contact_invalid_address(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        with self.assertRaises(ValueError):
            wallet.add_contact("Ghost", "not-an-address")

    def test_add_contact_valid(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        valid = wallet.address()
        added = wallet.add_contact("New", valid)
        self.assertEqual(len(wallet.contacts()), 6)
        self.assertEqual(added.address, valid)

    def test_update_contact(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        original = wallet.contacts()[0]
        updated = Contact(id=original.id, name="Renamed", address=original.address,
                          favorite=True)
        wallet.update_contact(updated)
        found = next(c for c in wallet.contacts() if c.id == original.id)
        self.assertEqual(found.name, "Renamed")
        self.assertTrue(found.favorite)

    def test_save_group_replaces_by_id(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        group = wallet.rain_groups()[0]
        replacement = RainGroup(id=group.id, name="Renamed Band",
                                member_ids=group.member_ids, favorite=False)
        wallet.save_group(replacement)
        self.assertEqual(len(wallet.rain_groups()), 2)
        self.assertEqual(wallet.rain_groups()[0].name, "Renamed Band")

    def test_delete_group(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        wallet.delete_group(wallet.rain_groups()[0].id)
        self.assertEqual(len(wallet.rain_groups()), 1)

    def test_transactions_newest_first(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        first = wallet.send("BTC", 1, wallet.contacts()[0].id)
        second = wallet.send("BTC", 2, wallet.contacts()[1].id)
        history = wallet.transactions()
        self.assertEqual(history[0].id, second.id)
        self.assertEqual(history[1].id, first.id)


if __name__ == "__main__":
    unittest.main()
