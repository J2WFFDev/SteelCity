import sqlite3
import tempfile
from pathlib import Path

from tools.timing_correlation_report import generate_matches, connect


def _create_events_db(path: Path, rows):
    con = sqlite3.connect(str(path))
    try:
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seq INTEGER,
                ts_ms REAL,
                type TEXT,
                msg TEXT,
                plate TEXT,
                t_rel_ms REAL,
                session_id TEXT,
                pid INTEGER,
                schema TEXT,
                data_json TEXT
            )
            """
        )
        for r in rows:
            cur.execute(
                "INSERT INTO events (seq, ts_ms, type, msg, plate, t_rel_ms, session_id, pid, schema, data_json) VALUES (?,?,?,?,?,?,?,?,?,?)",
                r,
            )
        con.commit()
    finally:
        con.close()


def test_simple_matching(tmp_path: Path):
    db = tmp_path / "events.db"
    # session S1: T0 at 1000, HIT at 1010 -> offset 10
    rows = [
        (1, 1000.0, "event", "T0", None, None, "S1", 1, "v1", "{}"),
        (2, 1010.0, "event", "HIT", "P1", None, "S1", 1, "v1", "{}"),
        # session S1: another T0 with no hit within window
        (3, 2000.0, "event", "T0", None, None, "S1", 1, "v1", "{}"),
        # session S2: T0 and HIT
        (4, 3000.0, "event", "T0", None, None, "S2", 1, "v1", "{}"),
        (5, 3040.0, "event", "HIT", "P2", None, "S2", 1, "v1", "{}"),
    ]
    _create_events_db(db, rows)
    con = connect(db)
    try:
        matches = generate_matches(con, None, max_lag_ms=100.0)
        # Expect two matches: one in S1 (T0->HIT) and one in S2
        assert len(matches) == 2
        offsets = sorted([m.offset_ms for m in matches])
        assert offsets == [10.0, 40.0]
    finally:
        con.close()
