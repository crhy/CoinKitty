"""The Rain screen: split one total across the members of checked rain groups."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ..demo_backend import DemoBackend  # noqa: F401 (type hint only)
from ..models import Contact, RainGroup
from ..rain import rain_recipients, split_equal
from ..units import ASSETS, parse_amount, format_amount
from .group_editor import GroupEditor


class RainPage(Gtk.Box):
    """Rain screen: pick an asset, a total, and one or more rain groups."""

    def __init__(self, backend, on_open_page=None, on_changed=None):
        super().__init__()
        self.backend = backend
        self.on_open_page = on_open_page
        self.on_changed = on_changed

        self._asset_code = "KITTY"
        self._group_rows: dict[Adw.ActionRow, RainGroup] = {}
        self._edit_button_group: dict[Gtk.Button, RainGroup] = {}
        self._preview_rows: dict[Adw.ActionRow, str] = {}
        self._group_checks: dict[str, Gtk.CheckButton] = {}
        self._custom_entries: dict[str, Gtk.Entry] = {}
        self._active_editor: GroupEditor | None = None

        # ---- toast overlay wraps the whole page ---------------------------
        self.toast_overlay = Adw.ToastOverlay()
        self.append(self.toast_overlay)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
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

        # ---- asset + total ------------------------------------------------
        total_group = Adw.PreferencesGroup()
        total_group.set_title("Rain")
        asset_row = Adw.ActionRow()
        asset_row.set_title("Asset")
        model = Gtk.StringList.new(["KITTY", "BTC"])
        self.asset_dropdown = Gtk.DropDown(model=model)
        self.asset_dropdown.connect("notify::selected", self._on_asset_selected)
        asset_row.add_suffix(self.asset_dropdown)
        total_group.add(asset_row)
        self.total_entry = Gtk.Entry()
        self.total_entry.set_placeholder_text("Total to rain")
        self.total_entry.connect("changed", self._on_total_changed)
        total_group.add(self.total_entry)
        self.content.append(total_group)

        # ---- group list ---------------------------------------------------
        groups_group = Adw.PreferencesGroup()
        groups_group.set_title("Groups")
        self.group_list = Gtk.ListBox()
        self.group_list.add_css_class("boxed-list")
        self.group_list.set_selection_mode(Gtk.SelectionMode.NONE)
        groups_group.add(self.group_list)
        new_group_button = Gtk.Button(label="New group")
        new_group_button.set_halign(Gtk.Align.CENTER)
        new_group_button.connect("clicked", self._on_new_group_clicked)
        groups_group.add(new_group_button)
        self.content.append(groups_group)

        # ---- split mode ---------------------------------------------------
        split_group = Adw.PreferencesGroup()
        split_group.set_title("Split")
        self.equal_toggle = Gtk.ToggleButton(label="Equal")
        self.equal_toggle.set_active(True)
        self.custom_toggle = Gtk.ToggleButton(label="Custom")
        self.custom_toggle.set_group(self.equal_toggle)
        split_group.add(self.equal_toggle)
        split_group.add(self.custom_toggle)
        self.content.append(split_group)

        # ---- preview ------------------------------------------------------
        preview_group = Adw.PreferencesGroup()
        preview_group.set_title("Preview")
        self.preview_list = Gtk.ListBox()
        self.preview_list.add_css_class("boxed-list")
        self.preview_list.set_selection_mode(Gtk.SelectionMode.NONE)
        preview_group.add(self.preview_list)
        self.assigned_label = Gtk.Label(label="")
        preview_group.add(self.assigned_label)
        self.content.append(preview_group)

        # ---- rain button + error -----------------------------------------
        self.rain_button = Gtk.Button(label="Rain")
        self.rain_button.add_css_class("suggested-action")
        self.rain_button.add_css_class("pill")
        self.rain_button.set_halign(Gtk.Align.CENTER)
        self.rain_button.connect("clicked", self._on_rain_clicked)
        self.content.append(self.rain_button)

        self.error_label = Gtk.Label(label="")
        self.error_label.add_css_class("error")
        self.error_label.set_visible(False)
        self.content.append(self.error_label)

        self._refresh_group_rows()
        self._refresh_preview()

    # ---- asset ------------------------------------------------------------

    def _on_asset_selected(self, dropdown, previous) -> None:
        """Track the asset chosen in the dropdown."""
        item = dropdown.get_selected_item()
        if item is not None:
            self._asset_code = item.get_string()

    # ---- groups -----------------------------------------------------------

    def _refresh_group_rows(self) -> None:
        """Rebuild one action row per rain group, with a check and an Edit."""
        self._group_checks = {}
        self._group_rows = {}
        self._edit_button_group = {}
        child = self.group_list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.group_list.remove(child)
            child = nxt
        for group in self.backend.rain_groups():
            row = Adw.ActionRow()
            check = Gtk.CheckButton(label=group.name)
            row.add_prefix(check)
            row.set_title(group.name)
            row.set_subtitle(f"{len(group.member_ids)} people")
            edit_button = Gtk.Button(label="Edit")
            edit_button.add_css_class("flat")
            edit_button.connect("clicked", self._make_edit_handler(group))
            row.add_suffix(edit_button)
            self.group_list.append(row)
            self._group_rows[row] = group
            self._group_checks[group.id] = check
            self._edit_button_group[edit_button] = group

    def _make_edit_handler(self, group: RainGroup):
        """Return a clicked-handler that opens the editor for ``group``."""
        return lambda *_: self._open_editor(group)

    def _open_editor(self, group: RainGroup | None) -> None:
        """Open a rain-group editor for ``group`` (None creates a new one)."""
        editor = GroupEditor(self.backend, group, on_saved=self._on_group_saved)
        self._active_editor = editor
        editor.present(self)

    def _on_new_group_clicked(self, button) -> None:
        """Open an editor for a brand-new group."""
        self._open_editor(None)

    def _on_group_saved(self) -> None:
        """A group was saved: refresh the page and tell the window favorites changed."""
        self.refresh()
        if self.on_changed is not None:
            self.on_changed()

    def preselect_group(self, group_id: str) -> None:
        """Check only the given group (used when a favorite group opens rain)."""
        for gid, check in self._group_checks.items():
            check.set_active(gid == group_id)
        self._refresh_preview()

    # ---- preview ----------------------------------------------------------

    def _checked_ids(self) -> list[str]:
        """Group ids whose check button is currently checked."""
        return [gid for gid, check in self._group_checks.items() if check.get_active()]

    def _refresh_preview(self) -> None:
        """Rebuild the per-recipient preview rows for the current selection."""
        ids = rain_recipients(self.backend.rain_groups(), self._checked_ids())
        self._preview_rows = {}
        self._custom_entries = {}
        child = self.preview_list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.preview_list.remove(child)
            child = nxt
        name_by_id = {c.id: c.name for c in self.backend.contacts()}
        asset = ASSETS[self._asset_code]
        if self._custom():
            amounts = self._custom_amounts(ids)
            for cid in ids:
                row = Adw.ActionRow()
                row.set_title(name_by_id.get(cid, ""))
                entry = Gtk.Entry()
                entry.set_placeholder_text("Amount")
                entry.connect("changed", self._on_custom_changed)
                row.add_suffix(entry)
                self.preview_list.append(row)
                self._preview_rows[row] = cid
                self._custom_entries[cid] = entry
            self._update_assigned()
        else:
            total = self._parse_total()
            shares = split_equal(total, ids) if (total is not None and ids) else {}
            for cid in ids:
                row = Adw.ActionRow()
                row.set_title(name_by_id.get(cid, ""))
                amount = shares.get(cid, 0)
                row.set_subtitle(f"{format_amount(amount, asset)} {self._asset_code}")
                self.preview_list.append(row)
                self._preview_rows[row] = cid
            self.assigned_label.set_text("")

    def _custom(self) -> bool:
        """True when the Custom split toggle is active."""
        return self.custom_toggle.get_active()

    def _parse_total(self) -> int | None:
        """Parse the total entry for the current asset, or None if invalid."""
        try:
            return parse_amount(self.total_entry.get_text(), ASSETS[self._asset_code])
        except ValueError:
            return None

    def _custom_amounts(self, ids: list[str]) -> dict[str, int]:
        """Parse each custom amount entry; invalid entries count as 0."""
        asset = ASSETS[self._asset_code]
        amounts: dict[str, int] = {}
        for cid in ids:
            entry = self._custom_entries.get(cid)
            try:
                amounts[cid] = parse_amount(entry.get_text(), asset)
            except (ValueError, AttributeError):
                amounts[cid] = 0
        return amounts

    def _on_custom_changed(self, entry) -> None:
        """A custom amount entry changed: update the assigned label and sensitivity."""
        self._update_assigned()
        self._update_rain_sensitivity()

    def _update_assigned(self) -> None:
        """Recompute the 'Assigned x of y' label for the current custom amounts."""
        ids = rain_recipients(self.backend.rain_groups(), self._checked_ids())
        asset = ASSETS[self._asset_code]
        amounts = self._custom_amounts(ids)
        assigned = sum(amounts.values())
        total = self._parse_total()
        self.assigned_label.set_text(
            f"Assigned {format_amount(assigned, asset)} of "
            f"{format_amount(total, asset) if total is not None else '?'}"
        )
        if total is not None and assigned != total:
            self.assigned_label.add_css_class("error")
        else:
            self.assigned_label.remove_css_class("error")

    def _on_total_changed(self, entry) -> None:
        """The total entry changed: refresh the preview and sensitivity."""
        self._refresh_preview()
        self._update_rain_sensitivity()

    # ---- rain button ------------------------------------------------------

    def _update_rain_sensitivity(self) -> None:
        """Enable the Rain button only when the rain would be valid."""
        self.rain_button.set_sensitive(self._rain_is_valid())

    def _rain_is_valid(self) -> bool:
        """True when clicking Rain would send a valid rain."""
        if self._asset_code == "BTC":
            return False
        total = self._parse_total()
        if total is None or total <= 0:
            return False
        ids = rain_recipients(self.backend.rain_groups(), self._checked_ids())
        if not ids:
            return False
        if self._custom():
            amounts = self._custom_amounts(ids)
            if sum(amounts.values()) != total:
                return False
            if any(amount <= 0 for amount in amounts.values()):
                return False
        return True

    def _on_rain_clicked(self, button) -> None:
        """Confirm the rain, or show an error and send nothing."""
        if self._asset_code == "BTC":
            self._set_error("Bitcoin rain arrives with atomic swaps")
            return
        total = self._parse_total()
        if total is None or total <= 0:
            self._set_error("Enter a positive total")
            return
        ids = rain_recipients(self.backend.rain_groups(), self._checked_ids())
        if not ids:
            self._set_error("No recipients selected")
            return
        amounts = self._custom_amounts(ids) if self._custom() else None
        try:
            self.backend.rain(self._asset_code, total, ids, amounts)
        except ValueError as exc:
            self._set_error(str(exc))
            return
        asset = ASSETS[self._asset_code]
        self.toast_overlay.add_toast(
            Adw.Toast.new(
                f"Rained {format_amount(total, asset)} {self._asset_code} "
                f"on {len(ids)} people"
            )
        )
        self.total_entry.set_text("")
        self._clear_error()
        self._refresh_preview()
        self._update_rain_sensitivity()

    def _set_error(self, text: str) -> None:
        """Show an error message."""
        self.error_label.set_text(text)
        self.error_label.set_visible(True)

    def _clear_error(self) -> None:
        """Hide the error message."""
        self.error_label.set_visible(False)

    # ---- public helpers ---------------------------------------------------

    def refresh(self) -> None:
        """Rebuild group rows and the preview from the current backend state."""
        self._refresh_group_rows()
        self._refresh_preview()
        self._update_rain_sensitivity()
