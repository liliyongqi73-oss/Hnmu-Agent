$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

Set-Location $projectRoot
if (Test-Path $python) {
    & $python -m uvicorn server.app.main:app --host 127.0.0.1 --port 8000
}
else {
    & py -3.12 -m uvicorn server.app.main:app --host 127.0.0.1 --port 8000
}
