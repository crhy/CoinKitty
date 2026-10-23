"""Pure bounty transition logic for the CoinKitty Wallet.

No GTK and no backend access live here. Money is always an ``int`` count of the
smallest KITTY unit, and timestamps are converted to ``int`` Unix seconds at
the boundary.
"""

from __future__ import annotations

from .models import Bid, Bounty


def rank_bids(bids: list[Bid]) -> list[Bid]:
    """Return bids ordered by price ascending, reputation descending, then id."""
    return sorted(bids, key=lambda bid: (bid.price, -bid.reputation, bid.id))


def fund(b: Bounty, balance: int) -> int:
    """Move the bounty price from ``balance`` into escrow and return the new balance."""
    if b.status != "open":
        raise ValueError("only an open bounty can be funded")
    if not isinstance(balance, int) or isinstance(balance, bool):
        raise ValueError("balance must be an int count of the smallest unit")
    if balance < b.price:
        raise ValueError("balance must cover the bounty price")

    b.escrow = b.price
    b.status = "funded"
    return balance - b.price


def accept(b: Bounty, bid_id: str) -> None:
    """Assign a funded bounty to a bid whose price fits the escrow."""
    if b.status != "funded":
        raise ValueError("only a funded bounty can accept a bid")

    bid = _find_bid(b, bid_id)
    if bid is None:
        raise ValueError(f"no bid with id {bid_id!r}")
    if bid.price > b.escrow:
        raise ValueError("the escrow must cover the accepted bid price")

    b.accepted_bid_id = bid_id
    b.status = "assigned"


def deliver(b: Bounty, now: int | float) -> None:
    """Mark an assigned bounty as delivered at ``now``."""
    if b.status != "assigned":
        raise ValueError("only an assigned bounty can be delivered")

    b.delivered_at = _as_time(now)
    b.status = "delivered"


def release(b: Bounty) -> tuple[int, int]:
    """Release a delivered bounty and return ``(paid_to_hunter, refunded_to_poster)``."""
    if b.status != "delivered":
        raise ValueError("only a delivered bounty can be released")

    bid = _find_bid(b, b.accepted_bid_id)
    if bid is None:
        raise ValueError("a released bounty must have an accepted bid")
    if bid.price > b.escrow:
        raise ValueError("the escrow must cover the accepted bid price")

    paid_to_hunter = bid.price
    refunded_to_poster = b.escrow - paid_to_hunter
    b.escrow = 0
    b.status = "released"
    return paid_to_hunter, refunded_to_poster


def auto_release_due(b: Bounty, now: int | float, review_seconds: int = 24 * 3600) -> bool:
    """Return whether a delivered bounty is due for automatic release."""
    if b.status != "delivered" or b.delivered_at is None:
        return False
    if not isinstance(review_seconds, int) or isinstance(review_seconds, bool):
        raise ValueError("review_seconds must be an int count of seconds")

    return _as_time(now) >= b.delivered_at + review_seconds


def cancel(b: Bounty) -> int:
    """Cancel an open or funded bounty and return the escrow refunded to the poster."""
    if b.status not in ("open", "funded"):
        raise ValueError("only an open or funded bounty can be cancelled")

    refunded = b.escrow
    b.escrow = 0
    b.status = "cancelled"
    return refunded


def create_child(parent: Bounty, title: str, price: int, now: int | float) -> Bounty:
    """Create a funded child bounty from a funded or assigned parent's escrow."""
    if parent.status not in ("funded", "assigned"):
        raise ValueError("only a funded or assigned parent can create a child bounty")
    if not isinstance(price, int) or isinstance(price, bool):
        raise ValueError("price must be an int count of the smallest unit")
    if price <= 0:
        raise ValueError("price must be positive")
    if price > parent.escrow:
        raise ValueError("child price must not exceed the parent escrow")

    start = _as_time(now)
    before = parent.escrow
    parent.escrow -= price
    child_id = f"{parent.id}.child.{start}.{price}.{before}"

    return Bounty(
        id=child_id,
        poster=parent.poster,
        title=title,
        description=parent.description,
        category=parent.category,
        location=parent.location,
        window_start=start,
        window_end=max(parent.window_end, start),
        price=price,
        parent_id=parent.id,
        status="funded",
        bids=[],
        accepted_bid_id=None,
        escrow=price,
        delivered_at=None,
    )


def _find_bid(b: Bounty, bid_id: str | None) -> Bid | None:
    """Return the bid with ``bid_id`` from ``b.bids``, or ``None``."""
    if bid_id is None or b.bids is None:
        return None
    for bid in b.bids:
        if bid.id == bid_id:
            return bid
    return None


def _as_time(value: int | float) -> int:
    """Convert a Unix timestamp to an ``int`` at the boundary."""
    if isinstance(value, bool):
        raise ValueError("time must be an int or float count of Unix seconds")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    raise ValueError("time must be an int or float count of Unix seconds")
