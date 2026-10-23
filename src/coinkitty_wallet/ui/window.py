"""The CoinKitty desktop window: navigation, sidebars, bottom bar, placeholder pages.

This is the only module that imports GTK. All page/navigation data comes from
:mod:`coinkitty_wallet.pages`; all money data comes from the injected backend.
"""

from __future__ import annotations

import gi

import random

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ..pages import PAGES, BOTTOM_BAR, page_title
from ..ui.home_page import HomePage
from ..ui.wallet_page import WalletPage
from ..ui.send_page import SendPage
from ..ui.rain_page import RainPage
from ..ui.contacts_page import ContactsPage
from ..ui.vault_page import VaultPage
from ..ui.launch_window_page import LaunchWindowPage
from ..ui.swap_page import SwapPage
from ..ui.earn_page import EarnPage
from ..ui.launch_page import LaunchPage
from ..ui.style import install_css

BANNER_TEXT = "Demo coins: KittyChain is not live yet. Nothing here is real money."


class WalletWindow(Adw.ApplicationWindow):
    """The application window wiring navigation, favorites and the bottom bar."""

    def __init__(self, app, backend):
        super().__init__()
        self._app = app
        self._backend = backend
        self._current_page = "home"
        self._selecting = False

        install_css()

        # ---- content: one page per PAGES entry -----------------------------
        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._pages: dict[str, Gtk.Widget] = {}
        for page_id, title, icon in PAGES:
            if page_id == "home":
                page = HomePage(backend, self._open_page)
            elif page_id == "wallet":
                page = WalletPage(backend)
            elif page_id == "send":
                page = SendPage(backend, on_open_page=self.show_page)
            elif page_id == "rain":
                page = RainPage(
                    backend,
                    on_open_page=self.show_page,
                    on_changed=self.refresh_favorites,
                )
            elif page_id == "contacts":
                page = ContactsPage(
                    backend,
                    on_open_page=self.show_page,
                    on_changed=self.refresh_favorites,
                    on_pay=lambda cid: self._pages["send"].start_with_contact(cid),
                )
            elif page_id == "vault":
                page = VaultPage(backend)
            elif page_id == "launch-window":
                page = LaunchWindowPage(backend)
            elif page_id == "swap":
                page = SwapPage(backend, rng=random.Random(7))
            elif page_id == "earn":
                page = EarnPage(backend, on_open_bounty=lambda bounty_id: None)
            elif page_id == "launch":
                page = LaunchPage(backend, on_open_bounty=lambda bounty_id: None)
            else:
                status = Adw.StatusPage()
                status.set_icon_name(icon)
                status.set_title(title)
                status.set_description("Coming soon")
                page = status
            self.content_stack.add_named(page, page_id)
            self._pages[page_id] = page

        # ---- left sidebar: main menu --------------------------------------
        self.menu_list = Gtk.ListBox()
        self.menu_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._menu_rows: dict[str, Adw.ActionRow] = {}
        self._menu_row_pages: dict[Adw.ActionRow, str] = {}
        for page_id, title, icon in PAGES:
            row = Adw.ActionRow()
            row.set_title(title)
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            self.menu_list.append(row)
            self._menu_rows[page_id] = row
            self._menu_row_pages[row] = page_id
        self.menu_list.connect("row-activated", self._on_menu_row_activated)

        # ---- select the Home menu row at startup ---------------------------
        self._selecting = True
        try:
            self.menu_list.select_row(self._menu_rows["home"])
        finally:
            self._selecting = False

        # ---- right sidebar: favorites -------------------------------------
        self.favorites_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        favorites_heading = Gtk.Label(label="Favorites")
        favorites_heading.set_margin_top(12)
        favorites_heading.set_margin_bottom(6)
        favorites_heading.add_css_class("heading")
        self.favorites_widget.append(favorites_heading)
        self.favorites_list = Gtk.ListBox()
        self._favorite_row_pages: dict[Adw.ActionRow, str] = {}
        self._favorite_row_contact: dict[Adw.ActionRow, str] = {}
        self._favorite_row_group: dict[Adw.ActionRow, str] = {}
        self._build_favorite_rows()
        self.favorites_widget.append(self.favorites_list)
        self.favorites_list.connect("row-activated", self._on_favorite_activated)

        # ---- split views --------------------------------------------------
        self.right_split = Adw.OverlaySplitView()
        self.right_split.set_sidebar_position(Gtk.PackType.END)
        self.right_split.set_content(self.content_stack)
        self.right_split.set_sidebar(self.favorites_widget)

        self.left_split = Adw.OverlaySplitView()
        self.left_split.set_sidebar(self.menu_list)
        self.left_split.set_content(self.right_split)

        # ---- toolbar: header + content + bottom bar + banner --------------
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)
        toolbar.set_content(self.left_split)

        self.title_widget = Adw.WindowTitle()
        self.title_widget.set_title("CoinKitty")
        self.title_widget.set_subtitle(page_title(self._current_page))
        header.set_title_widget(self.title_widget)

        left_toggle = Gtk.ToggleButton(icon_name="sidebar-show-symbolic")
        header.pack_start(left_toggle)
        left_toggle.connect(
            "notify::active",
            lambda *_: self.left_split.set_show_sidebar(left_toggle.get_active()),
        )
        right_toggle = Gtk.ToggleButton(icon_name="starred-symbolic")
        header.pack_end(right_toggle)
        right_toggle.connect(
            "notify::active",
            lambda *_: self.right_split.set_show_sidebar(right_toggle.get_active()),
        )

        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bottom_bar.set_halign(Gtk.Align.CENTER)
        bottom_bar.set_homogeneous(True)
        bottom_bar.set_margin_top(8)
        bottom_bar.set_margin_bottom(8)
        self.bottom_buttons: dict[str, Gtk.Button] = {}
        for page_id in BOTTOM_BAR:
            button = Gtk.Button(label=page_title(page_id))
            button.add_css_class("pill")
            button.connect("clicked", self._make_bottom_handler(page_id))
            bottom_bar.append(button)
            self.bottom_buttons[page_id] = button
        toolbar.add_bottom_bar(bottom_bar)

        self.banner = Adw.Banner()
        self.banner.set_title(BANNER_TEXT)
        self.banner.set_revealed(True)
        toolbar.add_top_bar(self.banner)

        self.set_content(toolbar)
        self.set_default_size(1000, 720)

        if app:
            self.set_application(app)

    # ---- signal handlers --------------------------------------------------

    def _on_menu_row_activated(self, list_box, row, user_initiated):
        if self._selecting:
            return
        page_id = self._menu_row_pages.get(row)
        if page_id is not None:
            self.show_page(page_id)

    def _on_favorite_activated(self, list_box, row, user_initiated):
        page_id = self._favorite_row_pages.get(row)
        if page_id is None:
            return
        self.show_page(page_id)
        contact_id = self._favorite_row_contact.get(row)
        if page_id == "send" and contact_id is not None:
            self._pages["send"].start_with_contact(contact_id)
        group_id = self._favorite_row_group.get(row)
        if page_id == "rain" and group_id is not None:
            self._pages["rain"].preselect_group(group_id)

    def refresh_favorites(self) -> None:
        """Rebuild the favorites sidebar from the current backend state."""
        self._build_favorite_rows()

    def _build_favorite_rows(self) -> None:
        """Clear and repopulate the favorites list from backend favorites."""
        self._favorite_row_pages = {}
        self._favorite_row_contact = {}
        self._favorite_row_group = {}
        child = self.favorites_list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.favorites_list.remove(child)
            child = nxt
        for contact in self._backend.contacts():
            if contact.favorite:
                row = Adw.ActionRow()
                row.set_title(contact.name)
                row.set_subtitle("Contact")
                row.set_activatable(True)
                self.favorites_list.append(row)
                self._favorite_row_pages[row] = "send"
                self._favorite_row_contact[row] = contact.id
        for group in self._backend.rain_groups():
            if group.favorite:
                row = Adw.ActionRow()
                row.set_title(group.name)
                row.set_subtitle("Rain group")
                row.set_activatable(True)
                self.favorites_list.append(row)
                self._favorite_row_pages[row] = "rain"
                self._favorite_row_group[row] = group.id

    def _make_bottom_handler(self, page_id: str):
        return lambda *_: self.show_page(page_id)

    def _open_page(self, page_id: str) -> None:
        """Callback handed to pages so they can request a page switch."""
        self.show_page(page_id)

    # ---- navigation -------------------------------------------------------

    def show_page(self, page_id: str) -> None:
        """Switch the visible page, update the subtitle, select the menu row."""
        if page_id not in self._menu_rows:
            raise KeyError(page_id)
        self.content_stack.set_visible_child_name(page_id)
        self.title_widget.set_subtitle(page_title(page_id))
        self._current_page = page_id
        if not self._selecting:
            self._selecting = True
            try:
                self.menu_list.select_row(self._menu_rows[page_id])
            finally:
                self._selecting = False
        page = self._pages.get(page_id)
        if page is not None and hasattr(page, "refresh"):
            page.refresh()

    def current_page(self) -> str:
        """Return the id of the page currently shown."""
        return self._current_page
