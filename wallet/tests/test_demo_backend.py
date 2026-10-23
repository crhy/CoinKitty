import os
import unittest

import json
import random
import tempfile
import time

from coinkitty_wallet.demo_backend import DemoBackend
from coinkitty_wallet.models import Contact, RainGroup, Transaction


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

    def test_created_at_round_trip(self):
        wallet = DemoBackend.create(self.path, random.Random(42))
        reloaded = DemoBackend.load(self.path)
        self.assertIsNotNone(wallet._created_at)
        self.assertEqual(reloaded._created_at, wallet._created_at)

    def test_days_since_created(self):
        wallet = DemoBackend.create(self.path, random.Random(42))
        created = wallet._created_at
        self.assertEqual(wallet.days_since_created(created), 1)
        self.assertEqual(wallet.days_since_created(created + 86400), 2)
        self.assertEqual(wallet.days_since_created(created + 3 * 86400 + 5), 4)

    def test_load_without_created_at_uses_mtime(self):
        wallet = DemoBackend.create(self.path, random.Random(42))
        with open(self.path) as handle:
            state = json.load(handle)
        state.pop("created_at")
        old = self.path + ".old.json"
        with open(old, "w") as handle:
            json.dump(state, handle)
        reloaded = DemoBackend.load(old)
        self.assertEqual(reloaded._created_at, int(os.path.getmtime(old)))

    def test_earned_today(self):
        wallet = DemoBackend.create(self.path, random.Random(42))
        lt = time.localtime()
        noon = int(time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 12, 0, 0, 0, 0, lt.tm_isdst)))
        wallet._transactions.append(Transaction(
            id="r1", kind="receive", asset="KITTY", amount=2 * 10**24,
            counterparty="A", memo="", timestamp=noon))
        wallet._transactions.append(Transaction(
            id="r2", kind="receive", asset="KITTY", amount=3 * 10**24,
            counterparty="B", memo="", timestamp=noon + 60))
        wallet._transactions.append(Transaction(
            id="r3", kind="receive", asset="KITTY", amount=7 * 10**24,
            counterparty="C", memo="", timestamp=noon + 3 * 86400))
        wallet._transactions.append(Transaction(
            id="r4", kind="receive", asset="BTC", amount=99,
            counterparty="D", memo="", timestamp=noon))
        self.assertEqual(wallet.earned_today("KITTY", noon), 5 * 10**24)
        self.assertEqual(wallet.earned_today("BTC", noon), 99)
        self.assertEqual(wallet.earned_today("KITTY", noon + 3 * 86400), 7 * 10**24)

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

    def test_save_atomic_no_tmp_left(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        wallet.send("BTC", 1, wallet.contacts()[0].id)
        self.assertFalse(os.path.exists(self.path + ".tmp"))
        reloaded = DemoBackend.load(self.path)
        self.assertEqual(reloaded.address(), wallet.address())
        self.assertEqual(reloaded.balance("BTC"), wallet.balance("BTC"))

    def test_send_bool_amount_rejected(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        target = wallet.contacts()[0]
        before = wallet.balance("KITTY")
        with self.assertRaises(ValueError):
            wallet.send("KITTY", True, target.id)
        self.assertEqual(wallet.balance("KITTY"), before)
        self.assertEqual(wallet.transactions(), [])

    def test_rain_bool_total_rejected(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        group = wallet.rain_groups()[0]
        before = wallet.balance("KITTY")
        with self.assertRaises(ValueError):
            wallet.rain("KITTY", True, group.member_ids)
        self.assertEqual(wallet.balance("KITTY"), before)
        self.assertEqual(wallet.transactions(), [])

    def test_rain_bool_custom_amount_rejected(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        group = wallet.rain_groups()[0]
        before = wallet.balance("KITTY")
        amounts = {member_id: 5 * 10**24 for member_id in group.member_ids}
        amounts[group.member_ids[0]] = True
        with self.assertRaises(ValueError):
            wallet.rain("KITTY", 15 * 10**24, group.member_ids, amounts)
        self.assertEqual(wallet.balance("KITTY"), before)
        self.assertEqual(wallet.transactions(), [])


if __name__ == "__main__":
    unittest.main()
