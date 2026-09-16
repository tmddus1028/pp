$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run uv sync --python 3.11 first.' }
foreach ($port in @(8000, 8501)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Check the running app or stop it first."
    }
}
$outputDir = Join-Path $projectRoot 'data\outputs'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$env:PYTHONUTF8 = '1'
$processes = @()
try {
    $apiProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $outputDir 'api.log') -RedirectStandardError (Join-Path $outputDir 'api-error.log')
    $processes += $apiProcess
    $uiProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-m', 'streamlit', 'run', 'frontend/app.py', '--server.address', '127.0.0.1', '--server.port', '8501', '--server.headless', 'true') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $outputDir 'ui.log') -RedirectStandardError (Join-Path $outputDir 'ui-error.log')
    $processes += $uiProcess
    $records = @($processes | ForEach-Object { @{ process_id = $_.Id; started = $_.StartTime.ToUniversalTime().ToString('o') } })
    $records | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputDir 'server-processes.json') -Encoding UTF8
    Write-Output 'Web UI: http://127.0.0.1:8501'
    Write-Output 'API docs: http://127.0.0.1:8000/docs'
    Write-Output 'Stop: .\scripts\stop.ps1'
} catch {
    $processes | Stop-Process -ErrorAction SilentlyContinue
    throw
}
