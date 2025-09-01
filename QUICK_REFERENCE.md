# Quick Testing Commands Reference
## SteelCity Impact Detection System

### 🔧 **Bridge Service Management**
```bash
# Connect to Pi
ssh raspberrypi
cd ~/projects/steelcity

# Start bridge (BT50-only)
source .venv/bin/activate
python scripts/run_bridge.py --config config.yaml

# Stop bridge
pkill -f run_bridge

# Check bridge status
ps aux | grep run_bridge
```

### 📊 **Real-Time Monitoring**
```bash
# Monitor all events
tail -f logs/bridge_$(date +%Y%m%d).ndjson

# Filter by device type
tail -f logs/bridge_$(date +%Y%m%d).ndjson | grep "Timer_"    # AMG events
tail -f logs/bridge_$(date +%Y%m%d).ndjson | grep "Sensor_"   # BT50 events

# Monitor shot correlation
tail -f logs/bridge_$(date +%Y%m%d).ndjson | grep -E "(Shot_detected|Sensor_HIT)"

# Beautified output
tail -f logs/bridge_$(date +%Y%m%d).ndjson | python tools/beautify_ndjson.py -
```

### 🔍 **Diagnostic Commands**
```bash
# BT50 temperature and status
source .venv/bin/activate
python tools/wtvb_live_decode.py --mac F8:FE:92:31:12:E3

# BT50 connection test
python tools/ble_connect_test.py --bt50 F8:FE:92:31:12:E3

# AMG connection test
python tools/ble_connect_test.py --amg 60:09:C3:1F:DC:1A

# AMG signal monitoring
python tools/watch_amg.py 60:09:C3:1F:DC:1A
```

### ⚙️ **Configuration Quick Switch**

**BT50-Only Mode:**
```yaml
# Comment out AMG section in config.yaml
# amg:
#   adapter: "hci0"
#   mac: "60:09:C3:1F:DC:1A"
#   ...

sensors:
  - plate: "P1"
    mac: "F8:FE:92:31:12:E3"
detector:
  triggerHigh: 0.5   # Max sensitivity
```

**Combined Mode:**
```yaml
amg:
  adapter: "hci0"
  mac: "60:09:C3:1F:DC:1A"
  # ... [full config]

sensors:
  - plate: "P1"
    mac: "F8:FE:92:31:12:E3"
```

### 📈 **Analysis Tools**
```bash
# Session summary
python tools/summarize_ndjson.py logs/bridge_$(date +%Y%m%d).ndjson

# Last session data
python tools/last_session.py

# Validate log format
python tools/validate_logs.py logs/bridge_$(date +%Y%m%d).ndjson
```

### 🎯 **Testing Sequence Checklist**

**BT50 Test:**
1. ✅ Configure BT50-only mode
2. ✅ Start bridge service  
3. ✅ Power on BT50 → Wait for `Sensor_connected`
4. ✅ Shoot 5-10 rounds → Verify `Sensor_HIT` events
5. ✅ Count impacts vs actual shots

**Combined Test:**
1. ✅ Enable both AMG and BT50
2. ✅ Start bridge → Verify dual connection
3. ✅ Press AMG start button → `Timer_START_BTN`
4. ✅ Shoot sequence → Correlate `Shot_detected` + `Sensor_HIT`
5. ✅ Analyze timing offset (5-20ms expected)

### 🚨 **Emergency Commands**
```bash
# Kill all bridge processes
pkill -f run_bridge
pkill -f bridge.py

# Reset Bluetooth
sudo systemctl restart bluetooth

# Check system resources
htop
df -h
```

### 📝 **Expected Event Samples**

**BT50 Connection:**
```json
{"timestamp": "2025-08-31T02:15:23.456Z", "event_type": "Sensor_connected", "device_category": "Impact Sensor", "device_id": "12E3", "sensor_id": "P1"}
```

**BT50 Impact:**
```json
{"timestamp": "2025-08-31T02:16:45.123Z", "event_type": "Sensor_HIT", "device_category": "Impact Sensor", "device_id": "12E3", "sensor_id": "P1", "magnitude": 15.2}
```

**AMG Timer Start:**
```json
{"timestamp": "2025-08-31T02:20:00.000Z", "event_type": "Timer_START_BTN", "device_category": "Smart Timer", "device_id": "DC1A"}
```

**AMG Shot Detection:**
```json
{"timestamp": "2025-08-31T02:20:00.580Z", "event_type": "Shot_detected", "device_category": "Smart Timer", "device_id": "DC1A", "shot_time": 0.58, "split_time": 0.58}
```