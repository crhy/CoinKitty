import random
import shutil
import tempfile
import time
import unittest

from coinkitty_wallet.demo_backend import DemoBackend
from coinkitty_wallet.models import Vault
from coinkitty_wallet.vaults import next_unlock, planned_steps, unlocked_amount

DAY = 86400


def ts(year, month, day, hour=0, minute=0, second=0):
    """Local-time unix seconds built from time.mktime (never the real clock)."""
    return int(time.mktime((year, month, day, hour, minute, second, 0, 0, -1)))


NOW = ts(2026, 1, 1, 12, 0, 0)


class VaultMathTest(unittest.TestCase):
    def test_all_at_once(self):
        unlock = NOW + 30 * DAY
        v = Vault(id="x", asset="KITTY", amount=1000, created_at=NOW,
                  unlock_at=unlock, step_percent=0, step_days=0)
        self.assertEqual(unlocked_amount(v, NOW), 0)
        self.assertEqual(unlocked_amount(v, unlock), 1000)
        self.assertEqual(unlocked_amount(v, unlock + DAY), 1000)
        self.assertEqual(next_unlock(v, NOW), (unlock, 1000))
        self.assertIsNone(next_unlock(v, unlock))

    def test_step_release(self):
        unlock = NOW + 30 * DAY
        v = Vault(id="x", asset="KITTY", amount=1000, created_at=NOW,
                  unlock_at=unlock, step_percent=25, step_days=30)
        self.assertEqual(unlocked_amount(v, NOW), 0)
        self.assertEqual(unlocked_amount(v, unlock), 250)
        self.assertEqual(unlocked_amount(v, unlock + 30 * DAY), 500)
        self.assertEqual(unlocked_amount(v, unlock + 60 * DAY), 750)
        self.assertEqual(unlocked_amount(v, unlock + 90 * DAY), 1000)
        self.assertEqual(unlocked_amount(v, unlock + 999 * DAY), 1000)
        self.assertEqual(next_unlock(v, NOW), (unlock, 250))
        self.assertEqual(next_unlock(v, unlock), (unlock + 30 * DAY, 250))
        self.assertIsNone(next_unlock(v, unlock + 90 * DAY))

    def test_remainder_on_last_step(self):
        unlock = NOW + 30 * DAY
        v = Vault(id="x", asset="KITTY", amount=1000, created_at=NOW,
                  unlock_at=unlock, step_percent=30, step_days=30)
        self.assertEqual(unlocked_amount(v, unlock), 300)
        self.assertEqual(unlocked_amount(v, unlock + 30 * DAY), 600)
        self.assertEqual(unlocked_amount(v, unlock + 60 * DAY), 900)
        self.assertEqual(unlocked_amount(v, unlock + 90 * DAY), 1000)
        self.assertEqual(next_unlock(v, unlock + 60 * DAY), (unlock + 90 * DAY, 100))

    def test_steps_over_months_sum_exactly(self):
        unlock = NOW + 30 * DAY
        v = Vault(id="x", asset="KITTY", amount=1000, created_at=NOW,
                  unlock_at=unlock, step_percent=10, step_days=30)
        total = 0
        for step in range(10):
            total = unlocked_amount(v, unlock + step * 30 * DAY)
        self.assertEqual(total, 1000)

    def test_three_kitoshis_fully_unlock_on_last_step(self):
        unlock = 1000
        v = Vault(id="tiny", asset="KITTY", amount=3, created_at=0,
                  unlock_at=unlock, step_percent=25, step_days=30)
        self.assertEqual(unlocked_amount(v, unlock), 0)
        self.assertEqual(unlocked_amount(v, unlock + 30 * DAY), 1)
        self.assertEqual(unlocked_amount(v, unlock + 60 * DAY), 2)
        self.assertEqual(unlocked_amount(v, unlock + 90 * DAY), 3)
        self.assertEqual(unlocked_amount(v, unlock + 999 * DAY), 3)
        self.assertIsNone(next_unlock(v, unlock + 90 * DAY))

    def test_kitty_plus_three_fully_unlock_on_last_step(self):
        unlock = 1000
        amount = 10 ** 24 + 3
        v = Vault(id="tiny-remainder", asset="KITTY", amount=amount, created_at=0,
                  unlock_at=unlock, step_percent=25, step_days=30)
        self.assertLess(unlocked_amount(v, unlock + 60 * DAY), amount)
        self.assertEqual(unlocked_amount(v, unlock + 90 * DAY), amount)
        self.assertEqual(unlocked_amount(v, unlock + 999 * DAY), amount)
        self.assertIsNone(next_unlock(v, unlock + 90 * DAY))

    def test_planned_steps_release_all_by_last_step(self):
        unlock = 1000
        for percent in (10, 25, 33, 50, 100):
            for amount in (1, 2, 3, 7, 10 ** 24, 10 ** 24 + 7):
                v = Vault(id="x", asset="KITTY", amount=amount, created_at=0,
                          unlock_at=unlock, step_percent=percent, step_days=30)
                planned = planned_steps(v)
                previous = 0
                for step in range(1, planned + 1):
                    now = unlock + (step - 1) * 30 * DAY
                    current = unlocked_amount(v, now)
                    self.assertLessEqual(previous, current)
                    self.assertLessEqual(current, amount)
                    if step == planned:
                        self.assertEqual(current, amount)
                    else:
                        self.assertLess(current, amount)
                    previous = current
                for step in range(planned, planned + 3):
                    now = unlock + (step - 1) * 30 * DAY
                    self.assertIsNone(next_unlock(v, now))


class BackendVaultTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="coinkitty-vault-")
        self.backend = DemoBackend.create(self.tmpdir + "/demo-wallet.json",
                                          random.Random(1))
        self.backend.clock = lambda: NOW

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_validation(self):
        b = self.backend
        with self.assertRaises(ValueError):
            b.create_vault("KITTY", 0, NOW + DAY)
        with self.assertRaises(ValueError):
            b.create_vault("KITTY", True, NOW + DAY)
        with self.assertRaises(ValueError):
            b.create_vault("KITTY", 10 ** 30, NOW + DAY)
        with self.assertRaises(ValueError):
            b.create_vault("KITTY", 100, NOW)
        with self.assertRaises(ValueError):
            b.create_vault("KITTY", 100, NOW + DAY, step_percent=101)
        with self.assertRaises(ValueError):
            b.create_vault("KITTY", 100, NOW + DAY, step_percent=10, step_days=0)
        self.assertEqual(b.balance("KITTY"), 25 * 10 ** 24)

    def test_create_moves_out_of_balance(self):
        b = self.backend
        vault = b.create_vault("KITTY", 10 * 10 ** 24, NOW + 30 * DAY,
                               step_percent=25, step_days=30)
        self.assertEqual(b.balance("KITTY"), 15 * 10 ** 24)
        self.assertEqual(len(b.vaults()), 1)
        self.assertEqual(vault.amount, 10 * 10 ** 24)

    def test_early_withdraw_moves_nothing(self):
        b = self.backend
        vault = b.create_vault("KITTY", 10 * 10 ** 24, NOW + 30 * DAY,
                               step_percent=25, step_days=30)
        moved = b.withdraw_vault(vault.id, NOW)
        self.assertEqual(moved, 0)
        self.assertEqual(b.balance("KITTY"), 15 * 10 ** 24)

    def test_withdraw_after_unlock(self):
        b = self.backend
        vault = b.create_vault("KITTY", 1000, NOW + 30 * DAY,
                               step_percent=25, step_days=30)
        moved = b.withdraw_vault(vault.id, NOW + 30 * DAY)
        self.assertEqual(moved, 250)
        self.assertEqual(b.balance("KITTY"), 25 * 10 ** 24 - 1000 + 250)
        again = b.withdraw_vault(vault.id, NOW + 30 * DAY)
        self.assertEqual(again, 0)

    def test_no_delete_or_early_withdraw(self):
        b = self.backend
        self.assertFalse(hasattr(b, "delete_vault"))
        self.assertFalse(hasattr(b, "unlock_vault"))


class LaunchWindowTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="coinkitty-launch-")
        self.backend = DemoBackend.create(self.tmpdir + "/demo-wallet.json",
                                          random.Random(2))
        self.backend.clock = lambda: NOW

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_window_bounds(self):
        now = ts(2026, 6, 1, 21, 5, 0)
        start, end = self.backend.launch_window(now)
        self.assertEqual(start, ts(2026, 6, 1, 21, 0, 0))
        self.assertEqual(end, ts(2026, 6, 1, 21, 15, 0))

    def test_window_rolls_to_next_day(self):
        now = ts(2026, 6, 1, 22, 0, 0)
        start, end = self.backend.launch_window(now)
        self.assertEqual(start, ts(2026, 6, 2, 21, 0, 0))
        self.assertEqual(end, ts(2026, 6, 2, 21, 15, 0))

    def test_check_in_inside_window(self):
        now = ts(2026, 6, 1, 21, 5, 0)
        self.assertTrue(self.backend.check_in(now))

    def test_check_in_outside_window_fails(self):
        now = ts(2026, 6, 1, 20, 0, 0)
        self.assertFalse(self.backend.check_in(now))

    def test_check_in_twice_same_night_fails(self):
        now = ts(2026, 6, 1, 21, 5, 0)
        self.assertTrue(self.backend.check_in(now))
        self.assertFalse(self.backend.check_in(now + 60))

    def test_lottery_pool_starts_at_two_kitty(self):
        self.assertEqual(self.backend.lottery_pool(), 2 * 10 ** 24)

    def test_draw_only_when_checked_in(self):
        now = ts(2026, 6, 1, 21, 5, 0)
        date = time.strftime("%Y-%m-%d", time.localtime(now))
        self.assertFalse(self.backend.run_demo_draw(date, random.Random(0)))
        self.backend.check_in(now)
        self.assertFalse(self.backend.run_demo_draw(date, random.Random(0)))

    def test_draw_win_pays_ten_percent(self):
        now = ts(2026, 6, 1, 21, 5, 0)
        date = time.strftime("%Y-%m-%d", time.localtime(now))
        self.backend.check_in(now)
        won = self.backend.run_demo_draw(date, random.Random(31))
        self.assertTrue(won)
        prize = 2 * 10 ** 24 * 10 // 100
        self.assertEqual(self.backend.balance("KITTY"), 25 * 10 ** 24 + prize)
        txn = self.backend.transactions()[0]
        self.assertEqual(txn.kind, "receive")
        self.assertEqual(txn.counterparty, "Launch Window lottery")
        self.assertEqual(txn.amount, prize)

    def test_draw_lose_adds_nothing(self):
        now = ts(2026, 6, 1, 21, 5, 0)
        date = time.strftime("%Y-%m-%d", time.localtime(now))
        self.backend.check_in(now)
        won = self.backend.run_demo_draw(date, random.Random(1))
        self.assertFalse(won)
        self.assertEqual(self.backend.balance("KITTY"), 25 * 10 ** 24)

    def test_draw_once_per_night(self):
        now = ts(2026, 6, 1, 21, 5, 0)
        date = time.strftime("%Y-%m-%d", time.localtime(now))
        self.backend.check_in(now)
        self.backend.run_demo_draw(date, random.Random(0))
        self.assertFalse(self.backend.run_demo_draw(date, random.Random(0)))


if __name__ == "__main__":
    unittest.main()
