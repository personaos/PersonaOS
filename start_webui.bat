@echo off
echo Starting PersonaOS Web UI...
echo.

REM Check if .env file exists
if not exist ".env" (
    echo ERROR: .env file not found. Please run setup first:
    echo python core/main.py
    pause
    exit /b 1
)

REM Load environment variables
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="WEB_UI_PORT" set BACKEND_PORT=%%b
    if "%%a"=="FRONTEND_PORT" set FRONTEND_PORT=%%b
)

REM Set defaults if not found
if not defined BACKEND_PORT set BACKEND_PORT=8000
if not defined FRONTEND_PORT set FRONTEND_PORT=5173

echo Backend will start on port %BACKEND_PORT%
echo Frontend will start on port %FRONTEND_PORT%
echo.

REM Start backend in new window
echo Starting backend...
start "PersonaOS Backend" cmd /k "cd persona_web_ui\backend && python main.py"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in new window
echo Starting frontend...
start "PersonaOS Frontend" cmd /k "cd persona_web_ui\frontend && npm run dev"

echo.
echo Both services starting...
echo Backend: http://localhost:%BACKEND_PORT%
echo Frontend: http://localhost:%FRONTEND_PORT%
echo.
echo Press any key to close this window (services will continue running)
pause >nul