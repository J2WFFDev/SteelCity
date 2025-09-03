# Move cli objects from doc/* entries to corresponding tools/* entries
$path = 'C:\sandbox\TargetSensor\SteelCity\doc\INVENTORY.json'
$j = Get-Content -Raw $path | ConvertFrom-Json
# mapping from doc path to tool path
$map = @{
    'doc/INGEST.md' = 'tools/watch_events.py'
    'doc/HANDOFF_20250901.md' = 'tools/watch_amg.py'
    'doc/AMG_SIGNALS.md' = 'tools/wtvb_offline_decode.py'
    'doc/project context.md' = 'tools/wtvb_offline_dump.py'
    'doc/VENV_SETUP.md' = 'tools/wtvb_send.py'
}
$modified = $false
foreach ($docPath in $map.Keys) {
    $docItem = $j | Where-Object { $_.path -eq $docPath }
    if ($null -ne $docItem -and $docItem.cli -ne $null) {
        $toolPath = $map[$docPath]
        $toolItem = $j | Where-Object { $_.path -eq $toolPath }
        if ($null -eq $toolItem) {
            Write-Host "Target tool entry not found for $docPath -> $toolPath"
            continue
        }
        # if tool already has cli, merge args by name
        if ($toolItem.cli -eq $null) {
            $toolItem | Add-Member -MemberType NoteProperty -Name cli -Value $docItem.cli
            Write-Host "Moved cli from $docPath to $toolPath"
        } else {
            $existing = @{}
            foreach ($a in $toolItem.cli.args) { $existing[$a.name] = $true }
            foreach ($a in $docItem.cli.args) {
                if (-not $existing.ContainsKey($a.name)) {
                    $toolItem.cli.args += $a
                }
            }
            Write-Host "Merged cli from $docPath into $toolPath"
        }
        # remove cli from doc entry
        $docItem.PSObject.Properties.Remove('cli') | Out-Null
        $modified = $true
    }
}
if ($modified) {
    $jsonOut = $j | ConvertTo-Json -Depth 10
    # write back
    Set-Content -Path $path -Value $jsonOut -Encoding UTF8
    Write-Host "WROTE $path"
} else {
    Write-Host 'No changes made'
}
