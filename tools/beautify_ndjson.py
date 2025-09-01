#!/usr/bin/env python3
"""
Beautify NDJSON Log Viewer
Pretty-prints NDJSON content in human readable format
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

def format_timestamp(ts_ms=None, hms=None, t_iso=None):
    """Format timestamp for display"""
    if hms:
        return hms
    elif t_iso:
        try:
            dt = datetime.fromisoformat(t_iso.replace('Z', '+00:00'))
            return dt.strftime('%H:%M:%S.%f')[:-3]
        except:
            return t_iso[:12] if len(t_iso) > 12 else t_iso
    elif ts_ms:
        try:
            dt = datetime.fromtimestamp(ts_ms / 1000)
            return dt.strftime('%H:%M:%S.%f')[:-3]
        except:
            return str(ts_ms)
    else:
        return "no-time"

def colorize(text, color):
    """Add color to text for terminal display"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'gray': '\033[90m',
        'reset': '\033[0m'
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"

def get_event_color(event_type, msg):
    """Determine color based on event type and message"""
    if event_type == "error":
        return 'red'
    elif event_type == "event":
        if "T0" in msg or "BEEP" in msg:
            return 'yellow'
        elif "HIT" in msg:
            return 'magenta'
        elif "START_BTN" in msg:
            return 'green'
        elif "END" in msg:
            return 'cyan'
        else:
            return 'green'
    elif event_type == "info":
        if "connected" in msg:
            return 'green'
        elif "disconnected" in msg or "failed" in msg:
            return 'red'
        else:
            return 'cyan'
    elif event_type == "status":
        return 'gray'
    else:
        return 'white'

def format_event(record, args):
    """Format a single event record"""
    timestamp = format_timestamp(
        record.get('ts_ms'), 
        record.get('hms'), 
        record.get('t_iso')
    )
    
    event_type = record.get('type', 'unknown')
    msg = record.get('msg', 'no-msg')
    data = record.get('data', {})
    
    # Skip alive messages unless verbose
    if not args.verbose and event_type == "status" and msg == "alive":
        return None
    
    color = get_event_color(event_type, msg)
    
    if args.verbose:
        # Detailed format
        result = f"[{timestamp}] {event_type} : {msg}"
        if args.color:
            result = colorize(result, color)
        
        if data:
            data_str = json.dumps(data, separators=(',', ':'))
            data_line = f"    Data: {data_str}"
            if args.color:
                data_line = colorize(data_line, 'gray')
            result += "\n" + data_line
        
        return result
    else:
        # Concise format with emojis
        summary = format_message_summary(msg, data, record)
        
        prefix = f"[{timestamp}] "
        if args.color:
            prefix = colorize(prefix, 'gray')
            summary = colorize(summary, color)
        
        return prefix + summary

def format_message_summary(msg, data, record):
    """Create human-friendly message summaries"""
    summaries = {
        "amg_connecting": "AMG connecting...",
        "amg_connected": "AMG connected ✓",
        "amg_disconnected": "AMG disconnected",
        "amg_connect_failed": f"AMG connect FAILED: {data.get('error', 'unknown error')}",
        "T0": "🔔 BEEP (T0)",
        "AMG_T0": "🎯 AMG T0 signal",
        "AMG_START_BTN": "🔘 Start button pressed",
        "AMG_ARROW_END": "➡️ Arrow pressed",
        "AMG_TIMEOUT_END": "⏰ Timeout",
        "SESSION_END": f"🏁 Session ended ({data.get('reason', 'unknown')})",
        "bt50_connected": "BT50 connected ✓",
        "bt50_disconnected": "BT50 disconnected",
        "bt50_connect_failed": f"BT50 connect FAILED: {data.get('error', 'unknown error')}",
    }
    
    if msg in summaries:
        return summaries[msg]
    elif msg == "HIT":
        plate = record.get('plate', '?')
        time_s = record.get('t_rel_ms', 0) / 1000 if record.get('t_rel_ms') else 0
        return f"💥 HIT on {plate} at {time_s:.3f}s"
    else:
        return msg

def print_stats(records):
    """Print quick statistics"""
    print("\n" + "="*50)
    print("QUICK STATS")
    print("="*50)
    
    stats = {
        'total_events': len(records),
        'amg_connects': 0,
        'amg_disconnects': 0,
        't0_events': 0,
        'hits': 0,
        'start_buttons': 0,
        'arrow_presses': 0,
        'timeouts': 0,
        'session_ends': 0,
        'errors': 0
    }
    
    for record in records:
        msg = record.get('msg', '')
        event_type = record.get('type', '')
        
        if msg == 'amg_connected':
            stats['amg_connects'] += 1
        elif msg == 'amg_disconnected':
            stats['amg_disconnects'] += 1
        elif 'T0' in msg:
            stats['t0_events'] += 1
        elif msg == 'HIT':
            stats['hits'] += 1
        elif msg == 'AMG_START_BTN':
            stats['start_buttons'] += 1
        elif msg == 'AMG_ARROW_END':
            stats['arrow_presses'] += 1
        elif msg == 'AMG_TIMEOUT_END':
            stats['timeouts'] += 1
        elif msg == 'SESSION_END':
            stats['session_ends'] += 1
        elif event_type == 'error':
            stats['errors'] += 1
    
    for key, value in stats.items():
        if value > 0:
            print(f"{key.replace('_', ' ').title()}: {value}")

def main():
    parser = argparse.ArgumentParser(description='Pretty-print NDJSON log files')
    parser.add_argument('file', nargs='?', help='NDJSON file to read (default: stdin)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output with data')
    parser.add_argument('--no-color', action='store_true', help='Disable color output')
    parser.add_argument('--stats', '-s', action='store_true', help='Show statistics summary')
    parser.add_argument('--amg-only', action='store_true', help='Show only AMG-related events')
    parser.add_argument('--tail', '-n', type=int, help='Show only last N lines')
    
    args = parser.parse_args()
    args.color = not args.no_color and sys.stdout.isatty()
    
    # Read input
    if args.file:
        try:
            with open(args.file, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found", file=sys.stderr)
            sys.exit(1)
    else:
        lines = sys.stdin.readlines()
    
    # Apply tail limit
    if args.tail:
        lines = lines[-args.tail:]
    
    # Parse and filter records
    records = []
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        
        try:
            record = json.loads(line)
            records.append(record)
        except json.JSONDecodeError as e:
            if not args.verbose:
                continue
            print(f"Line {line_num}: Invalid JSON - {e}", file=sys.stderr)
    
    # Filter AMG-only if requested
    if args.amg_only:
        amg_keywords = ['amg', 'T0', 'AMG_', 'START_BTN', 'ARROW_END', 'TIMEOUT_END', 'SESSION_END']
        records = [r for r in records if any(kw in r.get('msg', '') for kw in amg_keywords)]
    
    # Format and print events
    if args.file and args.color:
        print(colorize(f"=== {Path(args.file).name} ===", 'cyan'))
    
    for record in records:
        formatted = format_event(record, args)
        if formatted:
            print(formatted)
    
    # Print stats if requested
    if args.stats:
        print_stats(records)

if __name__ == '__main__':
    main()