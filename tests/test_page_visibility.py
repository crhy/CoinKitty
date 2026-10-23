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


class PageVisibilityTest(unittest.TestCase):
    def setUpClass():
        if not Gtk.init_check():
            raise unittest.SkipTest("GTK init unavailable")
        Adw.init()

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="coinkitty-visibility-")
        self.backend = DemoBackend.create(self.tmpdir + "/demo-wallet.json",
                                          random.Random(0))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def present(self, window):
        """Lay the window out: present it, then pump the main context (bounded)."""
        window.content_stack.set_transition_duration(0)
        window.present()
        ctx = GLib.MainContext.default()
        for _ in range(200):
            n = 0
            while ctx.iteration(False):
                n += 1
                if n >= 1000:
                    break

    def assert_on_screen(self, window, widget):
        """Assert a widget is really drawn inside the window's bounds."""
        ok, rect = widget.compute_bounds(window)
        self.assertTrue(ok)
        self.assertGreater(rect.get_height(), 0)
        self.assertLessEqual(rect.get_y() + rect.get_height(),
                             window.get_height())
        node = widget
        steps = 0
        while node is not None and steps < 100:
            if node is window:
                break
            if isinstance(node, Gtk.ScrolledWindow):
                self.assertGreaterEqual(node.get_height(), 300)
            node = node.get_parent()
            steps += 1

    def test_send_pick(self):
        window = WalletWindow(None, self.backend)
        window.show_page("send")
        self.present(window)
        send = window._pages["send"]
        self.assert_on_screen(window, send.contact_list)
        self.assert_on_screen(window, send.luck_button)

    def test_send_amount(self):
        window = WalletWindow(None, self.backend)
        window.show_page("send")
        julie = next(c for c in self.backend.contacts() if c.name == "Julie")
        window._pages["send"].start_with_contact(julie.id)
        self.present(window)
        send = window._pages["send"]
        self.assert_on_screen(window, send.amount_entry)
        self.assert_on_screen(window, send.send_button)

    def test_rain(self):
        window = WalletWindow(None, self.backend)
        window.show_page("rain")
        self.present(window)
        rain = window._pages["rain"]
        self.assert_on_screen(window, rain.group_list)
        self.assert_on_screen(window, rain.rain_button)

    def test_contacts(self):
        window = WalletWindow(None, self.backend)
        window.show_page("contacts")
        self.present(window)
        contacts = window._pages["contacts"]
        self.assert_on_screen(window, contacts.contact_list)
        self.assert_on_screen(window, contacts.add_button)

    def test_wallet(self):
        window = WalletWindow(None, self.backend)
        window.show_page("wallet")
        self.present(window)
        wallet = window._pages["wallet"]
        self.assert_on_screen(window, wallet.asset_list)
        self.assert_on_screen(window, wallet.copy_button)

    def test_home(self):
        window = WalletWindow(None, self.backend)
        window.show_page("home")
        self.present(window)
        home = window._pages["home"]
        self.assert_on_screen(window, home.sun_button)
        self.assert_on_screen(window, home.launch_button)

    def test_vault(self):
        window = WalletWindow(None, self.backend)
        self.backend.create_vault("KITTY", 1000, 4_000_000_000)
        window.show_page("vault")
        self.present(window)
        vault = window._pages["vault"]
        self.assert_on_screen(window, vault.vault_list)
        self.assert_on_screen(window, vault.lock_button)

    def test_launch_window(self):
        window = WalletWindow(None, self.backend)
        window.show_page("launch-window")
        self.present(window)
        launch = window._pages["launch-window"]
        self.assert_on_screen(window, launch.countdown_label)
        self.assert_on_screen(window, launch.check_in_button)


if __name__ == "__main__":
    unittest.main()
