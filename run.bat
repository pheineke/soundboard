@echo off
title Soundboard Server

echo Starting Soundboard Server...
echo.
echo ╔═══════════════════════════════════════════════╗
echo ║              🎵 SOUNDBOARD 🎵                 ║
echo ║                                               ║
echo ║  Server will start on: http://localhost:5000 ║
echo ║                                               ║
echo ║  Press Ctrl+C to stop the server             ║
echo ╚═══════════════════════════════════════════════╝
echo.

REM Check if executable exists
if not exist "soundboard.exe" (
    echo ✗ soundboard.exe not found!
    echo ✗ Please run build.bat first to compile the application.
    echo.
    pause
    exit /b 1
)

REM Start the server
echo Starting server...
soundboard.exe

REM If we get here, the server stopped
echo.
echo Server stopped.
pause
