"""Demo conversion between assets, for the Home and Wallet screens.

KittyChain is not live, so the cross-asset rate below is INVENTED for the demo
only; it is not a real price. Money stays an ``int`` count of the smallest unit
throughout (KITTY kitoshi, BTC sats); no float is ever used.
"""

from __future__ import annotations

from .units import KITTY, BTC

# INVENTED demo rate: one KITTY is worth this many sats. Not a real price.
DEMO_SATS_PER_KITTY = 2_000


def value_in_sats(asset_code: str, units: int) -> int:
    """Return ``units`` of ``asset_code`` expressed in sats (an int).

    KITTY kitoshi are scaled by :data:`DEMO_SATS_PER_KITTY` and divided by
    ``10**24`` (integer division); BTC units are already sats. Raises
    ``ValueError`` for an unknown asset code.
    """
    if asset_code == KITTY.code:
        return units * DEMO_SATS_PER_KITTY // 10**KITTY.decimals
    if asset_code == BTC.code:
        return units
    raise ValueError(f"unknown asset code {asset_code!r}")


def portfolio_shares(balances: dict[str, int]) -> list[tuple[str, int]]:
    """Value of each asset in sats, in the given dict order.

    Assets whose value in sats is 0 are left out. Returns ``(code, sats)``
    pairs.
    """
    shares: list[tuple[str, int]] = []
    for code, units in balances.items():
        value = value_in_sats(code, units)
        if value != 0:
            shares.append((code, value))
    return shares


def percent_shares(shares: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Turn ``(code, sats)`` shares into ``(code, percent)`` ints summing to 100.

    Each percent is the floor of its exact share of the total; the leftover
    rounding remainder is added to the largest share so the percents total 100.
    An empty or zero-total input returns an empty list.
    """
    total = sum(value for _code, value in shares)
    if total == 0:
        return []

    percents = [(code, value * 100 // total) for code, value in shares]
    remainder = 100 - sum(percent for _code, percent in percents)
    if remainder:
        largest = max(range(len(shares)), key=lambda i: shares[i][1])
        code, percent = percents[largest]
        percents[largest] = (code, percent + remainder)
    return percents
