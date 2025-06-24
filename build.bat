@echo off
echo Building Go Soundboard executable...

REM Initialize Go module if not exists
if not exist go.sum (
    echo Downloading Go dependencies...
    go mod tidy
)

REM Build the executable
echo Compiling...
go build -ldflags="-s -w" -o soundboard.exe main.go

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ Build successful! 
    echo ✓ Executable created: soundboard.exe
    echo.
    echo To run the soundboard:
    echo   1. Double-click soundboard.exe
    echo   2. Open http://localhost:5000 in your browser
    echo.
    pause
) else (
    echo.
    echo ✗ Build failed! Check the errors above.
    echo.
    pause
)
