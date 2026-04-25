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

set PYTHON_EXE=C:\Users\Eureka\AppData\Local\Programs\Python\Python312\python.exe

if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" main.py
) else (
    python main.py
)

pause
