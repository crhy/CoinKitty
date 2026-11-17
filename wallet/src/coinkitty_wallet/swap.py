"""Atomic swaps (HTLCs) between KITTY and another chain.

White paper v0.3 §11.6: swaps use hash time-locked contracts. "Either both
sides complete or both sides get their coins back. Neither party can take the
other's coins."  Timeouts *(proposed)*: "the party who starts the swap locks for
24 hours, the responder for 12 hours, so the starter can always refund safely if
the other side disappears."  Liveness: "A swap participant must come back online
to claim before the timeout. The wallet does this automatically in the background,
and a user's own SuperMox node can act as a watchtower that claims on their
behalf."

Wallet spec §3.9: if anything goes wrong the Swap screen shows the **refund
countdown** and returns the coins automatically when the timeout passes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from . import amounts

__all__ = [
    "STARTER_TIMEOUT_HOURS",
    "RESPONDER_TIMEOUT_HOURS",
    "SwapError",
    "SwapNotReady",
    "SwapExpired",
    "Party",
    "HtlcSwap",
]

#: §11.6 proposed timeouts, in hours
STARTER_TIMEOUT_HOURS = 24
RESPONDER_TIMEOUT_HOURS = 12

OFFERED = "offered"
LOCKED = "locked"
COMPLETED = "completed"
REFUNDED = "refunded"


class SwapError(ValueError):
    """Raised for any swap step this wallet refuses to take."""


class SwapNotReady(SwapError):
    """Raised when a participant is offline, so the swap cannot be claimed."""


class SwapExpired(SwapError):
    """Raised when a timeout has passed, so the swap can only be refunded."""


@dataclass
class Party:
    """One side of a swap: what they offer, and whether they are reachable."""

    name: str
    asset: str
    amount: int
    online: bool = True
    watchtower: bool = False

    def __post_init__(self) -> None:
        self.amount = amounts.kitoshi(self.amount)
        if self.amount <= 0:
            raise SwapError(f"{self.name} must offer a positive amount")


class HtlcSwap:
    """One swap offer, its responder, its two timeouts, and its outcome."""

    def __init__(
        self,
        starter: Party,
        started_at,
        *,
        starter_timeout_hours: int = STARTER_TIMEOUT_HOURS,
        responder_timeout_hours: int = RESPONDER_TIMEOUT_HOURS,
    ) -> None:
        for label, hours in (("starter", starter_timeout_hours), ("responder", responder_timeout_hours)):
            if isinstance(hours, bool) or not isinstance(hours, int) or hours <= 0:
                raise SwapError(f"bad {label} timeout: {hours!r}")
        self.starter = starter
        self.responder: Party | None = None
        self.started_at = started_at
        self.starter_deadline = started_at + timedelta(hours=starter_timeout_hours)
        self.responder_timeout_hours = responder_timeout_hours
        self.responder_deadline = None  # set when someone answers the offer
        self.status = OFFERED
        #: coins each side holds from this swap; each starts holding their own
        self.holds = {starter.name: starter.amount}
        self.refunded: set[str] = set()
        self.progress: list[str] = ["matching an offer"]

    def match(self, responder: Party, locked_at) -> None:
        """The responder accepts the offer and locks their side for 12 hours."""
        if self.status != OFFERED:
            raise SwapError(f"swap is already {self.status}; it cannot be matched again")
        if responder.name == self.starter.name:
            raise SwapError("a party cannot swap with itself")
        self.responder = responder
        self.responder_deadline = locked_at + timedelta(hours=self.responder_timeout_hours)
        self.holds[responder.name] = responder.amount
        self.status = LOCKED
        self.progress += [
            f"locking {self.starter.asset} until {self.starter_deadline}",
            f"locking {responder.asset} until {self.responder_deadline}",
            "waiting for confirmations",
        ]

    def claim(self, now) -> dict[str, int]:
        """Complete the swap: each side receives the other's coins.

        A participant must be back online before their timeout, or run a watchtower
        that claims for them (§11.6).  If either side is unreachable, nothing moves.
        """
        if self.status == COMPLETED:
            raise SwapError("swap already completed")
        if self.status == REFUNDED:
            raise SwapError("swap already refunded; its coins are back")
        if self.responder is None:
            raise SwapNotReady("no one has matched this offer yet")
        if now >= self.starter_deadline or now >= self.responder_deadline:
            raise SwapExpired(
                "a timeout has passed, so the swap can no longer complete: "
                "both sides get their coins back (§11.6)"
            )
        for party in (self.starter, self.responder):
            if not (party.online or party.watchtower):
                raise SwapNotReady(
                    f"{party.name} is offline: a participant must come back online "
                    "to claim before the timeout"
                )
        self.holds[self.starter.name] = self.responder.amount
        self.holds[self.responder.name] = self.starter.amount
        self.status = COMPLETED
        self.progress += [
            f"receiving {self.responder.amount} {self.responder.asset}",
            f"receiving {self.starter.amount} {self.starter.asset}",
            "done",
        ]
        return dict(self.holds)

    def refund(self, now, who: str) -> int:
        """Give one side their own coins back, once their own timeout has passed.

        The starter locks for 24 hours and the responder for 12, so the starter
        can always refund safely if the other side disappears (§11.6).
        """
        party = self._named(who)
        if self.status == COMPLETED:
            raise SwapError("swap completed; there is nothing to refund")
        if party.name in self.refunded:
            raise SwapError(f"{party.name} already refunded")
        deadline = self.starter_deadline if party is self.starter else self.responder_deadline
        if deadline is None:
            raise SwapError(
                "no one matched this offer, so the starter's coins never moved: "
                "there is nothing to refund"
            )
        if now < deadline:
            raise SwapError(
                f"{party.name} may refund only after their own timeout "
                f"({self._deadline_label(party)})"
            )
        self.holds[party.name] = party.amount
        self.refunded.add(party.name)
        if self.responder is not None and len(self.refunded) == 2:
            self.status = REFUNDED
        self.progress += [f"{party.name} refunded {party.amount} {party.asset}"]
        return party.amount

    def refund_all(self, now) -> dict[str, int]:
        """A swap that cannot complete returns both sides' coins."""
        if self.responder is None:
            self.holds[self.starter.name] = self.starter.amount
            self.status = REFUNDED
            return dict(self.holds)
        self.refund(now, self.starter.name)
        self.refund(now, self.responder.name)
        return dict(self.holds)

    def settle(self, now) -> dict[str, int]:
        """The background sweep the wallet runs for every unfinished swap.

        It claims if both sides are reachable in time, otherwise it refunds
        whoever is allowed to refund (§3.9: "returns the coins automatically
        when the timeout passes").
        """
        try:
            return self.claim(now)
        except SwapNotReady:
            return dict(self.holds)
        except SwapExpired:
            return self.refund_all(now)

    def refund_countdown(self, now) -> dict[str, float]:
        """Hours until each side may refund -- the countdown the Swap screen shows."""
        out: dict[str, float] = {}
        for party, deadline in ((self.starter, self.starter_deadline), (self.responder, self.responder_deadline)):
            if party is None or deadline is None:
                continue
            out[party.name] = max(0.0, (deadline - now).total_seconds() / 3600)
        return out

    def _named(self, who: str) -> Party:
        for party in (self.starter, self.responder):
            if party is not None and who == party.name:
                return party
        raise SwapError(f"unknown swap participant: {who!r}")

    def _deadline_label(self, party: Party) -> str:
        return "24h starter timeout" if party is self.starter else "12h responder timeout"

    def coins(self) -> int:
        """Total coins inside the swap: conserved whatever happens to it."""
        if self.responder is None:
            return self.starter.amount
        return self.starter.amount + self.responder.amount
