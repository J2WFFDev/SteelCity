#!/usr/bin/env python3
"""
Real BT50 Frame Capture Tool
Captures actual individual frames for impact analysis
"""

import asyncio
import datetime
from bleak import BleakClient
import struct
import time

# Parse BT50 frames (uses exact logic from working wtvb_live_decode.py)
HDR = 0x55
FLAG = 0x61
FRAME_DATA_LEN = 28

def parse_5561(payload):
    # accepts 28..32 bytes, only decodes the first 28
    if len(payload) < FRAME_DATA_LEN:
        return None
    b = payload[:FRAME_DATA_LEN]
    if b[0] != HDR or b[1] != FLAG:
        return None
    
    # unpack 13 little-endian uint16 after the 2-byte header
    vals = struct.unpack_from('<' + 'H'*13, b, 2)
    (VXL, VYL, VZL, ADXL, ADYL, ADZL, TEMPL,
     DXL, DYL, DZL, HZXL, HZYL, HZZL) = vals

    def s16(u): 
        return struct.unpack('<h', struct.pack('<H', u))[0]  # signed
    
    VX, VY, VZ = s16(VXL), s16(VYL), s16(VZL)        # mm/s
    ADX, ADY, ADZ = (s16(ADXL)/32768*180,
                     s16(ADYL)/32768*180,
                     s16(ADZL)/32768*180)            # degrees
    TEMP = s16(TEMPL)/100.0                         # °C
    DX, DY, DZ = s16(DXL), s16(DYL), s16(DZL)        # µm
    HZX, HZY, HZZ = s16(HZXL), s16(HZYL), s16(HZZL)  # Hz

    return {
        'VX': float(VX), 'VY': float(VY), 'VZ': float(VZ),
        'ADX': ADX, 'ADY': ADY, 'ADZ': ADZ,
        'TEMP': TEMP,
        'DX': float(DX), 'DY': float(DY), 'DZ': float(DZ),
        'HZX': float(HZX), 'HZY': float(HZY), 'HZZ': float(HZZ)
    }

class FrameCapture:
    def __init__(self, mac_address):
        self.mac = mac_address
        self.frames = []
        self.start_time = None
        
    async def capture_frames(self, duration_seconds=10):
        """Capture real BT50 frames for specified duration"""
        print(f"Connecting to BT50 sensor {self.mac}...")
        
        async with BleakClient(self.mac) as client:
            print(f"Connected! Capturing frames for {duration_seconds} seconds...")
            print("PERFORM 10 DOUBLE TAPS - SPACED 5-6 SECONDS APART!")
            
            self.start_time = time.time_ns()
            
            def frame_handler(sender, data):
                ts_ns = time.time_ns()
                
                # Debug: show what we actually received
                print(f"  Raw data: len={len(data)} hex={data.hex()}")
                
                pkt = parse_5561(data)
                if pkt:
                    # Calculate amplitude like bridge does
                    vx, vy, vz = pkt['VX'], pkt['VY'], pkt['VZ']
                    amp = (vx*vx + vy*vy + vz*vz) ** 0.5
                    
                    self.frames.append({
                        'ts_ns': ts_ns,
                        'ts_rel_ms': (ts_ns - self.start_time) / 1_000_000,
                        'amplitude': amp,
                        'vx': vx, 'vy': vy, 'vz': vz,
                        'temp': pkt['TEMP'],
                        'dx': pkt['DX'], 'dy': pkt['DY'], 'dz': pkt['DZ'],
                        'raw_bytes': data.hex()
                    })
                    
                    # Real-time feedback
                    if amp > 0.1:
                        print(f"  Frame {len(self.frames):3d}: amp={amp:6.2f}, vz={vz:6.1f}, temp={pkt['TEMP']:5.1f}°C")
                else:
                    print(f"  Parse failed for {len(data)}-byte frame")
            
            # Start notifications (UUID for BT50 data characteristic, FFE4)
            await client.start_notify("0000ffe4-0000-1000-8000-00805f9a34fb", frame_handler)
            
            # Capture for specified duration
            await asyncio.sleep(duration_seconds)
            
            await client.stop_notify("0000ffe4-0000-1000-8000-00805f9a34fb")
            
        print(f"\nCaptured {len(self.frames)} frames")
        return self.frames
    
    def write_analysis_file(self, filename=None):
        """Write detailed frame analysis to file"""
        if not self.frames:
            print("No frames to write")
            return
            
        if filename is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/real_bt50_frames_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write("# REAL BT50 Frame Data Capture\n")
            f.write(f"# Sensor MAC: {self.mac}\n")
            f.write(f"# Total Frames: {len(self.frames)}\n")
            f.write(f"# Duration: {(self.frames[-1]['ts_ns'] - self.frames[0]['ts_ns'])/1_000_000:.1f} ms\n")
            f.write("#\n")
            f.write("# This shows ACTUAL individual BT50 frames to analyze impact patterns\n")
            f.write("# Format: idx, ts_rel_ms, amplitude, vx, vy, vz, temp_c, dx, dy, dz\n")
            f.write("#\n")
            
            for i, frame in enumerate(self.frames):
                f.write(f"{i:3d}, {frame['ts_rel_ms']:8.1f}, {frame['amplitude']:8.3f}, "
                       f"{frame['vx']:8.1f}, {frame['vy']:8.1f}, {frame['vz']:8.1f}, "
                       f"{frame['temp']:6.1f}, {frame['dx']:6.0f}, {frame['dy']:6.0f}, {frame['dz']:6.0f}\n")
            
            # Analysis section
            f.write("\n# IMPACT ANALYSIS:\n")
            
            # Find amplitude peaks
            peaks = []
            for i, frame in enumerate(self.frames):
                if frame['amplitude'] > 1.0:  # Significant amplitude
                    peaks.append((i, frame['ts_rel_ms'], frame['amplitude']))
            
            f.write(f"# Amplitude Peaks (>1.0): {len(peaks)}\n")
            for i, (idx, ts_ms, amp) in enumerate(peaks):
                f.write(f"#   Peak {i+1}: Frame {idx}, {ts_ms:.1f}ms, amp={amp:.3f}\n")
            
            # Time separations between peaks
            if len(peaks) > 1:
                f.write("# Peak Separations:\n")
                for i in range(1, len(peaks)):
                    dt_ms = peaks[i][1] - peaks[i-1][1]
                    f.write(f"#   Peak {i} to {i+1}: {dt_ms:.1f}ms\n")
            
            # Current bridge calculation equivalent
            total_amp = sum(f['amplitude'] for f in self.frames)
            avg_amp = total_amp / len(self.frames)
            max_amp = max(f['amplitude'] for f in self.frames)
            
            f.write(f"#\n")
            f.write(f"# Bridge Equivalent Calculations:\n")
            f.write(f"# avg_amp (what bridge reports): {avg_amp:.6f}\n")
            f.write(f"# max_amp: {max_amp:.3f}\n")
            f.write(f"# frame_count: {len(self.frames)}\n")
            
        print(f"Analysis written to: {filename}")
        return filename

async def main():
    mac = "F8:FE:92:31:12:E3"  # BT50 MAC address
    
    print("=== Real BT50 Frame Capture ===")
    print("This tool captures ACTUAL individual frames from the BT50 sensor")
    print("to analyze impact patterns with 0.12s separation timing.")
    print()
    
    capture = FrameCapture(mac)
    
    try:
        frames = await capture.capture_frames(duration_seconds=60)
        
        if frames:
            filename = capture.write_analysis_file()
            print(f"\nReal frame data captured! Check file: {filename}")
            print("\nThis shows exactly how individual impacts appear in the")
            print("~50 frames that the bridge aggregates into avg_amp values.")
        else:
            print("No frames captured. Ensure BT50 is powered and nearby.")
            
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure BT50 sensor is powered on and tap it to wake up!")

if __name__ == "__main__":
    asyncio.run(main())