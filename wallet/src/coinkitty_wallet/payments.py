"""Claimable payments and the Launch Window lottery share.

White paper v0.3 §11.3: to pay someone who has not activated an account, the
sender creates a claimable payment (recipient address, amount, expiry *default
30 days, maximum 365*).  The coins sit in protocol-held escrow.  If the payment
is **not claimed** -- because it expired, or because the sender cancelled it
before the claim -- "the sender gets it back minus a **lottery share** (proposed:
2%), which goes to the Launch Window lottery pool".  "Treating cancellations and
expirations the same way means no one can dodge the share by cancelling at the
last minute."

So: the refund is always ``amount - amount * 2 // 100`` to the sender and
``amount * 2 // 100`` to the pool.  Nothing else can make coins disappear.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from . import address, amounts

__all__ = [
    "DEFAULT_EXPIRY_DAYS",
    "MAX_EXPIRY_DAYS",
    "LOTTERY_SHARE",
    "PaymentError",
    "LotteryPool",
    "ClaimablePayment",
]

#: §11.3 expiry, in days
DEFAULT_EXPIRY_DAYS = 30
MAX_EXPIRY_DAYS = 365

#: §11.3 lottery share, as a fraction: 2%
LOTTERY_SHARE = (2, 100)

PENDING = "pending"
CLAIMED = "claimed"
EXPIRED = "expired"
CANCELLED = "cancelled"


class PaymentError(ValueError):
    """Raised for any payment this wallet would refuse to carry out."""


class LotteryPool:
    """The Launch Window lottery pool (§11.4), funded by lottery shares."""

    def __init__(self) -> None:
        self.total = 0
        self.sources: list[tuple[str, int]] = []

    def add_share(self, source: str, share: int) -> int:
        """Add a share to the pool and return the new total."""
        self.total = amounts.kitoshi(self.total + amounts.kitoshi(share))
        self.sources.append((source, amounts.kitoshi(share)))
        return self.total


class ClaimablePayment:
    """One claimable payment: recipient, amount, expiry, and its escrow."""

    def __init__(
        self,
        recipient: str,
        amount: int,
        *,
        created_at,
        expiry_days: int = DEFAULT_EXPIRY_DAYS,
        pool: LotteryPool | None = None,
        recipient_activated: bool = False,
    ) -> None:
        self.recipient = address.send_target(recipient)
        self.amount = amounts.kitoshi(amount)
        if self.amount <= 0:
            raise PaymentError("a claimable payment must carry some coins")
        if isinstance(expiry_days, bool) or not isinstance(expiry_days, int):
            raise PaymentError(f"expiry must be a whole number of days, got {expiry_days!r}")
        if not 1 <= expiry_days <= MAX_EXPIRY_DAYS:
            raise PaymentError(
                f"expiry must be between 1 and {MAX_EXPIRY_DAYS} days, got {expiry_days}"
            )
        if recipient_activated:
            raise PaymentError(
                "the recipient has already activated their account: send an ordinary "
                "transfer instead of a claimable payment (§11.2)"
            )
        self.created_at = created_at
        self.expires_at = created_at + timedelta(days=expiry_days)
        self.pool = pool if pool is not None else LotteryPool()
        self.status = PENDING
        self.escrow = self.amount

    @property
    def lottery_share(self) -> int:
        """The share the sender agreed to when creating this payment (§11.8)."""
        num, den = LOTTERY_SHARE
        return amounts.percent_of(self.amount, num, den)

    def claim(self, now) -> int:
        """The recipient activates and claims: they receive the full amount."""
        if self.status != PENDING:
            raise PaymentError(f"payment is already {self.status}; it cannot be claimed")
        if now >= self.expires_at:
            self._refund(now)
            raise PaymentError("payment expired before the claim; the sender got the refund")
        self.status = CLAIMED
        self.escrow = 0
        return self.amount

    def expire(self, now) -> tuple[int, int]:
        """The clock ran out: sender gets it back minus the lottery share."""
        return self._refund(now)

    def cancel(self, now) -> tuple[int, int]:
        """The sender gave up: identical to an expiration, §11.3.

        Cancelling at the last minute cannot dodge the share.
        """
        return self._refund(now)

    def _refund(self, now) -> tuple[int, int]:
        if self.status != PENDING:
            raise PaymentError(f"payment is already {self.status}; it cannot be refunded")
        share = self.lottery_share
        back_to_sender = self.amount - share
        self.status = CANCELLED if now < self.expires_at else EXPIRED
        self.escrow = 0
        self.pool.add_share(f"claimable-payment:{self.recipient}", share)
        return back_to_sender, share

    def settle(self, now) -> tuple[int, int]:
        """Let the wallet close out a payment it lost track of.

        Used by the background sweep: if the payment is still pending once the
        expiry has passed, it is refunded exactly as an expiration would be.
        """
        if self.status != PENDING:
            return 0, 0
        if now < self.expires_at:
            return 0, 0
        return self._refund(now)
