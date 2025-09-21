#!/usr/bin/env python3
"""Simple data collector for testing sensor readings."""

import sys
import os
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sensor_hub import create_app
from sensor_hub.models import Sensor, SensorReading, db
from sensor_hub.sensor_registry import SensorRegistry


def collect_once():
    """Collect sensor data once and print results."""
    app = create_app()
    app.config['TESTING'] = True
    
    with app.app_context():
        registry = SensorRegistry()
        sensors = Sensor.query.all()
        
        print(f"Found {len(sensors)} sensors in database")
        success_count = 0
        error_count = 0
        
        for sensor in sensors:
            try:
                # Create sensor instance
                config = {'i2c_address': sensor.i2c_address}
                if sensor.calibration_data:
                    config.update(sensor.calibration_data)
                
                sensor_class = registry.get_sensor_class(sensor.sensor_type)
                if not sensor_class:
                    print(f"❌ {sensor.id}: No sensor class found for type {sensor.sensor_type}")
                    error_count += 1
                    continue
                
                sensor_instance = sensor_class(sensor.id, config)
                data = sensor_instance.read()
                
                if data and 'error' not in data:
                    print(f"✅ {sensor.id}: {data}")
                    
                    # Extract specific fields from different sensor types
                    reading_data = {}
                    temperature = None
                    humidity = None
                    pressure = None
                    light_level = None
                    ir_level = None
                    
                    # Handle different data formats
                    if 'data' in data and isinstance(data['data'], dict):
                        # BME280 format: data contains nested dict
                        sensor_data = data['data']
                        temperature = sensor_data.get('temperature')
                        humidity = sensor_data.get('humidity')
                        pressure = sensor_data.get('pressure')
                        reading_data = sensor_data
                    else:
                        # Direct format for LTR329 and MPU6050
                        temperature = data.get('temperature')
                        humidity = data.get('humidity')
                        pressure = data.get('pressure')
                        light_level = data.get('light_level')
                        ir_level = data.get('ir_level')
                        reading_data = data
                    
                    # Store in database
                    reading = SensorReading(
                        sensor_id=sensor.id,
                        sensor_type=sensor.sensor_type,
                        temperature=temperature,
                        humidity=humidity,
                        pressure=pressure,
                        light_level=light_level,
                        ir_level=ir_level,
                        data=reading_data,  # Store all data in JSON field
                        timestamp=datetime.utcnow()
                    )
                    
                    db.session.add(reading)
                    success_count += 1
                else:
                    print(f"❌ {sensor.id}: Read error - {data}")
                    error_count += 1
                
            except Exception as e:
                print(f"❌ {sensor.id}: Exception - {e}")
                error_count += 1
        
        try:
            db.session.commit()
            print(f"✅ Data saved to database: {success_count} success, {error_count} errors")
        except Exception as e:
            print(f"❌ Database error: {e}")
            db.session.rollback()


if __name__ == '__main__':
    collect_once()