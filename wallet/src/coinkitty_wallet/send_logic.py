"""Send-screen logic (no GTK): contact ranking, search, payment requests.

Money is always an ``int`` count of the asset's smallest unit.
"""

from __future__ import annotations

from dataclasses import dataclass

from .bech32m import is_valid_address
from .units import ASSETS
from urllib.parse import urlencode, parse_qs

SCHEME = "coinkitty:"


def top_contacts(contacts, transactions, n=5) -> list:
    """Contacts to offer first: favorites, then most-paid-by-name, then name.

    Counts ``send`` transactions whose counterparty matches the contact's
    name. Returns at most ``n`` contacts.
    """
    send_counts: dict[str, int] = {}
    for txn in transactions:
        if txn.kind == "send":
            send_counts[txn.counterparty] = send_counts.get(txn.counterparty, 0) + 1
    ranked = sorted(
        contacts,
        key=lambda c: (not c.favorite, -send_counts.get(c.name, 0), c.name),
    )
    return ranked[:n]


def search_contacts(contacts, query) -> list:
    """Case-insensitive substring match on contact name; empty query returns all."""
    if query == "":
        return sorted(contacts, key=lambda c: c.name)
    needle = query.lower()
    return sorted(
        (c for c in contacts if needle in c.name.lower()),
        key=lambda c: c.name,
    )


@dataclass
class PaymentRequest:
    """A payment request: who must pay whom, how much, and a memo."""

    address: str
    asset: str
    amount: int
    memo: str

    def to_uri(self) -> str:
        """Encode as ``coinkitty:<address>?asset=..&amount=..&memo=<urlencoded>``."""
        memo = urlencode({"memo": self.memo})[len("memo="):]
        return f"{SCHEME}{self.address}?asset={self.asset}&amount={self.amount}&memo={memo}"

    @staticmethod
    def from_uri(uri: str) -> "PaymentRequest":
        """Decode a URI back into a :class:`PaymentRequest` (ValueError if malformed)."""
        if not uri.startswith(SCHEME):
            raise ValueError(f"unknown scheme in {uri!r}")
        rest = uri[len(SCHEME):]
        address, _, query = rest.partition("?")
        if not is_valid_address(address):
            raise ValueError(f"invalid address: {address!r}")
        fields = parse_qs(query, keep_blank_values=True)
        for key in ("asset", "amount", "memo"):
            if len(fields.get(key, [])) != 1:
                raise ValueError(f"expected exactly one {key!r} in {uri!r}")
        asset = fields["asset"][0]
        if asset not in ASSETS:
            raise ValueError(f"unknown asset: {asset!r}")
        raw_amount = fields["amount"][0]
        try:
            amount = int(raw_amount)
        except ValueError:
            raise ValueError(f"amount must be an integer: {raw_amount!r}")
        if amount < 0:
            raise ValueError(f"amount must not be negative: {amount}")
        return PaymentRequest(address=address, asset=asset, amount=amount, memo=fields["memo"][0])
