$invPath = 'C:\sandbox\TargetSensor\SteelCity\doc\INVENTORY.json'
$j = Get-Content -Raw $invPath | ConvertFrom-Json
$j | Where-Object { $_.cli -ne $null } | ForEach-Object { $count = 0; if ($_.cli -and $_.cli.args) { $count = $_.cli.args.Count }; Write-Host ("{0} -> cli args: {1}" -f $_.path, $count) }
