"""The Wallet (portfolio) screen: asset list, donut chart, legend, receive box.

Plain GTK only; all money data comes from the injected backend.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from ..units import ASSETS, format_amount
from ..demo_prices import portfolio_shares, percent_shares

import math

# Donut colours: KITTY gold, BTC orange (as cairo rgba fractions).
COLORS = {"KITTY": (0.96, 0.77, 0.26), "BTC": (0.97, 0.58, 0.1)}
DEFAULT_COLOR = (0.5, 0.5, 0.5)


class WalletPage(Gtk.Box):
    """Vertical box: asset list, donut + legend, and the receive box."""

    def __init__(self, backend):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._backend = backend
        self._row_asset: dict[Adw.ActionRow, str] = {}
        self._row_check: dict[Adw.ActionRow, Gtk.Image] = {}

        # ---- asset list (single selection) --------------------------------
        self.asset_list = Gtk.ListBox()
        self.asset_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        for code, asset in ASSETS.items():
            row = Adw.ActionRow()
            row.set_title(asset.name)
            row.set_subtitle(asset.code)
            badge = Gtk.Label(label=asset.code[0])
            badge.add_css_class("ck-badge")
            row.add_prefix(badge)
            balance = format_amount(self._balance(code), asset)
            row.add_suffix(Gtk.Label(label=f"{balance} {asset.code}"))
            check = Gtk.Image.new_from_icon_name("object-select-symbolic")
            check.set_visible(False)
            row.add_suffix(check)
            self.asset_list.append(row)
            self._row_asset[row] = code
            self._row_check[row] = check
        self._refresh_checks()
        self.asset_list.connect("row-activated", self._on_row_activated)

        # ---- donut chart --------------------------------------------------
        self.donut = Gtk.DrawingArea()
        self.donut.set_content_width(220)
        self.donut.set_content_height(220)
        self.donut.set_draw_func(self._draw_donut)
        chart_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        chart_row.append(self.donut)

        # ---- legend -------------------------------------------------------
        self.legend_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._build_legend()
        chart_row.append(self.legend_box)
        self.append(chart_row)

        # ---- receive box --------------------------------------------------
        self._receive_heading = Gtk.Label(label=self._heading_text())
        self.append(self._receive_heading)
        self.address_label = Gtk.Label(label=self._address_text())
        self.address_label.add_css_class("monospace")
        self.address_label.set_selectable(True)
        self.append(self.address_label)
        self.copy_button = Gtk.Button(label="Copy")
        self.copy_button.connect("clicked", self._on_copy_clicked)
        self.append(self.copy_button)
        self.append(Gtk.Label(label="QR code: coming soon"))

    # ---- selection --------------------------------------------------------

    def selected_asset(self) -> str:
        """Return the asset code of the currently selected row ("" if none)."""
        row = self.asset_list.get_selected_row()
        if row is None:
            return ""
        return self._row_asset[row]

    def _refresh_checks(self) -> None:
        selected = self.asset_list.get_selected_row()
        for row, check in self._row_check.items():
            check.set_visible(row is selected)

    def _on_row_activated(self, list_box, row, user_initiated) -> None:
        """Selection changed: update the check icons and the receive box."""
        self._refresh_checks()
        self._refresh_receive_box()

    def _refresh_receive_box(self) -> None:
        self._receive_heading.set_label(self._heading_text())
        self.address_label.set_label(self._address_text())

    # ---- receive box text -------------------------------------------------

    def _heading_text(self) -> str:
        return f"Your {self.selected_asset()} address"

    def _address_text(self) -> str:
        if self.selected_asset() == "KITTY":
            return self._backend.address()
        return "Bitcoin receiving arrives with atomic swaps"

    def _on_copy_clicked(self, button) -> None:
        """Copy the selected address to the clipboard, then flash 'Copied'."""
        if self.selected_asset() == "KITTY":
            self.get_clipboard().set(self._backend.address())
        button.set_label("Copied")
        GLib.timeout_add_seconds(2, self._reset_copy_button)

    def _reset_copy_button(self) -> bool:
        self.copy_button.set_label("Copy")
        return False

    # ---- donut drawing ----------------------------------------------------

    def _draw_donut(self, area, cr, width, height) -> None:
        shares = portfolio_shares(self._balances())
        if not shares:
            return
        total = sum(value for _code, value in shares)
        cx = width / 2.0
        cy = height / 2.0
        radius = min(width, height) / 2.0 - 20.0
        selected = self.selected_asset()
        start = -math.pi / 2.0
        for code, value in shares:
            sweep = 2.0 * math.pi * value / total
            cr.set_source_rgba(*COLORS.get(code, DEFAULT_COLOR), 1.0)
            cr.set_line_width(36.0 if code == selected else 28.0)
            cr.arc(cx, cy, radius, start, start + sweep)
            cr.stroke()
            start += sweep

    # ---- legend -----------------------------------------------------------

    def _build_legend(self) -> None:
        for child in self._drain(self.legend_box):
            self.legend_box.remove(child)
        shares = portfolio_shares(self._balances())
        for code, percent in percent_shares(shares):
            name = ASSETS[code].name
            self.legend_box.append(Gtk.Label(label=f"{name} {percent}%"))

    # ---- helpers ----------------------------------------------------------

    def _balance(self, code: str) -> int:
        return self._backend.balance(code)

    def _balances(self) -> dict[str, int]:
        return {code: self._backend.balance(code) for code in ASSETS}

    def _drain(self, box):
        children = []
        child = box.get_first_child()
        while child is not None:
            children.append(child)
            child = child.get_next_sibling()
        return children
