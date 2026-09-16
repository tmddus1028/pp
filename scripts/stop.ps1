$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$stateFile = Join-Path $projectRoot 'data\outputs\server-processes.json'
if (-not (Test-Path -LiteralPath $stateFile)) { Write-Output 'No saved server processes.'; exit }
$records = Get-Content -LiteralPath $stateFile -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($record in $records) {
    $serverProcess = Get-Process -Id $record.process_id -ErrorAction SilentlyContinue
    if ($serverProcess -and $serverProcess.StartTime.ToUniversalTime().ToString('o') -eq $record.started) {
        Stop-Process -Id $serverProcess.Id
    }
}
Remove-Item -LiteralPath $stateFile
Write-Output 'Project servers stopped.'
