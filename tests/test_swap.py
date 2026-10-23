"""Tests for the simulated swap: order book, offers, states, backend move, UI."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

import random
import unittest

from coinkitty_wallet.demo_backend import DemoBackend
from coinkitty_wallet.units import ASSETS, BTC, KITTY, KITOSHI_PER_KITTY
from coinkitty_wallet.ui.window import WalletWindow
from coinkitty_wallet.ui.swap_page import NOTE_TEXT
from coinkitty_wallet.swap import (
    DEMO_RATE,
    STEPS,
    Offer,
    best_offer,
    demo_order_book,
    quote,
    SimulatedSwap,
)


class SwapLogicTest(unittest.TestCase):
    def test_order_book_within_five_percent(self):
        book = demo_order_book(random.Random(1))
        self.assertEqual(len(book), 4)
        low = DEMO_RATE * 95 // 100
        high = DEMO_RATE * 105 // 100
        for offer in book:
            self.assertGreaterEqual(offer.rate_kitoshi_per_sat, low)
            self.assertLessEqual(offer.rate_kitoshi_per_sat, high)
            self.assertTrue(offer.maker.startswith("Kitty-"))

    def test_best_offer_picks_best_rate(self):
        book = [
            Offer(id="a", sell_asset="BTC", buy_asset="KITTY",
                  rate_kitoshi_per_sat=5 * 10**20, max_sats=10**6, maker="Kitty-aaaa"),
            Offer(id="b", sell_asset="BTC", buy_asset="KITTY",
                  rate_kitoshi_per_sat=6 * 10**20, max_sats=10**6, maker="Kitty-bbbb"),
        ]
        self.assertEqual(best_offer(book, "BTC", 1000).id, "b")
        book2 = [
            Offer(id="c", sell_asset="KITTY", buy_asset="BTC",
                  rate_kitoshi_per_sat=5 * 10**20, max_sats=10**6, maker="Kitty-cccc"),
            Offer(id="d", sell_asset="KITTY", buy_asset="BTC",
                  rate_kitoshi_per_sat=4 * 10**20, max_sats=10**6, maker="Kitty-dddd"),
        ]
        self.assertEqual(best_offer(book2, "KITTY", 10**24).id, "d")

    def test_quote_integer_math_both_ways(self):
        btc_offer = Offer(id="x", sell_asset="BTC", buy_asset="KITTY",
                          rate_kitoshi_per_sat=5 * 10**20, max_sats=10**6, maker="Kitty-xxxx")
        self.assertEqual(quote(btc_offer, "BTC", 1000), 1000 * 5 * 10**20)
        kitty_offer = Offer(id="y", sell_asset="KITTY", buy_asset="BTC",
                            rate_kitoshi_per_sat=5 * 10**20, max_sats=10**6, maker="Kitty-yyyy")
        self.assertEqual(quote(kitty_offer, "KITTY", 10**24), 10**24 // (5 * 10**20))

    def test_simulated_swap_states(self):
        offer = Offer(id="s", sell_asset="BTC", buy_asset="KITTY",
                      rate_kitoshi_per_sat=5 * 10**20, max_sats=10**6, maker="Kitty-ssss")
        swap = SimulatedSwap(offer, "BTC", 1000, 5 * 10**23, 0)
        for t, expected in ((0, 0), (3, 1), (6, 2), (9, 3), (12, 4), (100, 4)):
            self.assertEqual(swap.state(t), STEPS[expected])

    def test_fail_refunds(self):
        offer = Offer(id="s", sell_asset="BTC", buy_asset="KITTY",
                      rate_kitoshi_per_sat=5 * 10**20, max_sats=10**6, maker="Kitty-ssss")
        swap = SimulatedSwap(offer, "BTC", 1000, 5 * 10**23, 0)
        swap.fail()
        self.assertEqual(swap.state(0), "Refunding")
        self.assertEqual(swap.state(24 * 3600 - 1), "Refunding")
        self.assertEqual(swap.state(24 * 3600), "Refunded")
        self.assertEqual(swap.refund_countdown(0), 24 * 3600)
        self.assertEqual(swap.refund_countdown(24 * 3600), 0)

    def test_state_accepts_float_clock(self):
        offer = Offer(id="f", sell_asset="BTC", buy_asset="KITTY",
                      rate_kitoshi_per_sat=5 * 10**20, max_sats=10**6, maker="Kitty-ffff")
        swap = SimulatedSwap(offer, "BTC", 1000, 5 * 10**23, 0)
        self.assertEqual(swap.state(1003.5), "Done")

    def test_apply_swap_all_or_nothing(self):
        backend = DemoBackend.create("/tmp/swap-test.json", random.Random(2))
        start = backend.balance("BTC")
        with self.assertRaises(ValueError):
            backend.apply_swap("BTC", start + 1, "KITTY", 1000)
        self.assertEqual(backend.balance("BTC"), start)
        with self.assertRaises(ValueError):
            backend.apply_swap("BTC", 0, "KITTY", 1000)
        with self.assertRaises(ValueError):
            backend.apply_swap("BTC", True, "KITTY", 1000)
        out, in_txn = backend.apply_swap("BTC", 1000, "KITTY", 5 * 10**23)
        self.assertEqual(backend.balance("BTC"), start - 1000)
        self.assertEqual(out.kind, "send")
        self.assertEqual(in_txn.kind, "receive")
        self.assertEqual(out.counterparty, "Simulated swap")


class SwapUiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not Gtk.init_check():
            raise unittest.SkipTest("GTK init unavailable")
        Adw.init()

    def present(self, window):
        window.content_stack.set_transition_duration(0)
        window.present()
        ctx = GLib.MainContext.default()
        for _ in range(200):
            n = 0
            while ctx.iteration(False):
                n += 1
                if n >= 1000:
                    break

    def test_swap_applies_only_after_done(self):
        backend = DemoBackend.create("/tmp/swap-ui.json", random.Random(3))
        window = WalletWindow(None, backend)
        window.show_page("swap")
        self.present(window)
        swap = window._pages["swap"]
        holder = {"t": 0}
        swap.clock = lambda: holder["t"]
        swap._asset_code = "BTC"
        swap.amount_entry.set_text("0.0001")
        swap._update_form()
        self.assertTrue(swap.swap_button.get_sensitive())
        swap._on_swap_clicked(swap.swap_button)
        holder["t"] = 3
        swap._tick()
        self.assertEqual(backend.balance("BTC"), 150_000)
        holder["t"] = 12
        swap._tick()
        self.assertEqual(backend.balance("BTC"), 150_000 - 10_000)

    def test_swap_float_clock(self):
        backend = DemoBackend.create("/tmp/swap-ui-float.json", random.Random(5))
        window = WalletWindow(None, backend)
        window.show_page("swap")
        self.present(window)
        swap = window._pages["swap"]
        holder = {"t": 1000.7}
        swap.clock = lambda: holder["t"]
        swap._asset_code = "BTC"
        swap.amount_entry.set_text("0.0001")
        swap._update_form()
        self.assertTrue(swap.swap_button.get_sensitive())
        swap._on_swap_clicked(swap.swap_button)
        holder["t"] = 1003.9
        swap._tick()
        self.assertEqual(backend.balance("BTC"), 150_000)
        holder["t"] = 1012.1
        swap._tick()
        self.assertEqual(backend.balance("BTC"), 150_000 - 10_000)

    def test_launch_window_float_clock(self):
        backend = DemoBackend.create("/tmp/launch-ui-float.json", random.Random(6))
        window = WalletWindow(None, backend)
        window.show_page("launch-window")
        self.present(window)
        launch = window._pages["launch-window"]
        launch.clock = lambda: 1000.7
        launch._update_countdown()
        self.assertTrue(launch.countdown_label.get_text())

    def test_vault_float_clock(self):
        backend = DemoBackend.create("/tmp/vault-ui-float.json", random.Random(7))
        backend.create_vault("KITTY", 1000, 4_000_000_000)
        backend.clock = lambda: 1000.7
        window = WalletWindow(None, backend)
        window.show_page("vault")
        self.present(window)
        vault_page = window._pages["vault"]
        vault_page._refresh_vault_rows()
        self.assertIsNotNone(vault_page.vault_list.get_first_child())

    def test_over_balance_insensitive(self):
        backend = DemoBackend.create("/tmp/swap-ui2.json", random.Random(4))
        window = WalletWindow(None, backend)
        window.show_page("swap")
        self.present(window)
        swap = window._pages["swap"]
        swap._asset_code = "BTC"
        swap.amount_entry.set_text("0.002")
        swap._update_form()
        self.assertFalse(swap.swap_button.get_sensitive())

    def _pump(self):
        ctx = GLib.MainContext.default()
        for _ in range(50):
            n = 0
            while ctx.iteration(False):
                n += 1
                if n >= 1000:
                    break

    def test_amount_signal_updates_form(self):
        backend = DemoBackend.create("/tmp/swap-ui-signal.json", random.Random(11))
        window = WalletWindow(None, backend)
        window.show_page("swap")
        self.present(window)
        page = window._pages["swap"]
        page.amount_entry.set_text("2")
        self._pump()
        self.assertTrue(page.summary_label.get_text().startswith("You receive about"))
        self.assertTrue(page.swap_button.get_sensitive())
        page.amount_entry.set_text("abc")
        self._pump()
        self.assertFalse(page.swap_button.get_sensitive())

    def test_step_icons_one_stack_each(self):
        backend = DemoBackend.create("/tmp/swap-ui-icons.json", random.Random(12))
        window = WalletWindow(None, backend)
        window.show_page("swap")
        self.present(window)
        page = window._pages["swap"]
        page._asset_code = "BTC"
        page.amount_entry.set_text("0.0001")
        self._pump()
        page._on_swap_clicked(page.swap_button)
        started = page._swap.started_at
        holder = {"t": float(started)}
        page.clock = lambda: holder["t"]
        for _ in range(20):
            holder["t"] += 0.325
            page._tick()
        self.assertAlmostEqual(holder["t"], float(started) + 6.5, places=3)
        names = []
        for row in page._step_rows:
            stacks = 0
            stack = None

            def descend(widget, depth):
                nonlocal stacks, stack
                if depth > 4:
                    return
                child = widget.get_first_child()
                n = 0
                while child is not None:
                    nxt = child.get_next_sibling()
                    if isinstance(child, Gtk.Stack):
                        stacks += 1
                        stack = child
                    descend(child, depth + 1)
                    child = nxt
                    n += 1
                    if n >= 20:
                        break

            descend(row, 0)
            self.assertEqual(stacks, 1)
            names.append(stack.get_visible_child_name())
        self.assertEqual(names, ["done", "done", "current", "todo", "todo"])

    def test_progress_button_visibility(self):
        backend = DemoBackend.create("/tmp/swap-ui-vis.json", random.Random(13))
        window = WalletWindow(None, backend)
        window.show_page("swap")
        self.present(window)
        page = window._pages["swap"]
        page._asset_code = "BTC"
        page.amount_entry.set_text("0.0001")
        self._pump()
        page._on_swap_clicked(page.swap_button)
        started = page._swap.started_at
        holder = {"t": float(started)}
        page.clock = lambda: holder["t"]
        self.assertFalse(page.done_button.get_visible())
        self.assertTrue(page.fail_button.get_visible())
        holder["t"] = float(started + 12)
        page._tick()
        self.assertTrue(page.done_button.get_visible())
        self.assertFalse(page.fail_button.get_visible())

    def test_done_shows_check_on_every_step(self):
        backend = DemoBackend.create("/tmp/swap-ui-done.json", random.Random(14))
        window = WalletWindow(None, backend)
        window.show_page("swap")
        self.present(window)
        page = window._pages["swap"]
        page._asset_code = "BTC"
        page.amount_entry.set_text("0.0001")
        self._pump()
        page._on_swap_clicked(page.swap_button)
        started = page._swap.started_at
        holder = {"t": float(started)}
        page.clock = lambda: holder["t"]
        holder["t"] = float(started + 12)
        page._tick()
        for stack, _spinner in page.step_icons:
            self.assertEqual(stack.get_visible_child_name(), "done")

    def test_progress_shows_simulated_notice(self):
        backend = DemoBackend.create("/tmp/swap-ui-notice.json", random.Random(15))
        window = WalletWindow(None, backend)
        window.show_page("swap")
        self.present(window)
        page = window._pages["swap"]
        page._asset_code = "BTC"
        page.amount_entry.set_text("0.0001")
        self._pump()
        page._on_swap_clicked(page.swap_button)

        def find_notice(widget, depth):
            if depth > 6:
                return False
            child = widget.get_first_child()
            n = 0
            while child is not None:
                nxt = child.get_next_sibling()
                if isinstance(child, Gtk.Label) and child.get_text() == NOTE_TEXT:
                    return True
                if find_notice(child, depth + 1):
                    return True
                child = nxt
                n += 1
                if n >= 50:
                    break
            return False

        self.assertTrue(find_notice(page.progress_box, 0))


if __name__ == "__main__":
    unittest.main()
