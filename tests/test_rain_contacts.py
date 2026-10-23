import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, GLib

import random
import shutil
import tempfile
import unittest

from coinkitty_wallet.demo_backend import DemoBackend
from coinkitty_wallet.models import Contact, RainGroup
from coinkitty_wallet.rain import rain_recipients
from coinkitty_wallet.ui.window import WalletWindow
from coinkitty_wallet.ui.contacts_page import shorten_address


class RainRecipientsTest(unittest.TestCase):
    def test_union_first_seen_order(self):
        band = RainGroup(id="b", name="Band", member_ids=["rick", "sam", "maya"])
        kids = RainGroup(id="k", name="Kids", member_ids=["julie", "maya"])
        self.assertEqual(
            rain_recipients([band, kids], {"b", "k"}),
            ["rick", "sam", "maya", "julie"],
        )

    def test_only_kids(self):
        band = RainGroup(id="b", name="Band", member_ids=["rick", "sam", "maya"])
        kids = RainGroup(id="k", name="Kids", member_ids=["julie", "maya"])
        self.assertEqual(rain_recipients([band, kids], {"k"}), ["julie", "maya"])

    def test_none_checked(self):
        band = RainGroup(id="b", name="Band", member_ids=["rick", "sam", "maya"])
        self.assertEqual(rain_recipients([band], set()), [])


class ShortenAddressTest(unittest.TestCase):
    def test_short_unchanged(self):
        self.assertEqual(shorten_address("abcdefghij"), "abcdefghij")

    def test_long_shortened(self):
        address = "a" * 12 + "middle" + "z" * 6
        self.assertEqual(
            shorten_address(address),
            address[:12] + "\u2026" + address[-6:],
        )


class RainContactsTest(unittest.TestCase):
    def setUpClass():
        if not Gtk.init_check():
            raise unittest.SkipTest("GTK init unavailable")
        Adw.init()

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="coinkitty-rain-")
        self.backend = DemoBackend.create(
            self.tmpdir + "/demo-wallet.json", random.Random(0)
        )
        self.window = WalletWindow(None, self.backend)
        ctx = GLib.MainContext.default()
        for _ in range(50):
            n = 0
            while ctx.iteration(False):
                n += 1
                if n >= 1000:
                    break

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _id_by_name(self):
        return {c.name: c.id for c in self.backend.contacts()}

    def _group_by_name(self):
        return {g.name: g for g in self.backend.rain_groups()}

    def _count_rows(self, list_box):
        count = 0
        child = list_box.get_first_child()
        while child is not None:
            count += 1
            child = child.get_next_sibling()
        return count

    # ---- rain: equal split ------------------------------------------------

    def test_rain_equal_split(self):
        rain = self.window._pages["rain"]
        band = self._group_by_name()["Band"]
        rain.preselect_group(band.id)
        rain.total_entry.set_text("3")
        self.assertEqual(self._count_rows(rain.preview_list), 3)
        first = rain.preview_list.get_first_child()
        self.assertEqual(first.get_subtitle(), "1 KITTY")
        self.assertTrue(rain.rain_button.get_sensitive())
        rain.rain_button.emit("clicked")
        self.assertEqual(self.backend.balance("KITTY"), 22 * 10**24)
        rain_txns = [t for t in self.backend.transactions() if t.kind == "rain"]
        self.assertEqual(len(rain_txns), 3)

    # ---- rain: custom split mismatch --------------------------------------

    def test_custom_split_mismatch_then_fix(self):
        rain = self.window._pages["rain"]
        band = self._group_by_name()["Band"]
        ids = self._id_by_name()
        rain.preselect_group(band.id)
        rain.total_entry.set_text("3")
        rain.custom_toggle.set_active(True)
        rain._refresh_preview()
        for name, value in (("Rick", "1"), ("Sam", "1"), ("Maya", "0.5")):
            rain._custom_entries[ids[name]].set_text(value)
        self.assertIn("Assigned 2.5 of 3", rain.assigned_label.get_label())
        self.assertFalse(rain.rain_button.get_sensitive())
        rain._custom_entries[ids["Maya"]].set_text("1")
        self.assertTrue(rain.rain_button.get_sensitive())

    # ---- rain: over balance -----------------------------------------------

    def test_rain_over_balance(self):
        rain = self.window._pages["rain"]
        band = self._group_by_name()["Band"]
        rain.preselect_group(band.id)
        rain.total_entry.set_text("999999")
        rain.rain_button.emit("clicked")
        self.assertTrue(rain.error_label.get_visible())
        self.assertEqual(self.backend.balance("KITTY"), 25 * 10**24)

    # ---- group editor: create a new group ---------------------------------

    def test_group_editor_creates_group(self):
        rain = self.window._pages["rain"]
        ids = self._id_by_name()
        rain._open_editor(None)
        editor = rain._active_editor
        editor.name_entry.set_text("Crew")
        for check, contact in editor._check_by_contact.items():
            if contact.name in ("Rick", "Sam"):
                check.set_active(True)
        editor.save_button.emit("clicked")
        names = {g.name for g in self.backend.rain_groups()}
        self.assertIn("Crew", names)
        self.assertEqual(len(self.backend.rain_groups()), 3)

    def test_group_editor_save_insensitive_empty_name(self):
        rain = self.window._pages["rain"]
        rain._open_editor(None)
        editor = rain._active_editor
        self.assertFalse(editor.save_button.get_sensitive())

    # ---- group editor: delete a group -------------------------------------

    def test_group_editor_deletes_group(self):
        rain = self.window._pages["rain"]
        kids = self._group_by_name()["Kids"]
        rain._open_editor(kids)
        editor = rain._active_editor
        editor._on_delete_clicked(editor.delete_button)
        editor._on_delete_response(editor.confirm_dialog, "delete")
        names = {g.name for g in self.backend.rain_groups()}
        self.assertNotIn("Kids", names)
        self.assertEqual(len(self.backend.rain_groups()), 1)

    # ---- contacts: search -------------------------------------------------

    def test_contacts_search_filters(self):
        contacts = self.window._pages["contacts"]
        contacts.search_entry.set_text("ju")
        self.assertEqual(self._count_rows(contacts.contact_list), 1)

    # ---- contacts: star a contact, favorites grow -------------------------

    def test_contacts_star_sam(self):
        contacts = self.window._pages["contacts"]
        ids = self._id_by_name()
        contacts._star_buttons[ids["Sam"]].emit("clicked")
        sam = next(c for c in self.backend.contacts() if c.name == "Sam")
        self.assertTrue(sam.favorite)
        self.window.refresh_favorites()
        self.assertEqual(self._count_rows(self.window.favorites_list), 4)

    # ---- contacts: add with invalid address keeps Save off ----------------

    def test_add_contact_invalid_address(self):
        from coinkitty_wallet.ui.contacts_page import AddContactDialog

        dialog = AddContactDialog(self.backend)
        dialog.name_entry.set_text("Zed")
        dialog.address_entry.set_text("not-an-address")
        self.assertFalse(dialog.save_button.get_sensitive())
        valid = self.backend.contacts()[0].address
        dialog.address_entry.set_text(valid)
        self.assertTrue(dialog.save_button.get_sensitive())

    # ---- contacts: delete removes from rain groups ------------------------

    def test_delete_contact_removes_from_group(self):
        from coinkitty_wallet.ui.contacts_page import ContactDialog

        ids = self._id_by_name()
        rick = next(c for c in self.backend.contacts() if c.name == "Rick")
        dialog = ContactDialog(self.backend, rick)
        dialog._on_delete_clicked(dialog.delete_button)
        dialog._on_delete_response(dialog.confirm_dialog, "delete")
        band = self._group_by_name()["Band"]
        self.assertNotIn(ids["Rick"], band.member_ids)
        self.assertEqual(len(band.member_ids), 2)


if __name__ == "__main__":
    unittest.main()
