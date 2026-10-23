"""Demo backend: the wallet's whole state stored in one JSON file.

KittyChain does not exist yet, so this is a fake/demo backend. Balances are
DEMO coins, never real. Big ints survive the JSON round trip exactly (Python's
``json`` keeps arbitrary-precision ints; nothing is ever converted to float).
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict
from typing import Callable

from .bech32m import encode_address, is_valid_address
from .bounties import accept, cancel, create_child, deliver, fund, release
from .models import Bid, Bounty, Contact, RainGroup, Transaction, Vault
from .rain import split_equal, validate_custom
from .vaults import unlocked_amount

_DEMO_CONTACTS = ("Babysitter", "Julie", "Rick", "Sam", "Maya")
_DEMO_FAVORITES = frozenset({"Babysitter", "Julie"})
_DEMO_POSTERS = ("Neighborhood", "Downtown", "Riverside", "Hilltop", "Old Town", "Market Row")


def _default_clock() -> int:
    return int(time.time())


def _is_money(value: object) -> bool:
    """True for a positive int that is not a bool (True is an int in Python)."""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _seed_bounties(now: int) -> list[Bounty]:
    """Build the six demo open bounties other people posted.

    The "Build a shed" bounty is funded and carries two funded sub-bounties
    carved out of its escrow. Money is KITTY's smallest unit; windows are
    Unix-second ints.
    """
    day = 86400
    specs = (
        ("seed-smoothie", "Neighborhood", "Smoothie", "A fresh-fruit smoothie.", "Food", "Corner cafe", 10**24, 2),
        ("seed-cello", "Downtown", "Cello lesson", "One hour of cello tuition.", "Music", "Recital hall", 2 * 10**24, 5),
        ("seed-dishwasher", "Riverside", "Dishwasher shift", "Unload and load a dishwasher.", "Chores", "Community kitchen", 10**24, 1),
        ("seed-carwash", "Hilltop", "Car wash", "Wash and wax one car.", "Errands", "Gas station bay", 3 * 10**24, 3),
        ("seed-guitar", "Old Town", "Guitar for sale", "Acoustic guitar, good condition.", "Goods", "Flea market", 5 * 10**24, 7),
    )
    bounties: list[Bounty] = []
    for bid_id, poster, title, description, category, location, price, window_days in specs:
        bounties.append(Bounty(
            id=bid_id,
            poster=poster,
            title=title,
            description=description,
            category=category,
            location=location,
            window_start=now,
            window_end=now + window_days * day,
            price=price,
        ))

    shed = Bounty(
        id="seed-shed",
        poster="Market Row",
        title="Build a shed",
        description="Assemble a backyard storage shed.",
        category="Skills",
        location="Rental lot",
        window_start=now,
        window_end=now + 14 * day,
        price=10 * 10**24,
        status="funded",
        escrow=10 * 10**24,
    )
    bounties.append(shed)
    bounties.append(create_child(shed, "Dig the foundation", 4 * 10**24, now))
    bounties.append(create_child(shed, "Raise the walls", 3 * 10**24, now))
    return bounties


class DemoBackend:
    """In-memory wallet state backed by a single JSON file on disk."""

    def __init__(self, path: str, clock: Callable[[], int] = _default_clock) -> None:
        self.path = path
        self.clock = clock
        self._address: str | None = None
        self._balances: dict[str, int] = {}
        self._contacts: list[Contact] = []
        self._rain_groups: list[RainGroup] = []
        self._transactions: list[Transaction] = []  # oldest first
        self._created_at: int | None = None
        self._vaults: list[Vault] = []
        self._checked_in: list[str] = []  # local dates the user checked in
        self._drawn: list[str] = []  # local dates the lottery was drawn
        self._pool: int = 2 * 10**24  # demo prize pool, KITTY
        self._bounties: list[Bounty] = []

    # ---- construction / persistence -------------------------------------

    @classmethod
    def create(cls, path: str, rng) -> "DemoBackend":
        """Build a fresh demo wallet (random addresses) and save it."""
        obj = cls(path)
        obj._address = encode_address(bytes(rng.randbytes(20)))
        obj._balances = {"KITTY": 25 * 10**24, "BTC": 150_000}
        obj._created_at = obj.clock()

        by_name: dict[str, str] = {}
        for name in _DEMO_CONTACTS:
            contact = Contact(
                id=uuid.uuid4().hex,
                name=name,
                address=encode_address(bytes(rng.randbytes(20))),
                favorite=name in _DEMO_FAVORITES,
            )
            obj._contacts.append(contact)
            by_name[name] = contact.id

        obj._rain_groups.append(
            RainGroup(
                id=uuid.uuid4().hex,
                name="Band",
                member_ids=[by_name["Rick"], by_name["Sam"], by_name["Maya"]],
                favorite=True,
            )
        )
        obj._rain_groups.append(
            RainGroup(
                id=uuid.uuid4().hex,
                name="Kids",
                member_ids=[by_name["Julie"], by_name["Maya"]],
            )
        )
        obj._bounties = _seed_bounties(obj.clock())
        obj._save()
        return obj

    @classmethod
    def load(cls, path: str) -> "DemoBackend":
        """Read an existing wallet file back into memory."""
        obj = cls(path)
        with open(path) as handle:
            state = json.load(handle)
        obj._address = state["address"]
        obj._balances = dict(state["balances"])
        obj._contacts = [Contact(**row) for row in state["contacts"]]
        obj._rain_groups = [RainGroup(**row) for row in state["rain_groups"]]
        obj._transactions = [Transaction(**row) for row in state["transactions"]]
        created_at = state.get("created_at")
        if created_at is None:
            created_at = int(os.path.getmtime(path))
        obj._created_at = created_at
        obj._vaults = [Vault(**row) for row in state.get("vaults", [])]
        obj._checked_in = list(state.get("checked_in", []))
        obj._drawn = list(state.get("drawn", []))
        obj._pool = state.get("pool", 2 * 10**24)
        obj._bounties = [
            Bounty(**{**row, "bids": [Bid(**bid) for bid in row.get("bids", [])]})
            for row in state.get("bounties", [])
        ]
        return obj

    def _to_state(self) -> dict:
        return {
            "address": self._address,
            "balances": self._balances,
            "created_at": self._created_at,
            "contacts": [asdict(c) for c in self._contacts],
            "rain_groups": [asdict(g) for g in self._rain_groups],
            "transactions": [asdict(t) for t in self._transactions],
            "vaults": [asdict(v) for v in self._vaults],
            "checked_in": list(self._checked_in),
            "drawn": list(self._drawn),
            "pool": self._pool,
            "bounties": [asdict(b) for b in self._bounties],
        }

    def _save(self) -> None:
        """Write the state atomically: temp file in the same dir, fsync, rename."""
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as handle:
            json.dump(self._to_state(), handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, self.path)

    # ---- accessors -------------------------------------------------------

    def address(self) -> str:
        return self._address

    def balance(self, asset: str) -> int:
        if asset not in self._balances:
            raise ValueError(f"unknown asset {asset!r}")
        return self._balances[asset]

    def contacts(self) -> list[Contact]:
        return list(self._contacts)

    def rain_groups(self) -> list[RainGroup]:
        return list(self._rain_groups)

    def transactions(self) -> list[Transaction]:
        """Transaction history, newest first."""
        return list(reversed(self._transactions))

    def days_since_created(self, now: int) -> int:
        """Whole days since creation, counting the creation day as day 1.

        ``now`` is Unix seconds. Returns ``1`` when ``now`` is on the creation
        day, and grows by one per whole 86400-second day elapsed.
        """
        if self._created_at is None:
            raise ValueError("created_at is unknown")
        return (now - self._created_at) // 86400 + 1

    def earned_today(self, asset: str, now: int) -> int:
        """Sum of "receive" transactions in ``asset`` on ``now``'s local day.

        A transaction counts when its timestamp falls in the same local
        calendar day (year, month, day via :func:`time.localtime`) as ``now``.
        """
        now_day = time.localtime(now)[:3]
        total = 0
        for txn in self._transactions:
            if txn.kind == "receive" and txn.asset == asset:
                if time.localtime(txn.timestamp)[:3] == now_day:
                    total += txn.amount
        return total

    # ---- mutations (each saves the file) --------------------------------

    def add_contact(self, name: str, address: str, preferred_asset: str = "KITTY") -> Contact:
        if not is_valid_address(address):
            raise ValueError("invalid address")
        contact = Contact(id=uuid.uuid4().hex, name=name, address=address,
                          preferred_asset=preferred_asset)
        self._contacts.append(contact)
        self._save()
        return contact

    def update_contact(self, contact: Contact) -> None:
        """Replace the stored contact that shares ``contact.id``."""
        for index, existing in enumerate(self._contacts):
            if existing.id == contact.id:
                self._contacts[index] = contact
                self._save()
                return
        raise ValueError("no contact with that id")

    def delete_contact(self, contact_id: str) -> None:
        """Remove a contact and drop it from every rain group."""
        self._contacts = [c for c in self._contacts if c.id != contact_id]
        for group in self._rain_groups:
            group.member_ids = [m for m in group.member_ids if m != contact_id]
        self._save()

    def save_group(self, group: RainGroup) -> None:
        """Add a new group, or replace the existing one with the same id."""
        for index, existing in enumerate(self._rain_groups):
            if existing.id == group.id:
                self._rain_groups[index] = group
                self._save()
                return
        self._rain_groups.append(group)
        self._save()

    def delete_group(self, group_id: str) -> None:
        self._rain_groups = [g for g in self._rain_groups if g.id != group_id]
        self._save()

    def send(self, asset: str, amount: int, contact_id: str, memo: str = "") -> Transaction:
        """Send ``amount`` of ``asset`` to a contact; reduces the balance."""
        if not _is_money(amount):
            raise ValueError("amount must be a positive int (bools are not money)")
        if amount > self.balance(asset):
            raise ValueError("amount exceeds balance")
        contact = self._require_contact(contact_id)
        self._balances[asset] -= amount
        txn = Transaction(
            id=uuid.uuid4().hex,
            kind="send",
            asset=asset,
            amount=amount,
            counterparty=contact.name,
            memo=memo,
            timestamp=self.clock(),
        )
        self._transactions.append(txn)
        self._save()
        return txn

    def rain(self, asset: str, total: int, member_ids: list[str],
             amounts: dict[str, int] | None = None) -> list[Transaction]:
        """Send a rain: all-or-nothing against the balance.

        Splits ``total`` equally via :func:`split_equal` unless ``amounts`` is
        given and valid. Returns one transaction per member (newest first, like
        :meth:`transactions`).
        """
        if not _is_money(total):
            raise ValueError("total must be a positive int (bools are not money)")
        if total > self.balance(asset):
            raise ValueError("total exceeds balance")
        for member in member_ids:
            self._require_contact(member)

        if amounts is None:
            shares = split_equal(total, member_ids)
        else:
            if any(isinstance(value, bool) for value in amounts.values()):
                raise ValueError("custom amounts must be plain ints, not bools")
            validate_custom(total, amounts)
            shares = amounts

        self._balances[asset] -= total
        txns: list[Transaction] = []
        for member, amount in shares.items():
            contact = self._require_contact(member)
            txns.append(Transaction(
                id=uuid.uuid4().hex,
                kind="rain",
                asset=asset,
                amount=amount,
                counterparty=contact.name,
                memo="",
                timestamp=self.clock(),
            ))
        self._transactions.extend(txns)
        self._save()
        return list(reversed(txns))

    def pick_luck(self, rng) -> Contact:
        """Pick a random contact (the Launch Window). ValueError if none."""
        if not self._contacts:
            raise ValueError("no contacts to pick")
        return rng.choice(self._contacts)

    def apply_swap(self, sell_asset: str, amount: int, buy_asset: str,
                   receive: int) -> tuple[Transaction, Transaction]:
        """Apply a completed simulated swap: all-or-nothing balance move.

        Reduces ``sell_asset`` by ``amount`` and increases ``buy_asset`` by
        ``receive``, recording a "swap out" (kind ``send``) and a "swap in"
        (kind ``receive``) transaction, both with counterparty "Simulated swap".
        Raises ``ValueError`` if either amount is not a positive int (bools are
        not money) or the sell amount exceeds the balance. Nothing moves unless
        both sides validate, so the move is all-or-nothing.
        """
        if not _is_money(amount) or not _is_money(receive):
            raise ValueError("amount and receive must be positive ints (bools are not money)")
        if amount > self.balance(sell_asset):
            raise ValueError("amount exceeds balance")
        self._balances[sell_asset] = self.balance(sell_asset) - amount
        self._balances[buy_asset] = self.balance(buy_asset) + receive
        out = Transaction(
            id=uuid.uuid4().hex,
            kind="send",
            asset=sell_asset,
            amount=amount,
            counterparty="Simulated swap",
            memo="swap out",
            timestamp=self.clock(),
        )
        in_txn = Transaction(
            id=uuid.uuid4().hex,
            kind="receive",
            asset=buy_asset,
            amount=receive,
            counterparty="Simulated swap",
            memo="swap in",
            timestamp=self.clock(),
        )
        self._transactions.extend((out, in_txn))
        self._save()
        return (out, in_txn)

    # ---- vaults -----------------------------------------------------------

    def create_vault(self, asset: str, amount: int, unlock_at: int,
                     step_percent: int = 0, step_days: int = 0) -> Vault:
        """Lock ``amount`` of ``asset`` into a vault; it leaves the balance."""
        if not _is_money(amount):
            raise ValueError("amount must be a positive int (bools are not money)")
        if amount > self.balance(asset):
            raise ValueError("amount exceeds balance")
        now = self.clock()
        if unlock_at <= now:
            raise ValueError("unlock_at must be in the future")
        if not isinstance(step_percent, int) or isinstance(step_percent, bool):
            raise ValueError("step_percent must be an int 0..100")
        if not 0 <= step_percent <= 100:
            raise ValueError("step_percent must be 0..100")
        if step_percent > 0 and (not isinstance(step_days, int) or step_days < 1):
            raise ValueError("step_days must be an int >= 1 when step_percent > 0")
        vault = Vault(id=uuid.uuid4().hex, asset=asset, amount=amount,
                      created_at=now, unlock_at=unlock_at,
                      step_percent=step_percent, step_days=step_days)
        self._balances[asset] = self.balance(asset) - amount
        self._vaults.append(vault)
        self._save()
        return vault

    def vaults(self) -> list[Vault]:
        """All vaults, oldest first."""
        return list(self._vaults)

    def withdraw_vault(self, vault_id: str, now: int) -> int:
        """Move unlocked-but-unreleased coins of one vault back to the balance.

        Returns the amount moved (0 is fine). There is no way to withdraw
        early and no way to delete a vault.
        """
        vault = next((v for v in self._vaults if v.id == vault_id), None)
        if vault is None:
            raise ValueError(f"no vault with id {vault_id!r}")
        movable = unlocked_amount(vault, now) - vault.released
        if movable <= 0:
            return 0
        vault.released += movable
        self._balances[vault.asset] = self.balance(vault.asset) + movable
        self._save()
        return movable

    # ---- Launch Window (demo) ----------------------------------------------

    def launch_window(self, now: int) -> tuple[int, int]:
        """(start, end) of tonight's Launch Window: 21:00-21:15 local time.

        If ``now`` is after tonight's window, returns the next day's window.
        """
        start = self._window_start(now)
        end = start + 15 * 60
        if now > end:
            start = self._window_start(now + 86400)
            end = start + 15 * 60
        return (start, end)

    def _window_start(self, now: int) -> int:
        """Unix seconds of the 21:00 local-time start of the day of ``now``."""
        year, month, day = time.localtime(now)[:3]
        return int(time.mktime((year, month, day, 21, 0, 0, 0, 0, -1)))

    def check_in(self, now: int) -> bool:
        """Check in for the lottery: only inside the window, once per night."""
        start, end = self.launch_window(now)
        if not start <= now <= end:
            return False
        date = time.strftime("%Y-%m-%d", time.localtime(now))
        if date in self._checked_in:
            return False
        self._checked_in.append(date)
        self._save()
        return True

    def lottery_pool(self) -> int:
        """The demo prize pool, in KITTY's smallest unit."""
        return self._pool

    def checked_in_dates(self) -> list[str]:
        """Local dates the user has checked in for the lottery."""
        return list(self._checked_in)

    def run_demo_draw(self, date: str, rng) -> bool:
        """Draw the nightly lottery for ``date``; True if the user won.

        Only draws if the user checked in that date and it was not drawn yet.
        A win pays 10% of the pool into the KITTY balance as a receive
        transaction from "Launch Window lottery".
        """
        if date not in self._checked_in or date in self._drawn:
            return False
        self._drawn.append(date)
        won = rng.randrange(20) == 0
        if won:
            prize = self._pool * 10 // 100
            self._balances["KITTY"] = self.balance("KITTY") + prize
            self._transactions.append(Transaction(
                id=uuid.uuid4().hex,
                kind="receive",
                asset="KITTY",
                amount=prize,
                counterparty="Launch Window lottery",
                memo="",
                timestamp=self.clock(),
            ))
        self._save()
        return won

    # ---- bounties --------------------------------------------------------

    def bounties(self) -> list[Bounty]:
        """All bounty cards, oldest first."""
        return list(self._bounties)

    def my_posted(self) -> list[Bounty]:
        """Bounties the wallet's own address posted."""
        return [b for b in self._bounties if b.poster == self._address]

    def _require_bounty(self, bounty_id: str) -> Bounty:
        for bounty in self._bounties:
            if bounty.id == bounty_id:
                return bounty
        raise ValueError(f"no bounty with id {bounty_id!r}")

    def post_bounty(self, title: str, description: str, category: str,
                    location: str, price: int, window_days: int = 7) -> Bounty:
        """Post an open bounty from the wallet's own address and save it."""
        if not _is_money(price):
            raise ValueError("price must be a positive int (bools are not money)")
        if not isinstance(window_days, int) or isinstance(window_days, bool) or window_days < 1:
            raise ValueError("window_days must be an int >= 1")
        now = self.clock()
        bounty = Bounty(
            id=uuid.uuid4().hex,
            poster=self._address,
            title=title,
            description=description,
            category=category,
            location=location,
            window_start=now,
            window_end=now + window_days * 86400,
            price=price,
        )
        self._bounties.append(bounty)
        self._save()
        return bounty

    def place_demo_bids(self, bounty_id: str, rng) -> list[Bid]:
        """Add three demo bids ("Kitty-<hex>") within +/-20% of the price."""
        bounty = self._require_bounty(bounty_id)
        low = bounty.price * 80 // 100
        high = bounty.price * 120 // 100
        placed: list[Bid] = []
        for _ in range(3):
            price = rng.randrange(low, high + 1)
            price -= price % 10**22  # whole 0.01 KITTY, so bids read cleanly
            bid = Bid(
                id=uuid.uuid4().hex,
                bounty_id=bounty.id,
                bidder=f"Kitty-{rng.randrange(16 ** 8):08x}",
                price=price,
                reputation=rng.randint(1, 100),
            )
            bounty.bids.append(bid)
            placed.append(bid)
        self._save()
        return placed

    def fund(self, bounty_id: str) -> Bounty:
        """Fund a bounty: move its price from the KITTY balance into escrow."""
        bounty = self._require_bounty(bounty_id)
        self._balances["KITTY"] = fund(bounty, self.balance("KITTY"))
        self._save()
        return bounty

    def accept(self, bounty_id: str, bid_id: str) -> Bounty:
        """Assign a funded bounty to one of its bids."""
        bounty = self._require_bounty(bounty_id)
        accept(bounty, bid_id)
        self._save()
        return bounty

    def deliver(self, bounty_id: str) -> Bounty:
        """Mark an assigned bounty as delivered now."""
        bounty = self._require_bounty(bounty_id)
        deliver(bounty, self.clock())
        self._save()
        return bounty

    def release(self, bounty_id: str) -> tuple[int, int]:
        """Release a delivered bounty; refund the poster's balance.

        Returns ``(paid_to_hunter, refunded_to_poster)``. The refund returns to
        the wallet's KITTY balance only when the wallet itself posted the bounty.
        """
        bounty = self._require_bounty(bounty_id)
        paid, refunded = release(bounty)
        if bounty.poster == self._address and refunded > 0:
            self._balances["KITTY"] = self.balance("KITTY") + refunded
        self._save()
        return (paid, refunded)

    def cancel(self, bounty_id: str) -> Bounty:
        """Cancel an open or funded bounty; refund its escrow to the poster."""
        bounty = self._require_bounty(bounty_id)
        refunded = cancel(bounty)
        if bounty.poster == self._address and refunded > 0:
            self._balances["KITTY"] = self.balance("KITTY") + refunded
        self._save()
        return bounty

    # ---- helpers ---------------------------------------------------------

    def _require_contact(self, contact_id: str) -> Contact:
        for contact in self._contacts:
            if contact.id == contact_id:
                return contact
        raise ValueError(f"no contact with id {contact_id!r}")
