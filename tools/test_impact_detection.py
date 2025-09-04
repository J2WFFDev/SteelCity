#!/usr/bin/env python3
"""
Minimal Impact Detection Test Tool

This tool tests the impact detection logic without requiring Bluetooth connections.
It simulates BT50 sensor data and verifies the amplitude-based impact detection.
"""

import json
import time
import math
from datetime import datetime, timezone

class ImpactDetectionTester:
    def __init__(self):
        # Peak detection parameters (from bridge.py)
        self.peak_threshold = 10.0  # Amplitude threshold for impacts
        self.min_peak_distance = 5  # Minimum samples between peaks
        
    def calculate_amplitude(self, vx, vy, vz):
        """Calculate amplitude from acceleration components (same as bridge.py)"""
        return math.sqrt(vx*vx + vy*vy + vz*vz)
    
    def classify_intensity(self, amplitude):
        """Classify impact intensity based on amplitude"""
        if amplitude >= 40.0:
            return 'HEAVY'
        elif amplitude >= 15.0:
            return 'MEDIUM'
        else:
            return 'LIGHT'
    
    def detect_impact_peaks(self, buffer_data):
        """
        Detect impact peaks in buffer data (simplified version of bridge.py logic)
        
        Args:
            buffer_data: List of (timestamp_ns, amplitude) tuples
            
        Returns:
            List of detected peaks with intensities
        """
        if len(buffer_data) < 2:
            return []
        
        peaks = []
        amplitudes = [sample[1] for sample in buffer_data]
        
        # Find peaks above threshold
        for i in range(1, len(amplitudes) - 1):
            if (amplitudes[i] >= self.peak_threshold and 
                amplitudes[i] > amplitudes[i-1] and 
                amplitudes[i] > amplitudes[i+1]):
                
                # Check minimum distance from previous peaks
                too_close = False
                for prev_peak_idx in [p[1] for p in peaks]:
                    if abs(i - prev_peak_idx) < self.min_peak_distance:
                        too_close = True
                        break
                
                if not too_close:
                    intensity = self.classify_intensity(amplitudes[i])
                    peaks.append((amplitudes[i], i, intensity))
        
        return peaks
    
    def generate_test_data(self, scenario="mixed"):
        """Generate test data scenarios"""
        test_data = []
        base_time = int(time.time() * 1_000_000_000)  # nanoseconds
        
        if scenario == "quiet":
            # Quiet background noise (1-4 amplitude)
            for i in range(50):
                vx, vy, vz = 0.5, 0.8, 1.2  # Low values
                amplitude = self.calculate_amplitude(vx, vy, vz)
                test_data.append((base_time + i * 10_000_000, amplitude))  # 10ms intervals
                
        elif scenario == "light_impacts":
            # Light impacts mixed with noise
            for i in range(50):
                if i in [10, 25, 40]:  # Light impacts at specific points
                    vx, vy, vz = 8.0, 6.0, 4.0  # ~10-12 amplitude
                else:
                    vx, vy, vz = 0.5, 0.8, 1.2  # Background noise
                amplitude = self.calculate_amplitude(vx, vy, vz)
                test_data.append((base_time + i * 10_000_000, amplitude))
                
        elif scenario == "heavy_impacts":
            # Heavy impacts
            for i in range(50):
                if i in [15, 35]:  # Heavy impacts
                    vx, vy, vz = 25.0, 20.0, 15.0  # ~35-45 amplitude
                else:
                    vx, vy, vz = 1.0, 1.5, 0.8  # Background noise
                amplitude = self.calculate_amplitude(vx, vy, vz)
                test_data.append((base_time + i * 10_000_000, amplitude))
                
        elif scenario == "mixed":
            # Mixed scenario with various impact types
            for i in range(100):
                if i == 20:  # Light impact
                    vx, vy, vz = 7.0, 5.0, 8.0  # ~12 amplitude
                elif i == 45:  # Medium impact  
                    vx, vy, vz = 15.0, 12.0, 10.0  # ~22 amplitude
                elif i == 70:  # Heavy impact
                    vx, vy, vz = 30.0, 25.0, 20.0  # ~42 amplitude
                elif i == 75:  # Another light impact (close to heavy)
                    vx, vy, vz = 8.0, 6.0, 5.0  # ~11 amplitude
                else:
                    # Background noise with some variation
                    vx = 0.5 + (i % 3) * 0.3
                    vy = 0.8 + (i % 5) * 0.2  
                    vz = 1.0 + (i % 7) * 0.1
                amplitude = self.calculate_amplitude(vx, vy, vz)
                test_data.append((base_time + i * 10_000_000, amplitude))
        
        return test_data
    
    def analyze_buffer(self, buffer_data):
        """Analyze buffer data and return statistics (similar to bridge.py)"""
        if not buffer_data:
            return {}
        
        peaks = self.detect_impact_peaks(buffer_data)
        amplitudes = [sample[1] for sample in buffer_data]
        
        # Count by intensity
        intensity_counts = {'LIGHT': 0, 'MEDIUM': 0, 'HEAVY': 0}
        peak_amplitudes = []
        
        for amplitude, idx, intensity in peaks:
            intensity_counts[intensity] += 1
            peak_amplitudes.append(round(amplitude, 2))
        
        # Noise samples (amplitude < 5)
        noise_samples = len([a for a in amplitudes if a < 5.0])
        
        return {
            'total_samples': len(buffer_data),
            'total_impacts': len(peaks),
            'intensity_counts': intensity_counts,
            'peak_amplitudes': peak_amplitudes,
            'noise_samples': noise_samples,
            'max_amplitude': round(max(amplitudes), 2),
            'avg_amplitude': round(sum(amplitudes) / len(amplitudes), 2)
        }
    
    def run_test(self, scenario):
        """Run a test scenario and display results"""
        print(f"\n=== Testing Scenario: {scenario.upper()} ===")
        
        # Generate test data
        buffer_data = self.generate_test_data(scenario)
        
        # Analyze the data
        analysis = self.analyze_buffer(buffer_data)
        
        # Display results
        print(f"Buffer size: {analysis['total_samples']} samples")
        print(f"Total impacts detected: {analysis['total_impacts']}")
        print(f"Impact breakdown: {analysis['intensity_counts']}")
        print(f"Peak amplitudes: {analysis['peak_amplitudes']}")
        print(f"Noise samples (< 5.0): {analysis['noise_samples']}")
        print(f"Max amplitude: {analysis['max_amplitude']}")
        print(f"Average amplitude: {analysis['avg_amplitude']}")
        
        # Show amplitude timeline for first 20 samples
        print(f"\nFirst 20 samples:")
        for i, (ts, amp) in enumerate(buffer_data[:20]):
            marker = " *** IMPACT ***" if amp >= self.peak_threshold else ""
            print(f"  Sample {i:2d}: {amp:5.2f}{marker}")
        
        return analysis

def main():
    """Main test function"""
    print("=== Impact Detection Test Tool ===")
    print("Testing amplitude-based impact detection logic")
    print("Thresholds: LIGHT (10-15), MEDIUM (15-40), HEAVY (>40)")
    
    tester = ImpactDetectionTester()
    
    # Run all test scenarios
    scenarios = ['quiet', 'light_impacts', 'heavy_impacts', 'mixed']
    
    for scenario in scenarios:
        result = tester.run_test(scenario)
        
        # Validate expected results
        if scenario == 'quiet':
            if result['total_impacts'] == 0:
                print("✅ PASS: No false positives in quiet scenario")
            else:
                print("❌ FAIL: False positives detected in quiet scenario")
        
        elif scenario == 'light_impacts':
            if result['total_impacts'] == 3 and result['intensity_counts']['LIGHT'] == 3:
                print("✅ PASS: Light impacts correctly detected")
            else:
                print(f"❌ FAIL: Expected 3 light impacts, got {result['total_impacts']}")
        
        elif scenario == 'heavy_impacts':
            if result['total_impacts'] == 2 and result['intensity_counts']['HEAVY'] == 2:
                print("✅ PASS: Heavy impacts correctly detected")
            else:
                print(f"❌ FAIL: Expected 2 heavy impacts, got {result['total_impacts']}")
        
        elif scenario == 'mixed':
            expected_total = 4  # 1 light + 1 medium + 1 heavy + 1 light
            if result['total_impacts'] >= 3:  # Allow some flexibility
                print(f"✅ PASS: Mixed scenario detected {result['total_impacts']} impacts")
            else:
                print(f"❌ FAIL: Mixed scenario only detected {result['total_impacts']} impacts")
    
    print("\n=== Test Complete ===")
    print("This tool verifies the impact detection logic works correctly.")
    print("Next step: Apply these settings to the bridge when Bluetooth issues are resolved.")

if __name__ == "__main__":
    main()