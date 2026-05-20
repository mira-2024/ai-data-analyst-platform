$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$venvPython = Join-Path $root "venv\Scripts\python.exe"
$frontendNodeModules = Join-Path $frontendDir "node_modules"
$npm = "npm.cmd"

if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = "python"
}

Write-Host "Starting DataFlow without Docker..." -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8000"
Write-Host "Frontend: http://localhost:5173"

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command",
    "Set-Location '$backendDir'; & '$python' -c 'import fastapi' 2>`$null; if (`$LASTEXITCODE -ne 0) { Write-Host 'Installing backend dependencies...'; & '$python' -m pip install -r requirements.txt }; & '$python' -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
)

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command",
    "Set-Location '$frontendDir'; if (!(Test-Path '$frontendNodeModules')) { Write-Host 'Installing frontend dependencies...'; & '$npm' install }; & '$npm' run dev"
)
