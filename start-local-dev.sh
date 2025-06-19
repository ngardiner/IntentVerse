#!/bin/bash

# IntentVerse Local Development Start Script
# This script sets up and starts all IntentVerse services locally without Docker

# Exit on any error
set -e

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

# Function to clean up on error or interrupt
cleanup_on_error() {
    print_error "An error occurred. Stopping any started services..."
    
    # Check if stop script exists and is executable
    if [ -x ./stop-local-dev.sh ]; then
        ./stop-local-dev.sh
    else
        # Fallback if stop script is not available
        print_status "Stopping any running services..."
        
        # Kill processes by PID if we have them
        if [ -n "$CORE_PID" ] && ps -p $CORE_PID > /dev/null; then
            kill $CORE_PID 2>/dev/null || kill -9 $CORE_PID 2>/dev/null
        fi
        
        if [ -n "$MCP_PID" ] && ps -p $MCP_PID > /dev/null; then
            kill $MCP_PID 2>/dev/null || kill -9 $MCP_PID 2>/dev/null
        fi
        
        if [ -n "$WEB_PID" ] && ps -p $WEB_PID > /dev/null; then
            kill $WEB_PID 2>/dev/null || kill -9 $WEB_PID 2>/dev/null
        fi
        
        # Kill by port as a fallback
        if command -v lsof >/dev/null 2>&1; then
            lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
            lsof -ti:8001 2>/dev/null | xargs kill -9 2>/dev/null || true
            lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true
        fi
    fi
    
    # Remove PID file
    if [ -f ./.service_pids ]; then
        rm ./.service_pids
    fi
    
    exit 1
}

# Set up trap for error handling and interrupts
trap cleanup_on_error ERR INT

# Create logs directory if it doesn't exist
mkdir -p logs

# Check for required commands
check_command() {
    if ! command -v $1 &> /dev/null; then
        if [ "$1" = "python3" ] && command -v python &> /dev/null; then
            PYTHON_VERSION=$(python --version 2>&1)
            if [[ $PYTHON_VERSION == *"Python 3"* ]]; then
                print_warning "python3 command not found, but python is Python 3. Using python instead."
                alias python3=python
                return 0
            fi
        fi
        print_error "$1 is required but not installed. Please install it and try again."
        exit 1
    fi
}

print_status "Checking for required dependencies..."
check_command python3
check_command pip
check_command npm
check_command node

# Check if a port is already in use
check_port() {
    local port=$1
    if command -v lsof &> /dev/null; then
        if lsof -i:$port -sTCP:LISTEN &> /dev/null; then
            print_error "Port $port is already in use. Please stop any service using this port."
            return 1
        fi
    elif command -v netstat &> /dev/null; then
        if netstat -tuln | grep ":$port " &> /dev/null; then
            print_error "Port $port is already in use. Please stop any service using this port."
            return 1
        fi
    else
        print_warning "Cannot check if port $port is in use (lsof/netstat not available)"
    fi
    return 0
}

# Check if ports are available
check_port 8000 || exit 1  # Core service
check_port 8001 || exit 1  # MCP service
check_port 3000 || exit 1  # Web service

print_status "Starting IntentVerse local development services..."

# Function to create and activate a Python virtual environment
setup_venv() {
    local service_name=$1
    local service_dir=$2
    
    print_status "Setting up virtual environment for $service_name..."
    
    # Create venv if it doesn't exist
    if [ ! -d "$service_dir/venv" ]; then
        print_status "Creating new virtual environment for $service_name..."
        python3 -m venv "$service_dir/venv" || {
            print_error "Failed to create virtual environment for $service_name"
            return 1
        }
        print_status "Created new virtual environment for $service_name"
    else
        print_status "Using existing virtual environment for $service_name"
    fi
    
    # Activate venv and install requirements
    source "$service_dir/venv/bin/activate" || {
        print_error "Failed to activate virtual environment for $service_name"
        return 1
    }
    
    print_status "Installing dependencies for $service_name..."
    pip install --upgrade pip || print_warning "Failed to upgrade pip, continuing with existing version"
    pip install -r "$service_dir/requirements.txt" || {
        print_error "Failed to install dependencies for $service_name"
        deactivate
        return 1
    }
    print_success "$service_name dependencies installed"
    
    # Deactivate venv (we'll activate it again when starting the service)
    deactivate
    return 0
}

# Setup virtual environments
setup_venv "Core service" "core"
setup_venv "MCP service" "mcp"

# Function to start a service and wait for it to be ready
start_service() {
    local service_name=$1
    local service_dir=$2
    local port=$3
    local start_cmd=$4
    local log_file="../logs/${service_dir}.log"
    local max_wait=$5
    local health_endpoint=${6:-"/"}
    local pid_var_name=$7
    
    print_status "Starting $service_name on port $port..."
    
    # Change to service directory
    cd $service_dir
    
    # Start the service
    if [[ $service_dir == "web" ]]; then
        # For web service, use npm
        npm install --silent || {
            print_error "Failed to install npm dependencies for $service_name"
            cd ..
            return 1
        }
        nohup $start_cmd > $log_file 2>&1 &
    else
        # For Python services, use venv
        source venv/bin/activate || {
            print_error "Failed to activate virtual environment for $service_name"
            cd ..
            return 1
        }
        
        # Check for auto-reload capabilities
        if [[ $service_dir == "core" ]]; then
            # Check if uvicorn is installed with reload support
            if pip list | grep -q "watchfiles"; then
                print_status "Auto-reload support detected for Core service"
                start_cmd="uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
            else
                print_warning "Auto-reload support not detected for Core service"
                print_status "Installing watchfiles for auto-reload support..."
                pip install watchfiles
                start_cmd="uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
            fi
        fi
        
        export PYTHONPATH=$(pwd)
        if [[ $service_dir == "mcp" ]]; then
            export CORE_API_URL="http://localhost:8000"
        fi
        nohup $start_cmd > $log_file 2>&1 &
        deactivate
    fi
    
    # Save PID
    local PID=$!
    eval "$pid_var_name=$PID"
    
    # Return to root directory
    cd ..
    
    # Wait for service to be ready
    print_status "Waiting for $service_name to start (timeout: ${max_wait}s)..."
    local attempt=0
    while [ $attempt -lt $max_wait ]; do
        # Check if process is still running
        if ! ps -p $PID > /dev/null; then
            print_error "$service_name process died unexpectedly"
            print_error "Last few log lines:"
            tail -n 20 logs/${service_dir}.log
            return 1
        fi
        
        # Check if service is responding
        if curl -s http://localhost:$port$health_endpoint > /dev/null; then
            print_success "$service_name started successfully"
            return 0
        fi
        
        attempt=$((attempt+1))
        sleep 1
        
        # Show progress every 10 seconds
        if [ $((attempt % 10)) -eq 0 ]; then
            print_status "Still waiting for $service_name to start (${attempt}/${max_wait}s)..."
        fi
    done
    
    print_warning "$service_name did not respond within ${max_wait} seconds"
    print_warning "The service might still be starting up. Check logs/${service_dir}.log for details."
    
    # For core service, this is critical - fail if it doesn't start
    if [[ $service_name == "Core service" ]]; then
        print_error "Core service must be running for other services to work properly"
        tail -n 20 logs/${service_dir}.log
        return 1
    fi
    
    # For other services, just warn but continue
    return 0
}

# Start Core service
start_service "Core service" "core" 8000 "uvicorn app.main:app --host 0.0.0.0 --port 8000" 30 "/" CORE_PID || cleanup_on_error

# Start MCP service
start_service "MCP service" "mcp" 8001 "python -m app.main" 30 "/" MCP_PID || cleanup_on_error

# Start Web service
start_service "Web service" "web" 3000 "npm start" 60 "/" WEB_PID || cleanup_on_error

# Save PIDs to a file for the stop script
cat > .service_pids << EOF
# IntentVerse service PIDs - DO NOT EDIT MANUALLY
# Generated on $(date)
CORE_PID=$CORE_PID
MCP_PID=$MCP_PID
WEB_PID=$WEB_PID
EOF

# Verify all services are running
verify_running() {
    local pid=$1
    local name=$2
    if ps -p $pid > /dev/null; then
        print_success "$name is running (PID: $pid)"
        return 0
    else
        print_error "$name failed to start or crashed (expected PID: $pid)"
        return 1
    fi
}

print_status "Verifying all services are running..."
verify_running $CORE_PID "Core service" || print_warning "Check logs/core.log for details"
verify_running $MCP_PID "MCP service" || print_warning "Check logs/mcp.log for details"
verify_running $WEB_PID "Web service" || print_warning "Check logs/web.log for details"

# Print summary
print_success "All IntentVerse services started"
echo ""
print_status "=== SERVICE INFORMATION ==="
print_status "Core API:    http://localhost:8000"
print_status "MCP API:     http://localhost:8001"
print_status "Web UI:      http://localhost:3000"
echo ""
print_status "=== USEFUL COMMANDS ==="
print_status "View logs:   tail -f logs/{core,mcp,web}.log"
print_status "Stop all:    ./stop-local-dev.sh"
print_status "Restart all: ./stop-local-dev.sh && ./start-local-dev.sh"
echo ""
print_status "=== DEVELOPMENT TIPS ==="
print_status "- Core and MCP services will auto-reload when code changes"
print_status "- Web service will auto-reload when React code changes"
print_status "- Database is stored in core/intentverse.db"
echo ""