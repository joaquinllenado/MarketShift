# MarketShift — Start both frontend and backend dev servers
# Usage: .\start.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Start backend in new window
Write-Host "Starting backend (http://localhost:8000)..."
$BackendProc = Start-Process -FilePath "cmd" -ArgumentList "/c", "cd /d `"$Root\backend`" && venv\Scripts\activate.bat && uvicorn main:app --reload" -PassThru -WindowStyle Normal

Start-Sleep -Seconds 2

# Start frontend in new window
Write-Host "Starting frontend (http://localhost:5173)..."
$FrontendProc = Start-Process -FilePath "cmd" -ArgumentList "/c", "cd /d `"$Root\frontend`" && npm run dev" -PassThru -WindowStyle Normal

Write-Host ""
Write-Host "MarketShift dev servers running in separate windows:"
Write-Host "  Frontend: http://localhost:5173"
Write-Host "  Backend:  http://localhost:8000"
Write-Host ""
Write-Host "Close those windows or press Ctrl+C here to stop."
Write-Host ""

try {
    Wait-Process -Id $BackendProc.Id, $FrontendProc.Id -ErrorAction SilentlyContinue
} catch {
    $BackendProc | Stop-Process -Force -ErrorAction SilentlyContinue
    $FrontendProc | Stop-Process -Force -ErrorAction SilentlyContinue
}
