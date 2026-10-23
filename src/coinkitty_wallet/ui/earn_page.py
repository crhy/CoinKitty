"""Earn page: browse and search the open bounties other people posted.

Plain layout only; all bounty data comes from the injected demo backend. Money
is always an ``int`` count of the smallest KITTY unit, formatted with
:func:`coinkitty_wallet.units.format_amount`.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

import time

from ..models import Bounty
from ..units import KITTY, format_amount

CATEGORIES = ("All", "food", "lessons", "work", "services", "goods", "build")


def _window_text(bounty: Bounty) -> str:
    """Return the bounty's open window as ``YYYY-MM-DD -> YYYY-MM-DD``."""
    start = time.strftime("%Y-%m-%d", time.localtime(bounty.window_start))
    end = time.strftime("%Y-%m-%d", time.localtime(bounty.window_end))
    return f"{start} -> {end}"


def _subtitle_text(bounty: Bounty, titles: dict[str, str]) -> str:
    """Return the row subtitle: price, location, window, status and parent note."""
    parts = [
        f"{format_amount(bounty.price, KITTY)} KITTY",
        bounty.location,
        _window_text(bounty),
    ]
    if bounty.status == "funded":
        parts.append("Funded")
    if bounty.parent_id is not None and bounty.parent_id in titles:
        parts.append(f"Part of {titles[bounty.parent_id]}")
    return " · ".join(parts)


class EarnPage(Gtk.Box):
    """Searchable list of open or funded bounties posted by others."""

    def __init__(self, backend, on_open_bounty):
        super().__init__()
        self.backend = backend
        self.on_open_bounty = on_open_bounty
        self._ready = False
        self._bid_buttons: dict[str, Gtk.Button] = {}
        self._row_bounty: dict[Adw.ActionRow, str] = {}

        self._column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self._column.set_margin_start(24)
        self._column.set_margin_end(24)
        self._column.set_margin_top(24)
        self._column.set_margin_bottom(24)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(640)
        clamp.set_child(self._column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_propagate_natural_height(True)
        scrolled.set_child(clamp)
        self.append(scrolled)

        # ---- search -------------------------------------------------------
        search_group = Adw.PreferencesGroup()
        search_group.set_title("Search")
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search bounties")
        self.search_entry.connect("changed", self._on_search_changed)
        search_group.add(self.search_entry)
        self._column.append(search_group)

        # ---- category dropdown -------------------------------------------
        category_group = Adw.PreferencesGroup()
        category_group.set_title("Category")
        self.model = Gtk.StringList.new(list(CATEGORIES))
        self.dropdown = Gtk.DropDown(model=self.model)
        self.dropdown.connect("notify::selected", self._on_category_selected)
        category_group.add(self.dropdown)
        self._column.append(category_group)

        # ---- bounty list --------------------------------------------------
        list_group = Adw.PreferencesGroup()
        list_group.set_title("Open bounties")
        self.bounty_list = Gtk.ListBox()
        self.bounty_list.add_css_class("boxed-list")
        self.bounty_list.connect("row-activated", self._on_row_activated)
        list_group.add(self.bounty_list)
        self._column.append(list_group)

        self._refresh()
        self._ready = True

    # ---- signal handlers --------------------------------------------------

    def _on_search_changed(self, entry) -> None:
        if self._ready:
            self._refresh()

    def _on_category_selected(self, dropdown) -> None:
        if self._ready:
            self._refresh()

    def _on_row_activated(self, list_box, row, user_initiated) -> None:
        bounty_id = self._row_bounty.get(row)
        if bounty_id is not None:
            self.on_open_bounty(bounty_id)

    # ---- rendering --------------------------------------------------------

    def refresh(self) -> None:
        """Rebuild the bounty list from the current backend state."""
        self._refresh()

    def _refresh(self) -> None:
        """Repopulate the list from open or funded bounties matching search + category."""
        self._row_bounty: dict[Adw.ActionRow, str] = {}
        self._bid_buttons = {}
        child = self.bounty_list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.bounty_list.remove(child)
            child = nxt

        query = self.search_entry.get_text().strip().lower()
        category = self.dropdown.get_selected_item().get_string()
        own = self.backend.address()
        all_bounties = self.backend.bounties()
        titles = {bounty.id: bounty.title for bounty in all_bounties}
        for bounty in all_bounties:
            if bounty.status not in ("open", "funded") or bounty.poster == own:
                continue
            if category != "All" and bounty.category.lower() != category.lower():
                continue
            if query:
                haystack = " ".join(
                    (bounty.title, bounty.description, bounty.location, bounty.category)
                ).lower()
                if query not in haystack:
                    continue
            row = Adw.ActionRow()
            row.set_title(bounty.title)
            row.set_subtitle(_subtitle_text(bounty, titles))
            row.set_activatable(True)
            bid_button = Gtk.Button(label="Bid")
            bid_button.add_css_class("pill")
            bid_button.connect(
                "clicked", lambda *_: self.on_open_bounty(bounty.id)
            )
            row.add_suffix(bid_button)
            self.bounty_list.append(row)
            self._row_bounty[row] = bounty.id
            self._bid_buttons[bounty.id] = bid_button
