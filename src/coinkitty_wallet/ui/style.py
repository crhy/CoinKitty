"""Application CSS for the CoinKitty UI: orb buttons and asset badges.

The stylesheet is loaded at most once per process; :func:`install_css` guards
against re-adding it to the display.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk

CSS_TEXT = """
.ck-orb {
  border-radius: 9999px;
  min-width: 160px;
  min-height: 160px;
  padding: 0;
}
.ck-sun {
  background-color: #f5c442;
  color: #1a1a1a;
}
.ck-earth {
  background-color: #2b6cb0;
  color: #ffffff;
}
.ck-moon {
  background-color: #d9dce3;
  color: #1a1a1a;
}
.ck-badge {
  border-radius: 9999px;
  min-width: 32px;
  min-height: 32px;
  padding: 0;
  font-weight: bold;
  background-color: #f5c442;
  color: #1a1a1a;
}
"""

_installed = False


def install_css() -> None:
    """Add :data:`CSS_TEXT` to the default display, once per process."""
    global _installed
    if _installed:
        return
    provider = Gtk.CssProvider()
    provider.load_from_string(CSS_TEXT)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
    _installed = True
