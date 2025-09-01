#!/usr/bin/env pwsh
# Pretty NDJSON Viewer - Makes NDJSON readable
param(
    [string]$SshHost = 'raspberrypi',
    [switch]$AmgOnly,
    [switch]$Verbose
)

Write-Host "=== PRETTY NDJSON VIEWER ===" -ForegroundColor Cyan

# Get the latest NDJSON file
$latestFile = ssh $SshHost 'bash -lc "cd ~/projects/steelcity; ls -1t logs/bridge_*.ndjson 2>/dev/null | head -n 1"'
if (-not $latestFile) {
    Write-Host "No NDJSON files found!" -ForegroundColor Red
    exit 1
}

Write-Host "File: $latestFile" -ForegroundColor Green

# Get line count
$lineCount = ssh $SshHost "bash -lc 'cd ~/projects/steelcity; wc -l `"$latestFile`" | cut -d\" \" -f1'"
Write-Host "Lines: $lineCount" -ForegroundColor Green
Write-Host ""

if ($AmgOnly) {
    Write-Host "=== AMG EVENTS ONLY ===" -ForegroundColor Yellow
    $amgEvents = ssh $SshHost "bash -lc 'cd ~/projects/steelcity; PYTHONPATH=.:src .venv/bin/python -m tools.watch_amg --pretty --file `"$latestFile`" --from-start'"
    Write-Host $amgEvents
} else {
    Write-Host "=== ALL EVENTS (PRETTY FORMAT) ===" -ForegroundColor Yellow
    
    # Get raw content and format it nicely
    $rawContent = ssh $SshHost "bash -lc 'cd ~/projects/steelcity; cat `"$latestFile`"'"
    
    foreach ($line in $rawContent -split "`n") {
        if (-not $line.Trim()) { continue }
        
        try {
            $json = $line | ConvertFrom-Json
            $timestamp = if ($json.hms) { $json.hms } else { "no-time" }
            $type = if ($json.type) { $json.type } else { "unknown" }
            $msg = if ($json.msg) { $json.msg } else { "no-msg" }
            
            # Color code by type
            $color = switch ($type) {
                "info" { "Cyan" }
                "event" { "Green" }
                "error" { "Red" }
                "status" { "Gray" }
                "debug" { "Yellow" }
                default { "White" }
            }
            
            if ($Verbose) {
                Write-Host "[$timestamp] $type : $msg" -ForegroundColor $color
                if ($json.data) {
                    $dataStr = ($json.data | ConvertTo-Json -Compress)
                    Write-Host "    Data: $dataStr" -ForegroundColor DarkGray
                }
            } else {
                # Concise format
                if ($type -eq "status" -and $msg -eq "alive") {
                    # Skip alive messages unless verbose
                    continue
                }
                
                $summary = switch ($msg) {
                    "amg_connecting" { "AMG connecting..." }
                    "amg_connected" { "AMG connected ✓" }
                    "amg_disconnected" { "AMG disconnected" }
                    "amg_connect_failed" { 
                        $error = if ($json.data.error) { $json.data.error } else { "unknown error" }
                        "AMG connect FAILED: $error"
                    }
                    "T0" { "🔔 BEEP (T0)" }
                    "AMG_T0" { "🎯 AMG T0 signal" }
                    "AMG_START_BTN" { "🔘 Start button pressed" }
                    "AMG_ARROW_END" { "➡️ Arrow pressed" }
                    "AMG_TIMEOUT_END" { "⏰ Timeout" }
                    "SESSION_END" { 
                        $reason = if ($json.data.reason) { $json.data.reason } else { "unknown" }
                        "🏁 Session ended ($reason)"
                    }
                    "HIT" { 
                        $plate = if ($json.plate) { $json.plate } else { "?" }
                        $time = if ($json.t_rel_ms) { [math]::Round($json.t_rel_ms/1000, 3) } else { "?" }
                        "💥 HIT on $plate at ${time}s"
                    }
                    default { $msg }
                }
                
                Write-Host "[$timestamp] " -NoNewline -ForegroundColor DarkGray
                Write-Host $summary -ForegroundColor $color
            }
        } catch {
            Write-Host "Invalid JSON: $line" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "=== QUICK STATS ===" -ForegroundColor Cyan
$stats = ssh $SshHost "bash -lc 'cd ~/projects/steelcity; PYTHONPATH=.:src .venv/bin/python -m tools.grep_amg --file `"$latestFile`" --tail $lineCount'"
Write-Host $stats