#!/bin/bash

# IntentVerse Local Development Stop Script
# This script stops all locally running IntentVerse services

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

print_status "Stopping IntentVerse local development services..."

# Function to kill processes on a specific port
kill_port() {
    local port=$1
    local service_name=$2
    
    if command -v lsof >/dev/null 2>&1; then
        local pids=$(lsof -ti:$port 2>/dev/null)
        if [ -n "$pids" ]; then
            print_status "Stopping $service_name on port $port..."
            echo $pids | xargs kill -TERM 2>/dev/null || true
            sleep 2
            
            # Force kill if still running
            local remaining_pids=$(lsof -ti:$port 2>/dev/null)
            if [ -n "$remaining_pids" ]; then
                print_warning "Force killing $service_name..."
                echo $remaining_pids | xargs kill -9 2>/dev/null || true
            fi
            print_success "$service_name stopped"
        else
            print_status "$service_name was not running on port $port"
        fi
    else
        print_warning "lsof not available - cannot check port $port"
    fi
}

# Stop services on their respective ports
kill_port 8000 "Core service"
kill_port 8001 "MCP service"
kill_port 3000 "Web service"

# Also kill any uvicorn, node, or python processes that might be related
print_status "Cleaning up any remaining IntentVerse processes..."

# Kill uvicorn processes (core service)
pkill -f "uvicorn.*app.main:app" 2>/dev/null || true

# Kill MCP processes
pkill -f "python.*app.main" 2>/dev/null || true

# Kill React development server
pkill -f "react-scripts start" 2>/dev/null || true
pkill -f "node.*react-scripts" 2>/dev/null || true

print_success "All IntentVerse services stopped"

# Clean up log files if they exist
if [ -d "logs" ]; then
    print_status "Log files are preserved in logs/ directory"
    print_status "Use 'rm -rf logs/' to clean them up if desired"
fi