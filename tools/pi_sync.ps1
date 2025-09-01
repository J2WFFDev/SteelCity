param(
  [string]$SshHost = 'raspberrypi',
  [string]$Project = '~/projects/steelcity',
  [switch]$RestartBridge,
  [string]$Message = $("sync: push to Pi " + (Get-Date -Format s)),
  [switch]$DirectCopy
)

$ErrorActionPreference = 'Stop'

# Resolve repo root (parent of this script)
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Write-Host "[sync] Repo root: $repoRoot"

function Invoke-DirectCopy {
  param([string]$RepoRoot,[string]$SshHost,[string]$RemoteProject)
  $archive = Join-Path $RepoRoot 'steelcity_sync.tgz'
  if (Test-Path $archive) { Remove-Item $archive -Force }
  Write-Host "[pack] Creating archive $archive ..."
  try {
    Push-Location $RepoRoot
    tar -czf $archive --exclude .git --exclude .venv --exclude logs --exclude __pycache__ .
  } finally {
    Pop-Location
  }
  Write-Host ("[scp] Uploading to {0}:~/steelcity_sync.tgz ..." -f $SshHost)
  $dest = ("{0}:~/steelcity_sync.tgz" -f $SshHost)
  scp $archive $dest | Out-Host
  Write-Host ("[pi] Extracting into {0}:{1} ..." -f $SshHost, $RemoteProject)
  $remote = @(
    'set -e',
    "mkdir -p $RemoteProject",
    # Extract as-is preserving top-level folders (no strip-components)
    "tar -xzf ~/steelcity_sync.tgz -C $RemoteProject",
    'rm -f ~/steelcity_sync.tgz',
    "cd $RemoteProject",
    # Normalize line endings on shell scripts (avoid CRLF issues from Windows tars)
    "if compgen -G 'scripts/*.sh' > /dev/null; then sed -i 's/\r$//' scripts/*.sh || true; fi",
    # Ensure scripts are executable
    "chmod +x scripts/*.sh 2>/dev/null || true",
    'python3 -m venv .venv || true',
    'source .venv/bin/activate',
    'python -m pip install -U pip',
    "python -m pip install -e '.[dev]'"
  ) -join '; '
  ssh $SshHost "bash -lc '$remote'" | Out-Host
}

$gitAvailable = $false
try { $null = Get-Command git -ErrorAction Stop; $gitAvailable = $true } catch { $gitAvailable = $false }

if ($DirectCopy -or -not $gitAvailable) {
  if (-not $gitAvailable) { Write-Host "[git] git not found; using direct copy (tar+scp)" }
  Invoke-DirectCopy -RepoRoot $repoRoot -SshHost $SshHost -RemoteProject $Project
} else {
  # 1) Commit local changes if any and push
  $changes = & git -C $repoRoot status --porcelain
  if (-not [string]::IsNullOrWhiteSpace($changes)) {
    Write-Host "[git] Changes detected, committing..."
    & git -C $repoRoot add -A
    & git -C $repoRoot commit -m $Message | Out-Host
  } else {
    Write-Host "[git] No local changes to commit."
  }
  Write-Host "[git] Pushing to origin..."
  & git -C $repoRoot push | Out-Host

  # 2) Pull and install on Pi
  $remoteCmdPull = @(
    'set -e',
    "cd $Project",
    'git pull --rebase',
    'source .venv/bin/activate || true',
    'python -m pip install -U pip || true',
    "python -m pip install -e '.[dev]' || true"
  ) -join '; '

  Write-Host ("[pi] Pulling and installing on {0}:{1} ..." -f $SshHost, $Project)
  ssh $SshHost "bash -lc '$remoteCmdPull'" | Out-Host
}

if ($RestartBridge) {
  Write-Host "[pi] Restarting bridge..."
  ssh $SshHost 'pkill -f scripts.run_bridge || true' | Out-Null
  $remoteCmdRun = @(
    "cd $Project",
    'chmod +x scripts/run_bridge.sh scripts/tail_latest.sh || true',
    './scripts/run_bridge.sh'
  ) -join ' && '
  ssh $SshHost "bash -lc '$remoteCmdRun'" | Out-Host
  $remoteCmdTail = @(
    "cd $Project",
    './scripts/tail_latest.sh 40'
  ) -join ' && '
  ssh $SshHost "bash -lc '$remoteCmdTail'" | Out-Host
}

Write-Host "[done] Sync complete."