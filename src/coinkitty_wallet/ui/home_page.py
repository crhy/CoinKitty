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
    """Vertical box holding the orb row, the day counter and the Launch button."""

    def __init__(self, backend, on_open_page):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._backend = backend
        self._on_open_page = on_open_page

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # ---- Sun: holdings -------------------------------------------------
        self.sun_button = Gtk.Button()
        self.sun_button.add_css_class("ck-orb")
        self.sun_button.add_css_class("ck-sun")
        sun_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sun_box.append(Gtk.Label(label="Holdings"))
        self.sun_value_label = Gtk.Label(label=self._sun_text())
        sun_box.append(self.sun_value_label)
        self.sun_button.set_child(sun_box)
        self.sun_button.connect("clicked", lambda *_: self._on_open_page("wallet"))
        row.append(self.sun_button)

        # ---- Earth: today's earnings --------------------------------------
        self.earth_button = Gtk.Button()
        self.earth_button.add_css_class("ck-orb")
        self.earth_button.add_css_class("ck-earth")
        earth_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        earth_box.append(Gtk.Label(label="Today"))
        self.earth_value_label = Gtk.Label(label=self._earth_text())
        earth_box.append(self.earth_value_label)
        self.earth_button.set_child(earth_box)
        self.earth_button.connect("clicked", lambda *_: self._on_open_page("wallet"))
        row.append(self.earth_button)

        # ---- Moon: mission goal -------------------------------------------
        self.moon_button = Gtk.Button()
        self.moon_button.add_css_class("ck-orb")
        self.moon_button.add_css_class("ck-moon")
        moon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        moon_box.append(Gtk.Label(label="Goal"))
        moon_box.append(Gtk.Label(label="Set a goal"))
        self.moon_button.set_child(moon_box)
        self.moon_button.connect("clicked", lambda *_: self._on_open_page("mission"))
        row.append(self.moon_button)

        self.append(row)

        # ---- Day counter ---------------------------------------------------
        self.day_label = Gtk.Label(label=self._day_text())
        self.append(self.day_label)

        # ---- Launch --------------------------------------------------------
        self.launch_button = Gtk.Button(label="Launch")
        self.launch_button.add_css_class("suggested-action")
        self.launch_button.add_css_class("pill")
        self.launch_button.connect("clicked", lambda *_: self._on_open_page("launch-window"))
        self.append(self.launch_button)

    # ---- text builders ----------------------------------------------------

    def _sun_text(self) -> str:
        kitty = format_amount(self._backend.balance("KITTY"), KITTY)
        btc_sats = self._backend.balance("BTC")
        return f"{kitty}\n+ {btc_sats} sats BTC"

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
