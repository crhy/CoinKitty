import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

import random
import shutil
import tempfile
import unittest

from coinkitty_wallet.pages import PAGES
from coinkitty_wallet.demo_backend import DemoBackend
from coinkitty_wallet.ui.window import WalletWindow


class WindowTest(unittest.TestCase):
    def setUpClass():
        if not Gtk.init_check():
            raise unittest.SkipTest("GTK init unavailable")
        Adw.init()

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="coinkitty-window-")
        backend = DemoBackend.create(self.tmpdir + "/demo-wallet.json", random.Random(0))
        self.window = WalletWindow(None, backend)
        ctx = GLib.MainContext.default()
        for _ in range(50):
            n = 0
            while ctx.iteration(False):
                n += 1
                if n >= 1000:
                    break

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_stack_children(self):
        stack = self.window.content_stack
        count = 0
        child = stack.get_first_child()
        while child is not None:
            count += 1
            child = child.get_next_sibling()
        self.assertEqual(count, len(PAGES))
        for page_id, _title, _icon in PAGES:
            stack.set_visible_child_name(page_id)
            self.assertEqual(stack.get_visible_child_name(), page_id)

    def test_show_page(self):
        self.window.show_page("rain")
        self.assertEqual(self.window.current_page(), "rain")
        self.assertEqual(self.window.title_widget.get_subtitle(), "Rain")
        with self.assertRaises(KeyError):
            self.window.show_page("does-not-exist")

    def test_bottom_earn(self):
        self.window.bottom_buttons["earn"].emit("clicked")
        self.assertEqual(self.window.current_page(), "earn")

    def test_favorites_rows(self):
        rows = 0
        child = self.window.favorites_list.get_first_child()
        while child is not None:
            rows += 1
            child = child.get_next_sibling()
        self.assertEqual(rows, 3)

    def test_banner(self):
        self.assertTrue(self.window.banner.get_revealed())
        self.assertIn("Demo coins", self.window.banner.get_title())


if __name__ == "__main__":
    unittest.main()
