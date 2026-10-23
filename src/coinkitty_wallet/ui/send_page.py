"""The Send screen: pick a recipient, then enter an amount and send demo coins."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

import random

from ..demo_backend import DemoBackend  # noqa: F401 (type hint only)
from ..models import Contact
from ..send_logic import top_contacts, search_contacts
from ..units import ASSETS, parse_amount, format_amount
from ..bech32m import is_valid_address


class SendPage(Gtk.Box):
    """Send screen: a two-step Stack ("pick" then "amount") over demo coins."""

    def __init__(self, backend, rng: random.Random | None = None,
                 on_open_page=None):
        super().__init__()
        self.backend = backend
        self.rng = rng
        self.on_open_page = on_open_page

        self._step = "pick"
        self._asset_code = "KITTY"
        self._recipient_contact_id: str | None = None
        self._recipient_address: str | None = None
        self._recipient_name: str = ""
        self._row_contact: dict[Adw.ActionRow, Contact] = {}
        self._top_button_contact: dict[Gtk.Button, Contact] = {}
        self.selected_contact_id: str | None = None
        self.selected_address: str | None = None
        self.luck_dialog = None
        self._luck_contact: Contact | None = None

        # ---- toast overlay wraps the whole page ---------------------------
        self.toast_overlay = Adw.ToastOverlay()
        self.append(self.toast_overlay)

        self.stack = Gtk.Stack()
        self.toast_overlay.set_child(self.stack)

        self.stack.add_named(self._build_pick(), "pick")
        self.stack.add_named(self._build_amount(), "amount")
        self.stack.set_visible_child_name("pick")

    # ---- pick step --------------------------------------------------------

    def _build_pick(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        model = Gtk.StringList.new(list(ASSETS))
        self.asset_dropdown = Gtk.DropDown(model=model)
        self.asset_dropdown.connect("notify::selected", self._on_asset_selected)
        box.append(self.asset_dropdown)

        self.top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.append(self.top_box)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.connect("search-changed", self._on_search_changed)
        box.append(self.search_entry)

        self.contact_list = Gtk.ListBox()
        self.contact_list.connect("row-activated", self._on_row_activated)
        box.append(self.contact_list)

        self.address_entry = Gtk.Entry()
        self.address_entry.set_text("kitty1...")
        self.address_entry.connect("changed", self._on_address_changed)
        box.append(self.address_entry)

        self.use_address_button = Gtk.Button(label="Use address")
        self.use_address_button.set_sensitive(False)
        self.use_address_button.connect("clicked", self._on_use_address)
        box.append(self.use_address_button)

        self.luck_button = Gtk.Button(label="Luck")
        self.luck_button.connect("clicked", self._on_luck_clicked)
        box.append(self.luck_button)

        rain_button = Gtk.Button(label="Rain")
        rain_button.connect("clicked", self._on_rain_clicked)
        box.append(rain_button)

        self._refresh_pick()
        return box

    def _on_asset_selected(self, dropdown, previous) -> None:
        """Track the asset chosen in the dropdown."""
        item = dropdown.get_selected_item()
        if item is not None:
            self._asset_code = item.get_string()

    def _refresh_pick(self) -> None:
        """Rebuild the top-contact buttons and the searchable contact list."""
        contacts = self.backend.contacts()
        txns = self.backend.transactions()

        child = self.top_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.top_box.remove(child)
            self._top_button_contact.pop(child, None)
            child = nxt
        for contact in top_contacts(contacts, txns, n=5):
            button = Gtk.Button(label=contact.name)
            button.add_css_class("pill")
            button.connect("clicked", self._on_contact_clicked)
            self.top_box.append(button)
            self._top_button_contact[button] = contact

        self._rebuild_contact_rows(search_contacts(contacts, ""))

    def _on_search_changed(self, entry) -> None:
        """Rebuild the contact list rows for the current search text."""
        query = entry.get_text()
        self._rebuild_contact_rows(search_contacts(self.backend.contacts(), query))

    def _rebuild_contact_rows(self, contacts) -> None:
        """Replace every row in the contact list box with the given contacts."""
        self._row_contact = {}
        child = self.contact_list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.contact_list.remove(child)
            child = nxt
        for contact in contacts:
            row = Adw.ActionRow()
            row.set_title(contact.name)
            self.contact_list.append(row)
            self._row_contact[row] = contact

    def _on_contact_clicked(self, button) -> None:
        """A top-contact button was clicked: go to the amount step."""
        contact = self._top_button_contact.get(button)
        if contact is not None:
            self._recipient_contact_id = contact.id
            self._recipient_name = contact.name
            self.selected_contact_id = contact.id
            self.go_amount()

    def _on_row_activated(self, list_box, row, user_initiated) -> None:
        """A contact-list row was activated: go to the amount step."""
        contact = self._row_contact.get(row)
        if contact is not None:
            self._recipient_contact_id = contact.id
            self._recipient_name = contact.name
            self.selected_contact_id = contact.id
            self.go_amount()

    def _on_use_address(self, button) -> None:
        """Use a typed address as the recipient (only if it is valid)."""
        address = self.address_entry.get_text()
        if not is_valid_address(address):
            return
        self._recipient_address = address
        self._recipient_name = "New contact"
        self.selected_address = address
        self.go_amount()

    def _on_address_changed(self, entry) -> None:
        """Enable the 'Use address' button only for a valid address."""
        self.use_address_button.set_sensitive(is_valid_address(entry.get_text()))

    def _on_luck_clicked(self, button) -> None:
        """Pick a random contact and confirm through an alert dialog."""
        try:
            contact = self.backend.pick_luck(self.rng)
        except ValueError:
            return
        self._luck_contact = contact
        dialog = Adw.AlertDialog.new(f"Luck picked {contact.name}",
                                     f"Send to {contact.name}?")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("send", "Continue")
        dialog.set_response_appearance("send", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_luck_response)
        self.luck_dialog = dialog
        dialog.present(self)

    def _on_luck_response(self, dialog, response_id: str) -> None:
        """Handle the Luck dialog response; 'send' goes to the amount step."""
        if response_id == "send" and self._luck_contact is not None:
            contact = self._luck_contact
            self._recipient_contact_id = contact.id
            self._recipient_name = contact.name
            self.selected_contact_id = contact.id
            self.go_amount()

    def _on_rain_clicked(self, button) -> None:
        """Jump to the Rain screen with the current asset."""
        if self.on_open_page is not None:
            self.on_open_page("rain")

    # ---- amount step ------------------------------------------------------

    def _build_amount(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.recipient_label = Gtk.Label(label="")
        box.append(self.recipient_label)
        self.asset_label = Gtk.Label(label="")
        box.append(self.asset_label)
        self.balance_label = Gtk.Label(label="")
        box.append(self.balance_label)
        self.amount_entry = Gtk.Entry()
        box.append(self.amount_entry)
        self.memo_entry = Gtk.Entry()
        box.append(self.memo_entry)
        self.error_label = Gtk.Label(label="")
        self.error_label.add_css_class("error")
        self.error_label.set_visible(False)
        box.append(self.error_label)
        back_button = Gtk.Button(label="Back")
        back_button.connect("clicked", self._on_back_clicked)
        box.append(back_button)
        self.send_button = Gtk.Button(label="Send")
        self.send_button.connect("clicked", self._on_send_clicked)
        box.append(self.send_button)
        return box

    def go_amount(self) -> None:
        """Switch to the amount step and refresh its labels."""
        self._step = "amount"
        self.stack.set_visible_child_name("amount")
        self._clear_error()
        self.recipient_label.set_text(self._recipient_name)
        self.asset_label.set_text(self._asset_code)
        balance = format_amount(self.backend.balance(self._asset_code),
                                ASSETS[self._asset_code])
        self.balance_label.set_text(f"Balance: {balance} {self._asset_code}")

    def go_pick(self) -> None:
        """Return to the pick step and clear the chosen recipient."""
        self._step = "pick"
        self.stack.set_visible_child_name("pick")
        self._recipient_contact_id = None
        self._recipient_address = None
        self._recipient_name = ""
        self.selected_contact_id = None
        self.selected_address = None

    def _set_error(self, text: str) -> None:
        """Show an error message on the amount step."""
        self.error_label.set_text(text)
        self.error_label.set_visible(True)

    def _clear_error(self) -> None:
        """Hide the error message."""
        self.error_label.set_visible(False)

    def _on_back_clicked(self, button) -> None:
        """Go back to the pick step."""
        self.go_pick()

    def _on_send_clicked(self, button) -> None:
        """Validate the amount and send demo coins, or show an error."""
        if self._asset_code == "BTC":
            self._set_error("Bitcoin sending arrives with atomic swaps")
            return
        asset = ASSETS[self._asset_code]
        text = self.amount_entry.get_text()
        try:
            amount = parse_amount(text, asset)
        except ValueError:
            self._set_error(f"Invalid amount: {text!r}")
            return
        if amount > self.backend.balance(self._asset_code):
            self._set_error("Amount exceeds balance")
            return
        contact_id = self._recipient_contact_id
        if contact_id is None and self._recipient_address:
            added = self.backend.add_contact("New contact", self._recipient_address)
            contact_id = added.id
            self._recipient_name = added.name
        self.backend.send(self._asset_code, amount, contact_id,
                          self.memo_entry.get_text())
        self.toast_overlay.add_toast(
            Adw.Toast.new(f"Sent {format_amount(amount, asset)} "
                          f"{self._asset_code} to {self._recipient_name}"))
        self.go_pick()

    # ---- public helpers ---------------------------------------------------

    def refresh(self) -> None:
        """Rebuild contact buttons/list and the balance label."""
        self._refresh_pick()
        if self._step == "amount":
            balance = format_amount(self.backend.balance(self._asset_code),
                                    ASSETS[self._asset_code])
            self.balance_label.set_text(f"Balance: {balance} {self._asset_code}")

    def start_with_contact(self, contact_id: str) -> None:
        """Preselect a contact and open the amount step (favorite activation)."""
        for contact in self.backend.contacts():
            if contact.id == contact_id:
                self._recipient_contact_id = contact.id
                self._recipient_name = contact.name
                self.selected_contact_id = contact.id
                self.go_amount()
                return
