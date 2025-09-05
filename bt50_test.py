#!/usr/bin/env python3
"""
BT50 Specific Connection Test

Focused specifically on connecting to the BT50 sensor with aggressive cleanup
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from bleak import BleakClient, BleakScanner
import struct

class BT50Test:
    def __init__(self):
        self.bt50_mac = "F8:FE:92:31:12:E3"
        self.bt50_uuid = "0000ffe4-0000-1000-8000-00805f9a34fb"  # Correct BT50 UUID from config
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = Path(f"logs/bt50_test_{timestamp}.ndjson")
        self.seq = 0
    
    def log(self, msg_type, message, data=None):
        self.seq += 1
        now = time.time()
        # Per logging policy: do not include machine timestamps (ts_ms/t_iso).
        entry = {
            "type": msg_type,
            "msg": message,
            "data": data or {},
            "hms": datetime.fromtimestamp(now).strftime("%H:%M:%S.%f")[:-3],
            "seq": self.seq
        }
        
        print(f"[{entry['hms']}] {msg_type.upper()}: {message}")
        if data and len(str(data)) < 200:
            print(f"    {data}")
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    async def bt50_handler(self, sender, data):
        """Handle BT50 raw data"""
        hex_data = data.hex()
        self.log("bt50_raw", f"BT50 data ({len(data)} bytes): {hex_data}")
        
        # Try to parse as acceleration
        if len(data) >= 12:
            try:
                if len(data) == 12:
                    vx, vy, vz = struct.unpack('<fff', data)
                    self.log("bt50_accel", f"vx={vx:.3f}, vy={vy:.3f}, vz={vz:.3f}")
                elif len(data) >= 20:
                    parts = struct.unpack('<' + 'f' * (len(data) // 4), data)
                    self.log("bt50_multi", f"Multiple values: {parts}")
            except Exception as e:
                self.log("bt50_parse_error", f"Parse error: {e}")
    
    async def test_bt50_connection(self):
        """Test BT50 connection with detailed steps"""
        self.log("info", "Starting BT50 connection test")
        
        try:
            # Step 1: Extended scan
            self.log("info", "Scanning for BT50 sensor (15 second scan)...")
            devices = await BleakScanner.discover(timeout=15.0)
            
            bt50_device = None
            self.log("info", f"Found {len(devices)} devices in scan")
            
            # Show all devices for debugging
            for device in devices:
                if device.address.upper() == self.bt50_mac.upper():
                    bt50_device = device
                    self.log("success", f"Found BT50: {device.name} at {device.address}")
                    break
                else:
                    self.log("debug", f"Other device: {device.name} at {device.address}")
            
            if not bt50_device:
                self.log("error", "BT50 sensor not found in extended scan")
                return False
            
            # Step 2: Connection attempt with retries
            for attempt in range(3):
                try:
                    self.log("info", f"Connection attempt #{attempt + 1}")
                    
                    client = BleakClient(bt50_device)
                    await client.connect(timeout=20.0)  # Longer timeout
                    
                    if client.is_connected:
                        self.log("success", "BT50 connected successfully!")
                        
                        # Step 3: Enable notifications
                        await client.start_notify(self.bt50_uuid, self.bt50_handler)
                        self.log("success", "BT50 notifications enabled!")
                        
                        # Step 4: Monitor for data
                        self.log("info", "Monitoring BT50 data for 60 seconds...")
                        await asyncio.sleep(60)
                        
                        # Cleanup
                        await client.disconnect()
                        self.log("info", "BT50 disconnected")
                        return True
                    else:
                        self.log("error", f"Connection attempt #{attempt + 1} failed - not connected")
                        
                except Exception as e:
                    self.log("error", f"Connection attempt #{attempt + 1} error: {str(e)}")
                    if attempt < 2:  # Not the last attempt
                        self.log("info", "Waiting 5 seconds before retry...")
                        await asyncio.sleep(5)
            
            self.log("error", "All connection attempts failed")
            return False
            
        except Exception as e:
            self.log("error", f"BT50 test failed: {str(e)}")
            return False

async def main():
    test = BT50Test()
    print("🔧 BT50 Specific Connection Test")
    print("📊 Will scan extensively and try multiple connection attempts")
    print("")
    
    success = await test.test_bt50_connection()
    
    if success:
        print("\n✅ BT50 test completed successfully!")
    else:
        print("\n❌ BT50 test failed")

if __name__ == "__main__":
    asyncio.run(main())