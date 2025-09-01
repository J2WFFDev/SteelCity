#!/usr/bin/env python3
"""
BT50 Buffer Capture Tool - Captures raw individual frame data from BT50 sensor
Creates detailed text files with all ~50 samples when impact is detected.
"""

import asyncio
import argparse
import datetime as dt
import struct
from bleak import BleakScanner, BleakClient

# BT50 sensor constants
HDR = 0x55
FLAG = 0x61
FRAME_DATA_LEN = 28

def now():
    return dt.datetime.now().strftime('%H:%M:%S.%f')[:-3]

def parse_5561(payload: bytes):
    """Parse a single BT50 notification frame."""
    if len(payload) < FRAME_DATA_LEN:
        return None
    b = payload[:FRAME_DATA_LEN]
    if b[0] != HDR or b[1] != FLAG:
        return None
    
    vals = struct.unpack_from('<' + 'H'*13, b, 2)
    (VXL,VYL,VZL, ADXL,ADYL,ADZL, TEMPL,
     DXL,DYL,DZL, HZXL,HZYL,HZZL) = vals

    def s16(u): return struct.unpack('<h', struct.pack('<H', u))[0]
    
    VX,VY,VZ = s16(VXL), s16(VYL), s16(VZL)        # mm/s
    ADX,ADY,ADZ = (s16(ADXL)/32768*180,
                   s16(ADYL)/32768*180,
                   s16(ADZL)/32768*180)             # degrees
    TEMP = s16(TEMPL)/100.0                         # Celsius
    DX,DY,DZ = s16(DXL), s16(DYL), s16(DZL)        # micrometers  
    HZX,HZY,HZZ = s16(HZXL), s16(HZYL), s16(HZZL)  # Hz
    
    return {
        'VX': VX, 'VY': VY, 'VZ': VZ,
        'ADX': ADX, 'ADY': ADY, 'ADZ': ADZ,
        'TEMP': TEMP,
        'DX': DX, 'DY': DY, 'DZ': DZ,
        'HZX': HZX, 'HZY': HZY, 'HZZ': HZZ
    }

class BufferCapture:
    def __init__(self, device_mac, buffer_size=50, amp_threshold=0.5):
        self.device_mac = device_mac
        self.buffer_size = buffer_size
        self.amp_threshold = amp_threshold
        self.samples = []
        self.file_counter = 0
        
    def calculate_amplitude(self, vx, vy, vz):
        """Calculate amplitude from velocity components."""
        return (vx*vx + vy*vy + vz*vz) ** 0.5
    
    def add_sample(self, timestamp, pkt):
        """Add a sample to the buffer."""
        amp = self.calculate_amplitude(pkt['VX'], pkt['VY'], pkt['VZ'])
        sample = {
            'timestamp': timestamp,
            'amp': amp,
            'vx': pkt['VX'], 'vy': pkt['VY'], 'vz': pkt['VZ'],
            'temp': pkt['TEMP'],
            'dx': pkt['DX'], 'dy': pkt['DY'], 'dz': pkt['DZ'],
            'adx': pkt['ADX'], 'ady': pkt['ADY'], 'adz': pkt['ADZ'],
            'hzx': pkt['HZX'], 'hzy': pkt['HZY'], 'hzz': pkt['HZZ']
        }
        
        self.samples.append(sample)
        
        # Keep buffer size manageable
        if len(self.samples) > self.buffer_size * 2:
            self.samples = self.samples[-self.buffer_size:]
        
        # Check for impact detection
        if amp > self.amp_threshold:
            self.write_buffer_file(amp)
    
    def write_buffer_file(self, trigger_amp):
        """Write detailed buffer data to file."""
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.file_counter += 1
        filename = f"logs/buffer_detail_P1_{timestamp}_amp{trigger_amp:.3f}_count{self.file_counter}.txt"
        
        # Get the most recent samples
        buffer = self.samples[-self.buffer_size:] if len(self.samples) >= self.buffer_size else self.samples
        
        try:
            with open(filename, 'w') as f:
                f.write(f"# BT50 Raw Buffer Capture\n")
                f.write(f"# Device: {self.device_mac}\n")
                f.write(f"# Timestamp: {timestamp}\n")
                f.write(f"# Trigger Amplitude: {trigger_amp:.3f}\n")
                f.write(f"# Buffer Size: {len(buffer)} samples\n")
                f.write(f"# Threshold: {self.amp_threshold}\n")
                f.write(f"#\n")
                f.write(f"# Format: idx, timestamp, amp, vx, vy, vz, temp, dx, dy, dz, adx, ady, adz, hzx, hzy, hzz\n")
                f.write(f"#\n")
                
                for i, sample in enumerate(buffer):
                    f.write(f"{i:3d}, {sample['timestamp']}, {sample['amp']:8.3f}, "
                           f"{sample['vx']:6.1f}, {sample['vy']:6.1f}, {sample['vz']:6.1f}, "
                           f"{sample['temp']:5.2f}, "
                           f"{sample['dx']:6.1f}, {sample['dy']:6.1f}, {sample['dz']:6.1f}, "
                           f"{sample['adx']:7.2f}, {sample['ady']:7.2f}, {sample['adz']:7.2f}, "
                           f"{sample['hzx']:6.1f}, {sample['hzy']:6.1f}, {sample['hzz']:6.1f}\n")
                
                # Summary statistics
                max_amp = max(s['amp'] for s in buffer)
                non_zero_count = sum(1 for s in buffer if s['amp'] > 0.1)
                f.write(f"\n# Summary:\n")
                f.write(f"# Max Amplitude: {max_amp:.3f}\n")
                f.write(f"# Significant Motion Samples: {non_zero_count}\n")
                f.write(f"# Time Span: {buffer[-1]['timestamp']} to {buffer[0]['timestamp']}\n")
                
            print(f"[{now()}] Buffer file written: {filename} (trigger: {trigger_amp:.3f})")
            
        except Exception as e:
            print(f"[{now()}] Error writing buffer file: {e}")

async def main():
    parser = argparse.ArgumentParser(description='Capture BT50 buffer data')
    parser.add_argument('--mac', required=True, help='BT50 device MAC address')
    parser.add_argument('--threshold', type=float, default=0.5, help='Amplitude threshold for capture')
    parser.add_argument('--buffer-size', type=int, default=50, help='Buffer size in samples')
    args = parser.parse_args()
    
    print(f"[{now()}] Starting BT50 buffer capture for {args.mac}")
    print(f"[{now()}] Threshold: {args.threshold}, Buffer size: {args.buffer_size}")
    
    capture = BufferCapture(args.mac, args.buffer_size, args.threshold)
    
    device = await BleakScanner.find_device_by_address(args.mac)
    if not device:
        print(f"Device {args.mac} not found")
        return
    
    async with BleakClient(device) as client:
        print(f"[{now()}] Connected to {args.mac}")
        
        def on_notify(sender, data: bytearray):
            timestamp = dt.datetime.now().strftime('%H:%M:%S.%f')[:-3]
            pkt = parse_5561(bytes(data))
            if pkt:
                amp = capture.calculate_amplitude(pkt['VX'], pkt['VY'], pkt['VZ'])
                print(f"[{timestamp}] VX={pkt['VX']:>5} VY={pkt['VY']:>5} VZ={pkt['VZ']:>5} | "
                      f"Amp={amp:6.3f} | T={pkt['TEMP']:4.1f}°C", end="")
                if amp > args.threshold:
                    print(f" *** IMPACT DETECTED ***")
                else:
                    print()
                    
                capture.add_sample(timestamp, pkt)
        
        # Start notifications
        await client.start_notify("0000ffe4-0000-1000-8000-00805f9a34fb", on_notify)
        print(f"[{now()}] Monitoring... (Ctrl+C to stop)")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print(f"\n[{now()}] Stopping...")
        finally:
            await client.stop_notify("0000ffe4-0000-1000-8000-00805f9a34fb")

if __name__ == "__main__":
    asyncio.run(main())