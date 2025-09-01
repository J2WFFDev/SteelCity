# SteelCity Impact Detection System - Session Handoff Document
## Date: August 31, 2025

### 🎯 **Current Project Status**

**Hardware Platform:**
- Raspberry Pi 4B running bridge service
- AMG Smart Timer (MAC: 60:09:C3:1F:DC:1A) - Device ID: DC1A
- BT50 Impact Sensor (MAC: F8:FE:92:31:12:E3) - Sensor ID: P1

**System State:**
- ✅ Event labeling system modernized and implemented
- ✅ Device categorization with MAC suffix format working
- ✅ AMG-only testing validated (5-shot sequence successful)
- ✅ BT50 diagnostic confirmed (Temperature: 21.0-21.4°C, streaming at 30Hz)
- ⚠️ BT50 impact detection needs sensitivity tuning
- 🔄 Combined system testing pending

---

### 📋 **IMMEDIATE TESTING PLAN**

#### **Phase 1: BT50-Only Impact Testing**
**Objective:** Validate BT50 sensor detects impacts with maximum sensitivity

**Setup Requirements:**
1. **Configuration:** BT50-only mode (AMG disabled in config.yaml)
2. **Sensitivity:** Maximum detection threshold (any movement = impact)
3. **Bridge Status:** Service running with real-time logging
4. **Session ID:** Track with unique session identifier

**Test Procedure:**
```bash
# 1. Configure BT50-only mode
ssh raspberrypi 'cd ~/projects/steelcity'
# Verify config.yaml has AMG commented out and BT50 sensitivity maxed

# 2. Start bridge service
source .venv/bin/activate
python scripts/run_bridge.py --config config.yaml

# 3. Monitor real-time logging
tail -f logs/bridge_$(date +%Y%m%d).ndjson

# 4. User shooting sequence:
# - Power on BT50 sensor (wait for "Sensor_connected" event)
# - Fire 5-10 shots at target
# - Each impact should generate "Sensor_HIT" event with timestamp
```

**Expected Output Format:**
```json
{"timestamp": "2025-08-31T02:15:23.456Z", "event_type": "Sensor_connected", "device_category": "Impact Sensor", "device_id": "12E3", "sensor_id": "P1"}
{"timestamp": "2025-08-31T02:16:45.123Z", "event_type": "Sensor_HIT", "device_category": "Impact Sensor", "device_id": "12E3", "sensor_id": "P1", "magnitude": 15.2}
```

**Success Criteria:**
- [ ] BT50 connects and maintains stable connection
- [ ] Each shot generates corresponding "Sensor_HIT" event
- [ ] Timestamps show proper chronological sequence
- [ ] No false positives or missed impacts

---

#### **Phase 2: Combined AMG+BT50 Testing**
**Objective:** Validate synchronized timing between timer start and impact detection

**Setup Requirements:**
1. **Configuration:** Enable both AMG and BT50 in config.yaml
2. **Bridge Status:** Both devices connected simultaneously
3. **Timing Analysis:** Correlate T0 signals with impact events

**Test Procedure:**
```bash
# 1. Configure combined mode
# Enable both AMG and BT50 sensors in config.yaml

# 2. Start bridge with both devices
python scripts/run_bridge.py --config config.yaml
# Wait for both "Timer_connected" and "Sensor_connected" events

# 3. Execute synchronized test sequence:
# - Press AMG start button (generates Timer_START_BTN)
# - Fire shots during timing window
# - Each shot should generate both AMG timing and BT50 impact

# 4. Monitor for complete event sequence
tail -f logs/bridge_$(date +%Y%m%d).ndjson | grep -E "(Timer_|Sensor_)"
```

**Expected Time Sequence Log:**
```json
{"timestamp": "2025-08-31T02:20:00.000Z", "event_type": "Timer_START_BTN", "device_category": "Smart Timer", "device_id": "DC1A"}
{"timestamp": "2025-08-31T02:20:00.580Z", "event_type": "Shot_detected", "device_category": "Smart Timer", "device_id": "DC1A", "shot_time": 0.58, "split_time": 0.58}
{"timestamp": "2025-08-31T02:20:00.585Z", "event_type": "Sensor_HIT", "device_category": "Impact Sensor", "device_id": "12E3", "sensor_id": "P1", "magnitude": 12.7}
{"timestamp": "2025-08-31T02:20:00.950Z", "event_type": "Shot_detected", "device_category": "Smart Timer", "device_id": "DC1A", "shot_time": 0.95, "split_time": 0.37}
{"timestamp": "2025-08-31T02:20:00.955Z", "event_type": "Sensor_HIT", "device_category": "Impact Sensor", "device_id": "12E3", "sensor_id": "P1", "magnitude": 14.3}
```

**Analysis Requirements:**
- [ ] Correlate AMG shot timing with BT50 impact detection
- [ ] Measure timing offset between timer and impact (typically 5-10ms)
- [ ] Verify shot count matches between both systems
- [ ] Generate timing correlation report

---

### 🔧 **Current Configuration Status**

**config.yaml (BT50-only mode):**
```yaml
# amg: [COMMENTED OUT FOR BT50-ONLY TESTING]
sensors:
  - plate: "P1"
    adapter: "hci0"
    mac: "F8:FE:92:31:12:E3"
    notify_uuid: "0000ffe4-0000-1000-8000-00805f9a34fb"
    config_uuid: "0000ffe9-0000-1000-8000-00805f9a34fb"
detector:
  triggerHigh: 0.5   # Maximum sensitivity
  triggerLow: 0.1    # Minimal release threshold
  ring_min_ms: 10    # Short detection window
  dead_time_ms: 50   # Short dead time
```

**Bridge Service Status:**
- **Location:** `~/projects/steelcity/scripts/run_bridge.py`
- **Virtual Environment:** Required (`source .venv/bin/activate`)
- **Log Directory:** `~/projects/steelcity/logs/`
- **Current Issues:** Bridge startup failed - needs troubleshooting

---

### 🚨 **Known Issues & Troubleshooting**

**Bridge Startup Problem:**
- **Issue:** `python scripts/run_bridge.py --config config.yaml` exits with code 1
- **Status:** Unresolved - needs immediate attention
- **Next Step:** Debug bridge startup in virtual environment

**BT50 Sensitivity:**
- **Issue:** Previous test detected 0 impacts during shooting session
- **Solution:** Implemented maximum sensitivity settings
- **Status:** Ready for retest

**Event Naming:**
- **Status:** ✅ Completed - New naming convention implemented
- **Format:** Timer_* events for AMG, Sensor_* events for BT50

---

### 📁 **Key Files & Tools**

**Configuration:**
- `config.yaml` - Main system configuration
- `config.example.yaml` - Template with documentation

**Bridge Service:**
- `src/steelcity_impact_bridge/bridge.py` - Main bridge logic
- `scripts/run_bridge.py` - Service startup script

**Diagnostic Tools:**
- `tools/wtvb_live_decode.py --mac F8:FE:92:31:12:E3` - BT50 temperature/status
- `tools/ble_connect_test.py --bt50 F8:FE:92:31:12:E3` - BT50 connection test
- `tools/beautify_ndjson.py` - Log analysis and formatting

**Monitoring:**
- `tail -f logs/bridge_YYYYMMDD.ndjson` - Real-time event monitoring
- `tools/summarize_ndjson.py` - Session analysis and statistics

---

### 🎯 **Next Session Priorities**

1. **CRITICAL:** Debug and fix bridge service startup issue
2. **TEST:** BT50-only impact detection with maximum sensitivity
3. **TEST:** Combined AMG+BT50 with timing correlation analysis
4. **ANALYZE:** Generate time sequence correlation report
5. **TUNE:** Optimize BT50 sensitivity based on test results

---

### 📝 **Session Notes**

**Accomplishments:**
- Successfully modernized event labeling system
- Implemented device categorization and identification
- Validated AMG protocol analysis and shot detection
- Confirmed BT50 hardware health and connectivity
- Committed all changes to GitHub (commit: af6fc16)

**Outstanding Questions:**
- BT50 impact sensitivity calibration requirements
- Optimal timing correlation thresholds for shot matching
- False positive rate with maximum sensitivity settings

**Testing Environment:**
- **Date:** August 31, 2025
- **Hardware:** Raspberry Pi 4B, AMG Timer, BT50 Sensor
- **Software:** Updated bridge service with new event system
- **Repository:** All changes committed to GitHub main branch

---

### 📞 **Contact & Handoff**

**Repository:** https://github.com/J2WFFDev/SteelCity  
**Branch:** main  
**Last Commit:** af6fc16 - "Major update: Event labeling modernization and system testing"

**Immediate Action Required:**
1. Troubleshoot bridge service startup
2. Execute BT50-only testing protocol
3. Proceed to combined system validation

**Testing Readiness:** ⚠️ Ready pending bridge service resolution