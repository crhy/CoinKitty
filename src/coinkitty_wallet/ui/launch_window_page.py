"""The Launch Window screen: nightly lottery countdown, check-in, Kitty Parties."""

from __future__ import annotations

import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from ..demo_backend import DemoBackend  # noqa: F401 (type hint only)
from ..units import ASSETS, format_amount

KITTY = ASSETS["KITTY"]


def format_clock(seconds: int) -> str:
    """HH:MM:SS for a non-negative number of seconds."""
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class LaunchWindowPage(Gtk.Box):
    """Launch Window screen: countdown, check-in, lottery pool, Kitty Parties."""

    def __init__(self, backend, clock=None, rng=None):
        super().__init__()
        self.backend = backend
        self.clock = clock if clock is not None else backend.clock
        self.rng = rng
        self._timer_id = None
        self._last_result = ""

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

        # ---- countdown ----------------------------------------------------
        self.countdown_label = Gtk.Label(label="")
        self.countdown_label.add_css_class("title-1")
        self.countdown_label.set_halign(Gtk.Align.CENTER)
        self.content.append(self.countdown_label)

        # ---- check in -----------------------------------------------------
        self.check_in_button = Gtk.Button(label="Check in")
        self.check_in_button.add_css_class("suggested-action")
        self.check_in_button.add_css_class("pill")
        self.check_in_button.set_halign(Gtk.Align.CENTER)
        self.check_in_button.connect("clicked", self._on_check_in_clicked)
        self.content.append(self.check_in_button)

        self.ticket_label = Gtk.Label(label="")
        self.ticket_label.set_halign(Gtk.Align.CENTER)
        self.content.append(self.ticket_label)

        # ---- lottery ------------------------------------------------------
        lottery_group = Adw.PreferencesGroup()
        lottery_group.set_title("Lottery")
        self.pool_label = Gtk.Label(label="")
        lottery_group.add(self.pool_label)
        self.result_label = Gtk.Label(label="")
        lottery_group.add(self.result_label)
        self.content.append(lottery_group)

        # ---- kitty parties ------------------------------------------------
        parties_group = Adw.PreferencesGroup()
        parties_group.set_title("Kitty Parties")
        parties_label = Gtk.Label(
            label="In-person verification starts with KittyChain. Demo only.")
        parties_label.set_wrap(True)
        parties_group.add(parties_label)
        self.content.append(parties_group)

        self._refresh_lottery()
        self._update_countdown()
        self._update_check_in_sensitivity()
        self._start_timer()

    # ---- countdown timer --------------------------------------------------

    def _start_timer(self) -> None:
        """Schedule the once-per-second countdown update."""
        self._timer_id = GLib.timeout_add_seconds(1, self._on_tick)

    def _on_tick(self) -> bool:
        """Update countdown/sensitivity and maybe draw; True keeps it going."""
        self._update_countdown()
        self._update_check_in_sensitivity()
        self._maybe_draw()
        return True

    def stop_timer(self) -> None:
        """Cancel the scheduled countdown update (call when the page is gone)."""
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None

    def _update_countdown(self) -> None:
        """Set the countdown text: time to the window, or that it is open."""
        now = int(self.clock())
        start, end = self.backend.launch_window(now)
        if start <= now <= end:
            self.countdown_label.set_text("Launch Window is open")
        else:
            self.countdown_label.set_text(f"Launch in {format_clock(start - now)}")

    def _update_check_in_sensitivity(self) -> None:
        """Enable Check in only inside tonight's window and not yet checked in."""
        now = int(self.clock())
        start, end = self.backend.launch_window(now)
        inside = start <= now <= end
        date = time.strftime("%Y-%m-%d", time.localtime(now))
        already = date in self.backend.checked_in_dates()
        self.check_in_button.set_sensitive(inside and not already)

    def _maybe_draw(self) -> None:
        """Once tonight's window has passed, run the demo draw if we have an rng."""
        if self.rng is None:
            return
        now = int(self.clock())
        _start, end = self.backend.launch_window(now)
        if now <= end:
            return
        date = time.strftime("%Y-%m-%d", time.localtime(end))
        if date in self.backend.checked_in_dates() and date not in self.backend._drawn:
            won = self.backend.run_demo_draw(date, self.rng)
            self._last_result = "You won the lottery!" if won else "No win tonight."
            self._refresh_lottery()

    # ---- check in ---------------------------------------------------------

    def _on_check_in_clicked(self, button) -> None:
        """Check in for tonight's lottery, or show that it is not possible."""
        now = int(self.clock())
        if self.backend.check_in(now):
            self.ticket_label.set_text("You have tonight's ticket")
            self.toast_overlay.add_toast(
                Adw.Toast.new("Checked in for tonight's Launch Window"))
        else:
            self.ticket_label.set_text("")
        self._update_check_in_sensitivity()

    # ---- lottery ----------------------------------------------------------

    def _refresh_lottery(self) -> None:
        """Rebuild the pool and last-result labels from the backend."""
        pool = self.backend.lottery_pool()
        self.pool_label.set_text(f"Pool: {format_amount(pool, KITTY)} KITTY")
        self.result_label.set_text(self._last_result)

    def refresh(self) -> None:
        """Rebuild labels and countdown (called on page switch)."""
        self._refresh_lottery()
        self._update_countdown()
        self._update_check_in_sensitivity()
