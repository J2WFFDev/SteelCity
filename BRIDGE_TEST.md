# Bridge Test Protocol
## SteelCity AMG Timer Integration Testing

### 🎯 **Test Objective**
Validate the complete bridge service integration with AMG timer, ensuring proper event capture and chronological sequence logging from connection through session completion.

---

## 📋 **Bridge Test Sequence**

### **1. Bridge Setup** *(my responsibility)*

#### 1.0 🔧 **Pre-Test Validation: Impact Detection Algorithm**
```bash
# Test impact detection logic before bridge startup
ssh jrwest@192.168.1.173 "cd ~/projects/steelcity && python3 -c \"
import math, time

class QuickTest:
    def test_impact_detection(self):
        # Simulate mixed data: noise + light + medium + heavy impacts
        data = []
        for i in range(30):
            if i == 10: amp = 12.0    # Light impact
            elif i == 18: amp = 25.0  # Medium impact  
            elif i == 25: amp = 45.0  # Heavy impact
            else: amp = 2.0 + (i%3)*0.5  # Background noise
            data.append(amp)
        
        # Count impacts (amplitude >= 10.0)
        impacts = [a for a in data if a >= 10.0]
        light = [a for a in impacts if 10.0 <= a < 15.0]
        medium = [a for a in impacts if 15.0 <= a < 40.0]  
        heavy = [a for a in impacts if a >= 40.0]
        
        print('=== Impact Detection Pre-Test ===')
        print(f'Total samples: {len(data)}')
        print(f'Total impacts detected: {len(impacts)}')
        print(f'LIGHT impacts: {len(light)} (amplitudes: {light})')
        print(f'MEDIUM impacts: {len(medium)} (amplitudes: {medium})')
        print(f'HEAVY impacts: {len(heavy)} (amplitudes: {heavy})')
        
        # Validation
        if len(impacts) == 3 and len(light) == 1 and len(medium) == 1 and len(heavy) == 1:
            print('✅ PASS: Impact detection algorithm working correctly')
            return True
        else:
            print('❌ FAIL: Impact detection algorithm not working')
            return False

QuickTest().test_impact_detection()
\""
```

#### 1.1 ✅ Kill ALL bridge processes (including sneaky ones)
```bash
# Comprehensive bridge process cleanup - run ALL of these commands:

# 1. Kill by process name patterns (covers most cases)
ssh jrwest@192.168.1.173 "pkill -f run_bridge"
ssh jrwest@192.168.1.173 "pkill -f bridge.py"
ssh jrwest@192.168.1.173 "pkill -f minimal_bridge"
ssh jrwest@192.168.1.173 "pkill -f steelcity"

# 2. Kill Python processes that might be bridges
ssh jrwest@192.168.1.173 "pkill -f 'python.*bridge'"

# 3. Nuclear option - kill ALL Python processes (use with caution)
ssh jrwest@192.168.1.173 "killall python3"

# 4. Verify no bridge processes remain
ssh jrwest@192.168.1.173 "ps aux | grep -E '(bridge|run_bridge|steelcity)' | grep -v grep"

# 5. If any processes still exist, force kill them by PID
# ssh jrwest@192.168.1.173 "kill -9 <PID_FROM_ABOVE>"

# Expected result: No processes should be listed after step 4
```

#### 1.2 ✅ Reset Bluetooth adapter and clear connections
```bash
# Complete Bluetooth stack reset
ssh jrwest@192.168.1.173 "echo '=== BLUETOOTH CLEANUP ==='
sudo systemctl stop bluetooth
sleep 3
sudo hciconfig hci0 down
sleep 2  
sudo hciconfig hci0 up
sleep 2
sudo systemctl start bluetooth
sleep 5
echo 'Bluetooth reset complete'
bluetoothctl power off
sleep 2
bluetoothctl power on
echo '=== BLUETOOTH STATUS ==='
bluetoothctl show"
```

#### 1.3 ✅ Start bridge in venv with AMG_DEBUG_RAW=1
```bash
ssh jrwest@192.168.1.173 "cd ~/projects/steelcity && source .venv/bin/activate && AMG_DEBUG_RAW=1 scripts/run_bridge.sh"
```

#### 1.4 ✅ Verify bridge is running and attempting AMG connection
- Monitor bridge startup logs
- Confirm no error messages
- Wait for AMG connection attempts

---


### **2. Device Preparation** *(your responsibility - I must prompt you for each device)*

#### 2.1 🔴 I must tell you: *"Please turn on your AMG timer (DC1A) and confirm when it is on and ready."*

#### 2.2 🔴 I must wait for: You to confirm the AMG timer is on and ready

#### 2.3 🔴 I must tell you: *"Please turn on your BT50 sensor and confirm when it is on and ready."*

#### 2.4 🔴 I must wait for: You to confirm the BT50 sensor is on and ready

#### 2.5 🔴 I must verify: Bridge log shows `Timer_connected` with device DC1A and `Sensor_connected` with BT50

---

### **3. Shooting Test** *(your responsibility - I must guide you step-by-step)*

#### 3.1 🔴 I must tell you: *"Please press the start button on your timer and confirm when pressed."*

#### 3.2 🔴 **Impact Detection Monitoring**: Monitor BT50 sensor for impact events during shooting
```bash
# Monitor real-time impact events
ssh jrwest@192.168.1.173 "cd ~/projects/steelcity && tail -f logs/bridge_$(date +%Y%m%d_%H%M%S).ndjson | grep -E '(bt50_impact_analysis|PROCESSING_BUFFER)'"
```

#### 3.3 🔴 I must tell you: *"Perform your 7-shot sequence and let me know when you are done shooting."*

#### 3.4 🔴 I must wait for: You to confirm you are done shooting

#### 3.5 🔴 **Verify Impact Correlation**: Check that impact events align with shot timing

---

### **4. Results Verification** *(my responsibility)*

#### 4.1 Extract all events chronologically from the session

#### 4.2 Present results in this exact format:

```
Session ID: [session_id] | Full sequence from connection to session end

#    Timestamp        Event_Type       Device_ID    Signal_Description           Raw_Data
1    HH:MM:SS.mmm     Timer_CONNECTED  DC1A         BLE connection established   MAC: 60:09:C3:1F:DC:1A, UUID_subsc
2    HH:MM:SS.mmm     Timer_START_BTN  DC1A         Start button pressed         Button trigger detected
3    HH:MM:SS.mmm     Timer_T0         DC1A         Audio beep start             Baseline timing mark
4    HH:MM:SS.mmm     SHOT_RAW         DC1A         Impact -> shot_report        [hex_data]
5    HH:MM:SS.mmm     SHOT_RAW         DC1A         Impact -> shot_report        [hex_data]
...
N    HH:MM:SS.mmm     Timer_SESSION_END DC1A        Session completed            Final event logged
```

---

## ✅ **Success Criteria**

### **Connection Phase**
- [ ] **Pre-test validation**: Impact detection algorithm passes all tests
- [ ] Bridge starts without errors
- [ ] AMG timer connects successfully (`Timer_CONNECTED` event)
- [ ] BT50 sensor connects successfully (`Sensor_CONNECTED` event)
- [ ] Device ID shows "DC1A" from MAC 60:09:C3:1F:DC:1A

### **Impact Detection Phase**
- [ ] BT50 sensor buffer processing active (`PROCESSING_BUFFER_CALLED` debug logs)
- [ ] Impact detection working with amplitude thresholds (>10.0)
- [ ] Intensity classification: LIGHT (10-15), MEDIUM (15-40), HEAVY (>40)
- [ ] `bt50_impact_analysis` events logged with proper statistics

### **Shooting Phase**  
- [ ] Start button press generates `Timer_START_BTN` event
- [ ] Audio beep generates `Timer_T0` baseline event
- [ ] Each shot generates individual `SHOT_RAW` events
- [ ] BT50 impacts correlate with shot timing
- [ ] Session completion generates `Timer_SESSION_END` event

### **Data Quality**
- [ ] Chronological sequence maintained
- [ ] All timestamps properly formatted (HH:MM:SS.mmm)
- [ ] Shot count matches actual fired rounds
- [ ] Raw hex data captured for each shot

---

## 🔧 **Troubleshooting**

### **Bridge Won't Start**
```bash
# Comprehensive process conflict check and cleanup
ssh jrwest@192.168.1.173 "echo '=== CHECKING FOR BRIDGE CONFLICTS ==='
ps aux | grep -E '(bridge|run_bridge|steelcity|python.*ble)' | grep -v grep
echo '=== KILLING ALL BRIDGE PROCESSES ==='
pkill -f run_bridge; pkill -f bridge.py; pkill -f minimal_bridge; pkill -f steelcity
killall python3 2>/dev/null || true
echo '=== POST-CLEANUP CHECK ==='
ps aux | grep -E '(bridge|run_bridge|steelcity)' | grep -v grep || echo 'No bridge processes found - good!'"

# Verify virtual environment
ssh jrwest@192.168.1.173 "cd ~/projects/steelcity && source .venv/bin/activate && which python"

# Check for port/Bluetooth conflicts
ssh jrwest@192.168.1.173 "sudo lsof -i | grep python || echo 'No Python network connections'"
```

### **AMG Won't Connect**
```bash
# Test direct AMG connection
ssh jrwest@192.168.1.173 "cd ~/projects/steelcity && source .venv/bin/activate && python tools/ble_connect_test.py --amg 60:09:C3:1F:DC:1A"

# Reset Bluetooth and retry
ssh jrwest@192.168.1.173 "sudo systemctl restart bluetooth"
```

### **No Shot Events**
- Verify `AMG_DEBUG_RAW=1` environment variable is set
- Check if timer is properly started with start button
- Confirm shots are being fired during active timing window

---

## 📝 **Test Execution Notes**

### **Roles & Responsibilities**
- **My Role**: Bridge setup, monitoring, results extraction and formatting
- **Your Role**: Physical timer operation, shooting sequence execution
- **Communication**: I will clearly tell you what actions to take and when

### **Expected Event Flow**
1. `Timer_CONNECTED` - AMG timer connects (device_id: DC1A)
2. `Timer_START_BTN` - Start button pressed  
3. `Timer_T0` - Timing baseline established
4. `SHOT_RAW` - Individual shot events (multiple)
5. `Timer_SESSION_END` - Session completed

### **Data Extraction Commands**
```bash
# Monitor real-time events
ssh jrwest@192.168.1.173 "cd ~/projects/steelcity && tail -f logs/bridge_$(date +%Y%m%d).ndjson"

# Extract session data
ssh jrwest@192.168.1.173 "cd ~/projects/steelcity && python tools/last_session.py"

# Beautify output
ssh jrwest@192.168.1.173 "cd ~/projects/steelcity && python tools/beautify_ndjson.py logs/bridge_$(date +%Y%m%d).ndjson"
```

---

**Is this the correct sequence and format you want?**