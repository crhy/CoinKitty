"""Money units and text formatting for the CoinKitty Wallet.

Money is ALWAYS an ``int`` count of the asset's smallest unit (never a float).
``decimal.Decimal`` is used only to parse and format human-facing text.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Context, Decimal, InvalidOperation, localcontext

KITOSHI_PER_KITTY = 10**24
SATS_PER_BTC = 10**8


@dataclass(frozen=True)
class Asset:
    code: str
    name: str
    decimals: int


KITTY = Asset("KITTY", "KittyCoin", 24)
BTC = Asset("BTC", "Bitcoin", 8)
ASSETS = {"KITTY": KITTY, "BTC": BTC}

# Explicit context with precision 80: enough significant digits that
# multiplying a realistic amount by the asset scale stays exact.
_PARSE_CONTEXT = Context(prec=80)


def _is_plain_decimal(s: str) -> bool:
    """True only for ``digits`` or ``digits.digits`` (at least one digit each side)."""
    if not s:
        return False
    whole, dot, fraction = s.partition(".")
    if dot:
        return whole.isdigit() and fraction.isdigit()
    return whole.isdigit()


def parse_amount(text: str, asset: Asset) -> int:
    """Parse a plain decimal string into an int count of the smallest unit.

    Accepts optional surrounding whitespace and ``,`` as a thousands separator
    (``"1,000.25"``). Raises ``ValueError`` for empty text, negatives, more
    fractional digits than ``asset.decimals``, or anything that is not a plain
    decimal number (no ``1e5``, no ``nan``, no stray characters).
    """
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    cleaned = text.strip().replace(",", "")
    if not _is_plain_decimal(cleaned):
        raise ValueError(f"{text!r} is not a plain decimal number")

    _, dot, fraction = cleaned.partition(".")
    if dot and len(fraction) > asset.decimals:
        raise ValueError(f"too many fractional digits for {asset.code}")

    with localcontext(_PARSE_CONTEXT):
        try:
            value = Decimal(cleaned)
        except InvalidOperation:
            raise ValueError(f"{text!r} is not a valid decimal") from None
        scaled = value * (10 ** asset.decimals)
    if scaled != scaled.to_integral_value():
        raise ValueError(f"{text!r} has more precision than {asset.code} supports")
    return int(scaled)


def format_amount(units: int, asset: Asset, max_decimals: int = 8) -> str:
    """Format an int count of the smallest unit as human text.

    Truncates (rounds DOWN) to ``max_decimals`` fractional digits, trims
    trailing zeros, and adds thousands separators to the whole part
    (``"12,345.6"``). Zero renders as ``"0"``. A non-zero amount that truncates
    to zero renders as ``"<0.00000001"`` (``max_decimals`` digits: zeros then a
    1). Raises ``ValueError`` for negative units.
    """
    if not isinstance(units, int) or units < 0:
        raise ValueError("units must be a non-negative int")
    if units == 0:
        return "0"

    scale = 10 ** asset.decimals
    whole, frac = divmod(units, scale)
    frac_str = str(frac).zfill(asset.decimals)
    truncated = frac_str[:max_decimals].rstrip("0")

    whole_str = f"{whole:,}"
    if truncated:
        return f"{whole_str}.{truncated}"
    if whole == 0:
        # Non-zero amount too small to show at this precision.
        return "<0." + "0" * (max_decimals - 1) + "1"
    return whole_str
