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
