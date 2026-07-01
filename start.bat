@echo off
echo Starting DevOps Concierge Agent...
echo.

start "KeyOptimus Scheduler" cmd /k "cd /d %~dp0 && python -m uvicorn backend.key_optimizer.main:app --reload --port 8005"
timeout /t 2 /nobreak >nul
start "Backend" cmd /k "cd /d %~dp0 && python -m uvicorn backend.main:app --reload --port 8000"
timeout /t 3 /nobreak >nul
start "Frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo KeyOptimus Scheduler: http://localhost:8005
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
