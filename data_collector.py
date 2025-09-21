#!/usr/bin/env python3
"""Data collection service for storing periodic sensor readings."""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from sensor_hub import create_app
from sensor_hub.models import Sensor, SensorReading, db
from sensor_hub.sensor_registry import SensorRegistry

logger = logging.getLogger(__name__)


class DataCollectionService:
    """Service for periodically collecting and storing sensor data."""
    
    def __init__(self, interval_seconds: int = 60):
        """Initialize data collection service.
        
        Args:
            interval_seconds: How often to collect data (default: 60 seconds)
        """
        self.interval = interval_seconds
        self.registry = SensorRegistry()
        self.running = False
    
    def collect_sensor_data(self) -> Dict[str, Any]:
        """Collect data from all sensors and store in database."""
        sensors = Sensor.query.all()
        results = {
            'success_count': 0,
            'error_count': 0,
            'sensors': []
        }
        
        for sensor in sensors:
            try:
                # Build sensor configuration
                config = {'i2c_address': sensor.i2c_address}
                if sensor.calibration_data:
                    config.update(sensor.calibration_data)
                
                # Create sensor instance and take reading
                sensor_class = self.registry.get_sensor_class(sensor.sensor_type)
                if not sensor_class:
                    logger.warning(f"No sensor class found for {sensor.sensor_type}")
                    continue
                
                sensor_instance = sensor_class(sensor.id, config)
                reading_data = sensor_instance.read()
                
                if reading_data and 'error' not in reading_data:
                    # Store reading in database
                    reading = SensorReading(
                        sensor_id=sensor.id,
                        sensor_type=sensor.sensor_type,
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    # Map sensor-specific data to database fields
                    if sensor.sensor_type == 'bme280' and 'data' in reading_data:
                        data = reading_data['data']
                        reading.temperature = data.get('temperature')
                        reading.humidity = data.get('humidity')
                        reading.pressure = data.get('pressure')
                        reading.data = data
                    
                    elif sensor.sensor_type == 'ltr329':
                        reading.light_level = reading_data.get('light_level')
                        reading.ir_level = reading_data.get('ir_level')
                        reading.data = reading_data
                    
                    elif sensor.sensor_type == 'mpu6050':
                        reading.temperature = reading_data.get('temperature')
                        reading.data = {
                            'accel_x': reading_data.get('accel_x'),
                            'accel_y': reading_data.get('accel_y'),
                            'accel_z': reading_data.get('accel_z'),
                            'gyro_x': reading_data.get('gyro_x'),
                            'gyro_y': reading_data.get('gyro_y'),
                            'gyro_z': reading_data.get('gyro_z'),
                            'temperature': reading_data.get('temperature')
                        }
                    
                    else:
                        # Generic handling for other sensor types
                        reading.data = reading_data
                    
                    reading.status = 'active'
                    db.session.add(reading)
                    
                    results['success_count'] += 1
                    results['sensors'].append({
                        'sensor_id': sensor.id,
                        'status': 'success',
                        'reading': reading_data
                    })
                    
                    logger.debug(f"Stored reading for {sensor.id}")
                
                else:
                    # Store error reading
                    error_msg = reading_data.get('error', 'Unknown error') if reading_data else 'No data'
                    reading = SensorReading(
                        sensor_id=sensor.id,
                        sensor_type=sensor.sensor_type,
                        timestamp=datetime.now(timezone.utc),
                        status='error',
                        error_message=error_msg
                    )
                    db.session.add(reading)
                    
                    results['error_count'] += 1
                    results['sensors'].append({
                        'sensor_id': sensor.id,
                        'status': 'error',
                        'error': error_msg
                    })
                    
                    logger.warning(f"Error reading sensor {sensor.id}: {error_msg}")
            
            except Exception as e:
                logger.error(f"Exception collecting data from {sensor.id}: {e}")
                results['error_count'] += 1
                results['sensors'].append({
                    'sensor_id': sensor.id,
                    'status': 'exception',
                    'error': str(e)
                })
        
        # Commit all readings at once
        try:
            db.session.commit()
            logger.info(f"Data collection complete: {results['success_count']} success, {results['error_count']} errors")
        except Exception as e:
            logger.error(f"Database commit failed: {e}")
            db.session.rollback()
            raise
        
        return results
    
    def run_continuous(self):
        """Run continuous data collection."""
        logger.info(f"Starting data collection service (interval: {self.interval}s)")
        self.running = True
        
        while self.running:
            try:
                self.collect_sensor_data()
                time.sleep(self.interval)
            except KeyboardInterrupt:
                logger.info("Data collection stopped by user")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Data collection error: {e}")
                time.sleep(5)  # Short delay before retry
    
    def stop(self):
        """Stop the data collection service."""
        self.running = False


def main():
    """Main entry point for data collection service."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sensor Hub Data Collection Service')
    parser.add_argument('--interval', type=int, default=60,
                       help='Collection interval in seconds (default: 60)')
    parser.add_argument('--once', action='store_true',
                       help='Collect data once and exit')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        service = DataCollectionService(interval_seconds=args.interval)
        
        if args.once:
            print("Collecting sensor data once...")
            results = service.collect_sensor_data()
            print(f"Results: {results['success_count']} successful, {results['error_count']} errors")
            
            for sensor_result in results['sensors']:
                status_emoji = "✅" if sensor_result['status'] == 'success' else "❌"
                print(f"  {status_emoji} {sensor_result['sensor_id']}: {sensor_result['status']}")
        else:
            try:
                service.run_continuous()
            except KeyboardInterrupt:
                print("\nData collection service stopped.")


if __name__ == '__main__':
    main()