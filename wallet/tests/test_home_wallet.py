import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

import random
import shutil
import tempfile
import unittest

from coinkitty_wallet.demo_backend import DemoBackend
from coinkitty_wallet.demo_prices import value_in_sats, portfolio_shares, percent_shares
from coinkitty_wallet.ui.home_page import HomePage
from coinkitty_wallet.ui.wallet_page import WalletPage
from coinkitty_wallet.ui.window import WalletWindow

from tests.helpers import find_all


def is_inside(widget, ancestor) -> bool:
    """True if ``widget`` is a descendant of ``ancestor`` (walk up, bounded)."""
    steps = 0
    current = widget.get_parent()
    while current is not None and steps < 100:
        if current is ancestor:
            return True
        current = current.get_parent()
        steps += 1
    return False


class HomeWalletTest(unittest.TestCase):
    def setUpClass():
        if not Gtk.init_check():
            raise unittest.SkipTest("GTK init unavailable")
        Adw.init()

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="coinkitty-home-")
        backend = DemoBackend.create(self.tmpdir + "/demo-wallet.json", random.Random(0))
        self.backend = backend
        self.open_calls: list[str] = []
        self.home = HomePage(backend, self._record_open)
        self.wallet = WalletPage(backend)
        ctx = GLib.MainContext.default()
        for _ in range(50):
            n = 0
            while ctx.iteration(False):
                n += 1
                if n >= 1000:
                    break

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _record_open(self, page_id):
        self.open_calls.append(page_id)

    def _asset_rows(self):
        rows = []
        child = self.wallet.asset_list.get_first_child()
        while child is not None:
            rows.append(child)
            child = child.get_next_sibling()
        return rows

    def test_sun_value(self):
        self.assertIn("25", self.home.sun_value_label.get_label())

    def test_day_label(self):
        self.assertEqual(self.home.day_label.get_label(), "Day 1")

    def test_moon_opens_mission(self):
        self.home.moon_button.emit("clicked")
        self.assertEqual(self.open_calls, ["mission"])

    def test_wallet_two_rows(self):
        self.assertEqual(len(self._asset_rows()), 2)

    def test_select_btc(self):
        btc_row = next(row for row in self._asset_rows() if row.get_subtitle() == "BTC")
        self.wallet.asset_list.select_row(btc_row)
        self.assertEqual(self.wallet.selected_asset(), "BTC")
        self.assertNotIn(self.backend.address(), self.wallet.address_label.get_label())
        self.assertEqual(
            self.wallet.address_label.get_label(),
            "Bitcoin receiving arrives with atomic swaps",
        )

    def test_copy_button(self):
        self.wallet.copy_button.emit("clicked")
        self.assertEqual(self.wallet.copy_button.get_label(), "Copied")

    def test_widgets_inside(self):
        self.assertTrue(is_inside(self.wallet.asset_list, self.wallet))
        self.assertTrue(is_inside(self.wallet.donut, self.wallet))
        self.assertTrue(is_inside(self.wallet.address_label, self.wallet))
        self.assertTrue(is_inside(self.wallet.copy_button, self.wallet))
        self.assertTrue(is_inside(self.home.sun_button, self.home))
        self.assertTrue(is_inside(self.home.earth_button, self.home))
        self.assertTrue(is_inside(self.home.moon_button, self.home))

    def test_fresh_wallet(self):
        self.assertEqual(self.wallet.selected_asset(), "KITTY")
        self.assertIn("KITTY", self.wallet._receive_heading.get_label())
        self.assertTrue(self.wallet.address_label.get_label().startswith("kitty1"))
        self.assertTrue(self.wallet.copy_button.get_visible())

    def test_btc_hides_copy(self):
        btc_row = next(row for row in self._asset_rows() if row.get_subtitle() == "BTC")
        self.wallet.asset_list.select_row(btc_row)
        self.assertFalse(self.wallet.copy_button.get_visible())
        self.assertIn("BTC", self.wallet._receive_heading.get_label())

    def test_sun_text(self):
        sun = self.home.sun_value_label.get_label()
        self.assertIn("KITTY", sun)
        self.assertIn("0.0015", sun)

    def test_orb_geometry(self):
        window = WalletWindow(None, self.backend)
        window.present()
        ctx = GLib.MainContext.default()
        for _ in range(50):
            n = 0
            while ctx.iteration(False):
                n += 1
                if n >= 1000:
                    break
        home = window._pages["home"]
        for orb in (home.sun_button, home.earth_button, home.moon_button):
            self.assertEqual(orb.get_width(), orb.get_height())
        self.assertLess(home.launch_button.get_width(), 400)

    def test_badge_circles(self):
        window = WalletWindow(None, self.backend)
        window.show_page("wallet")
        window.present()
        ctx = GLib.MainContext.default()
        for _ in range(50):
            n = 0
            while ctx.iteration(False):
                n += 1
                if n >= 1000:
                    break
        wallet = window._pages["wallet"]
        badges = [
            w for w in find_all(wallet, Gtk.Label)
            if "ck-badge" in w.get_css_classes()
        ]
        self.assertGreaterEqual(len(badges), 2)
        for badge in badges:
            self.assertEqual(badge.get_width(), badge.get_height())


class DemoPricesTest(unittest.TestCase):
    def test_value_in_sats(self):
        self.assertEqual(value_in_sats("KITTY", 25 * 10**24), 50_000)
        self.assertEqual(value_in_sats("BTC", 150_000), 150_000)
        with self.assertRaises(ValueError):
            value_in_sats("XYZ", 1)

    def test_portfolio_shares(self):
        self.assertEqual(
            portfolio_shares({"KITTY": 25 * 10**24, "BTC": 150_000}),
            [("KITTY", 50_000), ("BTC", 150_000)],
        )
        self.assertEqual(portfolio_shares({"KITTY": 0, "BTC": 150_000}), [("BTC", 150_000)])

    def test_percent_shares(self):
        self.assertEqual(
            percent_shares([("KITTY", 50_000), ("BTC", 150_000)]),
            [("KITTY", 25), ("BTC", 75)],
        )
        self.assertEqual(percent_shares([]), [])
        thirds = percent_shares([("A", 1), ("B", 1), ("C", 1)])
        self.assertEqual(sum(p for _c, p in thirds), 100)
        self.assertEqual(thirds[0], ("A", 34))


if __name__ == "__main__":
    unittest.main()
