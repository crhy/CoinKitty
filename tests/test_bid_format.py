import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

import random
import shutil
import tempfile
import unittest

from coinkitty_wallet.demo_backend import DemoBackend
from coinkitty_wallet.models import Bid
from coinkitty_wallet.ui.window import WalletWindow
from coinkitty_wallet.ui.bounty_card import BountyCard

from tests.helpers import find_all

BID = 9_026_221_997_261_515_336_958_808


class BidFormatTest(unittest.TestCase):
    def setUpClass():
        if not Gtk.init_check():
            raise unittest.SkipTest("GTK init unavailable")
        Adw.init()

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="coinkitty-bidfmt-")
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

    def test_card_subtitle_truncates_to_eight_decimals(self):
        self.window.show_page("earn")
        self.present()

        bounty = self.backend._require_bounty("seed-shed")
        bounty.bids.append(
            Bid(id="fmt-bid", bounty_id="seed-shed", bidder="Formatter",
                price=BID, reputation=42)
        )
        self.window._pages["earn"].refresh()
        self.window._pages["earn"]._bid_buttons["seed-shed"].emit("clicked")
        self.present()

        card = self.window._bounty_card
        self.assertIsNotNone(card)
        self.assertIsInstance(card, BountyCard)
        self.assertTrue(card.get_mapped())

        rows = find_all(card.bid_list, Adw.ActionRow)
        subtitles = [row.get_subtitle() for row in rows]
        self.assertTrue(any(s.startswith("9.02622199 KITTY") for s in subtitles))
        self.assertFalse(any("9.026221997261515336958808" in s for s in subtitles))

    def test_demo_bids_are_whole_cents(self):
        bids = self.backend.place_demo_bids("seed-shed", random.Random(2))
        self.assertEqual(len(bids), 3)
        for bid in bids:
            self.assertEqual(bid.price % 10**22, 0)


if __name__ == "__main__":
    unittest.main()
