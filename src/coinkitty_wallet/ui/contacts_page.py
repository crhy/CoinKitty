"""Contacts screen: search the address book, star favorites, view/edit a contact."""

from __future__ import annotations

import uuid

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ..demo_backend import DemoBackend  # noqa: F401 (type hint only)
from ..models import Contact, RainGroup
from ..send_logic import search_contacts
from ..bech32m import is_valid_address
from ..units import ASSETS


def shorten_address(address: str) -> str:
    """First 12 chars + an ellipsis + the last 6, for a compact subtitle."""
    if len(address) <= 18:
        return address
    return f"{address[:12]}…{address[-6:]}"


class ContactDialog(Adw.Dialog):
    """Detail view for a single contact: edit, star, pay, or delete it."""

    def __init__(self, backend, contact: Contact, on_pay=None,
                 on_open_page=None, on_changed=None):
        super().__init__()
        self.backend = backend
        self.contact = contact
        self.on_pay = on_pay
        self.on_open_page = on_open_page
        self.on_changed = on_changed
        self.confirm_dialog: Adw.AlertDialog | None = None

        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        details_group = Adw.PreferencesGroup()
        details_group.set_title("Details")
        self.name_entry = Adw.EntryRow()
        self.name_entry.set_title(contact.name)
        details_group.add(self.name_entry)
        self.address_label = Gtk.Label(label=contact.address)
        self.address_label.set_selectable(True)
        self.address_label.add_css_class("monospace")
        details_group.add(self.address_label)
        asset_row = Adw.ActionRow()
        asset_row.set_title("Preferred asset")
        model = Gtk.StringList.new(["KITTY", "BTC"])
        self.asset_dropdown = Gtk.DropDown(model=model)
        self.asset_dropdown.set_selected(
            0 if contact.preferred_asset == "KITTY" else 1)
        asset_row.add_suffix(self.asset_dropdown)
        details_group.add(asset_row)
        self.group_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for group in backend.rain_groups():
            if contact.id in group.member_ids:
                self.group_box.append(Gtk.Label(label=group.name))
        details_group.add(self.group_box)
        self.favorite_switch = Gtk.Switch()
        self.favorite_switch.set_active(bool(contact.favorite))
        details_group.add(self.favorite_switch)
        self.content.append(details_group)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_row.set_halign(Gtk.Align.CENTER)
        self.pay_button = Gtk.Button(label="Pay")
        self.pay_button.connect("clicked", self._on_pay_clicked)
        button_row.append(self.pay_button)
        self.save_button = Gtk.Button(label="Save")
        self.save_button.connect("clicked", self._on_save_clicked)
        button_row.append(self.save_button)
        self.content.append(button_row)

        self.delete_button = Gtk.Button(label="Delete")
        self.delete_button.add_css_class("destructive-action")
        self.delete_button.set_halign(Gtk.Align.CENTER)
        self.delete_button.connect("clicked", self._on_delete_clicked)
        self.content.append(self.delete_button)

        self.set_child(self.content)
        self.set_title(contact.name)
        self.set_content_width(360)

    def _on_pay_clicked(self, button) -> None:
        """Close, hand the contact to the send page, then open the send page."""
        contact_id = self.contact.id
        self.close()
        if self.on_pay is not None:
            self.on_pay(contact_id)
        if self.on_open_page is not None:
            self.on_open_page("send")

    def _on_save_clicked(self, button) -> None:
        """Persist the edited name, preferred asset and favorite flag."""
        updated = Contact(
            id=self.contact.id,
            name=self.name_entry.get_text(),
            address=self.contact.address,
            preferred_asset=self._selected_asset(),
            favorite=self.favorite_switch.get_active(),
        )
        self.backend.update_contact(updated)
        if self.on_changed is not None:
            self.on_changed()
        self.close()

    def _selected_asset(self) -> str:
        item = self.asset_dropdown.get_selected_item()
        return item.get_string() if item is not None else self.contact.preferred_asset

    def _on_delete_clicked(self, button) -> None:
        """Ask for confirmation before deleting this contact."""
        dialog = Adw.AlertDialog.new(
            "Are you sure?",
            f"Delete {self.contact.name}? They are removed from every rain group.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_delete_response)
        self.confirm_dialog = dialog
        dialog.present(self)

    def _on_delete_response(self, dialog, response_id: str) -> None:
        """Handle the delete confirmation; 'delete' removes the contact."""
        if response_id == "delete":
            self.backend.delete_contact(self.contact.id)
            if self.on_changed is not None:
                self.on_changed()
            self.close()


class AddContactDialog(Adw.Dialog):
    """Dialog that creates a new contact from a name and an address."""

    def __init__(self, backend, on_saved=None):
        super().__init__()
        self.backend = backend
        self.on_saved = on_saved

        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        details_group = Adw.PreferencesGroup()
        details_group.set_title("New contact")
        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("Name")
        self.name_entry.connect("changed", self._on_changed)
        details_group.add(self.name_entry)
        self.address_entry = Gtk.Entry()
        self.address_entry.set_placeholder_text("kitty1… address")
        self.address_entry.connect("changed", self._on_changed)
        details_group.add(self.address_entry)
        self.content.append(details_group)

        self.save_button = Gtk.Button(label="Save")
        self.save_button.add_css_class("suggested-action")
        self.save_button.set_halign(Gtk.Align.CENTER)
        self.save_button.connect("clicked", self._on_save_clicked)
        self.content.append(self.save_button)

        self.set_child(self.content)
        self.set_title("Add contact")
        self.set_content_width(360)
        self._update_save_sensitivity()

    def _update_save_sensitivity(self) -> None:
        """Enable Save only when the name is set and the address is valid."""
        name_ok = self.name_entry.get_text().strip() != ""
        addr_ok = is_valid_address(self.address_entry.get_text())
        self.save_button.set_sensitive(name_ok and addr_ok)

    def _on_changed(self, entry) -> None:
        """An entry changed: re-evaluate Save."""
        self._update_save_sensitivity()

    def _on_save_clicked(self, button) -> None:
        """Create the contact, notify, and close."""
        self.backend.add_contact(
            self.name_entry.get_text(),
            self.address_entry.get_text(),
        )
        if self.on_saved is not None:
            self.on_saved()
        self.close()


class ContactsPage(Gtk.Box):
    """Address book: a search box, a filtered contact list, and an add button."""

    def __init__(self, backend, on_open_page=None, on_changed=None, on_pay=None):
        super().__init__()
        self.backend = backend
        self.on_open_page = on_open_page
        self.on_changed = on_changed
        self.on_pay = on_pay

        self._contact_rows: dict[Adw.ActionRow, Contact] = {}
        self._star_buttons: dict[str, Gtk.ToggleButton] = {}

        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.content.set_margin_top(24)
        self.content.set_margin_bottom(24)
        self.content.set_margin_start(24)
        self.content.set_margin_end(24)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scrolled)
        self.clamp = Adw.Clamp()
        self.clamp.set_maximum_size(640)
        scrolled.set_child(self.clamp)
        self.clamp.set_child(self.content)

        contacts_group = Adw.PreferencesGroup()
        contacts_group.set_title("Contacts")
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search contacts")
        self.search_entry.connect("changed", self._on_search_changed)
        contacts_group.add(self.search_entry)
        self.contact_list = Gtk.ListBox()
        self.contact_list.add_css_class("boxed-list")
        self.contact_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.contact_list.connect("row-activated", self._on_row_activated)
        contacts_group.add(self.contact_list)
        self.content.append(contacts_group)

        self.add_button = Gtk.Button(label="Add contact")
        self.add_button.set_halign(Gtk.Align.CENTER)
        self.add_button.connect("clicked", self._on_add_clicked)
        self.content.append(self.add_button)

        self._refresh_rows()

    # ---- rows -------------------------------------------------------------

    def _refresh_rows(self) -> None:
        """Rebuild one action row per contact matching the current search."""
        self._contact_rows = {}
        self._star_buttons = {}
        child = self.contact_list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.contact_list.remove(child)
            child = nxt
        query = self.search_entry.get_text()
        for contact in search_contacts(self.backend.contacts(), query):
            row = Adw.ActionRow()
            row.set_title(contact.name)
            row.set_subtitle(
                f"{shorten_address(contact.address)} {contact.preferred_asset}"
            )
            row.set_activatable(True)
            star = Gtk.ToggleButton(
                icon_name="starred-symbolic" if contact.favorite
                else "non-starred-symbolic"
            )
            star.connect("clicked", self._make_star_handler(contact))
            row.add_suffix(star)
            self.contact_list.append(row)
            self._contact_rows[row] = contact
            self._star_buttons[contact.id] = star

    def _make_star_handler(self, contact: Contact):
        """Return a clicked-handler that flips this contact's favorite flag."""
        return lambda *_: self._toggle_favorite(contact)

    def _toggle_favorite(self, contact: Contact) -> None:
        """Flip the favorite flag, persist it, and refresh the page."""
        updated = Contact(
            id=contact.id,
            name=contact.name,
            address=contact.address,
            preferred_asset=contact.preferred_asset,
            favorite=not contact.favorite,
        )
        self.backend.update_contact(updated)
        self.refresh()
        if self.on_changed is not None:
            self.on_changed()

    def _on_search_changed(self, entry) -> None:
        """The search text changed: re-filter the list."""
        self._refresh_rows()

    def _on_row_activated(self, list_box, row, user_initiated) -> None:
        """A contact row was activated: open its detail dialog."""
        contact = self._contact_rows.get(row)
        if contact is not None:
            self._open_detail(contact)

    def _open_detail(self, contact: Contact) -> None:
        """Open the detail dialog for ``contact``."""
        dialog = ContactDialog(
            self.backend,
            contact,
            on_pay=self.on_pay,
            on_open_page=self.on_open_page,
            on_changed=self.on_changed,
        )
        dialog.present(self)

    def _on_add_clicked(self, button) -> None:
        """Open the add-contact dialog."""
        dialog = AddContactDialog(self.backend, on_saved=self._on_contact_saved)
        dialog.present(self)

    def _on_contact_saved(self) -> None:
        """A contact was added: refresh and tell the window favorites changed."""
        self.refresh()
        if self.on_changed is not None:
            self.on_changed()

    # ---- public -----------------------------------------------------------

    def refresh(self) -> None:
        """Rebuild the contact rows from the current backend and search text."""
        self._refresh_rows()
