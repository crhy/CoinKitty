"""Rain splitting: divide a total among members, exactly, with no float math."""

from __future__ import annotations


def split_equal(total: int, member_ids: list[str]) -> dict[str, int]:
    """Split ``total`` units equally among ``member_ids``.

    Each member gets ``total // n``; the remainder (``total % n``) is handed out
    one unit each to the first members in list order, so the values sum to
    exactly ``total``. Raises ``ValueError`` if there are no members, if any id
    is duplicated, or if ``total`` is not positive.
    """
    if not isinstance(total, int) or total <= 0:
        raise ValueError("total must be a positive int")
    if not member_ids:
        raise ValueError("need at least one member")
    if len(set(member_ids)) != len(member_ids):
        raise ValueError("member ids must be unique")

    n = len(member_ids)
    base, remainder = divmod(total, n)
    result: dict[str, int] = {}
    for index, member in enumerate(member_ids):
        result[member] = base + (1 if index < remainder else 0)
    return result


def validate_custom(total: int, amounts: dict[str, int]) -> None:
    """Raise ``ValueError`` unless every amount is positive and they sum to ``total``."""
    if not amounts:
        raise ValueError("need at least one amount")
    for member, amount in amounts.items():
        if not isinstance(amount, int) or amount <= 0:
            raise ValueError(f"amount for {member!r} must be a positive int")
    if sum(amounts.values()) != total:
        raise ValueError("amounts must sum to total")
