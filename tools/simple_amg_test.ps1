#!/usr/bin/env pwsh
# Simple AMG Test - Baby Steps
param(
    [string]$SshHost = 'raspberrypi'
)

Write-Host "[1/5] Restarting Pi..." -ForegroundColor Green
ssh $SshHost 'sudo reboot'
Write-Host "Waiting 60s for Pi to boot..."
Start-Sleep 60

Write-Host "[2/5] Clearing logs and restarting bridge..." -ForegroundColor Green
ssh $SshHost 'bash -lc "cd ~/projects/steelcity; rm -f logs/bridge_*.ndjson; systemctl --user restart bridge.user; sleep 3"'

Write-Host "[3/5] Verifying service is active..." -ForegroundColor Green
$serviceStatus = ssh $SshHost 'systemctl --user is-active bridge.user'
if ($serviceStatus -ne "active") {
    Write-Host "ERROR: Bridge service not active: $serviceStatus" -ForegroundColor Red
    exit 1
}
Write-Host "Bridge service: $serviceStatus" -ForegroundColor Green

Write-Host "[4/5] Ready for AMG test!" -ForegroundColor Yellow
Write-Host ""
Write-Host "NOW DO THIS:" -ForegroundColor Cyan
Write-Host "1. Turn on AMG timer" -ForegroundColor White
Write-Host "2. Press Start button" -ForegroundColor White
Write-Host "3. Wait for beep" -ForegroundColor White
Write-Host "4. Press Arrow (or let it timeout)" -ForegroundColor White
Write-Host ""
Write-Host "Press any key when done with AMG test..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host "[5/5] Stopping bridge and showing results..." -ForegroundColor Green
ssh $SshHost 'systemctl --user stop bridge.user'

Write-Host ""
Write-Host "=== LOG FILES ===" -ForegroundColor Cyan
ssh $SshHost 'bash -lc "cd ~/projects/steelcity; ls -la logs"'

Write-Host ""
Write-Host "=== NDJSON CONTENT ===" -ForegroundColor Cyan
$logContent = ssh $SshHost 'bash -lc "cd ~/projects/steelcity; f=\$(ls -1t logs/bridge_*.ndjson 2>/dev/null | head -n 1); if [ -n \"\$f\" ]; then echo \"FILE: \$f\"; wc -l \"\$f\"; echo \"--- CONTENT ---\"; cat \"\$f\"; else echo \"No NDJSON file found\"; fi"'
Write-Host $logContent

Write-Host ""
Write-Host "=== AMG EVENTS SUMMARY ===" -ForegroundColor Cyan
try {
    $amgSummary = ssh $SshHost 'bash -lc "cd ~/projects/steelcity; f=\$(ls -1t logs/bridge_*.ndjson 2>/dev/null | head -n 1); if [ -n \"\$f\" ]; then PYTHONPATH=.:src .venv/bin/python -m tools.grep_amg --file \"\$f\" --tail 800; else echo \"No file to analyze\"; fi"'
    Write-Host $amgSummary
} catch {
    Write-Host "Could not run AMG summary: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Test complete. Bridge stopped." -ForegroundColor Green