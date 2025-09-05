#!/usr/bin/env python3
"""
Minimal Bridge - Continuous Connection Monitor

This bridge:
1. Continuously scans for AMG timer and BT50 sensor
2. Connects when devices become available 
3. Logs raw data exactly as received
4. No processing, no analysis, no calculations

Purpose: Stay running and wait for devices to be powered on
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from bleak import BleakClient, BleakScanner
import struct
import logging

class ContinuousMinimalBridge:
    def __init__(self):
        # Device configurations
        self.amg_timer_mac = "60:09:C3:1F:DC:1A"
        self.bt50_sensor_mac = "F8:FE:92:31:12:E3"
        
        # UUIDs for notifications
        self.amg_notify_uuid = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
        self.bt50_notify_uuid = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
        
        # Connection state
        self.amg_client = None
        self.bt50_client = None
        
        # Logging
        self.session_id = str(int(time.time()))
        self.seq_counter = 0
        
        # Setup log file
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"continuous_bridge_{timestamp}.ndjson"
        
        print(f"🔄 Continuous Minimal Bridge starting")
        print(f"📁 Logging to: {self.log_file}")
        print(f"🔍 Will scan for devices every 10 seconds")
        print(f"💡 Power on your devices when ready...")
        print("")
        
    def log(self, msg_type, message, data=None):
        """Log an event in NDJSON format"""
        self.seq_counter += 1
        now = time.time()
        
        # Per logging policy: do not include machine timestamps (ts_ms/t_iso).
        log_entry = {
            "type": msg_type,
            "msg": message,
            "data": data or {},
            "hms": datetime.fromtimestamp(now).strftime("%H:%M:%S.%f")[:-3],
            "seq": self.seq_counter,
            "schema": "continuous_v1",
            "session_id": self.session_id
        }
        
        # Print to console with emojis for easy reading
        emoji = {"success": "✅", "error": "❌", "info": "ℹ️", "amg_raw": "🎯", "bt50_raw": "📊", "status": "🔄"}
        print(f"{emoji.get(msg_type, '📝')} [{log_entry['hms']}] {message}")
        if data and len(str(data)) < 100:  # Don't spam with huge data
            print(f"    📋 {data}")
        
        # Write to log file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    
    async def amg_notification_handler(self, sender, data):
        """Handle raw AMG timer notifications"""
        hex_data = data.hex()
        self.log("amg_raw", f"AMG timer data ({len(data)} bytes)", {
            "hex": hex_data,
            "bytes": len(data)
        })
        
        # Try to interpret as ASCII
        try:
            ascii_data = data.decode('ascii', errors='ignore').strip()
            if ascii_data:
                self.log("amg_ascii", f"AMG ASCII: '{ascii_data}'")
        except:
            pass
    
    async def bt50_notification_handler(self, sender, data):
        """Handle raw BT50 sensor notifications"""
        hex_data = data.hex()
        self.log("bt50_raw", f"BT50 sensor data ({len(data)} bytes)", {
            "hex": hex_data,
            "bytes": len(data)
        })
        
        # Try to parse as acceleration data
        if len(data) >= 12:
            try:
                if len(data) == 12:
                    vx, vy, vz = struct.unpack('<fff', data)
                    self.log("bt50_accel", f"BT50 accel: vx={vx:.3f}, vy={vy:.3f}, vz={vz:.3f}")
            except Exception as e:
                self.log("bt50_parse_error", f"Parse error: {str(e)}")
    
    async def try_connect_amg(self):
        """Try to connect to AMG timer"""
        if self.amg_client and self.amg_client.is_connected:
            return True
        
        try:
            self.log("info", "🔍 Scanning for AMG timer...")
            devices = await BleakScanner.discover(timeout=5.0)
            
            for device in devices:
                if device.address.upper() == self.amg_timer_mac.upper():
                    self.log("info", f"📍 Found AMG timer: {device.name} (RSSI: {device.rssi})")
                    
                    try:
                        self.amg_client = BleakClient(device)
                        await self.amg_client.connect()
                        await self.amg_client.start_notify(self.amg_notify_uuid, self.amg_notification_handler)
                        self.log("success", "🎯 AMG timer connected and notifications enabled!")
                        return True
                    except Exception as e:
                        self.log("error", f"AMG connection failed: {str(e)}")
                        self.amg_client = None
                        return False
            
            # Not found in scan
            return False
            
        except Exception as e:
            self.log("error", f"AMG scan failed: {str(e)}")
            return False
    
    async def try_connect_bt50(self):
        """Try to connect to BT50 sensor"""
        if self.bt50_client and self.bt50_client.is_connected:
            return True
        
        try:
            self.log("info", "🔍 Scanning for BT50 sensor...")
            devices = await BleakScanner.discover(timeout=5.0)
            
            for device in devices:
                if device.address.upper() == self.bt50_sensor_mac.upper():
                    self.log("info", f"📍 Found BT50 sensor: {device.name} (RSSI: {device.rssi})")
                    
                    try:
                        self.bt50_client = BleakClient(device)
                        await self.bt50_client.connect()
                        await self.bt50_client.start_notify(self.bt50_notify_uuid, self.bt50_notification_handler)
                        self.log("success", "📊 BT50 sensor connected and notifications enabled!")
                        return True
                    except Exception as e:
                        self.log("error", f"BT50 connection failed: {str(e)}")
                        self.bt50_client = None
                        return False
            
            # Not found in scan
            return False
            
        except Exception as e:
            self.log("error", f"BT50 scan failed: {str(e)}")
            return False
    
    async def monitor_connections(self):
        """Continuously monitor and maintain connections"""
        scan_count = 0
        
        while True:
            try:
                scan_count += 1
                
                # Check current connection status
                amg_connected = self.amg_client and self.amg_client.is_connected
                bt50_connected = self.bt50_client and self.bt50_client.is_connected
                
                # Try to connect to missing devices
                if not amg_connected:
                    await self.try_connect_amg()
                
                if not bt50_connected:
                    await self.try_connect_bt50()
                
                # Status update every few scans
                if scan_count % 3 == 0:
                    amg_status = "✅ Connected" if (self.amg_client and self.amg_client.is_connected) else "❌ Disconnected"
                    bt50_status = "✅ Connected" if (self.bt50_client and self.bt50_client.is_connected) else "❌ Disconnected"
                    
                    self.log("status", f"Device status check #{scan_count//3}", {
                        "amg_timer": amg_status,
                        "bt50_sensor": bt50_status
                    })
                    
                    print(f"📊 AMG Timer: {amg_status}")
                    print(f"📊 BT50 Sensor: {bt50_status}")
                    print("💡 Waiting for raw data...\n")
                
                # Wait before next scan
                await asyncio.sleep(10)
                
            except KeyboardInterrupt:
                self.log("info", "🛑 Shutdown requested")
                break
            except Exception as e:
                self.log("error", f"Monitor error: {str(e)}")
                await asyncio.sleep(5)
    
    async def run(self):
        """Main bridge execution"""
        self.log("info", "🚀 Continuous Minimal Bridge started", {
            "amg_mac": self.amg_timer_mac,
            "bt50_mac": self.bt50_sensor_mac
        })
        
        print("=== CONTINUOUS MINIMAL BRIDGE ACTIVE ===")
        print("🔍 Scanning for devices every 10 seconds")
        print("📊 Will show raw data when devices connect")
        print("🛑 Press Ctrl+C to stop")
        print("")
        
        try:
            await self.monitor_connections()
        finally:
            # Cleanup connections
            if self.amg_client and self.amg_client.is_connected:
                await self.amg_client.disconnect()
                self.log("info", "🎯 AMG timer disconnected")
            if self.bt50_client and self.bt50_client.is_connected:
                await self.bt50_client.disconnect()
                self.log("info", "📊 BT50 sensor disconnected")
            
            self.log("info", "🏁 Continuous Minimal Bridge shutdown complete")

async def main():
    """Main entry point"""
    bridge = ContinuousMinimalBridge()
    await bridge.run()

if __name__ == "__main__":
    print("=== Continuous Minimal Bridge - Device Connection Monitor ===")
    print("Purpose: Stay running and connect to devices as they become available")
    print("")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Shutdown complete.")
    except Exception as e:
        print(f"❌ Error: {e}")