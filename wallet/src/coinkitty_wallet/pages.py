"""Navigation model for the CoinKitty Wallet: the page list and bottom bar.

Plain data only; no GTK imports. Each page is ``(page id, title, icon name)``.
"""

from __future__ import annotations

PAGES: list[tuple[str, str, str]] = [
    ("home", "Home", "go-home-symbolic"),
    ("wallet", "Wallet", "wallet-symbolic"),
    ("send", "Send", "mail-send-symbolic"),
    ("rain", "Rain", "weather-showers-symbolic"),
    ("swap", "Swap", "media-playlist-repeat-symbolic"),
    ("earn", "Earn", "starred-symbolic"),
    ("launch", "Launch", "go-up-symbolic"),
    ("mission", "Mission", "find-location-symbolic"),
    ("vault", "Vault", "channel-secure-symbolic"),
    ("vote", "Vote", "emblem-ok-symbolic"),
    ("launch-window", "Launch Window", "alarm-symbolic"),
    ("contacts", "Contacts", "avatar-default-symbolic"),
    ("identity", "Identity", "system-users-symbolic"),
    ("settings", "Settings", "emblem-system-symbolic"),
]

BOTTOM_BAR = ["launch", "mission", "earn"]


def page_title(page_id: str) -> str:
    """Return the display title for ``page_id``. Raises KeyError if unknown."""
    for candidate_id, title, _icon in PAGES:
        if candidate_id == page_id:
            return title
    raise KeyError(page_id)
