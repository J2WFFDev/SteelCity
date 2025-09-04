#!/usr/bin/env python3
"""
BT50 Service Discovery Tool
Find all services and characteristics on BT50 sensor
"""
import asyncio
import logging
import struct
import sys
from datetime import datetime
from bleak import BleakClient, BleakScanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s.%(msecs)03d] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class BT50ServiceDiscovery:
    def __init__(self):
        self.bt50_uuid = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Standard Nordic UART
        
    def log(self, level, message, data=None):
        if data:
            logger.log(getattr(logging, level.upper()), f"{message}: {data}")
        else:
            logger.log(getattr(logging, level.upper()), message)
        
    async def discover_services(self):
        print("🔍 BT50 Service Discovery")
        print("📡 Finding all services and characteristics on BT50")
        print()
        
        try:
            # Scan for devices
            self.log("info", "Scanning for BT50 sensor (15 second scan)...")
            devices = await BleakScanner.discover(timeout=15.0)
            
            # Find BT50
            bt50_device = None
            for device in devices:
                if device.name and "BT50" in device.name:
                    bt50_device = device
                    self.log("success", f"Found BT50: {device.name} at {device.address}")
                    break
                    
            if not bt50_device:
                self.log("error", "BT50 sensor not found")
                return False
                
            # Connect and discover services
            self.log("info", "Connecting to BT50...")
            async with BleakClient(bt50_device, timeout=20.0) as client:
                self.log("success", "BT50 connected successfully!")
                
                # List all services
                print("\n📋 SERVICES DISCOVERED:")
                print("-" * 60)
                
                for service in client.services:
                    print(f"Service: {service.uuid}")
                    print(f"  Description: {service.description}")
                    
                    # List all characteristics for this service
                    print("  Characteristics:")
                    for char in service.characteristics:
                        props = []
                        if "read" in char.properties:
                            props.append("READ")
                        if "write" in char.properties:
                            props.append("WRITE")
                        if "notify" in char.properties:
                            props.append("NOTIFY")
                        if "indicate" in char.properties:
                            props.append("INDICATE")
                            
                        print(f"    {char.uuid} - {char.description}")
                        print(f"      Properties: {', '.join(props)}")
                        
                        # List descriptors
                        if char.descriptors:
                            print("      Descriptors:")
                            for desc in char.descriptors:
                                print(f"        {desc.uuid} - {desc.description}")
                    print()
                
                # Try to find notification characteristics
                print("🔔 NOTIFICATION CHARACTERISTICS:")
                print("-" * 60)
                
                notify_chars = []
                for service in client.services:
                    for char in service.characteristics:
                        if "notify" in char.properties:
                            notify_chars.append(char)
                            print(f"Found: {char.uuid} in service {service.uuid}")
                            
                if notify_chars:
                    print(f"\n✅ Found {len(notify_chars)} notification characteristics")
                    
                    # Test the first one
                    test_char = notify_chars[0]
                    print(f"\n🧪 Testing notifications on {test_char.uuid}...")
                    
                    data_count = 0
                    
                    def notification_handler(sender, data):
                        nonlocal data_count
                        data_count += 1
                        hex_data = data.hex()
                        
                        # Try to parse as acceleration data
                        if len(data) >= 12:
                            try:
                                vx, vy, vz = struct.unpack('<fff', data)
                                print(f"  [{data_count:3d}] Raw: {hex_data[:24]}... | vx={vx:.3f}, vy={vy:.3f}, vz={vz:.3f}")
                            except:
                                print(f"  [{data_count:3d}] Raw: {hex_data}")
                        else:
                            print(f"  [{data_count:3d}] Raw: {hex_data}")
                    
                    # Start notifications and monitor for 10 seconds
                    await client.start_notify(test_char.uuid, notification_handler)
                    print("  Monitoring for 10 seconds...")
                    await asyncio.sleep(10)
                    await client.stop_notify(test_char.uuid)
                    
                    print(f"  Received {data_count} notifications")
                else:
                    print("❌ No notification characteristics found")
                    
                return True
                
        except Exception as e:
            self.log("error", f"Service discovery failed: {e}")
            return False

async def main():
    discovery = BT50ServiceDiscovery()
    success = await discovery.discover_services()
    
    if success:
        print("\n✅ BT50 service discovery completed")
    else:
        print("\n❌ BT50 service discovery failed")

if __name__ == "__main__":
    asyncio.run(main())