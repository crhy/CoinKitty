import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

import random
import shutil
import tempfile
import unittest

from coinkitty_wallet.demo_backend import DemoBackend
from coinkitty_wallet.ui.send_page import SendPage
from coinkitty_wallet.units import ASSETS, format_amount


class SendTest(unittest.TestCase):
    def setUpClass():
        if not Gtk.init_check():
            raise unittest.SkipTest("GTK init unavailable")
        Adw.init()

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="coinkitty-send-")
        self.backend = DemoBackend.create(self.tmpdir + "/demo-wallet.json",
                                          random.Random(0))
        self.page = SendPage(self.backend, random.Random(1),
                             on_open_page=lambda pid: None)
        ctx = GLib.MainContext.default()
        for _ in range(50):
            n = 0
            while ctx.iteration(False):
                n += 1
                if n >= 1000:
                    break

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _julie_button(self):
        button = self.page.top_box.get_first_child()
        while button is not None:
            if button.get_label() == "Julie":
                return button
            button = button.get_next_sibling()
        raise AssertionError("Julie not in top contacts")

    def _kitty_balance(self) -> int:
        return self.backend.balance("KITTY")

    def test_pick_julie_goes_to_amount(self):
        self._julie_button().emit("clicked")
        self.assertEqual(self.page.stack.get_visible_child_name(), "amount")
        self.assertEqual(self.page.recipient_label.get_label(), "Julie")

    def test_send_reduces_balance(self):
        self._julie_button().emit("clicked")
        self.page.amount_entry.set_text("1.5")
        self.page.send_button.emit("clicked")
        expected = 25 * 10**24 - 15 * 10**23
        self.assertEqual(self._kitty_balance(), expected)
        self.assertEqual(self.page.stack.get_visible_child_name(), "pick")

    def test_invalid_amount_shows_error(self):
        self._julie_button().emit("clicked")
        self.page.amount_entry.set_text("abc")
        self.page.send_button.emit("clicked")
        self.assertTrue(self.page.error_label.get_visible())
        self.assertEqual(self._kitty_balance(), 25 * 10**24)

    def test_amount_above_balance_shows_error(self):
        self._julie_button().emit("clicked")
        self.page.amount_entry.set_text("999999")
        self.page.send_button.emit("clicked")
        self.assertTrue(self.page.error_label.get_visible())
        self.assertEqual(self._kitty_balance(), 25 * 10**24)

    def test_use_address_sensitivity(self):
        self.assertFalse(self.page.use_address_button.get_sensitive())
        self.page.address_entry.set_text("not-an-address")
        self.assertFalse(self.page.use_address_button.get_sensitive())
        valid = self.backend.contacts()[0].address
        self.page.address_entry.set_text(valid)
        self.assertTrue(self.page.use_address_button.get_sensitive())

    def test_luck_opens_dialog(self):
        self.page.luck_button.emit("clicked")
        self.assertIsNotNone(self.page.luck_dialog)
        self.page._on_luck_response(self.page.luck_dialog, "send")
        self.assertEqual(self.page.stack.get_visible_child_name(), "amount")

    def test_btc_send_shows_swap_message(self):
        self.page.asset_dropdown.set_selected(1)
        self.assertEqual(self.page._asset_code, "BTC")
        self._julie_button().emit("clicked")
        self.page.send_button.emit("clicked")
        self.assertIn("atomic swaps", self.page.error_label.get_label())
        self.assertEqual(self.backend.balance("BTC"), 150_000)


if __name__ == "__main__":
    unittest.main()
