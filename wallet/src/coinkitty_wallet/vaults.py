"""Time-locked Vault math: how much has unlocked and when the next step is.

Integer math only; timestamps are unix seconds and a step interval is a whole
number of days (86400 s). No GTK here.
"""

from __future__ import annotations

from .models import Vault

SECONDS_PER_DAY = 86400


def planned_steps(v: Vault) -> int:
    """Number of planned release steps: ceil(100 / step_percent), or 1 for all-at-once."""
    if v.step_percent == 0:
        return 1
    return (100 + v.step_percent - 1) // v.step_percent


def steps_elapsed(v: Vault, now: int) -> int:
    """How many release steps have happened at or before ``now``."""
    if now < v.unlock_at:
        return 0
    if v.step_percent == 0:
        return 1
    interval = v.step_days * SECONDS_PER_DAY
    return 1 + (now - v.unlock_at) // interval


def unlocked_after_step(v: Vault, step: int) -> int:
    """Total unlocked after the given 1-based release step."""
    if step <= 0:
        return 0
    planned = planned_steps(v)
    if v.step_percent == 0 or step >= planned:
        return v.amount
    return step * v.amount * v.step_percent // 100


def unlocked_amount(v: Vault, now: int) -> int:
    """Total unlocked so far: never above amount, integer math only."""
    if now < v.unlock_at:
        return 0
    if v.step_percent == 0:
        return v.amount
    step = min(steps_elapsed(v, now), planned_steps(v))
    return unlocked_after_step(v, step)


def next_unlock(v: Vault, now: int) -> tuple[int, int] | None:
    """(timestamp, amount) of the next scheduled unlock, or None when fully unlocked."""
    unlocked = unlocked_amount(v, now)
    if unlocked >= v.amount:
        return None
    if v.step_percent == 0:
        return (v.unlock_at, v.amount)

    step = steps_elapsed(v, now) + 1
    planned = planned_steps(v)
    if step > planned:
        return None

    timestamp = v.unlock_at + (step - 1) * v.step_days * SECONDS_PER_DAY
    amount = unlocked_after_step(v, step) - unlocked_after_step(v, step - 1)
    return (timestamp, amount)
