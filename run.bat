@echo off
cd /d "%~dp0"
if errorlevel 1 (
    pushd "%~dp0"
)

rem check admin, if not, elevate
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\"' -Verb RunAs"
    exit /b
)

py -3.12 main.py
if %errorlevel% neq 0 (
    python main.py
)

pause
