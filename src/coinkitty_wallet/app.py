"""The CoinKitty application entry point: an :class:`Adw.Application` that loads
the demo backend and presents the :class:`WalletWindow`."""

from __future__ import annotations

import os
import random
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib

from ..demo_backend import DemoBackend
from ..ui.window import WalletWindow

APPLICATION_ID = "io.github.crhy.CoinKittyWallet"


def wallet_path() -> str:
    """Absolute path of the demo wallet file inside the user data directory."""
    return GLib.get_user_data_dir() + "/coinkitty-wallet/demo-wallet.json"


class WalletApp(Adw.Application):
    """libadwaita application host for the CoinKitty wallet."""

    def __init__(self):
        super().__init__(application_id=APPLICATION_ID)

    def do_activate(self):
        """Load (or create) the demo backend, then present the window."""
        path = wallet_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            backend = DemoBackend.load(path)
        else:
            backend = DemoBackend.create(path, random.Random())
        self._window = WalletWindow(self, backend)
        self._window.present()


def main(argv=None) -> int:
    """Run the application; returns the process exit code."""
    return WalletApp().run(argv or sys.argv)
