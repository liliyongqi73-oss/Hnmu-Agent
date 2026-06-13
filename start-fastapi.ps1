$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

Set-Location $projectRoot
& $python -m uvicorn server.app.main:app --host 127.0.0.1 --port 8000
