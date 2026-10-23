"""Time-locked Vault math: how much has unlocked and when the next step is.

Integer math only; timestamps are unix seconds and a step interval is a whole
number of days (86400 s). No GTK here.
"""

from __future__ import annotations

from .models import Vault

SECONDS_PER_DAY = 86400


def step_size(v: Vault) -> int:
    """Kitoshi (or sats) released per step: step_percent of amount, floored."""
    return v.amount * v.step_percent // 100


def steps_elapsed(v: Vault, now: int) -> int:
    """How many release steps have happened at or before ``now``."""
    if now < v.unlock_at:
        return 0
    if v.step_percent == 0:
        return 1
    interval = v.step_days * SECONDS_PER_DAY
    return 1 + (now - v.unlock_at) // interval


def unlocked_amount(v: Vault, now: int) -> int:
    """Total unlocked so far: never above amount, integer math only."""
    if now < v.unlock_at:
        return 0
    if v.step_percent == 0:
        return v.amount
    return min(steps_elapsed(v, now) * step_size(v), v.amount)


def next_unlock(v: Vault, now: int) -> tuple[int, int] | None:
    """(timestamp, amount) of the next unlock, or None when fully unlocked."""
    unlocked = unlocked_amount(v, now)
    if unlocked >= v.amount:
        return None
    if v.step_percent == 0:
        return (v.unlock_at, v.amount)
    timestamp = v.unlock_at + steps_elapsed(v, now) * v.step_days * SECONDS_PER_DAY
    return (timestamp, min(step_size(v), v.amount - unlocked))
