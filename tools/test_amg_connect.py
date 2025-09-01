#!/usr/bin/env python3
"""
Simple AMG Connection Test
Direct test of BLE connection to AMG Smart Timer to isolate InProgress errors
"""
import asyncio
import logging
from bleak import BleakClient, BleakScanner
import sys

# AMG device info
AMG_MAC = "60:09:C3:1F:DC:1A"
AMG_NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

async def test_amg_connection():
    """Test direct connection to AMG device"""
    
    print("=== AMG Connection Test ===")
    print(f"Target MAC: {AMG_MAC}")
    print(f"Notify UUID: {AMG_NOTIFY_UUID}")
    print()
    
    # Step 1: Scan for device
    print("1. Scanning for AMG device...")
    try:
        devices = await BleakScanner.discover(timeout=10.0)
        amg_device = None
        for device in devices:
            if device.address.lower() == AMG_MAC.lower():
                amg_device = device
                break
        
        if amg_device:
            print(f"✓ Found AMG device: {amg_device.name} ({amg_device.address})")
            rssi = getattr(amg_device, 'rssi', 'unknown')
            print(f"  RSSI: {rssi}")
        else:
            print("✗ AMG device not found in scan")
            return False
    except Exception as e:
        print(f"✗ Scan failed: {e}")
        return False
    
    print()
    
    # Step 2: Connect to device
    print("2. Connecting to AMG device...")
    try:
        async with BleakClient(AMG_MAC, timeout=20.0) as client:
            print(f"✓ Connected to {AMG_MAC}")
            
            # Step 3: Check if connected
            if not client.is_connected:
                print("✗ Client reports not connected")
                return False
            
            print("✓ Connection verified")
            
            # Step 4: Discover services
            print("\n3. Discovering services...")
            services = client.services
            
            print(f"Found {len(services.services)} services:")
            for service in services.services.values():
                print(f"  Service: {service.uuid}")
                for char in service.characteristics:
                    props = ", ".join(char.properties)
                    print(f"    Char: {char.uuid} ({props})")
                    if char.uuid.lower() == AMG_NOTIFY_UUID.lower():
                        print(f"      → This is the AMG notify characteristic!")
            
            # Step 5: Test notification subscription
            print("\n4. Testing notification subscription...")
            
            def notification_handler(sender, data):
                print(f"✓ Received data: {data.hex()} (length: {len(data)})")
            
            try:
                await client.start_notify(AMG_NOTIFY_UUID, notification_handler)
                print("✓ Notification subscription successful")
                
                print("\n5. Listening for 10 seconds...")
                print("   (Press buttons on AMG device now)")
                await asyncio.sleep(10)
                
                await client.stop_notify(AMG_NOTIFY_UUID)
                print("✓ Notification stopped")
                
            except Exception as e:
                print(f"✗ Notification test failed: {e}")
                return False
            
            print("\n✓ All tests passed!")
            return True
            
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

async def main():
    """Main test function"""
    
    # Enable Bleak debug logging
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("bleak").setLevel(logging.DEBUG)
    
    success = await test_amg_connection()
    
    if success:
        print("\n🎉 AMG connection test PASSED")
        sys.exit(0)
    else:
        print("\n💥 AMG connection test FAILED")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(130)