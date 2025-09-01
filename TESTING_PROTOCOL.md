# BT50 & Combined System Testing Protocol
## SteelCity Impact Detection System

### 🎯 **Testing Objectives**

1. **BT50-Only Testing:** Validate impact sensor detects shots with maximum sensitivity
2. **Combined Testing:** Correlate AMG timer signals with BT50 impact detection
3. **Time Sequence Analysis:** Generate chronological log of all events

---

## 📋 **TEST 1: BT50-Only Impact Detection**

### **Pre-Test Setup**
```bash
# Connect to Raspberry Pi
ssh raspberrypi
cd ~/projects/steelcity

# Verify BT50-only configuration
cat config.yaml
# Ensure AMG section is commented out
# Ensure BT50 sensitivity is maximized (triggerHigh: 0.5)
```

### **Configuration Verification**
**Expected config.yaml state:**
```yaml
# amg: [COMMENTED OUT]
sensors:
  - plate: "P1"
    mac: "F8:FE:92:31:12:E3"
detector:
  triggerHigh: 0.5   # Maximum sensitivity
  triggerLow: 0.1
  ring_min_ms: 10
  dead_time_ms: 50
```

### **Test Execution Sequence**

#### **Step 1: Start Bridge Service**
```bash
source .venv/bin/activate
python scripts/run_bridge.py --config config.yaml
# Wait for successful startup (no error messages)
```

#### **Step 2: Monitor Real-Time Logging**
```bash
# In separate terminal:
ssh raspberrypi 'cd ~/projects/steelcity && tail -f logs/bridge_$(date +%Y%m%d).ndjson'
```

#### **Step 3: Power On BT50 Sensor**
**User Action:** Power on BT50 sensor and wait for connection
**Expected Event:**
```json
{"timestamp": "2025-08-31T...", "event_type": "Sensor_connecting", "device_category": "Impact Sensor", "device_id": "12E3", "sensor_id": "P1"}
{"timestamp": "2025-08-31T...", "event_type": "Sensor_connected", "device_category": "Impact Sensor", "device_id": "12E3", "sensor_id": "P1"}
```

#### **Step 4: Execute Shooting Sequence**
**User Action:** Fire 5-10 shots at target with BT50 sensor
**Expected Events per Shot:**
```json
{"timestamp": "2025-08-31T...", "event_type": "Sensor_HIT", "device_category": "Impact Sensor", "device_id": "12E3", "sensor_id": "P1", "magnitude": X.X}
```

### **Success Criteria - BT50 Test**
- [ ] BT50 connects successfully (`Sensor_connected` event)
- [ ] Each shot generates `Sensor_HIT` event
- [ ] Impact count matches actual shot count
- [ ] No false positives during idle time
- [ ] Timestamps show proper chronological sequence

---

## 📋 **TEST 2: Combined AMG+BT50 Testing**

### **Pre-Test Configuration Change**
```bash
# Edit config.yaml to enable both devices
nano config.yaml
# Uncomment AMG section
# Keep BT50 configuration active
```

**Expected config.yaml state:**
```yaml
amg:
  adapter: "hci0"
  mac: "60:09:C3:1F:DC:1A"
  # ... [full AMG configuration]
sensors:
  - plate: "P1"
    mac: "F8:FE:92:31:12:E3"
    # ... [full BT50 configuration]
```

### **Test Execution Sequence**

#### **Step 1: Start Combined Bridge Service**
```bash
# Stop existing service
pkill -f run_bridge
# Start with both devices
source .venv/bin/activate
python scripts/run_bridge.py --config config.yaml
```

#### **Step 2: Verify Dual Connection**
**Expected Events:**
```json
{"timestamp": "...", "event_type": "Timer_connecting", "device_category": "Smart Timer", "device_id": "DC1A"}
{"timestamp": "...", "event_type": "Timer_connected", "device_category": "Smart Timer", "device_id": "DC1A"}
{"timestamp": "...", "event_type": "Sensor_connecting", "device_category": "Impact Sensor", "device_id": "12E3"}
{"timestamp": "...", "event_type": "Sensor_connected", "device_category": "Impact Sensor", "device_id": "12E3"}
```

#### **Step 3: Execute Synchronized Test Sequence**

**User Actions:**
1. Press AMG timer start button
2. Fire shots during timing window
3. Complete shooting sequence

**Expected Event Sequence:**
```json
{"timestamp": "2025-08-31T02:20:00.000Z", "event_type": "Timer_START_BTN", "device_category": "Smart Timer", "device_id": "DC1A"}

{"timestamp": "2025-08-31T02:20:00.580Z", "event_type": "Shot_detected", "device_category": "Smart Timer", "device_id": "DC1A", "shot_time": 0.58, "split_time": 0.58}
{"timestamp": "2025-08-31T02:20:00.585Z", "event_type": "Sensor_HIT", "device_category": "Impact Sensor", "device_id": "12E3", "sensor_id": "P1", "magnitude": 12.7}

{"timestamp": "2025-08-31T02:20:00.950Z", "event_type": "Shot_detected", "device_category": "Smart Timer", "device_id": "DC1A", "shot_time": 0.95, "split_time": 0.37}
{"timestamp": "2025-08-31T02:20:00.955Z", "event_type": "Sensor_HIT", "device_category": "Impact Sensor", "device_id": "12E3", "sensor_id": "P1", "magnitude": 14.3}

{"timestamp": "2025-08-31T02:20:01.310Z", "event_type": "Shot_detected", "device_category": "Smart Timer", "device_id": "DC1A", "shot_time": 1.31, "split_time": 0.36}
{"timestamp": "2025-08-31T02:20:01.315Z", "event_type": "Sensor_HIT", "device_category": "Impact Sensor", "device_id": "12E3", "sensor_id": "P1", "magnitude": 13.2}
```

### **Success Criteria - Combined Test**
- [ ] Both devices connect successfully
- [ ] Timer START_BTN event triggers sequence
- [ ] Each AMG shot has corresponding BT50 impact
- [ ] Timing correlation within 5-20ms window
- [ ] Shot counts match between systems
- [ ] Chronological sequence maintained

---

## 📊 **Analysis & Reporting**

### **Real-Time Monitoring Commands**
```bash
# Monitor all events
tail -f logs/bridge_$(date +%Y%m%d).ndjson

# Filter timer events only
tail -f logs/bridge_$(date +%Y%m%d).ndjson | grep "Timer_"

# Filter sensor events only  
tail -f logs/bridge_$(date +%Y%m%d).ndjson | grep "Sensor_"

# Monitor shot correlation
tail -f logs/bridge_$(date +%Y%m%d).ndjson | grep -E "(Shot_detected|Sensor_HIT)"
```

### **Post-Test Analysis**
```bash
# Generate session summary
python tools/summarize_ndjson.py logs/bridge_$(date +%Y%m%d).ndjson

# Beautify log output
python tools/beautify_ndjson.py logs/bridge_$(date +%Y%m%d).ndjson

# Extract specific session data
python tools/last_session.py
```

### **Time Correlation Analysis**

**Key Metrics to Measure:**
- **Timer→Impact Delay:** Time between `Shot_detected` and `Sensor_HIT`
- **Shot Count Accuracy:** AMG shots vs BT50 impacts
- **False Positive Rate:** Unexpected `Sensor_HIT` events
- **Missed Detection Rate:** `Shot_detected` without corresponding `Sensor_HIT`

**Expected Timing Offsets:**
- Projectile flight time: 1-5ms (depending on distance)
- Impact sensor response: 2-10ms
- BLE transmission delay: 1-5ms
- **Total expected offset:** 5-20ms (BT50 after AMG)

---

## 🔧 **Troubleshooting Guide**

### **Bridge Service Won't Start**
```bash
# Check error output
python scripts/run_bridge.py --config config.yaml 2>&1

# Verify virtual environment
source .venv/bin/activate
which python
pip list | grep bleak

# Check config syntax
python -c "import yaml; print(yaml.safe_load(open('config.yaml')))"
```

### **BT50 Not Connecting**
```bash
# Test direct connection
source .venv/bin/activate
python tools/ble_connect_test.py --bt50 F8:FE:92:31:12:E3

# Check BT50 status
python tools/wtvb_live_decode.py --mac F8:FE:92:31:12:E3
```

### **No Impact Detection**
```bash
# Test manual impact (tap target)
# Should generate Sensor_HIT event

# Check sensitivity settings in config.yaml
# Reduce triggerHigh value for higher sensitivity

# Verify BT50 placement on target backing
```

### **AMG Connection Issues**
```bash
# Test AMG connection
python tools/ble_connect_test.py --amg 60:09:C3:1F:DC:1A

# Check AMG signals
python tools/watch_amg.py 60:09:C3:1F:DC:1A
```

---

## 📝 **Test Execution Checklist**

### **BT50-Only Test**
- [ ] Config verified (AMG disabled, BT50 sensitivity maxed)
- [ ] Bridge service starts successfully
- [ ] BT50 connects and shows `Sensor_connected`
- [ ] Execute 5-10 shot sequence
- [ ] Verify each shot generates `Sensor_HIT`
- [ ] Record shot count and timing data

### **Combined Test**
- [ ] Config updated (both AMG and BT50 enabled)
- [ ] Bridge service restarts with dual devices
- [ ] Both devices connect successfully
- [ ] Press AMG start button
- [ ] Execute synchronized shooting sequence  
- [ ] Verify timing correlation between systems
- [ ] Generate correlation analysis report

### **Post-Test Actions**
- [ ] Save log files with session identifier
- [ ] Generate summary statistics
- [ ] Document any anomalies or issues
- [ ] Update configuration based on results
- [ ] Commit findings to repository