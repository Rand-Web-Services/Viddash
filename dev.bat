@echo off
REM Development server with auto-reload enabled
REM This script enables Flask debug mode which auto-reloads on code changes
setlocal
set FLASK_ENV=development
set FLASK_DEBUG=1
set SSLKEYLOGFILE=
echo .
echo Starting Viddash development server with auto-reload...
echo Changes to files will automatically reload the server.
echo Press Ctrl+C to stop.
echo .
python -m flask --app app run
pause
