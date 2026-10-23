"""Launch page: post and fund a bounty from the wallet's own address.

Plain layout only; all bounty data comes from the injected demo backend. Money
is always an ``int`` count of the smallest KITTY unit, parsed and formatted with
:mod:`coinkitty_wallet.units`.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

import time

from ..models import Bounty
from ..units import KITTY, format_amount, parse_amount

POST_CATEGORIES = ("food", "lessons", "work", "services", "goods", "build")


def _window_text(bounty: Bounty) -> str:
    """Return the bounty's open window as ``YYYY-MM-DD -> YYYY-MM-DD``."""
    start = time.strftime("%Y-%m-%d", time.localtime(bounty.window_start))
    end = time.strftime("%Y-%m-%d", time.localtime(bounty.window_end))
    return f"{start} -> {end}"


class LaunchPage(Gtk.Box):
    """Post a bounty (with a confirm dialog) and list the wallet's own bounties."""

    def __init__(self, backend, on_open_bounty):
        super().__init__()
        self.backend = backend
        self.on_open_bounty = on_open_bounty
        self._ready = False
        self.confirm_dialog: Adw.AlertDialog | None = None
        self._row_bounty: dict[Adw.ActionRow, str] = {}

        # ---- toast overlay wraps the whole page ---------------------------
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_vexpand(True)
        self.append(self.toast_overlay)

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
        self.toast_overlay.set_child(scrolled)

        # ---- post a bounty group -----------------------------------------
        post_group = Adw.PreferencesGroup()
        post_group.set_title("Post a bounty")
        self.title_entry = Adw.EntryRow()
        self.title_entry.set_title("Title")
        post_group.add(self.title_entry)
        self.desc_entry = Adw.EntryRow()
        self.desc_entry.set_title("Description")
        post_group.add(self.desc_entry)
        self.price_entry = Adw.EntryRow()
        self.price_entry.set_title("Price (KITTY)")
        post_group.add(self.price_entry)
        self.location_entry = Adw.EntryRow()
        self.location_entry.set_title("Location")
        post_group.add(self.location_entry)
        self.model = Gtk.StringList.new(list(POST_CATEGORIES))
        self.dropdown = Gtk.DropDown(model=self.model)
        post_group.add(self.dropdown)
        self._column.append(post_group)

        self.error_label = Gtk.Label(label="")
        self.error_label.add_css_class("error")
        self.error_label.set_visible(False)
        self._column.append(self.error_label)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_row.set_halign(Gtk.Align.CENTER)
        self.post_button = Gtk.Button(label="Post and fund")
        self.post_button.add_css_class("suggested-action")
        self.post_button.add_css_class("pill")
        self.post_button.connect("clicked", self._on_post_clicked)
        button_row.append(self.post_button)
        self._column.append(button_row)

        # ---- your bounties list ------------------------------------------
        list_group = Adw.PreferencesGroup()
        list_group.set_title("Your bounties")
        self.bounty_list = Gtk.ListBox()
        self.bounty_list.add_css_class("boxed-list")
        self.bounty_list.connect("row-activated", self._on_row_activated)
        list_group.add(self.bounty_list)
        self._column.append(list_group)

        self._refresh()
        self._ready = True

    # ---- signal handlers --------------------------------------------------

    def _on_post_clicked(self, button) -> None:
        """Confirm posting and funding the bounty through an alert dialog."""
        self.confirm_dialog = Adw.AlertDialog.new(
            "Post and fund this bounty?",
            f"Post {self.title_entry.get_text() or 'a bounty'} and move its "
            f"price from your KITTY balance into escrow.",
        )
        self.confirm_dialog.add_response("cancel", "Cancel")
        self.confirm_dialog.add_response("confirm", "Post and fund")
        self.confirm_dialog.set_response_appearance(
            "confirm", Adw.ResponseAppearance.SUGGESTED
        )
        self.confirm_dialog.connect("response", self._on_post_response)
        self.confirm_dialog.present(self)

    def _on_post_response(self, dialog, response_id: str) -> None:
        """On confirm, post the bounty and fund it; otherwise do nothing."""
        if response_id != "confirm":
            return
        text = self.price_entry.get_text()
        try:
            price = parse_amount(text, KITTY)
        except ValueError:
            self._set_error(f"Invalid price: {text!r}")
            return
        try:
            bounty = self.backend.post_bounty(
                self.title_entry.get_text(),
                self.desc_entry.get_text(),
                self.dropdown.get_selected_item().get_string(),
                self.location_entry.get_text(),
                price,
            )
            self.backend.fund(bounty.id)
        except ValueError as exc:
            self._set_error(str(exc))
            return
        self._clear_error()
        self.toast_overlay.add_toast(
            Adw.Toast.new(
                f"Posted and funded {format_amount(price, KITTY)} KITTY bounty "
                f"{bounty.title}"
            )
        )
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
        """Repopulate the list from the wallet's own bounties."""
        self._row_bounty = {}
        child = self.bounty_list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.bounty_list.remove(child)
            child = nxt
        for bounty in self.backend.my_posted():
            row = Adw.ActionRow()
            row.set_title(bounty.title)
            row.set_subtitle(
                f"{bounty.status} · {len(bounty.bids)} bids · "
                f"{format_amount(bounty.price, KITTY)} KITTY · "
                f"{bounty.location} · {_window_text(bounty)}"
            )
            row.set_activatable(True)
            self.bounty_list.append(row)
            self._row_bounty[row] = bounty.id

    def _set_error(self, text: str) -> None:
        """Show an error message on the post step."""
        self.error_label.set_text(text)
        self.error_label.set_visible(True)

    def _clear_error(self) -> None:
        """Hide the error message."""
        self.error_label.set_visible(False)
