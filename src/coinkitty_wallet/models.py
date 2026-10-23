"""Data model for the CoinKitty Wallet: contacts, rain groups, transactions.

These are plain dataclasses with validation only; no business logic lives here.
Money amounts are always ``int`` counts of the asset's smallest unit.
"""

from __future__ import annotations

from dataclasses import dataclass

TRANSACTION_KINDS = ("send", "receive", "rain")


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
