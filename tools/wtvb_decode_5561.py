#!/usr/bin/env python3
"""
wtvb_decode_5561.py — v0.3.1 (compat + more column names)

Accepts either:
  - hex payload column (any of): raw_hex, tail_hex, hex, payload_hex, data_hex, bytes_hex, raw
  - word columns: w00..w15 (preferred) OR w0..w15 (unpadded)
Case-insensitive header matching; trims header whitespace.

Output CSV columns (order preserved):
  utc_iso,type_hex,w08,w09,w10,d08,d09,d10,mag,w07,w06,w11,w12,w15

Exit codes
  0 OK; 2 input open err; 3 output open err; 4 no valid rows; 5 internal.
"""

from __future__ import annotations
import argparse, csv, math, sys, struct
from typing import List, Tuple, Optional

REQUIRED_OUT_COLS = [
    "utc_iso","type_hex","w08","w09","w10","d08","d09","d10",
    "mag","w07","w06","w11","w12","w15",
]

HEX_COL_CANDIDATES = [
    "raw_hex","tail_hex","hex","payload_hex","data_hex","bytes_hex","raw",
]

def _err(msg: str) -> None:
    sys.stderr.write(msg.strip() + "\n")

def _u16_to_i16(u: int) -> int:
    return u - 0x10000 if (u & 0x8000) else u

def _parse_hex_words_le(hex_str: str) -> List[int]:
    # keep hex chars only; ignore spaces, commas, 0x, etc.
    h = "".join(ch for ch in hex_str if ch.lower() in "0123456789abcdef")
    if len(h) < 64:
        raise ValueError(f"payload too short: {len(h)} hex chars (<64)")
    try:
        data = bytes.fromhex(h[:64])  # first 32 bytes → 16 words
    except ValueError as e:
        raise ValueError(f"invalid hex: {e}")
    return list(struct.unpack("<16H", data))  # little-endian

def _get_first_present_key(d: dict, keys: List[str]) -> Optional[str]:
    for k in keys:
        if k in d and d[k]:
            return k
    return None

def _words_from_row(row: dict) -> Tuple[List[int], str]:
    # normalize keys: lowercase + strip spaces
    row_lc = { (k or "").strip().lower(): (v or "").strip() for k,v in row.items() }

    # utc-ish passthrough
    utc_iso = row_lc.get("utc_iso") or row_lc.get("utc") or row_lc.get("ts") \
           or row_lc.get("timestamp") or row_lc.get("time") or ""

    # 1) hex payload path
    hex_key = _get_first_present_key(row_lc, HEX_COL_CANDIDATES)
    if hex_key:
        return _parse_hex_words_le(row_lc[hex_key]), utc_iso

    # 2) word columns path — try padded (w00..w15) then unpadded (w0..w15)
    padded = [f"w{idx:02d}" for idx in range(16)]
    unpadded = [f"w{idx}" for idx in range(16)]
    if all(k in row_lc for k in padded):
        try:
            words = [int(row_lc[f"w{idx:02d}"], 0) & 0xFFFF for idx in range(16)]
        except Exception as e:
            raise ValueError(f"bad wXX value: {e}")
        return words, utc_iso
    if all(k in row_lc for k in unpadded):
        try:
            words = [int(row_lc[f"w{idx}"], 0) & 0xFFFF for idx in range(16)]
        except Exception as e:
            raise ValueError(f"bad wX value: {e}")
        return words, utc_iso

    raise ValueError("no hex-like column and no w00..w15 / w0..w15 columns")

def _row_to_output(words: List[int], utc_iso: str) -> List[str]:
    w = words
    d08, d09, d10 = _u16_to_i16(w[8]), _u16_to_i16(w[9]), _u16_to_i16(w[10])
    mag = math.sqrt(d08*d08 + d09*d09 + d10*d10)
    return [
        utc_iso,
        f"{w[0]:04x}",
        str(w[8]), str(w[9]), str(w[10]),
        str(d08), str(d09), str(d10),
        f"{mag:.1f}",
        str(w[7]), str(w[6]), str(w[11]), str(w[12]), str(w[15]),
    ]

def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Decode WTVB CSV rows → normalized output (v0.3.1).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("in_csv", help="Input CSV (has hex payload or w00..w15 / w0..w15).")
    ap.add_argument("out_csv", help="Output CSV path.")
    ap.add_argument("--baseline-ms", type=int, default=None,
        help="Accepted but unused (no-op) to preserve v0.2 magnitudes & counts.")
    ap.add_argument("--hex-col", default=None,
        help="Optional explicit hex column name (case-insensitive) if non-standard.")
    args = ap.parse_args(argv)

    try:
        fin = open(args.in_csv, "r", newline="")
    except OSError as e:
        _err(f"input error: {e}")
        return 2
    try:
        fout = open(args.out_csv, "w", newline="")
    except OSError as e:
        fin.close(); _err(f"output error: {e}"); return 3

    rdr = csv.DictReader(fin)
    wtr = csv.writer(fout)
    wtr.writerow(REQUIRED_OUT_COLS)

    n_in = n_ok = n_bad = 0

    # If user provided --hex-col, prepend it to candidates for this run
    hex_candidates = HEX_COL_CANDIDATES[:]
    if args.hex_col:
        hex_candidates = [args.hex_col.strip().lower()] + [k for k in hex_candidates if k != args.hex_col.strip().lower()]

    for row in rdr:
        n_in += 1
        try:
            # inject per-row candidates
            row_norm = { (k or "").strip().lower(): (v or "").strip() for k,v in row.items() }
            # fast-path override
            if args.hex_col and row_norm.get(args.hex_col.strip().lower()):
                words, utc_iso = _parse_hex_words_le(row_norm[args.hex_col.strip().lower()]), \
                                 (row_norm.get("utc_iso") or row_norm.get("utc") or row_norm.get("ts") or row_norm.get("timestamp") or row_norm.get("time") or "")
            else:
                words, utc_iso = _words_from_row(row)
            out = _row_to_output(words, utc_iso)
            wtr.writerow(out)
            n_ok += 1
        except Exception as e:
            _err(f"row {n_in}: {e}")
            n_bad += 1

    fin.close(); fout.close()

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
