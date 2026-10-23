"""The bounty card dialog: one bounty's details, bids and poster actions.

All money is an ``int`` count of the smallest KITTY unit (1 KITTY = 10**24).
Text is formatted with :mod:`decimal`; nothing here uses ``float`` for money.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

import uuid
from decimal import Decimal

from ..bounties import create_child, rank_bids
from ..models import Bid, Bounty

KITTY_UNIT = 10**24


def format_kitty(amount: int) -> str:
    """Return a plain decimal string for ``amount`` kitoshi (never a float)."""
    if not isinstance(amount, int) or isinstance(amount, bool):
        raise ValueError("amount must be an int count of the smallest unit")
    text = (Decimal(amount) / Decimal(KITTY_UNIT)).normalize()
    return format(text, "f")


def parse_kitty(text: str) -> int | None:
    """Parse a KITTY amount like ``"1.5"`` into kitoshi, or ``None`` if invalid."""
    try:
        value = Decimal(text.strip())
    except Exception:
        return None
    if value <= 0:
        return None
    kitoshi = value * Decimal(KITTY_UNIT)
    if kitoshi != kitoshi.to_integral_value():
        return None
    return int(kitoshi)


class BountyCard(Adw.Dialog):
    """An :class:`Adw.Dialog` showing one bounty and its allowed actions."""

    def __init__(self, backend, bounty: Bounty, on_changed=None) -> None:
        super().__init__()
        self.backend = backend
        self.bounty_id = bounty.id
        self._on_changed = on_changed
        self._poster = bounty.poster == backend.address()
        self._last_release: tuple[int, int] | None = None
        self._sub_bounties: list[Bounty] = []
        self.confirm_dialog: Adw.AlertDialog | None = None

        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.content.set_margin_start(18)
        self.content.set_margin_end(18)
        self.content.set_margin_top(18)
        self.content.set_margin_bottom(18)
        self.error_label = Gtk.Label(label="")
        self.error_label.add_css_class("error")
        self.error_label.set_visible(False)

        self._build_top()
        self._build_details()
        self._build_bids()
        if self._poster:
            self._build_poster_actions()
        else:
            self._build_bid_form()

        self.content.append(self.error_label)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self.content)

        view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        view.add_top_bar(header)
        view.set_content(scrolled)
        self.set_child(view)

        current = self._current_bounty()
        title_widget = Adw.WindowTitle()
        title_widget.set_title(current.title)
        title_widget.set_subtitle(f"{current.status} · {format_kitty(current.escrow)} KITTY")
        header.set_title_widget(title_widget)

        self.set_title(current.title)
        self.set_content_width(420)
        self.set_content_height(600)

    # ---- live bounty (always re-read from the backend by id) --------------

    def _current_bounty(self) -> Bounty:
        """Return the backend's current Bounty for ``bounty_id`` (never a stale copy)."""
        return self.backend._require_bounty(self.bounty_id)

    # ---- top: escrow + status -------------------------------------------

    def _build_top(self) -> None:
        """Show the escrow amount and status at the top of the card."""
        current = self._current_bounty()
        group = Adw.PreferencesGroup()
        group.set_title("Status")
        row = Adw.ActionRow()
        row.set_title(f"Escrow: {format_kitty(current.escrow)} KITTY")
        row.set_subtitle(current.status)
        group.add(row)
        self.content.append(group)

    # ---- details ---------------------------------------------------------

    def _build_details(self) -> None:
        """Show the bounty's description, category, location and window."""
        current = self._current_bounty()
        group = Adw.PreferencesGroup()
        group.set_title("Details")
        desc = Adw.ActionRow()
        desc.set_title(current.description)
        group.add(desc)
        meta = Adw.ActionRow()
        meta.set_title(current.category)
        meta.set_subtitle(current.location)
        group.add(meta)
        self.content.append(group)

    # ---- lead bid + ranked queue ----------------------------------------

    def _build_bids(self) -> None:
        """Show the lead bid and the full ranked queue of bids."""
        current = self._current_bounty()
        ranked = rank_bids(current.bids)
        self.bid_list = Gtk.ListBox()
        self.bid_list.add_css_class("boxed-list")
        if not ranked:
            empty = Gtk.Label(label="No bids yet")
            empty.add_css_class("dim-label")
            self.content.append(empty)
            return

        lead = Adw.PreferencesGroup()
        lead.set_title("Lead kitty")
        lead_row = Adw.ActionRow()
        lead_row.set_title(ranked[0].bidder)
        lead_row.set_subtitle(
            f"{format_kitty(ranked[0].price)} KITTY · reputation {ranked[0].reputation}"
        )
        lead.add(lead_row)
        self.content.append(lead)

        queue = Adw.PreferencesGroup()
        queue.set_title("All bids")
        for bid in ranked:
            row = Adw.ActionRow()
            row.set_title(bid.bidder)
            row.set_subtitle(f"{format_kitty(bid.price)} KITTY · reputation {bid.reputation}")
            self.bid_list.append(row)
        queue.add(self.bid_list)
        self.content.append(queue)

    # ---- poster actions --------------------------------------------------

    def _build_poster_actions(self) -> None:
        """Add Accept/deliver/release/cancel/hammer for the wallet's own bounty."""
        self._accept_buttons: dict[str, Gtk.Button] = {}
        for bid in self._current_bounty().bids:
            button = Gtk.Button(label="Accept")
            button.set_halign(Gtk.Align.CENTER)
            button.add_css_class("suggested-action")
            button.add_css_class("pill")
            button.connect("clicked", self._make_accept_handler(bid.id))
            self.content.append(button)
            self._accept_buttons[bid.id] = button

        self.deliver_button = Gtk.Button(label="Mark delivered")
        self.deliver_button.set_halign(Gtk.Align.CENTER)
        self.deliver_button.connect("clicked", self._on_deliver_clicked)
        self.content.append(self.deliver_button)

        self.release_button = Gtk.Button(label="Release payment")
        self.release_button.set_halign(Gtk.Align.CENTER)
        self.release_button.connect("clicked", self._on_release_clicked)
        self.content.append(self.release_button)

        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.set_halign(Gtk.Align.CENTER)
        self.cancel_button.add_css_class("destructive-action")
        self.cancel_button.add_css_class("pill")
        self.cancel_button.connect("clicked", self._on_cancel_clicked)
        self.content.append(self.cancel_button)

        self.hammer_title_entry = Adw.EntryRow()
        self.hammer_title_entry.set_title("Sub-bounty title")
        self.hammer_price_entry = Adw.EntryRow()
        self.hammer_price_entry.set_title("Sub-bounty price")
        self.hammer_button = Gtk.Button(label="Hammer: split into sub-bounty")
        self.hammer_button.set_halign(Gtk.Align.CENTER)
        self.hammer_button.connect("clicked", self._on_hammer_clicked)
        hammer_group = Adw.PreferencesGroup()
        hammer_group.set_title("Hammer")
        hammer_group.add(self.hammer_title_entry)
        hammer_group.add(self.hammer_price_entry)
        self.content.append(hammer_group)
        self.content.append(self.hammer_button)

    # ---- bid form for others --------------------------------------------

    def _build_bid_form(self) -> None:
        """Add a price/note form and a Place bid button for a non-poster."""
        self.bid_price_entry = Adw.EntryRow()
        self.bid_price_entry.set_title("Price")
        self.bid_note_entry = Adw.EntryRow()
        self.bid_note_entry.set_title("Note")
        self.place_bid_button = Gtk.Button(label="Place bid")
        self.place_bid_button.set_halign(Gtk.Align.CENTER)
        self.place_bid_button.add_css_class("suggested-action")
        self.place_bid_button.add_css_class("pill")
        self.place_bid_button.connect("clicked", self._on_place_bid_clicked)
        group = Adw.PreferencesGroup()
        group.set_title("Place a bid")
        group.add(self.bid_price_entry)
        group.add(self.bid_note_entry)
        self.content.append(group)
        self.content.append(self.place_bid_button)

    # ---- signal handlers -------------------------------------------------

    def _make_accept_handler(self, bid_id: str):
        return lambda *_: self._accept(bid_id)

    def _accept(self, bid_id: str) -> None:
        """Accept ``bid_id`` when the bounty is funded."""
        current = self._current_bounty()
        if current.status != "funded":
            self._show_error("Only a funded bounty can accept a bid")
            return
        self.backend.accept(current.id, bid_id)
        self._notify_changed()

    def _on_deliver_clicked(self, *_: object) -> None:
        """Mark the assigned bounty delivered."""
        current = self._current_bounty()
        if current.status != "assigned":
            self._show_error("Only an assigned bounty can be delivered")
            return
        self.backend.deliver(current.id)

    def _on_release_clicked(self, *_: object) -> None:
        """Release a delivered bounty and remember the payout."""
        current = self._current_bounty()
        if current.status != "delivered":
            self._show_error("Only a delivered bounty can be released")
            return
        self._last_release = self.backend.release(current.id)
        self._notify_changed()

    def _on_cancel_clicked(self, *_: object) -> None:
        """Ask to cancel a destructive action through a confirm dialog."""
        current = self._current_bounty()
        if current.status not in ("open", "funded"):
            self._show_error("Only an open or funded bounty can be cancelled")
            return
        dialog = Adw.AlertDialog.new(
            f"Cancel '{current.title}'?",
            "Its escrow is refunded to your balance.",
        )
        dialog.add_response("cancel", "Keep it")
        dialog.add_response("confirm", "Cancel bounty")
        dialog.set_default_response("cancel")
        dialog.connect("response", self._on_cancel_response)
        self.confirm_dialog = dialog
        dialog.present(self)

    def _on_cancel_response(self, dialog: Adw.AlertDialog, response: str) -> None:
        """Finish the cancel when the confirm dialog answers ``confirm``."""
        if response == "confirm":
            self.backend.cancel(self.bounty_id)
            self._notify_changed()

    def _on_hammer_clicked(self, *_: object) -> None:
        """Split the bounty into a funded sub-bounty out of its escrow."""
        current = self._current_bounty()
        if current.status not in ("funded", "assigned"):
            self._show_error("Only a funded or assigned bounty can be split")
            return
        title = self.hammer_title_entry.get_text().strip()
        price = parse_kitty(self.hammer_price_entry.get_text())
        if not title or price is None:
            self._show_error("Enter a title and a positive price")
            return
        child = create_child(current, title, price, self.backend.clock())
        self._sub_bounties.append(child)
        self.backend._bounties.append(child)
        self.backend._save()
        self._notify_changed()

    def _on_place_bid_clicked(self, *_: object) -> None:
        """Place a bid on the bounty from the wallet's own address."""
        price = parse_kitty(self.bid_price_entry.get_text())
        if price is None:
            self._show_error("Enter a positive price")
            return
        bid = Bid(
            id=uuid.uuid4().hex,
            bounty_id=self.bounty_id,
            bidder=self.backend.address(),
            price=price,
            note=self.bid_note_entry.get_text(),
        )
        self._current_bounty().bids.append(bid)
        self._notify_changed()

    def _notify_changed(self) -> None:
        """Tell the owner the card changed so it can refresh its pages."""
        if self._on_changed is not None:
            self._on_changed()

    def _show_error(self, message: str) -> None:
        """Show the error label (css ``error``) and hide it when empty."""
        self.error_label.set_label(message)
        self.error_label.set_visible(bool(message))


__all__ = ["BountyCard", "format_kitty", "parse_kitty"]
