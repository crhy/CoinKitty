"""The Vault screen: lock coins behind a time lock, withdraw what unlocked."""

from __future__ import annotations

import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from ..models import Vault
from ..units import ASSETS, parse_amount, format_amount
from ..vaults import next_unlock, unlocked_amount

RELEASE_MODES = (("All at once", 0, 0), ("10% per month", 10, 30), ("25% per month", 25, 30))


def format_date(timestamp: int) -> str:
    """Local-time YYYY-MM-DD for a unix timestamp."""
    return time.strftime("%Y-%m-%d", time.localtime(timestamp))


class VaultPage(Gtk.Box):
    """Vault screen: create a time-locked vault and withdraw what has unlocked."""

    def __init__(self, backend, on_changed=None):
        super().__init__()
        self.backend = backend
        self.on_changed = on_changed
        self._asset_code = "KITTY"
        self._step_percent = 0
        self._step_days = 0
        self._vault_rows: dict[Adw.ActionRow, Vault] = {}
        self._withdraw_buttons: dict[Gtk.Button, Vault] = {}
        self.confirm_dialog: Adw.AlertDialog | None = None

        self.toast_overlay = Adw.ToastOverlay()
        self.append(self.toast_overlay)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_vexpand(True)
        self.scrolled.set_propagate_natural_height(True)
        self.toast_overlay.set_child(self.scrolled)

        self.clamp = Adw.Clamp()
        self.clamp.set_maximum_size(640)
        self.scrolled.set_child(self.clamp)

        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.content.set_margin_top(24)
        self.content.set_margin_bottom(24)
        self.content.set_margin_start(24)
        self.content.set_margin_end(24)
        self.clamp.set_child(self.content)

        # ---- new vault ----------------------------------------------------
        new_group = Adw.PreferencesGroup()
        new_group.set_title("New vault")

        asset_row = Adw.ActionRow()
        asset_row.set_title("Asset")
        self.asset_dropdown = Gtk.DropDown(model=Gtk.StringList.new(
            [code for code, _asset in ASSETS.items()]))
        self.asset_dropdown.connect("notify::selected", self._on_asset_selected)
        asset_row.add_suffix(self.asset_dropdown)
        new_group.add(asset_row)

        self.amount_entry = Adw.EntryRow()
        self.amount_entry.set_title("Amount")
        self.amount_entry.connect("changed", self._clear_error)
        new_group.add(self.amount_entry)

        self.calendar = Gtk.Calendar()
        new_group.add(self.calendar)

        self.release_dropdown = Gtk.DropDown(model=Gtk.StringList.new(
            [name for name, _p, _d in RELEASE_MODES]))
        self.release_dropdown.connect("notify::selected", self._on_release_selected)
        release_row = Adw.ActionRow()
        release_row.set_title("Release")
        release_row.add_suffix(self.release_dropdown)
        new_group.add(release_row)

        self.warning_label = Gtk.Label(
            label="No one can open a vault early, including you.")
        self.warning_label.add_css_class("warning")
        self.warning_label.set_wrap(True)
        new_group.add(self.warning_label)
        self.content.append(new_group)

        self.lock_button = Gtk.Button(label="Lock it")
        self.lock_button.add_css_class("suggested-action")
        self.lock_button.add_css_class("pill")
        self.lock_button.set_halign(Gtk.Align.CENTER)
        self.lock_button.connect("clicked", self._on_lock_clicked)
        self.content.append(self.lock_button)

        # ---- your vaults ---------------------------------------------------
        vaults_group = Adw.PreferencesGroup()
        vaults_group.set_title("Your vaults")
        self.vault_list = Gtk.ListBox()
        self.vault_list.add_css_class("boxed-list")
        self.vault_list.set_selection_mode(Gtk.SelectionMode.NONE)
        vaults_group.add(self.vault_list)
        self.content.append(vaults_group)

        self.error_label = Gtk.Label(label="")
        self.error_label.add_css_class("error")
        self.error_label.set_visible(False)
        self.content.append(self.error_label)

        self._refresh_vault_rows()

    # ---- inputs ------------------------------------------------------------

    def _on_asset_selected(self, dropdown, previous) -> None:
        """Track the asset chosen in the dropdown."""
        item = dropdown.get_selected_item()
        if item is not None:
            self._asset_code = item.get_string()

    def _on_release_selected(self, dropdown, previous) -> None:
        """Track the release mode chosen in the dropdown."""
        item = dropdown.get_selected_item()
        if item is None:
            return
        name = item.get_string()
        for mode_name, percent, days in RELEASE_MODES:
            if name == mode_name:
                self._step_percent = percent
                self._step_days = days
                return

    def _unlock_timestamp(self) -> int:
        """The calendar's selected date as unix seconds (0 if unset)."""
        date = self.calendar.get_date()
        if date is None:
            return 0
        return int(date.to_unix())

    def _amount(self) -> int | None:
        """Parse the amount entry for the current asset, or None if invalid."""
        try:
            return parse_amount(self.amount_entry.get_text(), ASSETS[self._asset_code])
        except ValueError:
            return None

    # ---- locking ------------------------------------------------------------

    def _on_lock_clicked(self, button) -> None:
        """Ask for confirmation before locking coins into a vault."""
        amount = self._amount()
        unlock_at = self._unlock_timestamp()
        if amount is None or unlock_at <= 0:
            self._set_error("Pick an amount and an unlock date first.")
            return
        asset = ASSETS[self._asset_code]
        dialog = Adw.AlertDialog.new(
            f"Lock {format_amount(amount, asset)} {self._asset_code} until "
            f"{format_date(unlock_at)}?",
            "No one can open a vault early, including you.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("lock", "Lock it")
        dialog.set_response_appearance("lock", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_lock_response)
        self.confirm_dialog = dialog
        dialog.present(self)

    def _on_lock_response(self, dialog, response_id: str) -> None:
        """Create the vault when the confirmation says lock."""
        if response_id != "lock":
            return
        amount = self._amount()
        unlock_at = self._unlock_timestamp()
        if amount is None or unlock_at <= 0:
            self._set_error("Pick an amount and an unlock date first.")
            return
        try:
            self.backend.create_vault(
                self._asset_code, amount, unlock_at,
                self._step_percent, self._step_days)
        except ValueError as exc:
            self._set_error(str(exc))
            return
        self._clear_error()
        if self.on_changed is not None:
            self.on_changed()
        self.toast_overlay.add_toast(
            Adw.Toast.new(f"Vault locked: {format_amount(amount, ASSETS[self._asset_code])} "
                          f"{self._asset_code} until {format_date(unlock_at)}"))
        self._refresh_vault_rows()

    # ---- vault rows ----------------------------------------------------------

    def _refresh_vault_rows(self) -> None:
        """Rebuild one action row per vault, with a Withdraw button if due."""
        self._vault_rows = {}
        self._withdraw_buttons = {}
        child = self.vault_list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.vault_list.remove(child)
            child = nxt
        now = self.backend.clock()
        for vault in self.backend.vaults():
            asset = ASSETS[vault.asset]
            unlocked = unlocked_amount(vault, now)
            row = Adw.ActionRow()
            row.set_title(f"{format_amount(vault.amount, asset)} {vault.asset}")
            if unlocked == 0:
                row.set_subtitle(f"Unlocks {format_date(vault.unlock_at)}")
            elif unlocked >= vault.amount:
                row.set_subtitle("Fully unlocked")
            else:
                timestamp, _amount = next_unlock(vault, now)
                row.set_subtitle(
                    f"{format_amount(unlocked, asset)} unlocked, "
                    f"next {format_date(timestamp)}")
            if unlocked - vault.released > 0:
                button = Gtk.Button(label="Withdraw")
                button.add_css_class("pill")
                button.connect("clicked", self._make_withdraw_handler(vault))
                row.add_suffix(button)
                self._withdraw_buttons[button] = vault
            self.vault_list.append(row)
            self._vault_rows[row] = vault

    def _make_withdraw_handler(self, vault: Vault):
        return lambda *_: self._withdraw(vault)

    def _withdraw(self, vault: Vault) -> None:
        """Move everything unlocked of this vault back to the balance."""
        moved = self.backend.withdraw_vault(vault.id, self.backend.clock())
        if moved > 0:
            asset = ASSETS[vault.asset]
            self.toast_overlay.add_toast(
                Adw.Toast.new(f"Withdrew {format_amount(moved, asset)} {vault.asset}"))
            self._refresh_vault_rows()

    # ---- errors --------------------------------------------------------------

    def _set_error(self, text: str) -> None:
        self.error_label.set_text(text)
        self.error_label.set_visible(True)

    def _clear_error(self) -> None:
        self.error_label.set_text("")
        self.error_label.set_visible(False)

    def refresh(self) -> None:
        """Rebuild the vault rows (called on page switch)."""
        self._refresh_vault_rows()
