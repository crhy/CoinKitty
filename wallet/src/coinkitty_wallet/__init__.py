"""CoinKitty wallet core (demo).

The pure-Python rules the GTK screens import: money, addresses, claimable
payments, vaults and swaps.  KittyChain does not exist yet, so every balance
this wallet shows is a demo balance (issue #4: "Demo coins only ... every screen
says so").

White paper: ../spec/whitepaper-v0.3.md
Wallet screens: ../spec/wallet-android.md
"""

from . import amounts, address, payments, swap, vault  # noqa: F401

__all__ = ["amounts", "address", "payments", "swap", "vault"]

#: this slice is the wallet core only; the GTK screens come later
__version__ = "0.1-core"
