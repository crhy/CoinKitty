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

# Donut colours: KITTY gold, BTC blue (cairo rgba fractions). The two hues are
# far apart so colour-blind users can still tell the segments apart.
COLORS = {"KITTY": (0.96, 0.77, 0.26), "BTC": (0.25, 0.47, 0.85)}
DEFAULT_COLOR = (0.5, 0.5, 0.5)


class WalletPage(Gtk.Box):
    """Outer box holding a ScrolledWindow; the ScrolledWindow holds the page box."""

    def __init__(self, backend):
        super().__init__()
        self._backend = backend
        self._row_asset: dict[Adw.ActionRow, str] = {}
        self._row_check: dict[Adw.ActionRow, Gtk.Image] = {}
        self._row_balance_label: dict[Adw.ActionRow, Gtk.Label] = {}

        # ---- scrolled page box (never overflows) --------------------------
        self._scrolled = Gtk.ScrolledWindow()
        self._scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self._page.set_margin_top(24)
        self._page.set_margin_bottom(24)
        self._page.set_margin_start(24)
        self._page.set_margin_end(24)
        self._scrolled.set_child(self._page)
        self.append(self._scrolled)

        # ---- asset list (single selection) --------------------------------
        self.asset_list = Gtk.ListBox()
        self.asset_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.asset_list.add_css_class("boxed-list")
        kitty_row = None
        for code, asset in ASSETS.items():
            row = Adw.ActionRow()
            row.set_title(asset.name)
            row.set_subtitle(asset.code)
            badge = Gtk.Label(label=asset.code[0])
            badge.add_css_class("ck-badge")
            badge.set_size_request(32, 32)
            badge.set_halign(Gtk.Align.CENTER)
            badge.set_valign(Gtk.Align.CENTER)
            row.add_prefix(badge)
            balance = format_amount(self._balance(code), asset)
            balance_label = Gtk.Label(label=f"{balance} {asset.code}")
            row.add_suffix(balance_label)
            self._row_balance_label[row] = balance_label
            check = Gtk.Image.new_from_icon_name("object-select-symbolic")
            check.set_visible(False)
            row.add_suffix(check)
            self.asset_list.append(row)
            self._row_asset[row] = code
            self._row_check[row] = check
            if code == "KITTY":
                kitty_row = row
        frame = Gtk.Frame()
        frame.set_child(self.asset_list)
        self._page.append(frame)

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
        self._page.append(chart_row)

        # ---- receive box --------------------------------------------------
        self._receive_heading = Gtk.Label(label=self._heading_text())
        self._page.append(self._receive_heading)
        self.address_label = Gtk.Label(label=self._address_text())
        self.address_label.add_css_class("monospace")
        self.address_label.set_selectable(True)
        self._page.append(self.address_label)
        self.copy_button = Gtk.Button(label="Copy")
        self.copy_button.add_css_class("pill")
        self.copy_button.set_halign(Gtk.Align.CENTER)
        self.copy_button.connect("clicked", self._on_copy_clicked)
        self._page.append(self.copy_button)
        self._page.append(Gtk.Label(label="QR code: coming soon"))

        # ---- selection wiring (click + keyboard) --------------------------
        self.asset_list.connect("row-selected", self._on_row_changed)
        self.asset_list.connect("row-activated", self._on_row_changed)
        self._refresh_receive_box()

    # ---- selection --------------------------------------------------------

    def selected_asset(self) -> str:
        """Return the asset code of the selected row, defaulting to KITTY."""
        row = self.asset_list.get_selected_row()
        if row is None:
            return "KITTY"
        return self._row_asset[row]

    def _refresh_checks(self) -> None:
        selected = self.asset_list.get_selected_row()
        for row, check in self._row_check.items():
            check.set_visible(row is selected)

    def _on_row_changed(self, row, user_initiated) -> None:
        """Selection changed (click or keyboard): refresh checks and receive box."""
        self._refresh_checks()
        self._refresh_receive_box()

    def _refresh_receive_box(self) -> None:
        self._receive_heading.set_label(self._heading_text())
        self.address_label.set_label(self._address_text())
        self.copy_button.set_visible(self.selected_asset() == "KITTY")

    def refresh(self) -> None:
        """Re-read the backend and update each asset's balance label and the legend."""
        for row, code in self._row_asset.items():
            balance = format_amount(self._balance(code), ASSETS[code])
            self._row_balance_label[row].set_label(f"{balance} {code}")
        self._build_legend()

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
            entry = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            entry.append(self._legend_swatch(code))
            entry.append(Gtk.Label(label=f"{name} {percent}%"))
            self.legend_box.append(entry)

    def _legend_swatch(self, code: str) -> Gtk.DrawingArea:
        """A 12x12 square filled with the asset's donut colour."""
        color = COLORS.get(code, DEFAULT_COLOR)
        square = Gtk.DrawingArea()
        square.set_content_width(12)
        square.set_content_height(12)
        square.set_draw_func(self._make_legend_draw(color))
        return square

    def _make_legend_draw(self, color):
        def draw(area, cr, width, height) -> None:
            cr.set_source_rgb(*color)
            cr.paint()

        return draw

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
