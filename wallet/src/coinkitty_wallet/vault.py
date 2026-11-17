"""Time-locked vaults: no one can open a vault early, including you.

White paper v0.3 §11.7: "Any account can move KITTY into a **vault** with an
unlock date. Until that date, the coins cannot be moved by anyone, for any
reason. No owner, guardian, governance vote, or admin can open a vault early."
"A vault can release in steps (for example, 10% per month) instead of all at
once."  §11.8 adds: no confiscation, no admin reversal.

Wallet spec §3.13 warns the user of the same thing: **no one can open a vault
early, including you.**  So the caller's identity is a label, not a permission:
owner, guardian, governance and admin all take the same path.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta

from . import amounts

__all__ = [
    "VaultError",
    "VaultLocked",
    "Vault",
    "add_months",
    "months_between",
]


class VaultError(ValueError):
    """Raised for any vault operation this wallet refuses."""


class VaultLocked(VaultError):
    """Raised when coins are asked for before the vault's release date."""

    def __init__(self, message: str, *, release_at=None) -> None:
        super().__init__(message)
        self.release_at = release_at


def add_months(moment, months: int):
    """Add whole calendar months to a date or datetime, clamping the day."""
    if isinstance(months, bool) or not isinstance(months, int) or months < 0:
        raise VaultError(f"bad number of months: {months!r}")
    year = moment.year + (moment.month - 1 + months) // 12
    month = (moment.month - 1 + months) % 12 + 1
    day = min(moment.day, _days_in_month(year, month))
    replaced = moment.replace(year=year, month=month, day=day)
    return replaced


def _days_in_month(year: int, month: int) -> int:
    return monthrange(year, month)[1]


def months_between(start, end) -> int:
    """Whole calendar months elapsed from *start* to *end* (0 if end is earlier)."""
    if end < start:
        return 0
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if (end.day, _time_key(end)) < (start.day, _time_key(start)):
        months -= 1
    return max(0, months)


def _time_key(moment) -> tuple:
    return (getattr(moment, "hour", 0), getattr(moment, "minute", 0), getattr(moment, "second", 0))


class _Tranche:
    """One locked amount, with its own release schedule."""

    def __init__(self, amount: int, unlock_at, steps: int, step_months: int) -> None:
        self.amount = amount
        self.unlock_at = unlock_at
        self.steps = steps
        self.step_months = step_months
        self.withdrawn = 0

    def released(self, now) -> int:
        """How much of this tranche may move at *now* -- never early."""
        if now < self.unlock_at:
            return 0
        if self.steps <= 1:
            return self.amount
        elapsed = months_between(self.unlock_at, now)
        step = min(self.steps, elapsed // self.step_months)
        return self.amount * step // self.steps

    def available(self, now) -> int:
        return self.released(now) - self.withdrawn

    def next_release(self, now):
        """When the next coins of this tranche unlock, or None if all are out."""
        if now < self.unlock_at:
            return self.unlock_at
        if self.steps <= 1:
            return None
        step = min(self.steps, months_between(self.unlock_at, now) // self.step_months)
        if step >= self.steps:
            return None
        return add_months(self.unlock_at, (step + 1) * self.step_months)


class Vault:
    """A vault: locked KITTY plus the date (and optional steps) it unlocks on."""

    def __init__(
        self,
        amount: int = 0,
        unlock_at=None,
        *,
        step_months: int | None = None,
        steps: int | None = None,
        name: str = "vault",
    ) -> None:
        self.name = name
        self.tranches: list[_Tranche] = []
        if amount or unlock_at is not None:
            self.deposit(amount, unlock_at, step_months=step_months, steps=steps)

    def deposit(
        self,
        amount: int,
        unlock_at=None,
        *,
        step_months: int | None = None,
        steps: int | None = None,
    ) -> int:
        """Lock *amount* in the vault until *unlock_at*.

        A step release is given as ``steps`` releases every ``step_months``
        months -- 10% per month is ``steps=10, step_months=1``.
        """
        a = amounts.kitoshi(amount)
        if a <= 0:
            raise VaultError(f"a vault holds a positive amount, got {a}")
        if unlock_at is None:
            raise VaultError("a vault needs an unlock date")
        if step_months is not None and (
            isinstance(step_months, bool)
            or not isinstance(step_months, int)
            or step_months < 1
        ):
            raise VaultError(f"step releases need whole months: {step_months!r}")
        if steps is None:
            steps = 1
        if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
            raise VaultError(f"a vault releases in at least one step, got {steps!r}")
        if step_months is None:
            step_months = 1
        self.tranches.append(_Tranche(a, unlock_at, steps, step_months))
        return self.locked_total()

    def locked_total(self) -> int:
        """Everything the vault holds, released or not."""
        return sum(t.amount for t in self.tranches)

    def available(self, now) -> int:
        """What may be moved at *now*."""
        return sum(t.available(now) for t in self.tranches)

    def next_release(self, now):
        """The next moment coins unlock, or None once everything is out."""
        moments = [t.next_release(now) for t in self.tranches if t.available(now) < t.amount - t.withdrawn]
        moments = [m for m in moments if m is not None]
        if not moments:
            return None
        return min(moments)

    def withdraw(self, amount: int, now, *, caller: str = "owner") -> int:
        """Move *amount* out of the vault, or refuse.

        *caller* is a label for the screen, never a permission: owner, guardian,
        governance and admin all take this same path, and all of them get
        `VaultLocked` before the release date (§11.7).
        """
        a = amounts.kitoshi(amount)
        if a <= 0:
            raise VaultError(f"withdraw a positive amount, got {a}")
        available = self.available(now)
        if available <= 0:
            moment = self.next_release(now)
            raise VaultLocked(
                f"{self.name}: these coins cannot be moved by anyone until "
                f"{moment:%Y-%m-%d}; no owner, guardian, governance vote or admin can "
                "open a vault early (§11.7)",
                release_at=moment,
            )
        if a > available:
            raise VaultError(
                f"the vault has released {available} kitoshi so far; "
                f"cannot withdraw {a}"
            )
        remaining = a
        for tranche in self.tranches:
            take = min(tranche.available(now), remaining)
            if take:
                tranche.withdrawn += take
                remaining -= take
            if not remaining:
                break
        return a

    def balance(self, now) -> int:
        """Coins still locked in the vault."""
        return self.locked_total() - sum(t.withdrawn for t in self.tranches)
