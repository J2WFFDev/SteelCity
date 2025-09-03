$invPath = 'C:\sandbox\TargetSensor\SteelCity\doc\INVENTORY.json'
$j = Get-Content -Raw $invPath | ConvertFrom-Json
$groups = $j | Group-Object -Property path | Where-Object { $_.Count -gt 1 }
if (-not $groups -or $groups.Count -eq 0) {
    Write-Host 'No duplicates'
} else {
    foreach ($g in $groups) {
        Write-Host "DUP: $($g.Name) count=$($g.Count)"
        $g.Group | ConvertTo-Json -Depth 6 | Write-Host
        Write-Host '---'
    }
}
