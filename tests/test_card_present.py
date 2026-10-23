import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

import random
import shutil
import tempfile
import unittest

from coinkitty_wallet.demo_backend import DemoBackend
from coinkitty_wallet.ui.window import WalletWindow
from coinkitty_wallet.ui.bounty_card import BountyCard

from tests.helpers import find_all


class CardPresentTest(unittest.TestCase):
    def setUpClass():
        if not Gtk.init_check():
            raise unittest.SkipTest("GTK init unavailable")
        Adw.init()

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="coinkitty-card-")
        self.backend = DemoBackend.create(self.tmpdir + "/demo-wallet.json", random.Random(0))
        self.window = WalletWindow(None, self.backend)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def present(self):
        """Lay the window out: present it, then pump the main context (bounded)."""
        self.window.content_stack.set_transition_duration(0)
        self.window.present()
        ctx = GLib.MainContext.default()
        for _ in range(200):
            n = 0
            while ctx.iteration(False):
                n += 1
                if n >= 1000:
                    break

    def _open_from_earn_bid(self):
        """Click the first Earn row's Bid button and return the opened card."""
        earn = self.window._pages["earn"]
        bounty_id = next(iter(earn._bid_buttons))
        earn._bid_buttons[bounty_id].emit("clicked")
        self.present()
        return self.window._bounty_card

    def test_earn_bid_presents_card(self):
        self.window.show_page("earn")
        self.present()
        card = self._open_from_earn_bid()
        self.assertIsNotNone(self.window._bounty_card)
        self.assertIsInstance(card, BountyCard)
        self.assertTrue(card.get_mapped())

    def test_launch_row_presents_card(self):
        self.window.show_page("launch")
        self.present()
        launch = self.window._pages["launch"]
        launch.title_entry.set_text("Fix a bike")
        launch.desc_entry.set_text("Patch and true a wheel.")
        launch.price_entry.set_text("2")
        launch.location_entry.set_text("Garage")
        launch.dropdown.set_selected(0)
        launch.post_button.emit("clicked")
        launch._on_post_response(launch.confirm_dialog, "confirm")
        self.present()

        rows = find_all(launch.bounty_list, Adw.ActionRow)
        self.assertEqual(len(rows), 1)
        launch._on_row_activated(launch.bounty_list, rows[0], True)
        self.present()

        self.assertIsNotNone(self.window._bounty_card)
        self.assertTrue(self.window._bounty_card.get_mapped())

    def test_close_then_open_another(self):
        self.window.show_page("earn")
        self.present()
        first = self._open_from_earn_bid()
        self.assertTrue(first.get_mapped())

        first.close()
        self.present()

        earn = self.window._pages["earn"]
        second_id = list(earn._bid_buttons)[1]
        earn._bid_buttons[second_id].emit("clicked")
        self.present()

        second = self.window._bounty_card
        self.assertIsNotNone(second)
        self.assertIsNot(second, first)
        self.assertTrue(second.get_mapped())


if __name__ == "__main__":
    unittest.main()
