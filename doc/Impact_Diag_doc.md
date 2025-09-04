# Impact Diagnostics and Calibration System

**Date**: September 3, 2025  
**Version**: 1.0  
**Purpose**: Documentation for BT50 sensor impact detection diagnostics and calibration tools

## Overview

The Impact Diagnostics system provides real-time analysis and calibration capabilities for BT50 vibration sensors in the SteelCity bridge system. It captures raw buffer data ("strip chart" data) for visual analysis and processes it into discrete impact events with timing estimation.

## System Architecture

### Buffer Processing Pipeline
1. **Data Collection**: BT50 sensor streams accelerometer data (vx, vy, vz) with calculated amplitude
2. **Buffer Accumulation**: Samples collected in rolling buffer (typically 30-100 samples per 2-second window)
3. **Processing Trigger**: Buffer processed when >= 5 samples accumulated
4. **Impact Detection**: Amplitude-based peak detection with pattern classification
5. **Event Generation**: Discrete impact events with timing and classification

### Data Flow
```
BT50 Sensor → Buffer → Processing → Impact Events + Strip Chart Data
     ↓              ↓         ↓              ↓
(vx,vy,vz,amp) → [samples] → Peaks → BT50_RAW events + bt50_buffer_samples
```

## Configuration Changes for Diagnostics

### Key Parameters Modified
- **Buffer Size Threshold**: Changed from 40 to 5 samples for real-time processing
- **Time Window**: Changed from 2000ms to 100ms for frequent processing
- **Processing Condition**: Removed time window dependency to force processing on every buffer >= 5 samples

### Critical Code Changes
```python
# Original (too restrictive for real-time diagnostics)
if len(buffer) >= 40 and (ts_ns - self._bt50_last_processed[sensor_id]) > time_window_ns:

# Modified (enables real-time diagnostics)
if len(buffer) >= 5:
```

## Strip Chart Data Format

### Buffer Sample Log Structure
```json
{
  "type": "debug",
  "msg": "bt50_buffer_samples",
  "data": {
    "sensor_id": "Sensor_12E3",
    "sample_count": 89,
    "samples": [
      {"ts": 1234567890, "amp": 62.008, "vx": 14.0, "vy": 7.0, "vz": 60.0},
      {"ts": 1234567920, "amp": 1.414, "vx": 1.0, "vy": 1.0, "vz": 0.0},
      ...
    ]
  }
}
```

### Sample Data Characteristics Observed

#### Impact Signatures
- **High Impact**: amplitude 60+ (vx=14, vy=7, vz=60, amp=62.008)
- **Medium Impact**: amplitude 30-50 (vx=10, vy=3, vz=47, amp=48.146)
- **Low Impact**: amplitude 10-30 (vx=0, vy=1, vz=32, amp=32.016)
- **Background Noise**: amplitude 1-4 (vx=0-1, vy=0-1, vz=0-4, amp=1.0-4.0)

#### Timing Characteristics
- **Sample Rate**: ~32ms intervals between samples
- **Buffer Size**: Typically 30-100 samples per processing cycle
- **Buffer Duration**: ~1-3 seconds of sensor data per buffer

## Impact Detection Algorithm

### Peak Detection Logic
```python
def _detect_impact_peaks(self, buffer):
    peak_threshold = 0.5  # Minimum amplitude to consider a peak
    # Local maximum detection within 3-frame window
    # Prevents double-counting due to sensor resonance
```

### Classification Categories
- **SINGLE**: Individual impact event
- **DOUBLE**: Double-tap pattern (future enhancement)
- **TRIPLE**: Triple-tap pattern (future enhancement)

### Amplitude Thresholds (Recommended)
Based on observed data patterns:
- **Noise Floor**: < 5.0 amplitude
- **Light Impact**: 5.0 - 15.0 amplitude
- **Medium Impact**: 15.0 - 40.0 amplitude
- **Heavy Impact**: > 40.0 amplitude

## Event Output Format

### BT50_RAW Event Structure
```json
{
  "type": "event",
  "sensor_id": "Sensor_12E3",
  "device_id": "12E3",
  "t_rel_ms": 1234567.89,
  "event_type": "BT50_RAW",
  "msg": "Impact #1 detected",
  "signal_description": "Impact #1 detected",
  "raw_data": {
    "peak_amplitude": 62.008,
    "frame_index": 45,
    "peak_timestamp": 1234567890.1,
    "impact_type": "SINGLE"
  }
}
```

## Timing Estimation System

### Time Calculation Method
Since BT50 sensors don't have absolute time clocks:

1. **Buffer Receipt Time**: When bridge receives complete buffer
2. **Sample Intervals**: ~32ms between samples (observed)
3. **Backwards Calculation**: 
   ```
   impact_time = buffer_receipt_time - (samples_after_peak * 32ms)
   ```
4. **Processing Delay**: Add ~10-50ms adjustment for processing overhead

### Timing Accuracy
- **Precision**: ±32ms (one sample interval)
- **Latency**: 100ms-2s depending on buffer processing frequency
- **Relative Timing**: Accurate within buffer for multiple impacts

## Calibration Tools and Procedures

### Strip Chart Analysis
1. **Data Extraction**: 
   ```bash
   grep 'bt50_buffer_samples' logs/bridge_*.ndjson | jq '.data.samples[]'
   ```

2. **Amplitude Visualization**: Plot amplitude vs time for impact signature analysis

3. **Threshold Tuning**: Adjust `peak_threshold` based on noise floor analysis

### Testing Protocol
1. **Baseline Collection**: Record 5 minutes of no-impact data for noise characterization
2. **Controlled Impacts**: Generate known impacts at various intensities
3. **Pattern Analysis**: Analyze amplitude patterns, duration, and decay characteristics
4. **Threshold Validation**: Verify detection accuracy vs false positives

### Calibration Parameters
```python
# In bridge.py _detect_impact_peaks()
peak_threshold = 0.5      # Minimum amplitude (tune based on noise floor)
neighbor_window = 3       # Frames to check for local maximum
keep_recent = 10         # Samples to retain between buffer processing

# In bt50_connection_handler()
buffer_threshold = 5      # Minimum samples before processing
time_window_ns = 100_000_000  # 100ms processing frequency
```

## Diagnostic Commands

### Real-time Monitoring
```bash
# Monitor buffer status
tail -f logs/bridge_*.ndjson | grep 'bt50_buffer_status'

# Monitor buffer samples (strip chart data)
tail -f logs/bridge_*.ndjson | grep 'bt50_buffer_samples'

# Monitor impact events
tail -f logs/bridge_*.ndjson | grep 'BT50_RAW'

# Monitor impact analysis
tail -f logs/bridge_*.ndjson | grep 'bt50_impact_analysis'
```

### Data Extraction for Analysis
```bash
# Extract last 100 buffer samples
grep 'bt50_buffer_samples' logs/bridge_*.ndjson | tail -1 | jq '.data.samples[]'

# Extract impact events from last hour
grep 'BT50_RAW' logs/bridge_*.ndjson | tail -20

# Extract amplitude analysis
grep 'bt50_impact_analysis' logs/bridge_*.ndjson | tail -10 | jq '.data'
```

## Future Enhancements

### Visualization Tools
- Real-time amplitude strip chart web interface
- Impact event timeline visualization
- Amplitude distribution analysis
- Multi-sensor correlation views

### Advanced Calibration
- Automatic noise floor detection
- Dynamic threshold adjustment
- Machine learning impact classification
- Sensor sensitivity calibration per device

### Integration Features
- Export to standard analysis formats (CSV, HDF5)
- Integration with external analysis tools
- API for real-time data streaming
- Alert system for anomalous patterns

## Troubleshooting

### Common Issues
1. **No buffer processing**: Check `last_processed_ns` - should update regularly
2. **Missing strip chart data**: Verify `bt50_buffer_samples` logs are present
3. **No impact events**: Check amplitude thresholds vs actual sensor data
4. **Timing inconsistencies**: Verify sample rate calculations

### Debug Steps
1. Monitor buffer status for data accumulation
2. Check processing frequency via `last_processed_ns` updates
3. Analyze amplitude ranges in strip chart data
4. Validate peak detection thresholds
5. Verify event generation logic

## References
- Bridge system architecture: `HANDOFF_SESSION.md`
- Testing protocols: `TESTING_PROTOCOL.md`
- Sensor specifications: `AMG_SIGNALS.md`
- Configuration examples: `config.example.yaml`