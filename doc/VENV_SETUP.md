# Virtual Environment Setup for BT50 Compatibility

## Overview
This document covers virtual environment setup for the SteelCity Impact Bridge, specifically for BT50 sensor compatibility.

## Current Status

### AMG Timer Support
- ✅ **Works with system Python** (`/usr/bin/python3.11`)
- ✅ **Works with virtual environment** (`.venv/bin/python`)
- ✅ **Individual shot detection confirmed** via BT Test

### Virtual Environment Investigation Results

#### Bridge Script Behavior
The `scripts/run_bridge.sh` attempts venv activation but may fall back to system Python:
```bash
# Current behavior in run_bridge.sh
if [[ -d .venv ]]; then
    source .venv/bin/activate || true
fi
```

#### Confirmed Working Setups
1. **System Python**: `python -m scripts.run_bridge --config config.yaml`
2. **Manual venv**: `source .venv/bin/activate && python -m scripts.run_bridge --config config.yaml`

#### Package Requirements
Virtual environment includes all required packages:
```
bleak                   1.1.0
steelcity-impact-bridge 0.1.0   /home/jrwest/projects/steelcity
```

## BT50 Compatibility Preparation

### Why venv is Recommended for BT50
- **BLE library isolation**: `bleak` works better in controlled environments
- **Permission management**: Avoids conflicts with system-level Bluetooth packages
- **Dependency stability**: Prevents version conflicts

### Setup Commands
```bash
# Install in development mode (required)
cd ~/projects/steelcity
source .venv/bin/activate
pip install -e .

# Start bridge in venv
AMG_DEBUG_RAW=1 bash -c 'source .venv/bin/activate && ./scripts/run_bridge.sh'
```

### Verification Commands
```bash
# Check if bridge is running
ps aux | grep run_bridge | grep -v grep

# Check which Python is being used
readlink -f /proc/[PID]/exe

# Monitor bridge logs
tail -f logs/bridge_*.ndjson

# Check for connections
grep "Timer_connected\|Sensor_connected" logs/bridge_*.ndjson
```

## Recommendations

### For AMG Timer Development
- Current system Python setup is sufficient
- AMG individual shot detection confirmed working

### For BT50 Integration
1. **Always use virtual environment**
2. **Ensure `pip install -e .` is run**
3. **Test BLE functionality thoroughly**
4. **Document any venv-specific requirements**

## Test Results

### Successful BT Test (Session ID: 1571417576)
- ✅ 8 unique shots detected correctly
- ✅ Perfect session lifecycle: Connection → Start → T0 → Shots → End
- ✅ Proper SHOT_RAW event format matching BT50_RAW specification
- ✅ AMG_DEBUG_RAW=1 producing both debug and production events

### BT Test Format Confirmed
| Event Type        | Device ID | Signal Description    | Status |
|-------------------|-----------|----------------------|---------|
| Timer_connected   | DC1A      | BLE connection       | ✅ Working |
| Timer_START_BTN   | DC1A      | Start button pressed | ✅ Working |
| Timer_T0          | DC1A      | Audio beep start     | ✅ Working |
| SHOT_RAW          | DC1A      | Impact → shot_report | ✅ Working |
| Timer_SESSION_END | DC1A      | Session completed    | ✅ Working |

## Next Steps for BT50
1. Add BT50 sensor configuration to `config.yaml`
2. Test `bleak` BLE connectivity in venv environment
3. Validate BT50_RAW event format compatibility
4. Document any BT50-specific setup requirements