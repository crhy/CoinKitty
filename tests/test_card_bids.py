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


class CardBidsTest(unittest.TestCase):
    def setUpClass():
        if not Gtk.init_check():
            raise unittest.SkipTest("GTK init unavailable")
        Adw.init()

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="coinkitty-bids-")
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

    def test_earn_bid_card_shows_three_bids(self):
        self.window.show_page("earn")
        self.present()

        self.backend.place_demo_bids("seed-shed", random.Random(2))
        self.window._pages["earn"].refresh()
        self.window._pages["earn"]._bid_buttons["seed-shed"].emit("clicked")
        self.present()

        card = self.window._bounty_card
        self.assertIsNotNone(card)
        self.assertIsInstance(card, BountyCard)

        rows = find_all(card.bid_list, Adw.ActionRow)
        self.assertEqual(len(rows), 3)

        groups = find_all(card, Adw.PreferencesGroup)
        titles = [g.get_title() for g in groups]
        self.assertIn("Lead kitty", titles)


if __name__ == "__main__":
    unittest.main()
