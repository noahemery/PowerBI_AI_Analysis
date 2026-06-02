@echo off
echo Starting Alltech Jumbotron Monitor...

:: Set poppler path
set PATH=%PATH%;C:\poppler-26.02.0\Library\bin

:: Set project root
set PROJECT=C:\Users\Noah.Emery\OneDrive - Alltech, Inc\Documents\Projects\alltech_jumbotron

:: Start the AI monitor in its own window
start "Alltech Monitor" cmd /k "cd /d "%PROJECT%" && .venv\Scripts\python.exe main.py"

:: Start the display server in its own window
start "Alltech Display" cmd /k "cd /d "%PROJECT%\display" && python -m http.server 8000"

:: Open the browser after a 3 second delay
timeout /t 3 /nobreak > nul
start http://localhost:8000

echo Done. Close this window.
