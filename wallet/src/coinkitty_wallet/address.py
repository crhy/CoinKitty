"""Bech32m addresses: the wallet refuses to send to one that fails the check.

White paper v0.3 §11.1: "Addresses use **Bech32m** encoding with the prefix
``kitty1…``. The checksum is guaranteed to catch any mistake of up to 4
characters and almost always catches more. Wallets refuse to send to an address
that fails the check."

The checksum is the BIP-350 one: the Bech32 generator polynomial
(x^10 + x^6 + x^5 + x^3 + 1, written 0x3B0F) over the 5-bit values of the
human-readable part and the data, with the final xor constant 0x2AC3B7A4.
"""

from __future__ import annotations

__all__ = [
    "CHARSET",
    "DEFAULT_PREFIX",
    "InvalidAddress",
    "polymod",
    "checksum_values",
    "encode",
    "decode",
    "valid",
    "send_target",
    "convertbits",
    "encode_bytes",
    "decode_bytes",
]

#: the Bech32 character set (no "1", no "b", no "i", no "o")
CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

#: the address prefix the white paper fixes (§11.1)
DEFAULT_PREFIX = "kitty1"

#: BIP-350 final xor constant; a correct Bech32m string has polymod == this
BECH32M_CONST = 0x2AC3B7A4

#: the Bech32 generator polynomial x^10 + x^6 + x^5 + x^3 + 1
GENERATOR = 0x3B0F

#: a Bech32m string is at most 1024 characters, HRP at most 90
MAX_LEN = 1024
MAX_HRP_LEN = 90
CHECKSUM_LEN = 6


class InvalidAddress(ValueError):
    """Raised for any address that fails the Bech32m check."""


def polymod(values) -> int:
    """The Bech32 checksum accumulator over 5-bit values."""
    chk = 1
    for value in values:
        if not 0 <= value < 32:
            raise InvalidAddress(f"not a 5-bit value: {value!r}")
        chk = ((chk & 0x3FF) << 5) ^ value
        for i in range(5):
            if (chk >> (5 * (i + 1))) & 1:
                chk ^= [0x32, 0x76, 0xF4, 0x1CC, 0x3D8, 0x7D0, 0xFA0][i]
    return chk


def _hrp_values(hrp: str) -> list[int]:
    """The 5-bit values of the human-readable part (each ASCII char, split)."""
    values = []
    for ch in hrp:
        code = ord(ch)
        if not 1 <= code <= 127:
            raise InvalidAddress(f"human-readable part out of range: {hrp!r}")
        values += [code >> 5, code & 31]
    return values


def checksum_values(data, hrp: str) -> list[int]:
    """The 6 checksum symbols' 5-bit values for *data* under *hrp*."""
    poly = polymod(_hrp_values(hrp) + list(data)) ^ BECH32M_CONST
    return [(poly >> (5 * (5 - i))) & 31 for i in range(CHECKSUM_LEN)]


def convertbits(data, frombits: int, tobits: int, pad: bool = True):
    """Regroup a stream of *frombits*-bit values into *tobits*-bit values."""
    acc = 0
    bits = 0
    out = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if isinstance(value, bool) or not isinstance(value, int):
            raise InvalidAddress(f"not an integer value: {value!r}")
        if value < 0 or (value >> frombits):
            raise InvalidAddress(f"not a {frombits}-bit value: {value!r}")
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            out.append((acc >> bits) & maxv)
    if pad:
        if bits:
            out.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        raise InvalidAddress("unusable padding bits")
    return out


def encode(data, prefix: str = DEFAULT_PREFIX) -> str:
    """Encode 5-bit *data* as a Bech32m string starting with *prefix*.

    *data* may be an iterable of 5-bit values, or bytes (regrouped 8 -> 5).
    """
    if isinstance(data, (bytes, bytearray)):
        data = convertbits(data, 8, 5)
    values = list(data)
    if not values:
        raise InvalidAddress("nothing to encode")
    p = prefix.upper() if prefix.isupper() else prefix.lower()
    if not p.endswith("1"):
        p += "1"
    hrp = p[:-1]
    if not hrp or len(hrp) > MAX_HRP_LEN:
        raise InvalidAddress(f"bad prefix: {prefix!r}")
    chars = "".join(CHARSET[v] for v in checksum_values(values, hrp) + values)
    addr = hrp + "1" + chars
    if len(addr) > MAX_LEN:
        raise InvalidAddress(f"address is longer than {MAX_LEN} characters")
    return addr


def encode_bytes(data: bytes, prefix: str = DEFAULT_PREFIX) -> str:
    """Encode raw bytes as a Bech32m address."""
    return encode(convertbits(bytes(data), 8, 5), prefix)


def decode(text: str, prefix: str | None = DEFAULT_PREFIX):
    """Decode a Bech32m address.

    Returns ``(hrp, data)`` where *data* is a tuple of 5-bit values.  Raises
    `InvalidAddress` for anything that fails the check, including a prefix
    mismatch.  Pass ``prefix=None`` to accept any prefix (used by the BIP-350
    vectors, which carry their own).
    """
    if not isinstance(text, str):
        raise InvalidAddress(f"address must be text, got {text!r}")
    s = text.strip()
    if not s:
        raise InvalidAddress("empty address")
    if len(s) > MAX_LEN:
        raise InvalidAddress(f"address is longer than {MAX_LEN} characters")
    if s.lower() != s and s.upper() != s:
        raise InvalidAddress("address mixes upper and lower case")
    lowered = s.lower()
    sep = lowered.rfind("1")
    if sep < 1:
        raise InvalidAddress("no separator in the address")
    if len(lowered) - sep - 1 < CHECKSUM_LEN:
        raise InvalidAddress("address is too short to hold a checksum")
    hrp = lowered[:sep]
    if len(hrp) > MAX_HRP_LEN:
        raise InvalidAddress("human-readable part is longer than 90 characters")
    if not hrp.isascii():
        raise InvalidAddress("human-readable part must be ASCII")
    body = lowered[sep + 1:]
    if any(ch not in CHARSET for ch in body):
        bad = next(ch for ch in body if ch not in CHARSET)
        raise InvalidAddress(f"character {bad!r} is not in the Bech32 charset")
    values = [CHARSET.index(ch) for ch in body]
    if polymod(_hrp_values(hrp) + values) != BECH32M_CONST:
        raise InvalidAddress(f"checksum does not match: {text!r}")
    if prefix is not None:
        expected = prefix.lower().rstrip("1")
        if hrp != expected:
            raise InvalidAddress(f"address {text!r} is not a {prefix} address")
    return hrp, tuple(values[:-CHECKSUM_LEN])


def valid(text: str, prefix: str | None = DEFAULT_PREFIX) -> bool:
    """True if *text* is a well-formed address with a correct checksum."""
    try:
        decode(text, prefix)
    except InvalidAddress:
        return False
    return True


def send_target(text: str, prefix: str | None = DEFAULT_PREFIX) -> str:
    """The only address form the send path accepts.

    The Send screen validates as you type (wallet spec §3.3) and calls this
    before building a transaction: it returns the canonical lower-case address,
    or raises `InvalidAddress`.  There is no way to send to an address that
    fails the check.
    """
    hrp, _data = decode(text, prefix)
    return text.strip().lower()


def decode_bytes(text: str, prefix: str | None = DEFAULT_PREFIX) -> bytes:
    """The payload of an address, regrouped 5 -> 8 bits."""
    _hrp, values = decode(text, prefix)
    return bytes(convertbits(values, 5, 8, pad=False))
