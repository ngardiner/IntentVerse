#!/bin/bash

# IntentVerse MCP Server Start Script
# This script starts the MCP component in a virtual environment for local non-docker use as an MCP server

# Exit on any error
set -e

# Change to the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_error "Port $port is already in use. Please stop the service using that port."
        return 1
    fi
    return 0
}

# Function to check if core service is running
check_core_service() {
    local core_url=${1:-"http://localhost:8000"}
    print_status "Checking if Core service is available at $core_url..."
    
    if command_exists curl; then
        if curl -s "$core_url/" > /dev/null 2>&1; then
            print_success "Core service is running and accessible"
            return 0
        else
            print_warning "Core service is not accessible at $core_url"
            print_warning "Make sure the Core service is running before starting the MCP server"
            print_warning "You can start it with: ./start-local-dev.sh or run just the core service"
            return 1
        fi
    else
        print_warning "curl not found, skipping Core service check"
        print_warning "Please ensure the Core service is running at $core_url"
        return 0
    fi
}

# Parse command line arguments
STDIO_MODE=false
CORE_URL="http://localhost:8000"
API_KEY="dev-service-key-12345"
VENV_PATH="mcp/venv"

while [[ $# -gt 0 ]]; do
    case $1 in
        --stdio)
            STDIO_MODE=true
            shift
            ;;
        --core-url)
            CORE_URL="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        --venv-path)
            VENV_PATH="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Start the IntentVerse MCP server in a virtual environment"
            echo ""
            echo "Options:"
            echo "  --stdio              Run in stdio mode (for MCP client connections)"
            echo "  --core-url URL       Core service URL (default: http://localhost:8000)"
            echo "  --api-key KEY        Service API key (default: dev-service-key-12345)"
            echo "  --venv-path PATH     Virtual environment path (default: mcp/venv)"
            echo "  -h, --help           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                   # Start in HTTP mode for testing"
            echo "  $0 --stdio           # Start in stdio mode for MCP clients"
            echo "  $0 --core-url http://remote:8000 --stdio"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# In stdio mode, redirect all output to log file to preserve clean MCP protocol
if [ "$STDIO_MODE" = true ]; then
    # Create logs directory if it doesn't exist
    mkdir -p logs
    # Redirect both stdout and stderr to log file, save original stdout for MCP protocol
    exec 3>&1 1>>logs/mcp-stdio.log 2>&1
fi

print_status "Starting IntentVerse MCP Server..."
print_status "Mode: $([ "$STDIO_MODE" = true ] && echo "stdio (MCP client mode)" || echo "HTTP (testing mode)")"
print_status "Core URL: $CORE_URL"

# Check if we're in the right directory
if [ ! -d "mcp" ]; then
    print_error "mcp directory not found. Please run this script from the IntentVerse root directory."
    exit 1
fi

# Check required tools
if ! command_exists python3; then
    print_error "python3 is required but not installed."
    exit 1
fi

if ! command_exists pip; then
    print_error "pip is required but not installed."
    exit 1
fi

# Check if core service is running (only if not in stdio mode, as stdio mode might be used independently)
if [ "$STDIO_MODE" = false ]; then
    check_core_service "$CORE_URL" || {
        print_error "Core service check failed. Please start the Core service first."
        exit 1
    }
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Change to MCP directory
cd mcp

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install requirements
print_status "Installing Python dependencies..."
pip install -r requirements.txt > /dev/null 2>&1
print_success "Dependencies installed"

# Set environment variables
export PYTHONPATH=$(pwd)
export CORE_API_URL="$CORE_URL"
export SERVICE_API_KEY="$API_KEY"

print_status "Environment variables set:"
print_status "  PYTHONPATH=$PYTHONPATH"
print_status "  CORE_API_URL=$CORE_API_URL"
print_status "  SERVICE_API_KEY=$API_KEY"

# Prepare the command
if [ "$STDIO_MODE" = true ]; then
    CMD="python -m app.main --stdio"
    # In stdio mode, all output goes to log file to avoid interfering with MCP protocol
    print_status "Starting MCP server in stdio mode..."
    print_status "The server will communicate via stdin/stdout for MCP client connections"
    print_status "Command: $CMD"
    print_status "All logs will be sent to logs/mcp-stdio.log to preserve stdio protocol"
else
    CMD="python -m app.main"
    print_status "Starting MCP server in HTTP mode on port 8001..."
    print_status "You can test the server at: http://localhost:8001"
    
    # Check if port 8001 is available
    if ! check_port 8001; then
        exit 1
    fi
    
    print_status "Command: $CMD"
    print_status "Press Ctrl+C to stop the server"
    echo ""
fi

# Start the MCP server
if [ "$STDIO_MODE" = true ]; then
    # Restore stdout for MCP protocol communication
    exec 1>&3 3>&-
fi
exec $CMD