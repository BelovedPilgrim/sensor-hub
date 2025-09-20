# Sensor Hub Management Guide

This guide covers multiple ways to easily start, stop, and manage your Sensor Hub application.

## 🚀 Quick Start Methods

### Method 1: Simple Management Script (Recommended)

The easiest way to control your Sensor Hub:

```bash
# Start everything
./sensor_hub.sh start

# Check status
./sensor_hub.sh status

# View logs
./sensor_hub.sh logs

# Stop everything
./sensor_hub.sh stop

# Restart everything
./sensor_hub.sh restart
```

**Features:**
- ✅ Colored output with status indicators
- ✅ Process management with graceful shutdown
- ✅ Integrated logging with the new logging framework
- ✅ Real-time status monitoring
- ✅ Automatic error detection and recovery

### Method 2: Systemd Services (For Automatic Startup)

Install systemd services for automatic startup on boot:

```bash
# Install user services (recommended)
./systemd_setup.sh install

# Enable automatic startup
systemctl --user enable sensor-hub-scheduler sensor-hub-webapp

# Start services
systemctl --user start sensor-hub-scheduler sensor-hub-webapp

# Check status
systemctl --user status sensor-hub-scheduler sensor-hub-webapp

# Enable lingering (survive logout)
sudo loginctl enable-linger $USER
```

**For system-wide installation:**
```bash
# Install as root for system-wide services
sudo ./systemd_setup.sh install
sudo systemctl enable sensor-hub-scheduler sensor-hub-webapp
sudo systemctl start sensor-hub-scheduler sensor-hub-webapp
```

### Method 3: Desktop Shortcuts (GUI Access)

Install desktop shortcuts for point-and-click management:

```bash
# Install shortcuts
./desktop_setup.sh install
```

This creates:
- **Sensor Hub** - Start services
- **Sensor Hub - Stop** - Stop services  
- **Sensor Hub - Status** - Check status
- **Sensor Hub Dashboard** - Open web interface

Shortcuts appear in:
- Desktop folder
- Applications menu (System category)

### Method 4: Manual Commands (Advanced)

Direct Poetry/Flask commands for development:

```bash
# Start scheduler
poetry run flask --app src.sensor_hub.app start-scheduler

# Start web app (separate terminal)
poetry run flask --app src.sensor_hub.app run --host=0.0.0.0 --port=5001
```

## 📊 Monitoring and Logs

### Viewing Logs

**Using the management script:**
```bash
./sensor_hub.sh logs          # All recent logs
./sensor_hub.sh status        # Status with recent activity
```

**Direct log files:**
```bash
tail -f logs/sensor_hub.log   # Main application logs (structured)
tail -f logs/scheduler.log    # Scheduler console output
tail -f logs/webapp.log       # Web app console output
```

**Systemd logs (if using services):**
```bash
# User services
journalctl --user -fu sensor-hub-scheduler
journalctl --user -fu sensor-hub-webapp

# System services
sudo journalctl -fu sensor-hub-scheduler
sudo journalctl -fu sensor-hub-webapp
```

### Status Monitoring

The new management script provides comprehensive status information:

```bash
./sensor_hub.sh status
```

Shows:
- ✅ Service status (running/stopped) with PIDs
- 🌐 Web interface URL if running
- 📄 Recent log activity from all services
- 🔴/🟢 Visual indicators for quick status assessment

## 🔧 Configuration

### Log Levels

Edit `src/sensor_hub/config.py` to adjust logging:

```python
# Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = "INFO"

# Enable/disable file logging
LOG_TO_FILE = True

# Log file location
LOG_FILE = "logs/sensor_hub.log"
```

### Service Ports

Default web interface port is 5001. To change:

```bash
# Temporary change
poetry run flask --app src.sensor_hub.app run --port=8080

# Or edit the scripts/services
```

## 🛠️ Troubleshooting

### Common Issues

**Services won't start:**
```bash
./sensor_hub.sh logs         # Check for errors
./sensor_hub.sh stop         # Ensure clean stop
./sensor_hub.sh start        # Try starting again
```

**Port already in use:**
```bash
# Find what's using port 5001
sudo netstat -tlnp | grep :5001

# Kill the process if needed
sudo pkill -f "flask.*run"
```

**Permission issues:**
```bash
# Make scripts executable
chmod +x sensor_hub.sh systemd_setup.sh desktop_setup.sh

# Fix log directory permissions
mkdir -p logs
chmod 755 logs
```

**Systemd service issues:**
```bash
# Check service status
systemctl --user status sensor-hub-scheduler

# View detailed logs
journalctl --user -xe -u sensor-hub-scheduler

# Reload systemd if you edit service files
systemctl --user daemon-reload
```

### Getting Help

Run any script with `help` to see usage information:

```bash
./sensor_hub.sh help
./systemd_setup.sh help
./desktop_setup.sh help
```

## 📁 File Structure

```
sensor_hub/
├── sensor_hub.sh              # Main management script
├── systemd_setup.sh           # Systemd service installer
├── desktop_setup.sh           # Desktop shortcuts installer
├── systemd/                   # Service definition files
│   ├── sensor-hub-scheduler.service
│   └── sensor-hub-webapp.service
├── desktop/                   # Desktop shortcut files
│   ├── sensor-hub-start.desktop
│   ├── sensor-hub-stop.desktop
│   ├── sensor-hub-status.desktop
│   └── sensor-hub-dashboard.desktop
├── logs/                      # Log files
│   ├── sensor_hub.log         # Main structured logs
│   ├── scheduler.log          # Scheduler console output
│   └── webapp.log             # Web app console output
└── src/sensor_hub/
    ├── logging_config.py      # Logging framework
    └── ...                    # Application code
```

## 🎯 Best Practices

1. **Development:** Use `./sensor_hub.sh` commands for daily development
2. **Production:** Install systemd services for reliable operation
3. **Monitoring:** Check `./sensor_hub.sh status` regularly
4. **Logs:** Use `./sensor_hub.sh logs` to troubleshoot issues
5. **Updates:** Stop services before updating code, then restart

The new management system makes it incredibly easy to control your Sensor Hub - choose the method that works best for your needs!