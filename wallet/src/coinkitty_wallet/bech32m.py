"""Bech32m (BIP-350) address encoding for CoinKitty addresses.

Implements the exact constants and polymod from BIP-350. Addresses use the
human-readable prefix ``kitty`` and carry a 20- or 32-byte payload.
"""

from __future__ import annotations

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32M_CONST = 0x2BC830A3
GEN = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
HRP = "kitty"
_MAX_ADDRESS_LENGTH = 90


def _polymod(values: list[int]) -> int:
    """Bech32m polynomial modulus over the generator ``GEN``."""
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            chk ^= GEN[i] if ((b >> i) & 1) else 0
    return chk


def _hrp_expand(hrp: str) -> list[int]:
    """Expand the human-readable prefix into 5-bit groups for the checksum."""
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def convertbits(data: bytes | list[int], frombits: int, tobits: int, pad: bool) -> list[int]:
    """Regroup ``data`` from ``frombits``-wide values to ``tobits``-wide values.

    Standard BIP-173 implementation. Returns ``None`` when the input has a value
    too wide for ``frombits`` or (with ``pad=False``) when leftover bits are
    non-zero or too many.
    """
    acc = 0
    bits = 0
    ret: list[int] = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def _checksum_groups(hrp: str, data5: list[int]) -> list[int]:
    """The six 5-bit checksum groups (big-endian) for ``hrp`` + ``data5``."""
    gen = _polymod(_hrp_expand(hrp) + data5 + [0] * 6) ^ BECH32M_CONST
    return [(gen >> 5 * (5 - i)) & 31 for i in range(6)]


def encode(hrp: str, data5: list[int]) -> str:
    """Encode 5-bit ``data5`` with prefix ``hrp`` into a Bech32m string."""
    checksum = _checksum_groups(hrp, data5)
    return hrp + "1" + "".join(CHARSET[d] for d in data5 + checksum)


def decode(s: str) -> tuple[str, list[int]]:
    """Decode a Bech32m string to ``(hrp, data5)``.

    Raises ``ValueError`` on mixed case, length > 90, a missing ``1`` separator,
    an empty hrp, fewer than 6 data characters, a character outside the charset,
    or a bad checksum. Case-insensitive; the returned hrp is lowercase.
    """
    if len(s) > _MAX_ADDRESS_LENGTH:
        raise ValueError("address too long")
    if s.lower() != s and s.upper() != s:
        raise ValueError("mixed case")
    s = s.lower()

    sep = s.rfind("1")
    if sep == -1:
        raise ValueError("missing separator")
    hrp, data_part = s[:sep], s[sep + 1:]
    if not hrp:
        raise ValueError("empty hrp")
    if len(data_part) < 6:
        raise ValueError("too few data characters")

    data5: list[int] = []
    for ch in data_part:
        idx = CHARSET.find(ch)
        if idx == -1:
            raise ValueError("bad character")
        data5.append(idx)

    if _polymod(_hrp_expand(hrp) + data5) != BECH32M_CONST:
        raise ValueError("bad checksum")
    return hrp, data5[:-6]


def encode_address(payload: bytes) -> str:
    """Encode a 20- or 32-byte payload as a ``kitty`` Bech32m address."""
    if len(payload) not in (20, 32):
        raise ValueError("payload must be 20 or 32 bytes")
    data5 = convertbits(payload, 8, 5, True)
    return encode(HRP, data5)


def decode_address(addr: str) -> bytes:
    """Decode a ``kitty`` Bech32m address back to its payload bytes."""
    hrp, data5 = decode(addr)
    if hrp != HRP:
        raise ValueError(f"expected hrp {HRP!r}, got {hrp!r}")
    payload = convertbits(data5, 5, 8, False)
    if payload is None:
        raise ValueError("payload has invalid padding")
    return bytes(payload)


def is_valid_address(addr: str) -> bool:
    """True iff ``addr`` is a well-formed ``kitty`` Bech32m address."""
    try:
        decode_address(addr)
    except ValueError:
        return False
    return True
