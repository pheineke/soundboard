@echo off
title Soundboard - Go Version

echo.
echo ================================================================
echo                    SOUNDBOARD - GO VERSION                     
echo                                                                
echo  Your soundboard is starting up...                            
echo                                                                
echo  Server will start on: http://localhost:5000                  
echo  Open this URL in your web browser                            
echo                                                                
echo  Features:                                                     
echo     * Click buttons to play/stop sounds                       
echo     * Upload new audio files (MP3, WAV, OGG)                  
echo     * Edit mode: rearrange and color buttons                  
echo     * Real-time updates across multiple browsers              
echo                                                                
echo  Press Ctrl+C to stop the server                              
echo ================================================================
echo.

REM Check if executable exists
if not exist "soundboard.exe" (
    echo [ERROR] soundboard.exe not found!
    echo.
    echo Please make sure you have:
    echo 1. Built the application using: go build -o soundboard.exe main.go
    echo 2. Or run build.bat to compile it
    echo.
    pause
    exit /b 1
)

REM Check if required directories exist
if not exist "templates\index_go.html" (
    echo [ERROR] Required template file not found!
    echo Missing: templates\index_go.html
    echo.
    pause
    exit /b 1
)

if not exist "static\icons" (
    echo [ERROR] Static files directory not found!
    echo Missing: static\icons\
    echo.
    pause
    exit /b 1
)

echo [OK] All required files found. Starting server...
echo.
echo [INFO] Opening your default browser automatically...
echo.

REM Start the server in background and capture PID
start /B "" soundboard.exe

REM Wait a moment for server to start
timeout /t 2 /nobreak >nul

REM Try to open the browser
start "" "http://localhost:5000"

echo.
echo [SUCCESS] Server started successfully!
echo.
echo Tips:
echo    * Keep this window open while using the soundboard
echo    * Add your own audio files to the 'uploads' folder
echo    * The server will automatically detect new files
echo.
echo Press any key to stop the server...
pause >nul

REM Kill the server process
taskkill /F /IM soundboard.exe >nul 2>&1

echo.
echo [STOPPED] Server stopped. Thank you for using Soundboard!
pause
