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


class BountyPagesTest(unittest.TestCase):
    def setUpClass():
        if not Gtk.init_check():
            raise unittest.SkipTest("GTK init unavailable")
        Adw.init()

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="coinkitty-bounty-")
        self.backend = DemoBackend.create(
            self.tmpdir + "/demo-wallet.json", random.Random(0)
        )
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

    def _rows(self, list_box):
        return find_all(list_box, Adw.ActionRow)

    def test_earn_lists_open_bounties(self):
        self.window.show_page("earn")
        self.present()
        earn = self.window._pages["earn"]
        rows = self._rows(earn.bounty_list)
        self.assertEqual(len(rows), 5)

    def test_earn_search_filters(self):
        self.window.show_page("earn")
        self.window._pages["earn"].search_entry.set_text("smoothie")
        self.present()
        earn = self.window._pages["earn"]
        rows = self._rows(earn.bounty_list)
        self.assertEqual(len(rows), 1)

    def test_earn_visibility(self):
        self.window.show_page("earn")
        self.present()
        earn = self.window._pages["earn"]
        self.assert_on_screen(earn.search_entry)
        self.assert_on_screen(earn.bounty_list)

    def test_launch_post_and_fund(self):
        self.window.show_page("launch")
        self.present()
        launch = self.window._pages["launch"]
        self.assertEqual(len(self._rows(launch.bounty_list)), 0)

        before = self.backend.balance("KITTY")
        launch.title_entry.set_text("Fix a bike")
        launch.desc_entry.set_text("Patch and true a wheel.")
        launch.price_entry.set_text("2")
        launch.location_entry.set_text("Garage")
        launch.dropdown.set_selected(0)

        launch.post_button.emit("clicked")
        self.assertIsNotNone(launch.confirm_dialog)
        launch._on_post_response(launch.confirm_dialog, "confirm")

        price = 2 * 10**24
        self.assertEqual(self.backend.balance("KITTY"), before - price)
        rows = self._rows(launch.bounty_list)
        self.assertEqual(len(rows), 1)

    def test_launch_visibility(self):
        self.window.show_page("launch")
        self.present()
        launch = self.window._pages["launch"]
        self.assert_on_screen(launch.title_entry)
        self.assert_on_screen(launch.post_button)

    def _card_for(self, bounty):
        """Build a BountyCard for ``bounty`` (the same object the backend holds)."""
        return BountyCard(self.backend, bounty)

    def test_earn_row_opens_card(self):
        self.window.show_page("earn")
        self.present()
        earn = self.window._pages["earn"]
        bounty_id = next(iter(earn._bid_buttons))
        earn._bid_buttons[bounty_id].emit("clicked")
        self.assertIsNotNone(self.window._bounty_card)
        self.assertIsInstance(self.window._bounty_card, BountyCard)

    def test_card_places_bid(self):
        seeded = next(b for b in self.backend.bounties()
                      if b.poster != self.backend.address() and b.status == "open")
        card = self._card_for(seeded)
        card.bid_price_entry.set_text("1.5")
        card.bid_note_entry.set_text("I can patch it.")
        card.place_bid_button.emit("clicked")
        self.assertEqual(len(seeded.bids), 1)
        self.assertEqual(seeded.bids[0].bidder, self.backend.address())
        self.assertEqual(seeded.bids[0].price, 15 * 10**23)

    def test_poster_accept_deliver_release(self):
        bounty = self.backend.post_bounty(
            "Fix a bike", "Patch and true a wheel.", "Repairs", "Garage",
            10 * 10**24,
        )
        self.backend.fund(bounty.id)
        bids = self.backend.place_demo_bids(bounty.id, random.Random(7))
        card = self._card_for(bounty)
        self.assertTrue(card._poster)

        before = self.backend.balance("KITTY")
        escrow_before = bounty.escrow
        chosen = bids[0]
        card._accept_buttons[chosen.id].emit("clicked")
        self.assertEqual(bounty.status, "assigned")
        card.deliver_button.emit("clicked")
        self.assertEqual(bounty.status, "delivered")
        card.release_button.emit("clicked")
        paid, refunded = card._last_release
        self.assertEqual(paid + refunded, escrow_before)
        self.assertEqual(paid, chosen.price)
        self.assertEqual(self.backend.balance("KITTY"), before + escrow_before - paid)

    def test_hammer_splits_escrow(self):
        bounty = self.backend.post_bounty(
            "Fix a bike", "Patch and true a wheel.", "Repairs", "Garage",
            10 * 10**24,
        )
        self.backend.fund(bounty.id)
        card = self._card_for(bounty)
        self.assertTrue(card._poster)

        escrow_before = bounty.escrow
        child_price = 4 * 10**24
        card.hammer_title_entry.set_text("True the wheel")
        card.hammer_price_entry.set_text("4")
        card.hammer_button.emit("clicked")
        self.assertEqual(bounty.escrow, escrow_before - child_price)
        child = next(b for b in self.backend.bounties() if b.parent_id == bounty.id)
        self.assertEqual(child.status, "funded")
        self.assertEqual(child.escrow, child_price)

    def test_cancel_refunds(self):
        bounty = self.backend.post_bounty(
            "Fix a bike", "Patch and true a wheel.", "Repairs", "Garage",
            10 * 10**24,
        )
        self.backend.fund(bounty.id)
        card = self._card_for(bounty)
        self.assertTrue(card._poster)

        before = self.backend.balance("KITTY")
        escrow_before = bounty.escrow
        card.cancel_button.emit("clicked")
        self.assertIsNotNone(card.confirm_dialog)
        card._on_cancel_response(card.confirm_dialog, "confirm")
        self.assertEqual(bounty.status, "cancelled")
        self.assertEqual(self.backend.balance("KITTY"), before + escrow_before)

    def assert_on_screen(self, widget):
        ok, rect = widget.compute_bounds(self.window)
        self.assertTrue(ok)
        self.assertGreater(rect.get_height(), 0)
        self.assertLessEqual(rect.get_y() + rect.get_height(),
                             self.window.get_height())
        node = widget
        steps = 0
        while node is not None and steps < 100:
            if node is self.window:
                break
            if isinstance(node, Gtk.ScrolledWindow):
                self.assertGreaterEqual(node.get_height(), 300)
            node = node.get_parent()
            steps += 1


if __name__ == "__main__":
    unittest.main()
