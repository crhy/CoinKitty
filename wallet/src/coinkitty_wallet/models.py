"""Data model for the CoinKitty Wallet: contacts, rain groups, transactions.

These are plain dataclasses with validation only; no business logic lives here.
Money amounts are always ``int`` counts of the asset's smallest unit.
"""

from __future__ import annotations

from dataclasses import dataclass

TRANSACTION_KINDS = ("send", "receive", "rain")
BOUNTY_STATUSES = (
    "open",
    "funded",
    "assigned",
    "delivered",
    "released",
    "disputed",
    "cancelled",
)


@dataclass
class Contact:
    id: str
    name: str
    address: str
    preferred_asset: str = "KITTY"
    favorite: bool = False


@dataclass
class RainGroup:
    id: str
    name: str
    member_ids: list[str]
    favorite: bool = False


@dataclass
class Vault:
    id: str
    asset: str
    amount: int
    created_at: int
    unlock_at: int
    released: int = 0
    step_percent: int = 0
    step_days: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.amount, int) or isinstance(self.amount, bool):
            raise ValueError("amount must be an int count of the smallest unit")
        if not 0 <= self.step_percent <= 100:
            raise ValueError("step_percent must be 0..100")
        if self.step_percent > 0 and self.step_days < 1:
            raise ValueError("step_days must be >= 1 when step_percent > 0")


@dataclass
class Transaction:
    id: str
    kind: str
    asset: str
    amount: int
    counterparty: str
    memo: str
    timestamp: int

    def __post_init__(self) -> None:
        if self.kind not in TRANSACTION_KINDS:
            raise ValueError(f"kind must be one of {TRANSACTION_KINDS}, got {self.kind!r}")
        if not isinstance(self.amount, int):
            raise ValueError("amount must be an int count of the smallest unit")
        if not isinstance(self.timestamp, int):
            raise ValueError("timestamp must be an int of Unix seconds")


@dataclass
class Bid:
    id: str
    bounty_id: str
    bidder: str
    price: int
    note: str = ""
    reputation: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.price, int) or isinstance(self.price, bool):
            raise ValueError("price must be an int count of the smallest unit")
        if self.price <= 0:
            raise ValueError("price must be positive")
        if not isinstance(self.reputation, int) or isinstance(self.reputation, bool):
            raise ValueError("reputation must be an int")
        if self.reputation < 0:
            raise ValueError("reputation must be non-negative")


@dataclass
class Bounty:
    id: str
    poster: str
    title: str
    description: str
    category: str
    location: str
    window_start: int
    window_end: int
    price: int
    parent_id: str | None = None
    status: str = "open"
    bids: list[Bid] | None = None
    accepted_bid_id: str | None = None
    escrow: int = 0
    delivered_at: int | None = None

    def __post_init__(self) -> None:
        if self.status not in BOUNTY_STATUSES:
            raise ValueError(f"status must be one of {BOUNTY_STATUSES}, got {self.status!r}")
        if not isinstance(self.price, int) or isinstance(self.price, bool):
            raise ValueError("price must be an int count of the smallest unit")
        if self.price <= 0:
            raise ValueError("price must be positive")
        if not isinstance(self.escrow, int) or isinstance(self.escrow, bool):
            raise ValueError("escrow must be an int count of the smallest unit")
        if self.escrow < 0:
            raise ValueError("escrow must be non-negative")
        if not isinstance(self.window_start, int) or isinstance(self.window_start, bool):
            raise ValueError("window_start must be an int of Unix seconds")
        if not isinstance(self.window_end, int) or isinstance(self.window_end, bool):
            raise ValueError("window_end must be an int of Unix seconds")
        if self.window_end < self.window_start:
            raise ValueError("window_end must be >= window_start")
        if self.bids is None:
            self.bids = []
        for bid in self.bids:
            if bid.bounty_id != self.id:
                raise ValueError("bid.bounty_id must match the bounty id")
