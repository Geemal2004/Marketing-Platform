@echo off
REM ============================================================
REM AgentSociety Platform - Service Startup Script
REM ============================================================
REM This script starts all required services for the platform:
REM   1. FastAPI Backend (API server)
REM   2. Celery Worker (VLM video processing)
REM   3. Ray Simulation Worker (Agent simulation)
REM ============================================================

echo ============================================================
echo        AgentSociety Platform - Starting Services
echo ============================================================
echo.

REM Load backend\.env values into this shell so FastAPI, Celery, and the
REM simulation worker all use the same configuration.
if exist "%~dp0.env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%~dp0.env") do (
        if not defined %%A set "%%A=%%B"
    )
)

REM Local development defaults. Values in backend\.env or the current shell win.
if not defined DATABASE_URL set "DATABASE_URL=postgresql://agentsociety:dev_password@localhost:5433/agentsociety_db"
if not defined REDIS_URL set "REDIS_URL=redis://localhost:6379/0"
if not defined CHROMA_HOST set "CHROMA_HOST=localhost"
if not defined CHROMA_PORT set "CHROMA_PORT=8000"
if not defined CHROMA_SSL set "CHROMA_SSL=false"

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then install dependencies: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if node_modules exists
if not exist "..\frontend\node_modules" (
    echo WARNING: Frontend dependencies not installed.
    echo Run: cd ..\frontend ^&^& npm install
)

echo Starting services...
echo.
echo Backend dependencies:
echo   DATABASE_URL=loaded from backend\.env or shell
echo   REDIS_URL=%REDIS_URL%
echo   CHROMA_HOST=%CHROMA_HOST%:%CHROMA_PORT%
echo.

if /I not "%START_DOCKER_DEPS%"=="1" goto skip_docker_deps

echo [0/4] Starting local Docker dependencies
docker compose -f "%~dp0..\docker-compose.yml" up -d postgres redis chromadb emqx
if errorlevel 1 goto docker_start_failed

echo Waiting for PostgreSQL on localhost:5433...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(60); while((Get-Date) -lt $deadline){ if(Test-NetConnection -ComputerName 127.0.0.1 -Port 5433 -InformationLevel Quiet){ exit 0 }; Start-Sleep -Seconds 2 }; exit 1"
if errorlevel 1 goto postgres_wait_failed

echo Waiting for Redis on localhost:6379...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(30); while((Get-Date) -lt $deadline){ if(Test-NetConnection -ComputerName 127.0.0.1 -Port 6379 -InformationLevel Quiet){ exit 0 }; Start-Sleep -Seconds 2 }; exit 1"
if errorlevel 1 goto redis_wait_failed

echo Docker dependencies are reachable.
echo.
goto docker_deps_done

:skip_docker_deps
echo [0/4] Skipping Docker dependency startup.
echo       Existing containers/services are expected to be reachable separately.
echo       To let this script start Compose dependencies, set START_DOCKER_DEPS=1.
echo.
goto docker_deps_done

:docker_start_failed
echo.
echo ERROR: Docker dependencies could not be started.
echo Make sure Docker Desktop is running and this terminal can access Docker.
echo This step only runs when START_DOCKER_DEPS=1.
pause
exit /b 1

:postgres_wait_failed
echo.
echo ERROR: PostgreSQL did not become reachable on localhost:5433.
echo Check with: docker compose -f "%~dp0..\docker-compose.yml" logs postgres
pause
exit /b 1

:redis_wait_failed
echo.
echo ERROR: Redis did not become reachable on localhost:6379.
echo Check with: docker compose -f "%~dp0..\docker-compose.yml" logs redis
pause
exit /b 1

:docker_deps_done

REM Terminal 1: FastAPI Backend
echo [1/4] Starting FastAPI Backend on http://localhost:8001
start "Backend - FastAPI" cmd /k "cd /d %~dp0 && venv\Scripts\activate && cd backend && uvicorn app.main:app --reload --port 8001"
timeout /t 2 /nobreak > nul

REM Terminal 2: Celery Worker (VLM Processing)
echo [2/4] Starting Celery Worker (VLM Processing)
start "Celery - VLM Worker" cmd /k "cd /d %~dp0 && venv\Scripts\activate && cd backend && celery -A app.tasks worker --loglevel=info --pool=solo"
timeout /t 2 /nobreak > nul

REM Terminal 3: Ray Simulation Worker
echo [3/4] Starting Ray Simulation Worker (Agent Simulation)
start "Ray - Simulation Worker" cmd /k "cd /d %~dp0 && venv\Scripts\activate && python simulation\simulation_worker.py"
timeout /t 2 /nobreak > nul

REM Terminal 4: Frontend
echo [4/4] Starting Frontend on http://localhost:3000
start "Frontend - Next.js" cmd /k "cd /d %~dp0..\frontend && npm run dev"

echo.
echo ============================================================
echo              All Services Started Successfully!
echo ============================================================
echo.
echo Service URLs:
echo   - Frontend:      http://localhost:3000
echo   - Backend API:   http://localhost:8001
echo   - API Docs:      http://localhost:8001/docs
echo.
echo Architecture:
echo   - Celery Worker: Handles video processing (VLM)
echo   - Ray Worker:    Handles agent simulations
echo.
echo To stop all services, close all opened terminal windows
echo or press Ctrl+C in each terminal.
echo ============================================================
echo.
pause
