"""Command Line Interface for Sensor Hub."""

import click
from flask.cli import with_appcontext

from sensor_hub.database import create_tables
from sensor_hub.discovery_service import discovery_service


@click.command()
@with_appcontext
def init_db():
    """Initialize the database tables."""
    try:
        create_tables()
        click.echo("Database initialized successfully.")
    except Exception as e:
        click.echo(f"Error initializing database: {e}", err=True)


@click.command()
@with_appcontext
def discover_sensors():
    """Discover and register sensors automatically."""
    click.echo("Discovering sensors...")
    
    results = discovery_service.discover_and_register(auto_enable=False)
    
    click.echo("\nDiscovery Results:")
    click.echo(f"  Sensors discovered: {results['discovered_count']}")
    click.echo(f"  Sensors registered: {results['registered_count']}")
    click.echo(f"  Sensors updated: {results['updated_count']}")
    click.echo(f"  Sensors skipped: {results['skipped_count']}")
    
    if results['sensors']:
        click.echo("\nDetailed Results:")
        for sensor in results['sensors']:
            status = sensor['action'].upper()
            message = sensor.get('message', '')
            click.echo(f"  [{status}] {sensor['sensor_id']}: {message}")


@click.command()
@with_appcontext
def test_sensors():
    """Test connectivity for all registered sensors."""
    click.echo("Testing sensor connectivity...")
    
    results = discovery_service.test_all_sensors()
    
    click.echo("\nConnectivity Test Results:")
    click.echo(f"  Total sensors: {results['total_sensors']}")
    click.echo(f"  Available: {results['available_sensors']}")
    click.echo(f"  Unavailable: {results['unavailable_sensors']}")
    click.echo(f"  Errors: {results['error_sensors']}")


@click.command()
@with_appcontext
def status():
    """Show discovery service status."""
    status_info = discovery_service.get_discovery_status()
    
    click.echo("Sensor Hub Status:")
    last_discovery = status_info['last_discovery'] or 'Never'
    click.echo(f"  Last discovery: {last_discovery}")
    click.echo(f"  Total sensors: {status_info['total_sensors']}")
    click.echo(f"  Active sensors: {status_info['active_sensors']}")


@click.command()
@with_appcontext
def start_scheduler():
    """Start the sensor reading scheduler."""
    click.echo("Starting sensor scheduler...")
    
    from datetime import datetime, timezone
    import time
    from sensor_hub.models import Sensor, SensorReading
    from sensor_hub.sensor_registry import sensor_registry
    from sensor_hub import db
    
    try:
        # Get all enabled sensors
        enabled_sensors = Sensor.query.filter_by(enabled=True).all()
        
        if not enabled_sensors:
            click.echo("No enabled sensors found. Use 'discover-sensors' first.")
            return
            
        click.echo(f"Found {len(enabled_sensors)} enabled sensors")
        
        # Create sensor instances
        sensor_instances = {}
        for sensor_config in enabled_sensors:
            try:
                # Build configuration dict
                config = {
                    'i2c_address': sensor_config.i2c_address,
                    'bus_number': sensor_config.bus_number or 1,
                    'poll_interval': sensor_config.poll_interval or 30
                }
                
                # Add multiplexer configuration if available
                if sensor_config.calibration_data:
                    # calibration_data is already parsed as dict by SQLAlchemy JSON type
                    cal_data = sensor_config.calibration_data
                    if 'mux_address' in cal_data:
                        config['mux_address'] = cal_data['mux_address']
                    if 'mux_channel' in cal_data:
                        config['mux_channel'] = cal_data['mux_channel']
                    if 'mock_mode' in cal_data:
                        config['mock_mode'] = cal_data['mock_mode']
                
                sensor_instance = sensor_registry.create_sensor(
                    sensor_config.sensor_type,  # sensor_type first
                    sensor_config.id,           # sensor_id second
                    config                      # proper config dict
                )
                if sensor_instance and sensor_instance.is_available():
                    sensor_instances[sensor_config.id] = sensor_instance
                    click.echo(f"✓ {sensor_config.id} "
                               f"({sensor_config.sensor_type}) ready")
                else:
                    click.echo(f"✗ {sensor_config.id} not available")
            except Exception as e:
                click.echo(f"✗ {sensor_config.id} error: {e}")
        
        if not sensor_instances:
            click.echo("No sensors are available for data collection")
            return
            
        click.echo(f"Starting data collection for "
                   f"{len(sensor_instances)} sensors...")
        click.echo("Press Ctrl+C to stop")
        
        # Data collection loop
        while True:
            try:
                for sensor_id, sensor_instance in sensor_instances.items():
                    try:
                        # Read sensor data
                        reading_data = sensor_instance.read()
                        
                        if reading_data:
                            # Handle different sensor data formats
                            if 'data' in reading_data:
                                # BME280 format: {'data': {...}, 'status': '...'}
                                data_dict = reading_data['data']
                            else:
                                # LTR-329 format: direct data
                                data_dict = reading_data
                            
                            # Create database entry
                            reading = SensorReading(
                                sensor_id=sensor_id,
                                sensor_type=sensor_instance.get_sensor_type(),
                                timestamp=datetime.now(timezone.utc),
                                temperature=data_dict.get('temperature'),
                                humidity=data_dict.get('humidity'),
                                pressure=data_dict.get('pressure'),
                                light_level=data_dict.get('light_level'),
                                ir_level=data_dict.get('ir_level'),
                                data=data_dict
                            )
                            
                            db.session.add(reading)
                            
                            # Update sensor status
                            sensor_config = Sensor.query.get(sensor_id)
                            if sensor_config:
                                sensor_config.last_reading_at = (
                                    datetime.now(timezone.utc))
                                sensor_config.status = 'active'
                                sensor_config.error_count = 0
                            
                            temp = data_dict.get('temperature', 'N/A')
                            hum = data_dict.get('humidity', 'N/A')
                            press = data_dict.get('pressure', 'N/A')
                            light = data_dict.get('light_level')
                            ir = data_dict.get('ir_level')
                            
                            # Format output based on sensor type
                            if light is not None and ir is not None:
                                # LTR-329: display raw channel values
                                click.echo(f"📊 {sensor_id}: "
                                           f"CH0={light:.0f}, IR={ir:.0f}")
                            elif light is not None:
                                click.echo(f"📊 {sensor_id}: "
                                           f"Light={light:.2f} lux")
                            else:
                                click.echo(f"📊 {sensor_id}: T={temp}°C, "
                                           f"H={hum}%, P={press}hPa")
                        
                    except Exception as e:
                        click.echo(f"⚠️  Error reading {sensor_id}: {e}")
                        
                        # Update error count
                        sensor_config = Sensor.query.get(sensor_id)
                        if sensor_config:
                            error_count = (sensor_config.error_count or 0) + 1
                            sensor_config.error_count = error_count
                            sensor_config.status = 'error'
                
                # Commit all readings
                db.session.commit()
                
                # Wait before next reading (30 seconds)
                time.sleep(30)
                
            except KeyboardInterrupt:
                click.echo("\n🛑 Scheduler stopped by user")
                break
            except Exception as e:
                click.echo(f"⚠️  Scheduler error: {e}")
                time.sleep(5)  # Short delay before retry
                
    except Exception as e:
        click.echo(f"❌ Failed to start scheduler: {e}")
        return


# Register CLI commands
init_db_command = init_db
discover_sensors_command = discover_sensors
test_sensors_command = test_sensors
status_command = status
start_scheduler_command = start_scheduler
