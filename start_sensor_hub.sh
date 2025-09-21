#!/bin/bash

# Sensor Hub Startup Script
# This script starts both the scheduler and web application

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}=== Sensor Hub Startup Script ===${NC}"
echo -e "${BLUE}Working directory: $SCRIPT_DIR${NC}"
echo

# Function to check if a process is running
check_process() {
    local process_name="$1"
    if pgrep -f "$process_name" > /dev/null 2>&1; then
        return 0  # Process is running
    else
        return 1  # Process is not running
    fi
}

# Function to stop existing processes
stop_existing_processes() {
    echo -e "${YELLOW}Stopping any existing sensor hub processes...${NC}"
    
    # Stop scheduler
    if check_process "start-scheduler"; then
        echo "  Stopping existing scheduler..."
        pkill -f "start-scheduler"
        sleep 2
    fi
    
    # Stop web app (look for Flask with our app)
    if check_process "flask.*src\.sensor_hub.*run"; then
        echo "  Stopping existing web app..."
        pkill -f "flask.*src\.sensor_hub.*run"
        sleep 2
    fi
    
    echo -e "${GREEN}  Cleanup complete.${NC}"
}

# Function to start the scheduler
start_scheduler() {
    echo -e "${BLUE}Starting sensor scheduler...${NC}"
    
    # Use poetry if available, otherwise use direct python
    if command -v poetry &> /dev/null && [ -f "pyproject.toml" ]; then
        echo "  Using Poetry environment..."
        poetry run python -m flask --app src.sensor_hub start-scheduler > scheduler.log 2>&1 &
        SCHEDULER_PID=$!
        echo "  Scheduler PID: $SCHEDULER_PID"
    else
        echo "  Using direct Python..."
        python -m flask --app src.sensor_hub start-scheduler > scheduler.log 2>&1 &
        SCHEDULER_PID=$!
        echo "  Scheduler PID: $SCHEDULER_PID"
    fi
    
    sleep 8
    
    # Check if the process is still running and look for success indicators in log
    if kill -0 $SCHEDULER_PID 2>/dev/null; then
        # Also check if the scheduler is actually working by looking for data collection messages
        if grep -q "Starting data collection\|ready" scheduler.log; then
            echo -e "${GREEN}  ✅ Scheduler started successfully (PID: $SCHEDULER_PID)${NC}"
            echo "  📄 Logs: scheduler.log"
            return 0
        else
            echo -e "${YELLOW}  ⚠️  Scheduler process running but no sensors ready${NC}"
            echo "  📄 Check scheduler.log for sensor issues"
            return 0  # Still return success since the process is running
        fi
    else
        echo -e "${RED}  ❌ Failed to start scheduler${NC}"
        echo "  📄 Check scheduler.log for errors"
        return 1
    fi
}

# Function to start the web app
start_webapp() {
    echo -e "${BLUE}Starting web application...${NC}"
    
    # Use poetry if available, otherwise use direct python
    if command -v poetry &> /dev/null && [ -f "pyproject.toml" ]; then
        echo "  Using Poetry environment..."
        poetry run python -m flask --app src.sensor_hub run --host=0.0.0.0 --port=5001 > webapp.log 2>&1 &
        WEBAPP_PID=$!
        echo "  Web app PID: $WEBAPP_PID"
    else
        echo "  Using direct Python..."
        python -m flask --app src.sensor_hub run --host=0.0.0.0 --port=5001 > webapp.log 2>&1 &
        WEBAPP_PID=$!
        echo "  Web app PID: $WEBAPP_PID"
    fi
    
    sleep 5
    
    # Check if the process is still running
    if kill -0 $WEBAPP_PID 2>/dev/null; then
        echo -e "${GREEN}  ✅ Web app started successfully (PID: $WEBAPP_PID)${NC}"
        echo -e "${GREEN}  🌐 Web interface: http://localhost:5001${NC}"
        echo "  📄 Logs: webapp.log"
        return 0
    else
        echo -e "${RED}  ❌ Failed to start web app${NC}"
        echo "  📄 Check webapp.log for errors"
        return 1
    fi
}

# Function to show status
show_status() {
    echo
    echo -e "${BLUE}=== Service Status ===${NC}"
    
    if check_process "start-scheduler"; then
        echo -e "${GREEN}  📊 Scheduler: Running${NC}"
    else
        echo -e "${RED}  📊 Scheduler: Stopped${NC}"
    fi
    
    if check_process "flask.*src\.sensor_hub.*run"; then
        echo -e "${GREEN}  🌐 Web App: Running${NC}"
        echo -e "${GREEN}     URL: http://localhost:5001${NC}"
    else
        echo -e "${RED}  🌐 Web App: Stopped${NC}"
    fi
    
    echo
}

# Function to create a stop script
create_stop_script() {
    cat > stop_sensor_hub.sh << 'EOF'
#!/bin/bash

# Sensor Hub Stop Script
echo "Stopping Sensor Hub services..."

# Stop scheduler
if pgrep -f "start-scheduler" > /dev/null; then
    echo "  Stopping scheduler..."
    pkill -f "start-scheduler"
fi

# Stop web app
if pgrep -f "flask.*src\.sensor_hub.*run" > /dev/null; then
    echo "  Stopping web app..."
    pkill -f "flask.*src\.sensor_hub.*run"
fi

sleep 2
echo "✅ All services stopped."
EOF
    
    chmod +x stop_sensor_hub.sh
    echo -e "${GREEN}  📝 Created stop_sensor_hub.sh script${NC}"
}

# Main execution
main() {
    # Parse command line arguments
    case "${1:-start}" in
        "start")
            stop_existing_processes
            echo
            
            # Start scheduler
            if start_scheduler; then
                echo
                # Start web app
                if start_webapp; then
                    echo
                    create_stop_script
                    show_status
                    
                    echo -e "${GREEN}🚀 Sensor Hub is now running!${NC}"
                    echo -e "${YELLOW}💡 Tips:${NC}"
                    echo "   • Web interface: http://localhost:5001"
                    echo "   • Stop services: ./stop_sensor_hub.sh"
                    echo "   • View logs: Check terminal output"
                    echo
                else
                    echo -e "${RED}❌ Failed to start web app. Stopping scheduler...${NC}"
                    pkill -f "start-scheduler"
                    exit 1
                fi
            else
                echo -e "${RED}❌ Failed to start scheduler.${NC}"
                exit 1
            fi
            ;;
        "stop")
            stop_existing_processes
            ;;
        "status")
            show_status
            ;;
        "restart")
            stop_existing_processes
            sleep 2
            $0 start
            ;;
        *)
            echo "Usage: $0 {start|stop|status|restart}"
            echo "  start   - Start scheduler and web app"
            echo "  stop    - Stop all services"
            echo "  status  - Show service status"
            echo "  restart - Restart all services"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"