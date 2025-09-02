# Bridge Test Protocol
## SteelCity AMG Timer Integration Testing

### 🎯 **Test Objective**
Validate the complete bridge service integration with AMG timer, ensuring proper event capture and chronological sequence logging from connection through session completion.

---

## 📋 **Bridge Test Sequence**

### **1. Bridge Setup** *(my responsibility)*

#### 1.1 ✅ Kill existing bridge processes
```bash
ssh jrwest@192.168.1.173 "pkill -f run_bridge"
```

#### 1.2 ✅ Reset Bluetooth adapter  
```bash
ssh jrwest@192.168.1.173 "sudo systemctl restart bluetooth"
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

### **2. AMG Timer Preparation** *(your responsibility - I should ASK you to do this)*

#### 2.1 🔴 I should tell you: *"Please turn on your AMG timer"*

#### 2.2 🔴 I should wait for: You to confirm timer is on and ready

#### 2.3 🔴 I should verify: Bridge log shows `Timer_connected` with device DC1A

---

### **3. Shooting Test** *(your responsibility - I should guide you)*

#### 3.1 🔴 I should tell you: *"Please press the start button on your timer"*

#### 3.2 🔴 I should tell you: *"Perform your 7-shot sequence"*

#### 3.3 🔴 I should tell you: *"Let me know when you're done shooting"*

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
- [ ] Bridge starts without errors
- [ ] AMG timer connects successfully (`Timer_CONNECTED` event)
- [ ] Device ID shows "DC1A" from MAC 60:09:C3:1F:DC:1A

### **Shooting Phase**  
- [ ] Start button press generates `Timer_START_BTN` event
- [ ] Audio beep generates `Timer_T0` baseline event
- [ ] Each shot generates individual `SHOT_RAW` events
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
# Check for process conflicts
ssh jrwest@192.168.1.173 "ps aux | grep run_bridge"

# Verify virtual environment
ssh jrwest@192.168.1.173 "cd ~/projects/steelcity && source .venv/bin/activate && which python"
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