#!/bin/bash

# Sensor Hub Management Script
# A simple, unified script to start, stop, restart, and check status of the sensor hub

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
SCHEDULER_PROCESS="flask.*start-scheduler"
WEBAPP_PROCESS="flask.*run"
LOG_DIR="$SCRIPT_DIR/logs"
SCHEDULER_LOG="$LOG_DIR/scheduler.log"
WEBAPP_LOG="$LOG_DIR/webapp.log"

# Ensure logs directory exists
mkdir -p "$LOG_DIR"

# Function to print colored status messages
print_status() {
    local status="$1"
    local message="$2"
    case "$status" in
        "success") echo -e "${GREEN}✅ $message${NC}" ;;
        "error") echo -e "${RED}❌ $message${NC}" ;;
        "info") echo -e "${BLUE}ℹ️  $message${NC}" ;;
        "warning") echo -e "${YELLOW}⚠️  $message${NC}" ;;
        "running") echo -e "${GREEN}🟢 $message${NC}" ;;
        "stopped") echo -e "${RED}🔴 $message${NC}" ;;
    esac
}

# Function to check if a process is running
is_running() {
    local process_pattern="$1"
    pgrep -f "$process_pattern" > /dev/null 2>&1
}

# Function to get process PID
get_pid() {
    local process_pattern="$1"
    pgrep -f "$process_pattern" 2>/dev/null | head -1
}

# Function to stop a process gracefully
stop_process() {
    local process_pattern="$1"
    local service_name="$2"
    
    if is_running "$process_pattern"; then
        local pid=$(get_pid "$process_pattern")
        print_status "info" "Stopping $service_name (PID: $pid)..."
        pkill -f "$process_pattern"
        
        # Wait up to 10 seconds for graceful shutdown
        for i in {1..10}; do
            if ! is_running "$process_pattern"; then
                print_status "success" "$service_name stopped successfully"
                return 0
            fi
            sleep 1
        done
        
        # Force kill if still running
        print_status "warning" "Force stopping $service_name..."
        pkill -9 -f "$process_pattern"
        sleep 2
        
        if ! is_running "$process_pattern"; then
            print_status "success" "$service_name force stopped"
            return 0
        else
            print_status "error" "Failed to stop $service_name"
            return 1
        fi
    else
        print_status "info" "$service_name is not running"
        return 0
    fi
}

# Function to start the scheduler
start_scheduler() {
    print_status "info" "Starting sensor scheduler..."
    
    if is_running "$SCHEDULER_PROCESS"; then
        print_status "warning" "Scheduler is already running"
        return 0
    fi
    
    # Start scheduler with new logging
    poetry run flask --app src.sensor_hub.app start-scheduler > "$SCHEDULER_LOG" 2>&1 &
    local pid=$!
    
    # Wait a moment and check if it started successfully
    sleep 3
    
    if is_running "$SCHEDULER_PROCESS"; then
        print_status "success" "Scheduler started successfully (PID: $(get_pid "$SCHEDULER_PROCESS"))"
        print_status "info" "Scheduler logs: $SCHEDULER_LOG"
        return 0
    else
        print_status "error" "Failed to start scheduler"
        print_status "info" "Check logs: $SCHEDULER_LOG"
        return 1
    fi
}

# Function to start the web application
start_webapp() {
    print_status "info" "Starting web application..."
    
    if is_running "$WEBAPP_PROCESS"; then
        print_status "warning" "Web application is already running"
        return 0
    fi
    
    # Start web app
    poetry run flask --app src.sensor_hub.app run --host=0.0.0.0 --port=5001 > "$WEBAPP_LOG" 2>&1 &
    local pid=$!
    
    # Wait a moment and check if it started successfully
    sleep 3
    
    if is_running "$WEBAPP_PROCESS"; then
        print_status "success" "Web application started successfully (PID: $(get_pid "$WEBAPP_PROCESS"))"
        print_status "success" "🌐 Access at: http://localhost:5001"
        print_status "info" "Web app logs: $WEBAPP_LOG"
        return 0
    else
        print_status "error" "Failed to start web application"
        print_status "info" "Check logs: $WEBAPP_LOG"
        return 1
    fi
}

# Function to show current status
show_status() {
    echo -e "${BOLD}${CYAN}📊 Sensor Hub Status${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Check scheduler status
    if is_running "$SCHEDULER_PROCESS"; then
        local scheduler_pid=$(get_pid "$SCHEDULER_PROCESS")
        print_status "running" "Scheduler (PID: $scheduler_pid)"
    else
        print_status "stopped" "Scheduler"
    fi
    
    # Check web app status
    if is_running "$WEBAPP_PROCESS"; then
        local webapp_pid=$(get_pid "$WEBAPP_PROCESS")
        print_status "running" "Web Application (PID: $webapp_pid)"
        echo -e "    ${CYAN}🌐 URL: http://localhost:5001${NC}"
    else
        print_status "stopped" "Web Application"
    fi
    
    echo
    
    # Show recent log activity
    if [ -f "$SCHEDULER_LOG" ]; then
        echo -e "${BLUE}📄 Recent Scheduler Activity:${NC}"
        tail -3 "$SCHEDULER_LOG" 2>/dev/null | sed 's/^/    /' || echo "    No recent activity"
        echo
    fi
    
    if [ -f "$WEBAPP_LOG" ]; then
        echo -e "${BLUE}📄 Recent Web App Activity:${NC}"
        tail -3 "$WEBAPP_LOG" 2>/dev/null | sed 's/^/    /' || echo "    No recent activity"
        echo
    fi
}

# Function to start all services
start_all() {
    echo -e "${BOLD}${BLUE}🚀 Starting Sensor Hub${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local success=true
    
    # Start scheduler first
    if ! start_scheduler; then
        success=false
    fi
    
    echo
    
    # Start web app
    if ! start_webapp; then
        success=false
        # If web app fails, stop scheduler
        stop_process "$SCHEDULER_PROCESS" "scheduler"
    fi
    
    echo
    
    if $success; then
        print_status "success" "🎉 Sensor Hub is running!"
        echo
        echo -e "${YELLOW}💡 Quick Commands:${NC}"
        echo -e "   ${CYAN}• Stop:${NC}    ./sensor_hub.sh stop"
        echo -e "   ${CYAN}• Status:${NC}  ./sensor_hub.sh status"
        echo -e "   ${CYAN}• Restart:${NC} ./sensor_hub.sh restart"
        echo -e "   ${CYAN}• Logs:${NC}    ./sensor_hub.sh logs"
        echo
    else
        print_status "error" "Failed to start Sensor Hub"
        return 1
    fi
}

# Function to stop all services
stop_all() {
    echo -e "${BOLD}${YELLOW}🛑 Stopping Sensor Hub${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    stop_process "$WEBAPP_PROCESS" "web application"
    echo
    stop_process "$SCHEDULER_PROCESS" "scheduler"
    echo
    print_status "success" "🏁 Sensor Hub stopped"
}

# Function to restart all services
restart_all() {
    echo -e "${BOLD}${CYAN}🔄 Restarting Sensor Hub${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    stop_all
    echo
    sleep 2
    start_all
}

# Function to show logs
show_logs() {
    echo -e "${BOLD}${BLUE}📄 Sensor Hub Logs${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ -f "$SCHEDULER_LOG" ]; then
        echo -e "${CYAN}Scheduler Logs (last 20 lines):${NC}"
        tail -20 "$SCHEDULER_LOG" 2>/dev/null || echo "No scheduler logs found"
        echo
    fi
    
    if [ -f "$WEBAPP_LOG" ]; then
        echo -e "${CYAN}Web App Logs (last 20 lines):${NC}"
        tail -20 "$WEBAPP_LOG" 2>/dev/null || echo "No web app logs found"
        echo
    fi
    
    # Also show the main sensor hub log
    local main_log="$LOG_DIR/sensor_hub.log"
    if [ -f "$main_log" ]; then
        echo -e "${CYAN}Main Sensor Hub Logs (last 10 lines):${NC}"
        tail -10 "$main_log" 2>/dev/null || echo "No main logs found"
        echo
    fi
}

# Function to show help
show_help() {
    echo -e "${BOLD}${CYAN}Sensor Hub Management Script${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    echo -e "${BOLD}Usage:${NC}"
    echo "  ./sensor_hub.sh [command]"
    echo
    echo -e "${BOLD}Commands:${NC}"
    echo -e "  ${GREEN}start${NC}     Start the sensor hub (scheduler + web app)"
    echo -e "  ${RED}stop${NC}      Stop all sensor hub services"
    echo -e "  ${YELLOW}restart${NC}   Restart all services"
    echo -e "  ${BLUE}status${NC}    Show current status of all services"
    echo -e "  ${CYAN}logs${NC}      Show recent log output"
    echo -e "  ${CYAN}help${NC}      Show this help message"
    echo
    echo -e "${BOLD}Examples:${NC}"
    echo "  ./sensor_hub.sh start    # Start everything"
    echo "  ./sensor_hub.sh status   # Check what's running"
    echo "  ./sensor_hub.sh logs     # View recent activity"
    echo
}

# Main execution
case "${1:-help}" in
    "start")
        start_all
        ;;
    "stop")
        stop_all
        ;;
    "restart")
        restart_all
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo
        show_help
        exit 1
        ;;
esac