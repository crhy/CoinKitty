"""Rain-group editor: rename a group, toggle members, star it, save or delete."""

from __future__ import annotations

import uuid

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ..demo_backend import DemoBackend  # noqa: F401 (type hint only)
from ..models import Contact, RainGroup


class GroupEditor(Adw.Dialog):
    """Dialog that edits (or creates) a single rain group."""

    def __init__(self, backend, group: RainGroup | None = None, on_saved=None):
        super().__init__()
        self.backend = backend
        self.group = group
        self.on_saved = on_saved
        self._existing = group is not None
        self.confirm_dialog: Adw.AlertDialog | None = None
        self._check_by_contact: dict[Gtk.CheckButton, Contact] = {}

        member_ids = set(group.member_ids) if group else set()

        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("Group name")
        if group is not None:
            self.name_entry.set_text(group.name)
        self.name_entry.connect("changed", self._on_name_changed)
        self.content.append(self.name_entry)

        members_group = Adw.PreferencesGroup()
        members_group.set_title("Members")
        self.contact_list = Gtk.ListBox()
        self.contact_list.add_css_class("boxed-list")
        self.contact_list.set_selection_mode(Gtk.SelectionMode.NONE)
        for contact in backend.contacts():
            row = Adw.ActionRow()
            check = Gtk.CheckButton(label=contact.name)
            check.set_active(contact.id in member_ids)
            check.connect("notify::checked", self._on_check_changed)
            row.add_prefix(check)
            row.set_title(contact.name)
            self.contact_list.append(row)
            self._check_by_contact[check] = contact
        members_group.add(self.contact_list)
        self.favorite_switch = Gtk.Switch()
        self.favorite_switch.set_active(bool(group.favorite) if group else False)
        members_group.add(self.favorite_switch)
        self.content.append(members_group)

        if self._existing:
            self.delete_button = Gtk.Button(label="Delete")
            self.delete_button.add_css_class("destructive-action")
            self.delete_button.set_halign(Gtk.Align.CENTER)
            self.delete_button.connect("clicked", self._on_delete_clicked)
            self.content.append(self.delete_button)
        else:
            self.delete_button = None

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_row.set_halign(Gtk.Align.CENTER)
        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.connect("clicked", self._on_cancel_clicked)
        button_row.append(self.cancel_button)
        self.save_button = Gtk.Button(label="Save")
        self.save_button.add_css_class("suggested-action")
        self.save_button.connect("clicked", self._on_save_clicked)
        button_row.append(self.save_button)
        self.content.append(button_row)

        self.set_child(self.content)
        self.set_title("Edit group" if self._existing else "New group")
        self.set_content_width(360)
        self._update_save_sensitivity()

    # ---- sensitivity ------------------------------------------------------

    def _update_save_sensitivity(self) -> None:
        """Enable Save only when the name is set and at least one member checked."""
        name_ok = self.name_entry.get_text().strip() != ""
        any_member = any(check.get_active() for check in self._check_by_contact)
        self.save_button.set_sensitive(name_ok and any_member)

    def _on_name_changed(self, entry) -> None:
        """The name entry changed: re-evaluate Save."""
        self._update_save_sensitivity()

    def _on_check_changed(self, check, checked) -> None:
        """A member check changed: re-evaluate Save."""
        self._update_save_sensitivity()

    # ---- actions ----------------------------------------------------------

    def _on_save_clicked(self, button) -> None:
        """Build a RainGroup from the current state, save it, and close."""
        name = self.name_entry.get_text()
        member_ids = [
            contact.id
            for check, contact in self._check_by_contact.items()
            if check.get_active()
        ]
        group_id = self.group.id if self.group is not None else uuid.uuid4().hex
        group = RainGroup(
            id=group_id,
            name=name,
            member_ids=member_ids,
            favorite=self.favorite_switch.get_active(),
        )
        self.backend.save_group(group)
        if self.on_saved is not None:
            self.on_saved()
        self.close()

    def _on_cancel_clicked(self, button) -> None:
        """Discard the edit and close."""
        self.close()

    def _on_delete_clicked(self, button) -> None:
        """Ask for confirmation before deleting this group."""
        name = self.group.name if self.group is not None else self.name_entry.get_text()
        dialog = Adw.AlertDialog.new(f"Delete {name}?", f"Delete the group {name}?")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_delete_response)
        self.confirm_dialog = dialog
        dialog.present(self)

    def _on_delete_response(self, dialog, response_id: str) -> None:
        """Handle the delete confirmation; 'delete' removes the group."""
        if response_id == "delete" and self.group is not None:
            self.backend.delete_group(self.group.id)
            if self.on_saved is not None:
                self.on_saved()
            self.close()
