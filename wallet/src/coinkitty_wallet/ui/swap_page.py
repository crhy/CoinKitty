"""The Swap screen: a simulated atomic swap over the demo backend.

There is no real Bitcoin or KittyChain yet, so the swap is SIMULATED: the steps
are walked in plain language and the balance move is applied only when the
simulation reaches "Done". No real coins ever move. Money is always an ``int``
count of the asset's smallest unit; the rate is an ``int`` count of KITTY's
smallest unit (kitoshi) per one sat.
"""

from __future__ import annotations

import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from ..demo_backend import DemoBackend  # noqa: F401 (type hint only)
from ..units import ASSETS, KITOSHI_PER_KITTY, parse_amount, format_amount
from ..swap import STEPS, DEMO_RATE, Offer, best_offer, quote, demo_order_book, SimulatedSwap

NOTE_TEXT = "Simulated swap: no real Bitcoin moves."

DONE_ICON = "object-select-symbolic"
FUTURE_ICON = "content-loading-symbolic"


def _short_address(address: str) -> str:
    """First 12 chars + an ellipsis + the last 6, for a compact subtitle."""
    if len(address) <= 18:
        return address
    return f"{address[:12]}…{address[-6:]}"


def format_clock(seconds: int) -> str:
    """HH:MM:SS for a non-negative number of seconds."""
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def sats_per_kitty(rate_kitoshi_per_sat: int) -> int:
    """Turn a kitoshi-per-sat rate into whole sats per one KITTY."""
    return KITOSHI_PER_KITTY // rate_kitoshi_per_sat


class SwapPage(Gtk.Box):
    """Swap screen: a form step and a progress step over demo coins."""

    def __init__(self, backend, clock=time.time, rng=None):
        super().__init__()
        self.backend = backend
        self.clock = clock
        self.rng = rng
        self._book: list[Offer] = demo_order_book(rng) if rng is not None else []
        self._timer_id = None
        self._swap: SimulatedSwap | None = None
        self._applied = False
        self._asset_code = "KITTY"
        self._step_rows: list[Adw.ActionRow] = []
        self.step_icons: list[tuple[Gtk.Stack, Gtk.Spinner]] = []

        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_vexpand(True)
        self.append(self.toast_overlay)

        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.toast_overlay.set_child(self.stack)

        self.stack.add_named(self._build_form(), "form")
        self.stack.add_named(self._build_progress(), "progress")
        self.stack.set_visible_child_name("form")

        self._update_form()

    # ---- form step --------------------------------------------------------

    def _build_form(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
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

        group = Adw.PreferencesGroup()
        group.set_title("Swap")

        sell_row = Adw.ActionRow()
        sell_row.set_title("Sell")
        self.sell_dropdown = Gtk.DropDown(model=Gtk.StringList.new(
            [code for code in ASSETS]))
        self.sell_dropdown.connect("notify::selected", self._on_asset_selected)
        sell_row.add_suffix(self.sell_dropdown)
        group.add(sell_row)

        self.amount_entry = Adw.EntryRow()
        self.amount_entry.set_title(f"Amount to sell ({self._asset_code})")
        self.amount_entry.connect("changed", self._on_amount_changed)
        group.add(self.amount_entry)

        self.buy_label = Gtk.Label(label="")
        self.buy_label.add_css_class("dim-label")
        group.add(self.buy_label)

        self.summary_label = Gtk.Label(label="")
        self.summary_label.add_css_class("dim-label")
        self.summary_label.set_wrap(True)
        group.add(self.summary_label)
        content.append(group)

        note_label = Gtk.Label(label=NOTE_TEXT)
        note_label.add_css_class("warning")
        note_label.set_wrap(True)
        content.append(note_label)

        self.swap_button = Gtk.Button(label="Swap")
        self.swap_button.add_css_class("suggested-action")
        self.swap_button.add_css_class("pill")
        self.swap_button.set_halign(Gtk.Align.CENTER)
        self.swap_button.connect("clicked", self._on_swap_clicked)
        content.append(self.swap_button)
        return box

    def _on_amount_changed(self, entry) -> None:
        """GTK passes the changed entry as an argument; recompute the form."""
        self._update_form()

    def _on_asset_selected(self, dropdown, previous) -> None:
        """Track the asset chosen in the dropdown and relabel the amount row."""
        item = dropdown.get_selected_item()
        if item is not None:
            self._asset_code = item.get_string()
            self.amount_entry.set_title(f"Amount to sell ({self._asset_code})")
            self._update_form()

    def _update_form(self) -> None:
        """Recompute the summary label and the Swap button's sensitivity."""
        sell_asset = ASSETS[self._asset_code]
        try:
            amount = parse_amount(self.amount_entry.get_text(), sell_asset)
        except ValueError:
            self.summary_label.set_text("No offer can fill this amount")
            self.swap_button.set_sensitive(False)
            return
        offer = best_offer(self._book, self._asset_code, amount)
        if offer is None:
            self.summary_label.set_text("No offer can fill this amount")
            self.swap_button.set_sensitive(False)
            return
        received = quote(offer, self._asset_code, amount)
        buy_code = offer.buy_asset
        rate = sats_per_kitty(offer.rate_kitoshi_per_sat)
        self.buy_label.set_text(buy_code)
        self.summary_label.set_text(
            f"You receive about {format_amount(received, ASSETS[buy_code])} "
            f"{buy_code} · rate {rate} sats per KITTY · offer from {offer.maker}")
        enough = amount <= self.backend.balance(self._asset_code)
        self.swap_button.set_sensitive(enough)

    def _on_swap_clicked(self, button) -> None:
        """Start a simulated swap and switch to the progress view."""
        sell_asset = ASSETS[self._asset_code]
        try:
            amount = parse_amount(self.amount_entry.get_text(), sell_asset)
        except ValueError:
            return
        offer = best_offer(self._book, self._asset_code, amount)
        if offer is None or amount > self.backend.balance(self._asset_code):
            return
        received = quote(offer, self._asset_code, amount)
        self._swap = SimulatedSwap(offer, self._asset_code, amount, received,
                                   int(self.clock()))
        self._applied = False
        self._refresh_progress()
        self.stack.set_visible_child_name("progress")
        self._start_timer()

    # ---- progress step ----------------------------------------------------

    def _build_progress(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
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

        group = Adw.PreferencesGroup()
        group.set_title("Swap")
        self._step_rows = []
        self.step_icons = []
        for step in STEPS:
            row = Adw.ActionRow()
            row.set_title(step)
            stack = Gtk.Stack()
            stack.add_named(Gtk.Image.new_from_icon_name(DONE_ICON), "done")
            spinner = Gtk.Spinner()
            stack.add_named(spinner, "current")
            stack.add_named(Gtk.Image.new_from_icon_name(FUTURE_ICON), "todo")
            stack.set_visible_child_name("todo")
            row.add_prefix(stack)
            self.step_icons.append((stack, spinner))
            group.add(row)
            self._step_rows.append(row)
        content.append(group)

        self.progress_note_label = Gtk.Label(label=NOTE_TEXT)
        self.progress_note_label.add_css_class("warning")
        self.progress_note_label.set_wrap(True)
        content.append(self.progress_note_label)

        self.refund_label = Gtk.Label(label="")
        self.refund_label.add_css_class("warning")
        self.refund_label.set_wrap(True)
        content.append(self.refund_label)

        self.fail_button = Gtk.Button(label="Simulate a failure")
        self.fail_button.add_css_class("flat")
        self.fail_button.add_css_class("destructive-action")
        self.fail_button.set_halign(Gtk.Align.CENTER)
        self.fail_button.connect("clicked", self._on_fail_clicked)
        content.append(self.fail_button)

        self.done_button = Gtk.Button(label="Done")
        self.done_button.add_css_class("suggested-action")
        self.done_button.add_css_class("pill")
        self.done_button.set_halign(Gtk.Align.CENTER)
        self.done_button.connect("clicked", self._on_done_clicked)
        content.append(self.done_button)
        self.fail_button.set_visible(True)
        self.done_button.set_visible(False)
        self.progress_box = box
        return box

    def _refresh_progress(self) -> None:
        """Set each step row's icon from the current swap state."""
        if self._swap is None:
            return
        now = int(self.clock())
        state = self._swap.state(now)
        if self._swap._failed or state == "Done":
            current = len(STEPS)
        else:
            current = min((now - self._swap.started_at) // 3, len(STEPS) - 1)
        for index, row in enumerate(self._step_rows):
            if index < current:
                icon = DONE_ICON
            elif index == current:
                icon = None
            else:
                icon = FUTURE_ICON
            self._set_row_icon(index, icon)
        if self._swap._failed and state == "Refunding":
            self.refund_label.set_text(
                f"Refunding in {format_clock(self._swap.refund_countdown(now))}")
        else:
            self.refund_label.set_text("")

    def _set_row_icon(self, index: int, icon: str | None) -> None:
        """Point one step row's prefix Stack at the right named child."""
        stack, spinner = self.step_icons[index]
        if icon is None:
            stack.set_visible_child_name("current")
            spinner.start()
        elif icon == DONE_ICON:
            stack.set_visible_child_name("done")
            spinner.stop()
        else:
            stack.set_visible_child_name("todo")
            spinner.stop()

    def _start_timer(self) -> None:
        """Schedule the 500 ms progress tick."""
        self._timer_id = GLib.timeout_add(500, self._tick)

    def _tick(self) -> bool:
        """Advance the progress view; True keeps the timer running."""
        if self._swap is None:
            return False
        now = int(self.clock())
        state = self._swap.state(now)
        self._refresh_progress()
        if state == "Done":
            if not self._applied:
                self._applied = True
                sell_asset = self._swap.sell_asset
                buy_asset = self._swap.offer.buy_asset
                self.backend.apply_swap(sell_asset, self._swap.amount,
                                        buy_asset, self._swap.receive)
                self.toast_overlay.add_toast(
                    Adw.Toast.new(
                        f"Swapped {format_amount(self._swap.amount, ASSETS[sell_asset])} "
                        f"{sell_asset} for {format_amount(self._swap.receive, ASSETS[buy_asset])} "
                        f"{buy_asset}"))
            self.done_button.set_visible(True)
            self.fail_button.set_visible(False)
            return False
        if state == "Refunded":
            self.done_button.set_visible(True)
            self.fail_button.set_visible(False)
            return False
        self.fail_button.set_visible(True)
        self.done_button.set_visible(False)
        return True

    def stop_timer(self) -> None:
        """Cancel the scheduled tick (call when leaving the progress view)."""
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None

    def _on_fail_clicked(self, button) -> None:
        """Mark the running swap as failed to exercise the refund path."""
        if self._swap is not None:
            self._swap.fail()
            self._refresh_progress()

    def _on_done_clicked(self, button) -> None:
        """Return to the form once the swap finished or refunded."""
        self.stop_timer()
        self._swap = None
        self.stack.set_visible_child_name("form")
        self._update_form()

    # ---- public helpers ---------------------------------------------------

    def refresh(self) -> None:
        """Recompute the form (called on page switch)."""
        self._update_form()
