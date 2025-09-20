#!/bin/bash

# Desktop Shortcuts Installer for Sensor Hub
# This script installs desktop shortcuts for easy GUI access

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

install_shortcuts() {
    echo -e "${BOLD}${BLUE}🖥️  Installing Desktop Shortcuts${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Determine target directories
    local desktop_dir="$HOME/Desktop"
    local applications_dir="$HOME/.local/share/applications"
    
    # Create directories if they don't exist
    mkdir -p "$desktop_dir"
    mkdir -p "$applications_dir"
    
    # Copy desktop files
    local shortcuts=(
        "sensor-hub-start.desktop"
        "sensor-hub-stop.desktop"
        "sensor-hub-status.desktop"
        "sensor-hub-dashboard.desktop"
    )
    
    print_status "info" "Installing shortcuts to $desktop_dir and $applications_dir"
    echo
    
    for shortcut in "${shortcuts[@]}"; do
        local source_file="desktop/$shortcut"
        
        if [ -f "$source_file" ]; then
            # Copy to desktop
            cp "$source_file" "$desktop_dir/"
            chmod +x "$desktop_dir/$shortcut"
            
            # Copy to applications menu
            cp "$source_file" "$applications_dir/"
            chmod +x "$applications_dir/$shortcut"
            
            print_status "success" "Installed $shortcut"
        else
            print_status "error" "Source file not found: $source_file"
        fi
    done
    
    # Update desktop database
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$applications_dir" 2>/dev/null || true
        print_status "info" "Updated desktop database"
    fi
    
    echo
    print_status "success" "🎉 Desktop shortcuts installed!"
    echo
    echo -e "${YELLOW}📋 Available shortcuts:${NC}"
    echo "  • Sensor Hub (Start) - Start the sensor hub services"
    echo "  • Sensor Hub - Stop - Stop all services"
    echo "  • Sensor Hub - Status - Check status and view logs"
    echo "  • Sensor Hub Dashboard - Open web dashboard in browser"
    echo
    echo -e "${YELLOW}📍 Locations:${NC}"
    echo "  • Desktop: $desktop_dir"
    echo "  • Applications menu: $applications_dir"
}

uninstall_shortcuts() {
    echo -e "${BOLD}${YELLOW}🗑️  Uninstalling Desktop Shortcuts${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local desktop_dir="$HOME/Desktop"
    local applications_dir="$HOME/.local/share/applications"
    
    local shortcuts=(
        "sensor-hub-start.desktop"
        "sensor-hub-stop.desktop"
        "sensor-hub-status.desktop"
        "sensor-hub-dashboard.desktop"
    )
    
    for shortcut in "${shortcuts[@]}"; do
        # Remove from desktop
        if [ -f "$desktop_dir/$shortcut" ]; then
            rm "$desktop_dir/$shortcut"
            print_status "success" "Removed $shortcut from desktop"
        fi
        
        # Remove from applications menu
        if [ -f "$applications_dir/$shortcut" ]; then
            rm "$applications_dir/$shortcut"
            print_status "success" "Removed $shortcut from applications menu"
        fi
    done
    
    # Update desktop database
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$applications_dir" 2>/dev/null || true
        print_status "info" "Updated desktop database"
    fi
    
    print_status "success" "Desktop shortcuts uninstalled"
}

show_help() {
    echo -e "${BOLD}${CYAN}Sensor Hub Desktop Shortcuts Manager${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    echo -e "${BOLD}Usage:${NC}"
    echo "  ./desktop_setup.sh [command]"
    echo
    echo -e "${BOLD}Commands:${NC}"
    echo -e "  ${GREEN}install${NC}     Install desktop shortcuts"
    echo -e "  ${RED}uninstall${NC}   Remove desktop shortcuts"
    echo -e "  ${CYAN}help${NC}        Show this help message"
    echo
    echo -e "${BOLD}Created Shortcuts:${NC}"
    echo "  • Sensor Hub (Start) - Starts all services"
    echo "  • Sensor Hub - Stop - Stops all services"
    echo "  • Sensor Hub - Status - Shows current status"
    echo "  • Sensor Hub Dashboard - Opens web interface"
    echo
}

# Main execution
case "${1:-help}" in
    "install")
        install_shortcuts
        ;;
    "uninstall")
        uninstall_shortcuts
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