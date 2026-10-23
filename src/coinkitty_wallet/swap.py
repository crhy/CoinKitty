"""Swap logic: a simulated atomic swap over the demo backend.

There is no real Bitcoin or KittyChain yet, so a swap is SIMULATED: the steps
are walked in plain language and the balance move is applied only when the
simulation reaches "Done". No real coins ever move. Money is always an ``int``
count of the asset's smallest unit; the rate is an ``int`` count of KITTY's
smallest unit (kitoshi) per one sat.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from .units import KITOSHI_PER_KITTY

# Demo price: 2,000 sats per KITTY -> kitoshi of KITTY per 1 sat.
DEMO_RATE = KITOSHI_PER_KITTY // 2000

STEPS = ["Matching an offer", "Locking your coins",
         "Waiting for confirmations", "Receiving", "Done"]

_ASSETS = ("KITTY", "BTC")


@dataclass
class Offer:
    id: str
    sell_asset: str
    buy_asset: str
    rate_kitoshi_per_sat: int
    max_sats: int
    maker: str


def _other_asset(asset: str) -> str:
    """The asset on the other side of a KITTY<->BTC swap."""
    if asset == "KITTY":
        return "BTC"
    if asset == "BTC":
        return "KITTY"
    raise ValueError(f"unknown asset {asset!r}")


def _is_money(value: object) -> bool:
    """True for a positive int that is not a bool (True is an int in Python)."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def demo_order_book(rng) -> list[Offer]:
    """Four offers around the demo price, each within +/-5%, makers "Kitty-<4 hex>".

    Two offers sell KITTY (buy BTC) and two sell BTC (buy KITTY). ``rate_kitoshi_per_sat``
    is kitoshi of KITTY per one sat; ``max_sats`` is the most sats the maker will fill.
    """
    book: list[Offer] = []
    for index in range(4):
        sell = "KITTY" if index % 2 == 0 else "BTC"
        buy = _other_asset(sell)
        percent = rng.randint(-5, 5)
        rate = DEMO_RATE * (100 + percent) // 100
        maker = f"Kitty-{rng.randbytes(2).hex()}"
        book.append(Offer(
            id=uuid.uuid4().hex,
            sell_asset=sell,
            buy_asset=buy,
            rate_kitoshi_per_sat=rate,
            max_sats=1_000_000,
            maker=maker,
        ))
    return book


def quote(offer: Offer, sell_asset: str, amount: int) -> int:
    """Units of the buy asset received for ``amount`` of ``sell_asset`` (integer math).

    BTC->KITTY: ``amount_sats * rate`` kitoshi. KITTY->BTC: ``amount_kitoshi // rate`` sats.
    """
    if sell_asset == "BTC":
        return amount * offer.rate_kitoshi_per_sat
    if sell_asset == "KITTY":
        return amount // offer.rate_kitoshi_per_sat
    raise ValueError(f"unknown asset {sell_asset!r}")


def _can_fill(offer: Offer, sell_asset: str, amount: int) -> bool:
    """True when the maker has enough sats on offer to fill ``amount`` of ``sell_asset``."""
    if sell_asset == "BTC":
        return amount <= offer.max_sats
    if sell_asset == "KITTY":
        return amount // offer.rate_kitoshi_per_sat <= offer.max_sats
    raise ValueError(f"unknown asset {sell_asset!r}")


def best_offer(book: list[Offer], sell_asset: str, amount: int) -> Offer | None:
    """The offer that fills ``amount`` of ``sell_asset`` and returns the most, or None.

    "Best for the seller" means the highest :func:`quote` among offers that can fill
    the amount, which is the highest rate when selling BTC and the lowest when selling KITTY.
    """
    best: Offer | None = None
    best_receive = -1
    for offer in book:
        if offer.sell_asset != sell_asset:
            continue
        if not _can_fill(offer, sell_asset, amount):
            continue
        received = quote(offer, sell_asset, amount)
        if received > best_receive:
            best_receive = received
            best = offer
    return best


class SimulatedSwap:
    """A simulated atomic swap: walks :data:`STEPS` every 3 s of simulated time."""

    def __init__(self, offer: Offer, sell_asset: str, amount: int, receive: int,
                 started_at: int, refund_after: int = 24 * 3600) -> None:
        self.offer = offer
        self.sell_asset = sell_asset
        self.amount = amount
        self.receive = receive
        self.started_at = started_at
        self.refund_after = refund_after
        self._failed = False

    def fail(self) -> None:
        """Mark the swap as failed: it refunds instead of completing."""
        self._failed = True

    def state(self, now: int) -> str:
        """The current step name, advancing one step every 3 s from ``started_at``.

        Once :meth:`fail` was called, returns "Refunding" until
        ``started_at + refund_after`` and "Refunded" after that.
        """
        if self._failed:
            if now >= self.started_at + self.refund_after:
                return "Refunded"
            return "Refunding"
        index = min((now - self.started_at) // 3, len(STEPS) - 1)
        return STEPS[index]

    def refund_countdown(self, now: int) -> int:
        """Seconds until the refund fires (0 when there is no refund or it is done)."""
        if not self._failed:
            return 0
        return max(0, self.started_at + self.refund_after - now)
