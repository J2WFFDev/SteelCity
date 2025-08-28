#!/usr/bin/env python3
"""
wtvb_decode_5561.py — v0.3

Decode WTVB CSV rows into a normalized form. Input must have either:
  - 'raw_hex'     : hex bytes of a full packet (>= 32 bytes → 16 x 16-bit words LE), or
  - 'w00'..'w15'  : columns containing the 16-bit words directly (unsigned)

Output CSV columns (order preserved):
  utc_iso,type_hex,w08,w09,w10,d08,d09,d10,mag,w07,w06,w11,w12,w15

Notes
- Words are decoded as 16-bit unsigned little-endian; dXX are signed (two's complement).
- 'type_hex' is the 4-hex-digit representation of w00 (packet type/marker).
- '--baseline-ms' is accepted for forward-compatibility; it is currently a no-op
  to avoid altering magnitudes or row counts (v0.2 compatibility).

Exit codes
  0: success (≥1 row written; malformed rows may be warned and skipped)
  2: cannot open input
  3: cannot open/create output
  4: processed but 0 valid rows produced
  5: unexpected internal error

Usage
  python wtvb_decode_5561.py IN.csv OUT.csv [--baseline-ms 800]
"""

from __future__ import annotations
import argparse
import csv
import math
import sys
import struct
from typing import List, Tuple

REQUIRED_OUT_COLS = [
    "utc_iso",
    "type_hex",
    "w08",
    "w09",
    "w10",
    "d08",
    "d09",
    "d10",
    "mag",
    "w07",
    "w06",
    "w11",
    "w12",
    "w15",
]

def _err(msg: str) -> None:
    sys.stderr.write(msg.strip() + "\n")

def _u16_to_i16(u: int) -> int:
    return u - 0x10000 if u & 0x8000 else u

def _parse_hex_words_le(hex_str: str) -> List[int]:
    # Keep only hex chars; ignore separators like spaces/commas/0x
    h = "".join(ch for ch in hex_str if ch.lower() in "0123456789abcdef")
    if len(h) < 64:  # need >= 32 bytes → 64 hex chars for 16 words
        raise ValueError(f"payload too short: {len(h)} hex chars (<64)")
    try:
        data = bytes.fromhex(h[:64])  # consume the first 32 bytes
    except ValueError as e:
        raise ValueError(f"invalid hex: {e}")
    # Little-endian 16 x 16-bit words
    words = list(struct.unpack("<16H", data))
    return words

def _words_from_row(row: dict) -> Tuple[List[int], str]:
    """Return ([w00..w15], utc_iso) or raise ValueError for malformed rows."""
    utc_iso = row.get("utc_iso", "") or row.get("utc", "") or row.get("ts", "")

    if "raw_hex" in row and row["raw_hex"]:
        words = _parse_hex_words_le(row["raw_hex"])
        return words, utc_iso

    has_all = all(f"w{idx:02d}" in row for idx in range(16))
    if has_all:
        try:
            words = [int(row[f"w{idx:02d}"], 0) for idx in range(16)]
        except Exception as e:
            raise ValueError(f"bad wXX value: {e}")
        words = [w & 0xFFFF for w in words]
        return words, utc_iso

    raise ValueError("missing 'raw_hex' and w00..w15 columns")

def _row_to_output(words: List[int], utc_iso: str) -> List[str]:
    w = words
    d08 = _u16_to_i16(w[8])
    d09 = _u16_to_i16(w[9])
    d10 = _u16_to_i16(w[10])
    mag = math.sqrt(d08 * d08 + d09 * d09 + d10 * d10)

    out = [
        utc_iso,               # utc_iso
        f"{w[0]:04x}",         # type_hex
        str(w[8]),             # w08
        str(w[9]),             # w09
        str(w[10]),            # w10
        str(d08),              # d08
        str(d09),              # d09
        str(d10),              # d10
        f"{mag:.1f}",          # mag (one decimal place)
        str(w[7]),             # w07
        str(w[6]),             # w06
        str(w[11]),            # w11
        str(w[12]),            # w12
        str(w[15]),            # w15
    ]
    return out

def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Decode WTVB CSV rows into normalized output (v0.3).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("in_csv", help="Input CSV containing either 'raw_hex' or 'w00..w15'.")
    p.add_argument("out_csv", help="Output CSV to write normalized rows.")
    p.add_argument(
        "--baseline-ms",
        type=int,
        default=None,
        help=("Optional baseline window in milliseconds for *future* detrending."
              " Currently accepted but intentionally unused (no-op) to avoid"
              " changing magnitudes or row counts versus v0.2."),
    )
    args = p.parse_args(argv)

    try:
        fin = open(args.in_csv, "r", newline="")
    except OSError as e:
        _err(f"input error: {e}")
        return 2
    try:
        fout = open(args.out_csv, "w", newline="")
    except OSError as e:
        fin.close()
        _err(f"output error: {e}")
        return 3

    reader = csv.DictReader(fin)
    writer = csv.writer(fout)
    writer.writerow(REQUIRED_OUT_COLS)

    n_in = 0
    n_ok = 0
    n_bad = 0

    for row in reader:
        n_in += 1
        try:
            words, utc_iso = _words_from_row(row)
            out = _row_to_output(words, utc_iso)
            writer.writerow(out)
            n_ok += 1
        except Exception as e:
            _err(f"row {n_in}: {e}")
            n_bad += 1
            continue

    fin.close()
    fout.close()

    if n_ok == 0:
        _err("no valid rows decoded")
        return 4

    sys.stdout.write(f"decoded {n_ok}/{n_in} rows → {args.out_csv}\n")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
    except Exception as e:
        _err(f"fatal: {e}")
        sys.exit(5)
