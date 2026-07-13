@echo off
echo ===================================================
echo Starting Art Restoration Project
echo ===================================================

:: 1. Setup and Start Backend
echo Setting up and starting Backend Flask Server...
cd server
if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
)
echo Activating virtual environment and verifying dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt
echo Starting Flask backend in a new window...
start "Backend (Flask Server)" cmd /k "call venv\Scripts\activate.bat && python server.py"
cd ..

:: 2. Setup and Start Frontend
echo.
echo Setting up and starting Frontend React/Vite App...
cd client
if not exist node_modules (
    echo Installing frontend dependencies (this may take a minute)...
    call npm install
)
echo Starting Vite frontend in a new window...
start "Frontend (Vite Server)" cmd /k "npm run dev"
cd ..

echo.
echo ===================================================
echo Both services have been launched in separate windows!
echo - Backend: Running at http://localhost:5000
echo - Frontend: Running at http://localhost:3000
echo ===================================================
pause
