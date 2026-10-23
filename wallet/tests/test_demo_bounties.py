import os
import unittest

import json
import random
import tempfile

from coinkitty_wallet.demo_backend import DemoBackend
from coinkitty_wallet.models import Bid, Bounty


class DemoBountiesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "wallet.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_seeded_bounties_exist_after_create(self):
        wallet = DemoBackend.create(self.path, random.Random(42))
        titles = {b.title for b in wallet.bounties()}
        for expected in ("Smoothie", "Cello lesson", "Dishwasher shift",
                         "Car wash", "Guitar for sale", "Build a shed"):
            self.assertIn(expected, titles)
        shed = next(b for b in wallet.bounties() if b.title == "Build a shed")
        children = [b for b in wallet.bounties() if b.parent_id == shed.id]
        self.assertEqual(len(children), 2)
        self.assertEqual(shed.status, "funded")
        self.assertEqual(shed.escrow, 3 * 10**24)

    def test_post_then_fund_lowers_balance_by_price(self):
        wallet = DemoBackend.create(self.path, random.Random(1))
        before = wallet.balance("KITTY")
        bounty = wallet.post_bounty("Walk the dog", "One dog, one walk.",
                                    "Pets", "Park", 2 * 10**24)
        self.assertEqual(bounty.status, "open")
        self.assertEqual(bounty.poster, wallet.address())
        wallet.fund(bounty.id)
        self.assertEqual(wallet.balance("KITTY"), before - 2 * 10**24)
        self.assertEqual(bounty.status, "funded")
        self.assertEqual(bounty.escrow, 2 * 10**24)

    def test_accept_deliver_release_pays_and_refunds(self):
        wallet = DemoBackend.create(self.path, random.Random(7))
        before = wallet.balance("KITTY")
        bounty = wallet.post_bounty("Mow the lawn", "Cut the grass.",
                                    "Chores", "Backyard", 5 * 10**24)
        wallet.fund(bounty.id)
        self.assertEqual(wallet.balance("KITTY"), before - 5 * 10**24)
        wallet.place_demo_bids(bounty.id, random.Random(3))
        affordable = [b for b in bounty.bids if b.price <= bounty.escrow]
        self.assertTrue(affordable)
        chosen = min(affordable, key=lambda b: b.price)
        wallet.accept(bounty.id, chosen.id)
        wallet.deliver(bounty.id)
        escrow_before = bounty.escrow
        paid, refunded = wallet.release(bounty.id)
        self.assertEqual(paid, chosen.price)
        self.assertEqual(refunded, escrow_before - chosen.price)
        self.assertEqual(bounty.escrow, 0)
        self.assertEqual(bounty.status, "released")
        self.assertEqual(wallet.balance("KITTY"), before - chosen.price)

    def test_save_load_round_trip_keeps_bounties_and_bids(self):
        wallet = DemoBackend.create(self.path, random.Random(5))
        bounty = wallet.post_bounty("Fix the bike", "Patch a flat.",
                                    "Repair", "Garage", 3 * 10**24)
        wallet.place_demo_bids(bounty.id, random.Random(9))
        reloaded = DemoBackend.load(self.path)
        self.assertEqual(len(reloaded.bounties()), len(wallet.bounties()))
        same = next(b for b in reloaded.bounties() if b.id == bounty.id)
        self.assertEqual(len(same.bids), 3)
        for bid in same.bids:
            self.assertIsInstance(bid, Bid)
            self.assertEqual(bid.bounty_id, bounty.id)

    def test_old_file_without_bounties_key_loads(self):
        wallet = DemoBackend.create(self.path, random.Random(2))
        with open(self.path) as handle:
            state = json.load(handle)
        state.pop("bounties")
        old = self.path + ".old.json"
        with open(old, "w") as handle:
            json.dump(state, handle)
        reloaded = DemoBackend.load(old)
        self.assertEqual(reloaded.bounties(), [])
        self.assertEqual(reloaded.balance("KITTY"), wallet.balance("KITTY"))


if __name__ == "__main__":
    unittest.main()
