Timing Correlation Report
=========================

This tool generates a simple timing correlation CSV matching `T0` (timer) events to the next `HIT` (sensor) event within a configurable window.

Usage
-----

Run against the project SQLite DB (default `logs/bridge.db`):

```pwsh
python tools/timing_correlation_report.py --db logs/bridge.db --out reports/timing_correlation.csv
```

Options
-------
- `--session`: Limit to a specific `session_id`.
- `--max-lag-ms`: Maximum allowed lag between `T0` and `HIT` to be considered a match (default `500` ms).

Output
------
- CSV with columns: `session_id, t0_seq, t0_ts_ms, hit_seq, hit_ts_ms, offset_ms`.
- Summary printed to stdout with match counts and mean offset.

Notes
-----
- The matching algorithm is intentionally simple (first-hit-after-T0) to be conservative and easy to reason about. It can be extended to handle more complex pairing (bisecting, nearest neighbour, tolerance windows, 1-to-many mapping) as a follow-up.
