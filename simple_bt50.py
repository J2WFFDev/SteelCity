#!/usr/bin/env python3
"""
Minimal BT50 Connection Test
Based on proven witmotion_bt50.py approach - just connect and log success
"""
import asyncio
import time
from bleak import BleakScanner, BleakClient

async def minimal_bt50_test():
    print("🔧 Minimal BT50 Connection Test")
    print("📡 Using proven discovery approach from witmotion_bt50.py")
    print()
    
    bt50_mac = "F8:FE:92:31:12:E3"
    adapter = "hci0"
    target = bt50_mac.lower()
    
    # Step 1: Try direct connection first (fastest)
    print("[STEP 1] Attempting direct connection...")
    try:
        client = BleakClient(bt50_mac, device=adapter)
        await client.connect(timeout=20.0)
        print("✅ SUCCESS: Direct connection worked!")
        
        # Check services
        services = client.services
        service_count = len(list(services)) if services else 0
        print(f"📋 Found {service_count} services")
        
        await client.disconnect()
        print("✅ Test completed successfully - BT50 connects!")
        return True
        
    except Exception as e:
        print(f"❌ Direct connection failed: {e}")
        try:
            await client.disconnect()
        except:
            pass
    
    # Step 2: Discovery approach
    print("\n[STEP 2] Using device discovery...")
    
    for attempt in range(3):
        print(f"  Attempt {attempt + 1}/3...")
        
        # Try find_device_by_address first
        try:
            print("    Trying find_device_by_address...")
            device = await BleakScanner.find_device_by_address(bt50_mac, timeout=10.0)
            if device:
                print(f"    Found device: {device.name} at {device.address}")
                
                # Connect to found device
                client = BleakClient(device, device=adapter)
                await client.connect(timeout=20.0)
                print("    ✅ SUCCESS: Connected via device discovery!")
                
                services = client.services
                service_count = len(list(services)) if services else 0
                print(f"    📋 Found {service_count} services")
                
                await client.disconnect()
                print("✅ Test completed successfully - BT50 connects!")
                return True
                
        except Exception as e:
            print(f"    find_device_by_address failed: {e}")
        
        # Try full discovery scan
        try:
            print("    Trying full discovery scan...")
            discovered = await BleakScanner.discover(adapter=adapter, timeout=8.0)
            print(f"    Scanned {len(discovered)} devices")
            
            for d in discovered:
                if (d.address or "").lower() == target:
                    print(f"    Found BT50: {d.name} at {d.address}")
                    
                    # Connect to discovered device
                    client = BleakClient(d, device=adapter)
                    await client.connect(timeout=20.0)
                    print("    ✅ SUCCESS: Connected via full scan!")
                    
                    services = client.services
                    service_count = len(list(services)) if services else 0
                    print(f"    📋 Found {service_count} services")
                    
                    await client.disconnect()
                    print("✅ Test completed successfully - BT50 connects!")
                    return True
                    
        except TypeError:
            # Try without adapter parameter
            try:
                print("    Trying discovery without adapter param...")
                discovered = await BleakScanner.discover(timeout=8.0)
                print(f"    Scanned {len(discovered)} devices")
                
                for d in discovered:
                    if (d.address or "").lower() == target:
                        print(f"    Found BT50: {d.name} at {d.address}")
                        
                        client = BleakClient(d)
                        await client.connect(timeout=20.0)
                        print("    ✅ SUCCESS: Connected without adapter param!")
                        
                        services = client.services
                        service_count = len(list(services)) if services else 0
                        print(f"    📋 Found {service_count} services")
                        
                        await client.disconnect()
                        print("✅ Test completed successfully - BT50 connects!")
                        return True
                        
            except Exception as e:
                print(f"    Discovery scan failed: {e}")
        
        except Exception as e:
            print(f"    Discovery scan failed: {e}")
        
        # Brief backoff
        if attempt < 2:
            print("    Waiting 3 seconds before retry...")
            await asyncio.sleep(3.0)
    
    print("\n❌ All connection attempts failed")
    print("💡 Check: Is BT50 powered on? Is it in pairing/advertising mode?")
    return False

if __name__ == "__main__":
    success = asyncio.run(minimal_bt50_test())
    if success:
        print("\n🎉 BT50 CONNECTION SUCCESS!")
    else:
        print("\n💔 BT50 connection failed")