# Sensor Hub

A modern web application for reading and monitoring sensors connected to a Raspberry Pi 5.

## Features

- 🌡️ Real-time sensor data monitoring (temperature, humidity, pressure)
- 📊 Interactive charts with timezone and unit conversion (metric/imperial)
- 🕒 Auto-refresh dashboard with configurable intervals (1-600 seconds)
- 🌍 Multi-timezone support (Local, UTC, and major world timezones)
- 📱 Responsive design for mobile/desktop
- 🔄 Cross-page preference synchronization
- 📈 Dual-axis charts (temperature/humidity vs pressure)
- 🗃️ SQLite database for historical data storage
- 🔌 RESTful API for data access
- ⚡ Real-time data collection via background scheduler

## Hardware Requirements

- Raspberry Pi 5 with Raspberry Pi OS (latest)
- Supported sensors:
  - BME280 (temperature, humidity, pressure)
  - VCNL4020 (proximity, light level)
  - Custom sensors via GPIO

## Quick Start

### Prerequisites

- Python 3.11+
- Poetry for dependency management
- I2C enabled on Raspberry Pi (`sudo raspi-config` → Interface Options → I2C → Enable)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/BelovedPilgrim/sensor_hub.git
cd sensor_hub
```

2. Install dependencies:
```bash
poetry install
```

3. Set up environment variables (optional):
```bash
cp .env.example .env
# Edit .env with your configuration if needed
```

4. Initialize the database:
```bash
# Set Flask app
export FLASK_APP=src.sensor_hub.app

# Initialize database tables
poetry run flask init-db
```

### Running the Application

The Sensor Hub requires **two components** to run properly:

#### 1. Start the Sensor Data Scheduler (Required for data collection)

The scheduler collects data from sensors every 30 seconds:

```bash
# In one terminal - Start data collection scheduler
export FLASK_APP=src.sensor_hub.app
poetry run flask start-scheduler
```

Or run in background:
```bash
# Run scheduler in background with nohup
nohup poetry run env FLASK_APP=src.sensor_hub.app flask start-scheduler > scheduler.log 2>&1 &
```

#### 2. Start the Web Application

```bash
# In another terminal - Start web server
poetry run python src/sensor_hub/app.py
```

The application will be available at:
- **Local**: http://127.0.0.1:5000
- **Network**: http://YOUR_PI_IP:5000

### First-Time Setup

1. **Discover sensors** (if not already done):
```bash
export FLASK_APP=src.sensor_hub.app
poetry run flask discover-sensors
```

2. **Test sensor connectivity**:
```bash
poetry run flask test-sensors
```

3. **Check scheduler status**:
```bash
poetry run flask status
```

### Available Flask Commands

```bash
export FLASK_APP=src.sensor_hub.app

# Database commands
poetry run flask init-db           # Initialize database tables
poetry run flask db upgrade       # Run database migrations

# Sensor commands
poetry run flask discover-sensors  # Auto-discover connected sensors
poetry run flask test-sensors     # Test sensor connectivity
poetry run flask start-scheduler  # Start data collection scheduler
poetry run flask status           # Show system status

# Development
poetry run flask run              # Start development server
poetry run flask shell           # Open Flask shell
```

### Monitoring Data Collection

Check if data is being collected properly:

```bash
# Monitor scheduler log (if running in background)
tail -f scheduler.log

# Check database timestamps vs current time
poetry run python -c "
import sys; sys.path.append('src')
from flask import Flask
from sensor_hub import create_app
from sensor_hub.models import SensorReading
from datetime import datetime, timezone

app = create_app()
with app.app_context():
    latest = SensorReading.query.order_by(SensorReading.timestamp.desc()).first()
    now = datetime.now(timezone.utc)
    if latest:
        ts = latest.timestamp.replace(tzinfo=timezone.utc) if latest.timestamp.tzinfo is None else latest.timestamp
        diff = now - ts
        print(f'Latest reading: {ts.strftime(\"%H:%M:%S\")} ({diff.total_seconds():.0f}s ago)')
        print(f'Status: {\"🟢 Current\" if diff.total_seconds() < 60 else \"🔴 Stale\"}')
    else:
        print('No data found')
"
```

## Development

### Project Structure

```
sensor_hub/
├── pyproject.toml         # Project configuration and dependencies
├── src/
│   └── sensor_hub/
│       ├── app.py         # Flask application factory
│       ├── config.py      # Configuration settings
│       ├── models.py      # Database models
│       ├── run.py         # Application runner
│       ├── database/
│       │   └── models.py  # Database model definitions
│       ├── sensors/       # Sensor-specific modules
│       │   ├── base.py    # Base sensor interface
│       │   ├── bme280.py  # BME280 sensor implementation
│       │   └── vcnl4020.py # VCNL4020 sensor implementation
│       ├── static/        # CSS, JavaScript files
│       │   ├── css/
│       │   └── js/
│       ├── templates/     # HTML templates
│       └── utils/         # Utility modules
│           ├── export.py  # Data export functionality
│           ├── generate_secret.py # Secret key generation
│           ├── logging_config.py  # Logging configuration
│           └── timezone_util.py   # Timezone utilities
├── tests/                 # Test files
└── README.md
```

### Adding Custom Sensors

1. Create a new sensor module in `src/sensor_hub/sensors/`
2. Inherit from `BaseSensor` class
3. Implement required methods:
   - `read()`: Return sensor data
   - `get_sensor_type()`: Return sensor type string
   - `is_available()`: Check if sensor is connected

Example:
```python
from .base import BaseSensor

class CustomSensor(BaseSensor):
    def __init__(self, address=0x48):
        super().__init__(address)
        
    def read(self):
        # Implement sensor reading logic
        return {"value": 42}
        
    def get_sensor_type(self):
        return "custom"
        
    def is_available(self):
        # Check sensor connectivity
        return True
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src/sensor_hub --cov-report=html

# Run specific test file
poetry run pytest tests/test_sensors.py -v
```

### Development Server

For development with auto-reload:

```bash
export FLASK_APP=src.sensor_hub.app
export FLASK_ENV=development
poetry run flask run --host=0.0.0.0 --port=5000 --debug
```

## Production Deployment

### Using systemd (Recommended)

1. Create scheduler service file:
```bash
sudo nano /etc/systemd/system/sensor-scheduler.service
```

```ini
[Unit]
Description=Sensor Hub Data Scheduler
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/sensor_hub
Environment=FLASK_APP=src.sensor_hub.app
ExecStart=/home/pi/.local/bin/poetry run flask start-scheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Create web app service file:
```bash
sudo nano /etc/systemd/system/sensor-webapp.service
```

```ini
[Unit]
Description=Sensor Hub Web Application
After=network.target sensor-scheduler.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/sensor_hub
ExecStart=/home/pi/.local/bin/poetry run python src/sensor_hub/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sensor-scheduler.service
sudo systemctl enable sensor-webapp.service
sudo systemctl start sensor-scheduler.service
sudo systemctl start sensor-webapp.service
```

4. Check status:
```bash
sudo systemctl status sensor-scheduler.service
sudo systemctl status sensor-webapp.service
```

### Using Docker (Alternative)

```bash
# Build image
docker build -t sensor-hub .

# Run container
docker run -d 
  --name sensor-hub 
  --privileged 
  -p 5000:5000 
  -v /dev:/dev 
  sensor-hub
```

## Troubleshooting

### Common Issues

**1. No sensor data being collected**
- Check if scheduler is running: `poetry run flask status`
- Verify I2C is enabled: `sudo i2cdetect -y 1`
- Restart scheduler: `poetry run flask start-scheduler`

**2. Permission denied errors**
- Add user to i2c group: `sudo usermod -a -G i2c $USER`
- Logout and login again
- Check device permissions: `ls -la /dev/i2c-*`

**3. Database issues**
- Reinitialize database: `poetry run flask init-db`
- Check database file permissions
- Verify SQLite installation

**4. Web app not accessible from network**
- Check firewall settings: `sudo ufw status`
- Verify app is binding to 0.0.0.0, not 127.0.0.1
- Check network configuration

**5. Charts not updating or unit conversion not working**
- Check browser console for JavaScript errors
- Clear browser cache and cookies
- Verify sensor data is being collected (see monitoring section above)

### Logs

```bash
# Application logs (if using systemd)
sudo journalctl -u sensor-webapp.service -f

# Scheduler logs (if using systemd)
sudo journalctl -u sensor-scheduler.service -f

# Manual log files (if running in background)
tail -f scheduler.log
```

## API Reference

### Endpoints

- `GET /` - Main dashboard
- `GET /sensors/{sensor_id}` - Sensor detail page
- `GET /api/sensors` - List all sensors (JSON)
- `GET /api/sensors/{sensor_id}/data` - Get sensor readings (JSON)
- `GET /data/{sensor_id}` - Sensor data with timezone/unit conversion

### Query Parameters

- `timezone` - Timezone for timestamp conversion (e.g., "America/New_York")
- `units` - Unit system: "metric" or "imperial"
- `limit` - Number of recent readings to return (default: 100)

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `poetry run pytest`
5. Commit changes: `git commit -am 'Add feature'`
6. Push to branch: `git push origin feature-name`
7. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 Create an issue on GitHub
- 📖 Check the troubleshooting section above
- 🔧 Review the monitoring commands for system health

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=sensor_hub

# Run specific test categories
poetry run pytest -m unit
poetry run pytest -m integration
```

### Code Quality

```bash
# Format code
poetry run black src/ tests/

# Sort imports
poetry run isort src/ tests/

# Lint code
poetry run flake8 src/ tests/

# Type checking
poetry run mypy src/
```

## Deployment

### Production with systemd

1. Create systemd service file
2. Configure nginx reverse proxy
3. Set up SSL certificates
4. Configure monitoring and backups

See [docs/deployment.md](docs/deployment.md) for detailed instructions.

### Docker

```bash
# Build image
docker build -t sensor-hub .

# Run container
docker run -d --name sensor-hub -p 5000:5000 sensor-hub
```

## API Documentation

The application provides a RESTful API for accessing sensor data:

- `GET /api/sensors` - List all sensors
- `GET /api/sensors/<id>/data` - Get sensor data
- `GET /api/readings` - Get historical readings
- `POST /api/sensors/<id>/calibrate` - Calibrate sensor

See [docs/api.md](docs/api.md) for complete API documentation.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run quality checks
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Documentation: [docs/](docs/)
- Issues: [GitHub Issues](https://github.com/BelovedPilgrim/sensor_hub/issues)
- Discussions: [GitHub Discussions](https://github.com/BelovedPilgrim/sensor_hub/discussions)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release notes and version history.
