#!/bin/bash

# Sensor Hub Systemd Service Installer
# This script sets up systemd services for automatic startup

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

# Service files
SCHEDULER_SERVICE="systemd/sensor-hub-scheduler.service"
WEBAPP_SERVICE="systemd/sensor-hub-webapp.service"

print_status() {
    local status="$1"
    local message="$2"
    case "$status" in
        "success") echo -e "${GREEN}✅ $message${NC}" ;;
        "error") echo -e "${RED}❌ $message${NC}" ;;
        "info") echo -e "${BLUE}ℹ️  $message${NC}" ;;
        "warning") echo -e "${YELLOW}⚠️  $message${NC}" ;;
    esac
}

install_services() {
    echo -e "${BOLD}${BLUE}🔧 Installing Sensor Hub Systemd Services${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Check if running as root for system-wide install
    if [ "$EUID" -eq 0 ]; then
        local target_dir="/etc/systemd/system"
        print_status "info" "Installing system-wide services to $target_dir"
    else
        local target_dir="$HOME/.config/systemd/user"
        mkdir -p "$target_dir"
        print_status "info" "Installing user services to $target_dir"
    fi
    
    # Copy service files
    if [ -f "$SCHEDULER_SERVICE" ]; then
        cp "$SCHEDULER_SERVICE" "$target_dir/"
        print_status "success" "Installed scheduler service"
    else
        print_status "error" "Scheduler service file not found: $SCHEDULER_SERVICE"
        return 1
    fi
    
    if [ -f "$WEBAPP_SERVICE" ]; then
        cp "$WEBAPP_SERVICE" "$target_dir/"
        print_status "success" "Installed web app service"
    else
        print_status "error" "Web app service file not found: $WEBAPP_SERVICE"
        return 1
    fi
    
    # Reload systemd
    if [ "$EUID" -eq 0 ]; then
        systemctl daemon-reload
        print_status "success" "Reloaded systemd daemon"
    else
        systemctl --user daemon-reload
        print_status "success" "Reloaded user systemd daemon"
    fi
    
    echo
    print_status "success" "🎉 Services installed successfully!"
    echo
    echo -e "${YELLOW}📋 Next steps:${NC}"
    if [ "$EUID" -eq 0 ]; then
        echo "  • Enable services: sudo systemctl enable sensor-hub-scheduler sensor-hub-webapp"
        echo "  • Start services:  sudo systemctl start sensor-hub-scheduler sensor-hub-webapp"
        echo "  • Check status:    sudo systemctl status sensor-hub-scheduler sensor-hub-webapp"
        echo "  • View logs:       sudo journalctl -fu sensor-hub-scheduler"
    else
        echo "  • Enable services: systemctl --user enable sensor-hub-scheduler sensor-hub-webapp"
        echo "  • Start services:  systemctl --user start sensor-hub-scheduler sensor-hub-webapp"
        echo "  • Check status:    systemctl --user status sensor-hub-scheduler sensor-hub-webapp"
        echo "  • View logs:       journalctl --user -fu sensor-hub-scheduler"
        echo "  • Enable lingering: sudo loginctl enable-linger $USER"
    fi
}

uninstall_services() {
    echo -e "${BOLD}${YELLOW}🗑️  Uninstalling Sensor Hub Systemd Services${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ "$EUID" -eq 0 ]; then
        local target_dir="/etc/systemd/system"
        local ctl_cmd="systemctl"
    else
        local target_dir="$HOME/.config/systemd/user"
        local ctl_cmd="systemctl --user"
    fi
    
    # Stop and disable services
    $ctl_cmd stop sensor-hub-scheduler sensor-hub-webapp 2>/dev/null || true
    $ctl_cmd disable sensor-hub-scheduler sensor-hub-webapp 2>/dev/null || true
    
    # Remove service files
    rm -f "$target_dir/sensor-hub-scheduler.service"
    rm -f "$target_dir/sensor-hub-webapp.service"
    
    # Reload systemd
    $ctl_cmd daemon-reload
    
    print_status "success" "Services uninstalled"
}

show_status() {
    echo -e "${BOLD}${CYAN}📊 Systemd Service Status${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ "$EUID" -eq 0 ]; then
        local ctl_cmd="systemctl"
    else
        local ctl_cmd="systemctl --user"
    fi
    
    echo -e "${BLUE}Scheduler Service:${NC}"
    $ctl_cmd status sensor-hub-scheduler --no-pager --lines=3 2>/dev/null || echo "  Service not found or not running"
    
    echo
    echo -e "${BLUE}Web App Service:${NC}"
    $ctl_cmd status sensor-hub-webapp --no-pager --lines=3 2>/dev/null || echo "  Service not found or not running"
}

show_help() {
    echo -e "${BOLD}${CYAN}Sensor Hub Systemd Service Manager${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    echo -e "${BOLD}Usage:${NC}"
    echo "  ./systemd_setup.sh [command]"
    echo
    echo -e "${BOLD}Commands:${NC}"
    echo -e "  ${GREEN}install${NC}     Install systemd services"
    echo -e "  ${RED}uninstall${NC}   Remove systemd services"
    echo -e "  ${BLUE}status${NC}      Show service status"
    echo -e "  ${CYAN}help${NC}        Show this help message"
    echo
    echo -e "${BOLD}Notes:${NC}"
    echo "  • Run as regular user for user services"
    echo "  • Run with sudo for system-wide services"
    echo "  • User services require 'sudo loginctl enable-linger $USER'"
    echo
}

# Main execution
case "${1:-help}" in
    "install")
        install_services
        ;;
    "uninstall")
        uninstall_services
        ;;
    "status")
        show_status
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