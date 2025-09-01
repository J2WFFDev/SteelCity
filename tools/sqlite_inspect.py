import argparse
import sqlite3
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description="Inspect SQLite events table")
    ap.add_argument("--db", required=True, type=Path, help="Path to SQLite DB")
    args = ap.parse_args()

    con = sqlite3.connect(str(args.db))
    try:
        cur = con.cursor()
        cur.execute("select count(*) from events;")
        rows = cur.fetchone()[0]
        cur.execute("select min(ts_ms), max(ts_ms) from events;")
        ts_bounds = cur.fetchone()
        print(f"rows: {rows}")
        print(f"ts_bounds: {ts_bounds}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
