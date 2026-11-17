"""KITTY amounts as an exact integer count of kitoshi.

White paper v0.3 §9.1: the smallest unit is the **kitoshi**, ``1 CoinKitty =
10**24 kitoshi``, and "Amounts are stored as unsigned 128-bit integers".

Everything here is exact integer arithmetic.  No float ever touches an amount:
floats cannot represent 10**24 exactly, and a wallet that rounds money is a
wallet that loses it.
"""

from __future__ import annotations

__all__ = [
    "KITOSHI_PER_KITTY",
    "MAX_KITOSHI",
    "AmountError",
    "kitoshi",
    "parse_kitoshi",
    "parse_kitty",
    "format_kitoshi",
    "format_kitty",
    "split_kitty",
    "percent_of",
    "is_kitoshi",
]

#: kitoshi per CoinKitty (constitutional, §9.1)
KITOSHI_PER_KITTY = 10**24

#: amounts are unsigned 128-bit integers (§9.1)
MAX_KITOSHI = 2**128 - 1

#: digits after the point when writing KITTY in decimal
DECIMAL_PLACES = 24


class AmountError(ValueError):
    """Raised for any amount this wallet would have to guess about."""


def is_kitoshi(value) -> bool:
    """True if *value* is a usable amount: an exact int in range."""
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    return 0 <= value <= MAX_KITOSHI


def kitoshi(value) -> int:
    """Accept an already-exact amount, reject everything else."""
    if isinstance(value, bool):
        raise AmountError(f"amount must be an integer count of kitoshi, got {value!r}")
    if not isinstance(value, int):
        raise AmountError(
            "amounts are an integer count of kitoshi, not "
            f"{type(value).__name__}: floats are never used for money"
        )
    if value < 0:
        raise AmountError(f"amounts cannot be negative: {value}")
    if value > MAX_KITOSHI:
        raise AmountError(f"amount {value} exceeds the 128-bit maximum {MAX_KITOSHI}")
    return value


def parse_kitoshi(text) -> int:
    """Parse a plain count of kitoshi.  A fractional kitoshi does not exist."""
    if isinstance(text, bool) or not isinstance(text, str):
        raise AmountError(f"amount must be given as text, got {text!r}")
    s = text.strip().replace("_", "")
    if s.startswith("+"):
        s = s[1:]
    if not s.isdigit():
        raise AmountError(f"not a whole number of kitoshi: {text!r}")
    return kitoshi(int(s))


def parse_kitty(text) -> int:
    """Parse an amount written in CoinKitty, e.g. ``"1.5"`` -> 1.5 * 10**24.

    A decimal point is allowed only when the digits after it fit in 24 places;
    anything finer is a fractional kitoshi and is refused, never rounded.
    """
    if isinstance(text, bool) or not isinstance(text, str):
        raise AmountError(f"amount must be given as text, got {text!r}")
    s = text.strip().replace("_", "")
    if s.startswith("+"):
        s = s[1:]
    if not s or not s.replace(".", "", 1).isdigit():
        raise AmountError(f"not an amount of KITTY: {text!r}")
    whole, dot, frac = s.partition(".")
    if dot and not frac:
        raise AmountError(f"not an amount of KITTY: {text!r}")
    if len(frac) > DECIMAL_PLACES:
        raise AmountError(
            f"{text!r} is finer than the smallest unit (kitoshi), so it "
            "would have to be rounded: refused"
        )
    scale = 10 ** (DECIMAL_PLACES - len(frac))
    return kitoshi(int(whole + frac) * scale)


def format_kitoshi(value) -> str:
    """Format an amount as an exact count of kitoshi."""
    return str(kitoshi(value))


def format_kitty(value, group: bool = False) -> str:
    """Format an amount in CoinKitty, trailing zeros trimmed, never rounded.

    ``group=True`` inserts a thin space every three digits for readability; it
    only ever adds separators, it never changes a digit.
    """
    v = kitoshi(value)
    whole, frac = divmod(v, KITOSHI_PER_KITTY)
    if frac == 0:
        text = str(whole)
    else:
        text = f"{whole}.{str(frac).zfill(DECIMAL_PLACES).rstrip('0')}"
    if not group:
        return text
    whole_part, dot, frac_part = text.partition(".")
    grouped = "{:,}".format(whole).replace(",", "\u00a0")
    return grouped + dot + frac_part


def split_kitty(amount: int, parts: int) -> tuple[int, ...]:
    """Split *amount* into *parts* shares, exactly.

    Used by Rain (one payment across a group, wallet spec §3.6).  The shares
    differ by at most one kitoshi and add back up to the original amount: no
    kitoshi is created or destroyed by a split.
    """
    a = kitoshi(amount)
    if isinstance(parts, bool) or not isinstance(parts, int) or parts <= 0:
        raise AmountError(f"cannot split among {parts!r} recipients")
    base, rem = divmod(a, parts)
    return tuple(base + (1 if i < rem else 0) for i in range(parts))


def percent_of(amount: int, numerator: int, denominator: int = 100) -> int:
    """``amount * numerator // denominator``, rounded down to whole kitoshi.

    The lottery share of a claimable payment is ``amount * 2 // 100``
    (white paper §11.3, proposed 2%).
    """
    a = kitoshi(amount)
    if isinstance(numerator, bool) or not isinstance(numerator, int) or numerator < 0:
        raise AmountError(f"bad percentage numerator: {numerator!r}")
    if isinstance(denominator, bool) or not isinstance(denominator, int) or denominator <= 0:
        raise AmountError(f"bad percentage denominator: {denominator!r}")
    if numerator > denominator:
        raise AmountError(f"{numerator}/{denominator} is more than the whole amount")
    return a * numerator // denominator
