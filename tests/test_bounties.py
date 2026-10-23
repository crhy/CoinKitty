import unittest

import random

from coinkitty_wallet.models import Bid, Bounty
from coinkitty_wallet.bounties import accept, auto_release_due, cancel, create_child, deliver, fund, rank_bids, release


def make_bounty(
    *,
    bounty_id: str = "b1",
    status: str = "open",
    price: int = 100,
    escrow: int = 0,
    bids: list[Bid] | None = None,
    accepted_bid_id: str | None = None,
    delivered_at: int | None = None,
    parent_id: str | None = None,
) -> Bounty:
    return Bounty(
        id=bounty_id,
        poster="poster",
        title="title",
        description="description",
        category="category",
        location="location",
        window_start=0,
        window_end=1000,
        price=price,
        parent_id=parent_id,
        status=status,
        bids=bids,
        accepted_bid_id=accepted_bid_id,
        escrow=escrow,
        delivered_at=delivered_at,
    )


def make_bid(bid_id: str, bounty_id: str, price: int, reputation: int = 0) -> Bid:
    return Bid(id=bid_id, bounty_id=bounty_id, bidder="hunter", price=price, reputation=reputation)


class BountyLifecycleTests(unittest.TestCase):
    def test_full_lifecycle(self) -> None:
        bid = make_bid("bid1", "b1", 80, reputation=5)
        bounty = make_bounty(status="open", price=100, bids=[bid])

        new_balance = fund(bounty, 150)
        self.assertEqual(new_balance, 50)
        self.assertEqual(bounty.status, "funded")
        self.assertEqual(bounty.escrow, 100)

        accept(bounty, "bid1")
        self.assertEqual(bounty.status, "assigned")
        self.assertEqual(bounty.accepted_bid_id, "bid1")

        deliver(bounty, 10)
        self.assertEqual(bounty.status, "delivered")
        self.assertEqual(bounty.delivered_at, 10)

        paid, refunded = release(bounty)
        self.assertEqual((paid, refunded), (80, 20))
        self.assertEqual(bounty.status, "released")
        self.assertEqual(bounty.escrow, 0)

    def test_fund_requires_balance(self) -> None:
        bounty = make_bounty(status="open", price=100)
        with self.assertRaises(ValueError):
            fund(bounty, 99)

    def test_fund_only_from_open(self) -> None:
        bounty = make_bounty(status="funded", price=100, escrow=100)
        with self.assertRaises(ValueError):
            fund(bounty, 150)

    def test_accept_only_from_funded(self) -> None:
        bid = make_bid("bid1", "b1", 80)
        bounty = make_bounty(status="open", price=100, bids=[bid])
        with self.assertRaises(ValueError):
            accept(bounty, "bid1")

    def test_accept_requires_escrow_to_cover_bid(self) -> None:
        bid = make_bid("bid1", "b1", 101)
        bounty = make_bounty(status="funded", price=100, escrow=100, bids=[bid])
        with self.assertRaises(ValueError):
            accept(bounty, "bid1")

    def test_accept_requires_existing_bid(self) -> None:
        bounty = make_bounty(status="funded", price=100, escrow=100)
        with self.assertRaises(ValueError):
            accept(bounty, "missing")

    def test_deliver_only_from_assigned(self) -> None:
        bounty = make_bounty(status="funded", price=100, escrow=100)
        with self.assertRaises(ValueError):
            deliver(bounty, 10)

    def test_release_only_from_delivered(self) -> None:
        bounty = make_bounty(status="assigned", price=100, escrow=100, accepted_bid_id="bid1")
        with self.assertRaises(ValueError):
            release(bounty)

    def test_cancel_only_from_open_or_funded(self) -> None:
        bounty = make_bounty(status="delivered", price=100, escrow=100, delivered_at=10)
        with self.assertRaises(ValueError):
            cancel(bounty)

    def test_cancel_refunds_escrow(self) -> None:
        bounty = make_bounty(status="funded", price=100, escrow=100)
        refunded = cancel(bounty)
        self.assertEqual(refunded, 100)
        self.assertEqual(bounty.status, "cancelled")
        self.assertEqual(bounty.escrow, 0)


class RankingTests(unittest.TestCase):
    def test_rank_order(self) -> None:
        cheap = make_bid("b3", "b", 5, reputation=0)
        same_price_high_rep = make_bid("b2", "b", 10, reputation=2)
        same_price_low_rep = make_bid("b1", "b", 10, reputation=1)
        self.assertEqual(
            rank_bids([same_price_low_rep, same_price_high_rep, cheap]),
            [cheap, same_price_high_rep, same_price_low_rep],
        )


class SubBountyTests(unittest.TestCase):
    def test_create_child_from_funded_parent(self) -> None:
        parent = make_bounty(status="funded", price=100, escrow=100)
        child = create_child(parent, "child", 30, 10)
        self.assertEqual(parent.escrow, 70)
        self.assertEqual(child.status, "funded")
        self.assertEqual(child.escrow, 30)
        self.assertEqual(child.parent_id, parent.id)
        self.assertEqual(child.poster, parent.poster)
        self.assertEqual(parent.escrow + child.escrow, 100)

    def test_create_child_from_assigned_parent(self) -> None:
        bid = make_bid("bid1", "b1", 80)
        parent = make_bounty(status="assigned", price=100, escrow=100, bids=[bid], accepted_bid_id="bid1")
        child = create_child(parent, "child", 20, 10)
        self.assertEqual(parent.escrow + child.escrow, 100)

    def test_multiple_children_conserve_escrow(self) -> None:
        parent = make_bounty(status="funded", price=100, escrow=100)
        first = create_child(parent, "first", 30, 10)
        second = create_child(parent, "second", 20, 10)
        self.assertEqual(parent.escrow + first.escrow + second.escrow, 100)
        self.assertEqual(parent.escrow, 50)

    def test_create_child_rejects_bad_parent_status(self) -> None:
        parent = make_bounty(status="open", price=100, escrow=0)
        with self.assertRaises(ValueError):
            create_child(parent, "child", 1, 10)

    def test_create_child_rejects_bad_price(self) -> None:
        parent = make_bounty(status="funded", price=100, escrow=100)
        with self.assertRaises(ValueError):
            create_child(parent, "child", 0, 10)
        with self.assertRaises(ValueError):
            create_child(parent, "child", True, 10)
        with self.assertRaises(ValueError):
            create_child(parent, "child", 101, 10)


class SplitReleaseTests(unittest.TestCase):
    def test_release_after_split_from_assigned(self) -> None:
        bid = make_bid("bid1", "b1", 90)
        parent = make_bounty(status="assigned", price=100, escrow=100, bids=[bid], accepted_bid_id="bid1")
        child = create_child(parent, "child", 50, 10)
        deliver(parent, 20)
        paid, refunded = release(parent)
        self.assertEqual((paid, refunded), (50, 0))
        self.assertEqual(child.escrow, 50)

    def test_release_split_within_surplus(self) -> None:
        bid = make_bid("bid1", "b1", 90)
        parent = make_bounty(status="assigned", price=100, escrow=100, bids=[bid], accepted_bid_id="bid1")
        child = create_child(parent, "child", 5, 10)
        deliver(parent, 20)
        paid, refunded = release(parent)
        self.assertEqual((paid, refunded), (90, 5))
        self.assertEqual(child.escrow, 5)

    def test_release_without_children(self) -> None:
        bid = make_bid("bid1", "b1", 90)
        parent = make_bounty(status="assigned", price=100, escrow=100, bids=[bid], accepted_bid_id="bid1")
        deliver(parent, 20)
        paid, refunded = release(parent)
        self.assertEqual((paid, refunded), (90, 10))

    def test_random_scenarios_conserve_money(self) -> None:
        rng = random.Random(20261022)
        for _ in range(60):
            price = rng.randint(1, 1000)
            bid_price = rng.randint(1, price)
            bounty = make_bounty(status="open", price=price, bids=[make_bid("bid1", "b1", bid_price)])
            fund(bounty, price)
            accept(bounty, "bid1")
            children = []
            while bounty.escrow > 0 and rng.random() < 0.5:
                now = rng.uniform(0.0, 1000.0)
                child_price = rng.randint(1, bounty.escrow)
                children.append(create_child(bounty, "child", child_price, now))
            deliver(bounty, rng.uniform(0.0, 1000.0))
            paid, refunded = release(bounty)
            self.assertEqual(paid + refunded + sum(c.escrow for c in children), price)


class AutoReleaseTests(unittest.TestCase):
    def test_auto_release_at_exactly_24_hours(self) -> None:
        bid = make_bid("bid1", "b1", 100)
        bounty = make_bounty(status="delivered", price=100, escrow=100, bids=[bid], accepted_bid_id="bid1", delivered_at=0)
        self.assertTrue(auto_release_due(bounty, 24 * 3600))
        self.assertFalse(auto_release_due(bounty, 24 * 3600 - 1))

    def test_auto_release_with_float_now(self) -> None:
        bid = make_bid("bid1", "b1", 100)
        bounty = make_bounty(status="delivered", price=100, escrow=100, bids=[bid], accepted_bid_id="bid1", delivered_at=0)
        self.assertTrue(auto_release_due(bounty, float(24 * 3600)))
        self.assertFalse(auto_release_due(bounty, float(24 * 3600) - 0.1))


if __name__ == "__main__":
    unittest.main()
