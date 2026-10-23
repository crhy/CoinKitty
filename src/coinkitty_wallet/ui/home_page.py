"""The Home screen: three orb buttons (Sun, Earth, Moon), a day counter, Launch.

Plain GTK only; all money data comes from the injected backend, and page
switching is delegated to the ``on_open_page`` callback supplied by the window.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..units import format_amount, KITTY, BTC
from ..demo_backend import DemoBackend  # type: ignore  # only for the type hint


class HomePage(Gtk.Box):
    """Outer box holding a vertically-centred page box."""

    def __init__(self, backend, on_open_page):
        super().__init__()
        self._backend = backend
        self._on_open_page = on_open_page

        self._page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self._page.set_valign(Gtk.Align.CENTER)
        self._page.set_margin_top(24)
        self._page.set_margin_bottom(24)
        self._page.set_margin_start(24)
        self._page.set_margin_end(24)
        self.append(self._page)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        row.set_homogeneous(True)
        row.set_halign(Gtk.Align.CENTER)

        self.sun_button, self.sun_value_label = self._make_orb(
            ("ck-orb", "ck-sun"), ("Holdings", self._sun_text())
        )
        self.sun_button.connect("clicked", lambda *_: self._on_open_page("wallet"))
        row.append(self.sun_button)

        self.earth_button, self.earth_value_label = self._make_orb(
            ("ck-orb", "ck-earth"), ("Today", self._earth_text())
        )
        self.earth_button.connect("clicked", lambda *_: self._on_open_page("wallet"))
        row.append(self.earth_button)

        self.moon_button, _moon_label = self._make_orb(
            ("ck-orb", "ck-moon"), ("Goal", "Set a goal")
        )
        self.moon_button.connect("clicked", lambda *_: self._on_open_page("mission"))
        row.append(self.moon_button)

        self._page.append(row)

        self.day_label = Gtk.Label(label=self._day_text())
        self._page.append(self.day_label)

        self.launch_button = Gtk.Button(label="Launch")
        self.launch_button.add_css_class("suggested-action")
        self.launch_button.add_css_class("pill")
        self.launch_button.set_halign(Gtk.Align.CENTER)
        self.launch_button.set_size_request(200, -1)
        self.launch_button.connect("clicked", lambda *_: self._on_open_page("launch-window"))
        self._page.append(self.launch_button)

    # ---- orb builder ------------------------------------------------------

    def _make_orb(self, classes, texts):
        """Build one round orb button; return (button, last value label)."""
        button = Gtk.Button()
        for css in classes:
            button.add_css_class(css)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        value_label = None
        for text in texts:
            label = Gtk.Label(label=text)
            label.set_justify(Gtk.Justification.CENTER)
            box.append(label)
            value_label = label
        button.set_child(box)
        button.set_size_request(160, 160)
        button.set_halign(Gtk.Align.CENTER)
        button.set_valign(Gtk.Align.CENTER)
        return button, value_label

    # ---- text builders ----------------------------------------------------

    def _sun_text(self) -> str:
        kitty = format_amount(self._backend.balance("KITTY"), KITTY)
        btc = format_amount(self._backend.balance("BTC"), BTC)
        return f"{kitty} KITTY\n+ {btc} BTC"

    def _earth_text(self) -> str:
        earned = self._backend.earned_today("KITTY", self._backend.clock())
        return format_amount(earned, KITTY)

    def _day_text(self) -> str:
        days = self._backend.days_since_created(self._backend.clock())
        return f"Day {days}"

    def refresh(self) -> None:
        """Re-read the backend and update the value and day labels."""
        self.sun_value_label.set_label(self._sun_text())
        self.earth_value_label.set_label(self._earth_text())
        self.day_label.set_label(self._day_text())
