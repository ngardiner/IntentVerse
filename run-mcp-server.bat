@echo off
REM IntentVerse MCP Server Start Script for Windows
REM This script starts the MCP component in a virtual environment for local non-docker use as an MCP server

setlocal enabledelayedexpansion

REM Default values
set "STDIO_MODE=false"
set "CORE_URL=http://localhost:8000"
set "API_KEY=dev-service-key-12345"
set "VENV_PATH=mcp\venv"

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :args_done
if "%~1"=="--stdio" (
    set "STDIO_MODE=true"
    shift
    goto :parse_args
)
if "%~1"=="--core-url" (
    set "CORE_URL=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="--api-key" (
    set "API_KEY=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="--venv-path" (
    set "VENV_PATH=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="-h" goto :show_help
if "%~1"=="--help" goto :show_help
echo [ERROR] Unknown option: %~1
echo Use --help for usage information
exit /b 1

:show_help
echo Usage: %~nx0 [OPTIONS]
echo.
echo Start the IntentVerse MCP server in a virtual environment
echo.
echo Options:
echo   --stdio              Run in stdio mode (for MCP client connections)
echo   --core-url URL       Core service URL (default: http://localhost:8000)
echo   --api-key KEY        Service API key (default: dev-service-key-12345)
echo   --venv-path PATH     Virtual environment path (default: mcp\venv)
echo   -h, --help           Show this help message
echo.
echo Examples:
echo   %~nx0                   # Start in HTTP mode for testing
echo   %~nx0 --stdio           # Start in stdio mode for MCP clients
echo   %~nx0 --core-url http://remote:8000 --stdio
exit /b 0

:args_done

echo [INFO] Starting IntentVerse MCP Server...
if "%STDIO_MODE%"=="true" (
    echo [INFO] Mode: stdio (MCP client mode)
) else (
    echo [INFO] Mode: HTTP (testing mode)
)
echo [INFO] Core URL: %CORE_URL%

REM Check if we're in the right directory
if not exist "mcp" (
    echo [ERROR] mcp directory not found. Please run this script from the IntentVerse root directory.
    exit /b 1
)

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is required but not installed or not in PATH.
    exit /b 1
)

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Change to MCP directory
cd mcp

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    exit /b 1
)

REM Install/upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

REM Install requirements
echo [INFO] Installing Python dependencies...
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    exit /b 1
)
echo [SUCCESS] Dependencies installed

REM Set environment variables
set "PYTHONPATH=%CD%"
set "CORE_API_URL=%CORE_URL%"
set "SERVICE_API_KEY=%API_KEY%"

echo [INFO] Environment variables set:
echo [INFO]   PYTHONPATH=%PYTHONPATH%
echo [INFO]   CORE_API_URL=%CORE_API_URL%
echo [INFO]   SERVICE_API_KEY=%API_KEY%

REM Prepare the command
if "%STDIO_MODE%"=="true" (
    set "CMD=python -m app.main --stdio"
    echo [INFO] Starting MCP server in stdio mode...
    echo [INFO] The server will communicate via stdin/stdout for MCP client connections
) else (
    set "CMD=python -m app.main"
    echo [INFO] Starting MCP server in HTTP mode on port 8001...
    echo [INFO] You can test the server at: http://localhost:8001
)

echo [INFO] Command: !CMD!
echo [INFO] Press Ctrl+C to stop the server
echo.

REM Start the MCP server
!CMD!