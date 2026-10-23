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


def _short_address(address: str) -> str:
    """First 12 chars + an ellipsis + the last 6, for a compact subtitle."""
    if len(address) <= 18:
        return address
    return f"{address[:12]}…{address[-6:]}"


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
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        box.append(scrolled)
        clamp = Adw.Clamp()
        clamp.set_maximum_size(640)
        scrolled.set_child(clamp)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        clamp.set_child(content)

        # "Pay with": asset dropdown in an ActionRow suffix
        pay_group = Adw.PreferencesGroup()
        pay_group.set_title("Pay with")
        pay_row = Adw.ActionRow()
        pay_row.set_title("Pay with")
        model = Gtk.StringList.new(list(ASSETS))
        self.asset_dropdown = Gtk.DropDown(model=model)
        self.asset_dropdown.connect("notify::selected", self._on_asset_selected)
        pay_row.add_suffix(self.asset_dropdown)
        pay_group.add(pay_row)
        content.append(pay_group)

        # "Favorites": top-contact pill buttons in a centered FlowBox
        fav_group = Adw.PreferencesGroup()
        fav_group.set_title("Favorites")
        self.top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.top_box.set_halign(Gtk.Align.CENTER)
        fav_group.add(self.top_box)
        content.append(fav_group)

        # "All contacts": search entry, then a boxed list
        contacts_group = Adw.PreferencesGroup()
        contacts_group.set_title("All contacts")
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search contacts")
        self.search_entry.connect("search-changed", self._on_search_changed)
        contacts_group.add(self.search_entry)
        self.contact_list = Gtk.ListBox()
        self.contact_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.contact_list.add_css_class("boxed-list")
        self.contact_list.connect("row-activated", self._on_row_activated)
        contacts_group.add(self.contact_list)
        content.append(contacts_group)

        # "Or paste an address": entry row, then centered action buttons
        address_group = Adw.PreferencesGroup()
        address_group.set_title("Or paste an address")
        self.address_entry = Gtk.Entry()
        self.address_entry.set_placeholder_text("kitty1… address")
        self.address_entry.connect("changed", self._on_address_changed)
        address_group.add(self.address_entry)
        content.append(address_group)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_row.set_halign(Gtk.Align.CENTER)
        self.use_address_button = Gtk.Button(label="Use address")
        self.use_address_button.set_sensitive(False)
        self.use_address_button.connect("clicked", self._on_use_address)
        button_row.append(self.use_address_button)
        self.luck_button = Gtk.Button(label="Luck")
        self.luck_button.connect("clicked", self._on_luck_clicked)
        button_row.append(self.luck_button)
        rain_button = Gtk.Button(label="Rain")
        rain_button.connect("clicked", self._on_rain_clicked)
        button_row.append(rain_button)
        content.append(button_row)

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
            row.set_subtitle(_short_address(contact.address))
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
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        box.append(scrolled)
        clamp = Adw.Clamp()
        clamp.set_maximum_size(640)
        scrolled.set_child(clamp)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        clamp.set_child(content)

        self.recipient_label = Gtk.Label(label="")
        self.recipient_label.add_css_class("title-2")
        content.append(self.recipient_label)
        self.address_label = Gtk.Label(label="")
        self.address_label.add_css_class("dim-label")
        content.append(self.address_label)

        amount_group = Adw.PreferencesGroup()
        amount_group.set_title("Amount")
        self.amount_entry = Adw.EntryRow()
        self.amount_entry.set_title("Amount (KITTY)")
        amount_group.add(self.amount_entry)
        self.asset_label = Gtk.Label(label="")
        self.asset_label.add_css_class("dim-label")
        amount_group.add(self.asset_label)
        self.balance_label = Gtk.Label(label="")
        self.balance_label.add_css_class("dim-label")
        amount_group.add(self.balance_label)
        self.memo_entry = Adw.EntryRow()
        self.memo_entry.set_title("Memo (optional)")
        amount_group.add(self.memo_entry)
        content.append(amount_group)

        self.error_label = Gtk.Label(label="")
        self.error_label.add_css_class("error")
        self.error_label.set_visible(False)
        content.append(self.error_label)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_row.set_halign(Gtk.Align.CENTER)
        back_button = Gtk.Button(label="Back")
        back_button.connect("clicked", self._on_back_clicked)
        button_row.append(back_button)
        self.send_button = Gtk.Button(label="Send")
        self.send_button.add_css_class("suggested-action")
        self.send_button.add_css_class("pill")
        self.send_button.connect("clicked", self._on_send_clicked)
        button_row.append(self.send_button)
        content.append(button_row)
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
        address = self._recipient_address
        if address is None and self._recipient_contact_id is not None:
            for contact in self.backend.contacts():
                if contact.id == self._recipient_contact_id:
                    address = contact.address
                    break
        self.address_label.set_text(
            _short_address(address) if address else "")

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
            added = self.backend.add_contact("New contact",
                                             self._recipient_address)
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
