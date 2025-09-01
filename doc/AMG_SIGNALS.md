# AMG Signals: Current Mapping and Discovery Plan

## What We Parse Today
- `T0` (beep / start-of-window): Emitted when a notification matches the start signature.
  - Recognized by `ble/amg_signals.py::classify_signals`: returns `"T0"` for
    - 0x01 0x05 prefix (preferred)
    - Legacy 14-byte 0x01 frames with mid bytes zero as fallback
  - Bridge logs:
    - `event: T0` with `t_rel_ms: 0` (for timing base)
    - `event: AMG_T0` with raw bytes (generic structured signal stream)
- Optional raw notifications: if `AMG_DEBUG_RAW=1`, raw frames are emitted as `{type:'debug', msg:'amg_raw', data:{raw: <hex>}}`.

Additionally (experimental):
- `AMG_START_BTN` (inferred): First AMG signal after idle and before the next T0.
- `AMG_ARROW_END`: Tentatively mapped to subtype 0x01 0x09.
- `AMG_TIMEOUT_END`: Tentatively mapped to subtype 0x01 0x08.
  - On recognized end signals, the bridge emits `SESSION_END` with a reason.

These are subject to tuning as we gather labeled raw captures.

## Desired Signals / Open Questions
- Start button press distinct from the beep (countdown start)
  - The timer can be configured for instant or delayed/random beep. We want to know the selected/random delay.
  - Hypothesis: AMG may emit a distinct frame subtype on button press or a parameter packet reflecting the chosen delay.
- Arrow press (end of listening window)
  - Today we infer end-of-window via inactivity / session logic; we need to detect explicit arrow button end, if present.
- Auto end via inactivity timeout (configurable in AMG)
  - Need to determine if a separate frame is emitted when the device times out.
- Power-off during active listening
  - Need to determine if a shutdown/busy/terminate frame appears.

## Discovery Procedure
1. Enable raw capture for AMG (`export AMG_DEBUG_RAW=1`) and perform controlled tests:
   - Button press (no shot), wait for beep / no beep variants (instant vs delayed / random)
   - Arrow press to end window
   - Inactivity timeout
   - Power-off during active window
2. Annotate time-stamped notes alongside NDJSON to correlate user actions with raw frames.
3. Analyze raw frame patterns (`tools/summarize_ndjson.py` shows `amg_raw` counts; build a simple frame classifier if needed).
4. Extend `classify_signals` with new patterns for start-button, arrow, timeout, power-off, returning names like `START_BTN`, `ARROW_END`, `TIMEOUT_END`, `POWER_OFF`. The bridge will emit these as `AMG_<NAME>` alongside raw frames.
5. Emit structured events with parsed parameters (e.g., `random_delay_ms`) when decodable.

## Bridge Behavior Plan
- On `AMG_START_BTN`: start a `pending_beep` state; store configured/random delay if available.
- On `T0` (beep): set `t0_ns` and continue as today.
- On `AMG_ARROW_END` or `AMG_TIMEOUT_END` or `AMG_POWER_OFF`: emit `{type:'event', msg:'SESSION_END', data:{reason:'arrow'|'timeout'|'power_off'}}` and optionally rotate to a new `session_id`.
- Make session rolling configurable: `session.on_amg_end: rotate_session: true|false`.

## Notes
- If the protocol is not fully documented, we can maintain a safe allowlist of recognized opcodes and ignore others.
- We will keep the raw toggle to accelerate future reverse-engineering.
