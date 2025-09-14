"""Auto-discovery service for sensors."""

import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from sensor_hub.database import db
from sensor_hub.models import Sensor
from sensor_hub.sensor_registry import sensor_registry

logger = logging.getLogger(__name__)


class SensorDiscoveryService:
    """Service for discovering and managing sensors automatically."""
    
    def __init__(self):
        self.last_discovery = None
    
    def discover_and_register(self, auto_enable: bool = False) -> Dict[str, Any]:
        """
        Discover sensors and register them in the database.
        
        Args:
            auto_enable: Whether to automatically enable discovered sensors
        
        Returns:
            Dictionary with discovery results
        """
        logger.info("Starting sensor discovery...")
        
        # Discover sensors using the registry
        discovered_sensors = sensor_registry.discover_sensors()
        
        results = {
            'discovered_count': len(discovered_sensors),
            'registered_count': 0,
            'updated_count': 0,
            'skipped_count': 0,
            'sensors': []
        }
        
        for sensor_info in discovered_sensors:
            try:
                result = self._register_sensor(sensor_info, auto_enable)
                results['sensors'].append(result)
                
                if result['action'] == 'registered':
                    results['registered_count'] += 1
                elif result['action'] == 'updated':
                    results['updated_count'] += 1
                else:
                    results['skipped_count'] += 1
                    
            except Exception as e:
                logger.error(f"Error registering sensor {sensor_info.get('sensor_id', 'unknown')}: {e}")
                results['sensors'].append({
                    'sensor_id': sensor_info.get('sensor_id', 'unknown'),
                    'action': 'error',
                    'message': str(e)
                })
        
        self.last_discovery = datetime.now(timezone.utc)
        
        logger.info(f"Discovery complete: {results['registered_count']} registered, "
                   f"{results['updated_count']} updated, {results['skipped_count']} skipped")
        
        return results
    
    def _register_sensor(self, sensor_info: Dict[str, Any], auto_enable: bool) -> Dict[str, Any]:
        """Register a single discovered sensor."""
        sensor_id = sensor_info['sensor_id']
        
        # Check if sensor already exists
        existing_sensor = Sensor.query.filter_by(id=sensor_id).first()
        
        if existing_sensor:
            # Update existing sensor if configuration changed
            updated = False
            
            if existing_sensor.name != sensor_info.get('name'):
                existing_sensor.name = sensor_info.get('name')
                updated = True
            
            if existing_sensor.location != sensor_info.get('location'):
                existing_sensor.location = sensor_info.get('location')
                updated = True
            
            if existing_sensor.description != sensor_info.get('description'):
                existing_sensor.description = sensor_info.get('description')
                updated = True
            
            # Update configuration if different
            config = sensor_info.get('config', {})
            if existing_sensor.i2c_address != config.get('i2c_address'):
                existing_sensor.i2c_address = config.get('i2c_address')
                updated = True
            
            if existing_sensor.gpio_pin != config.get('pin'):
                existing_sensor.gpio_pin = config.get('pin')
                updated = True
            
            if existing_sensor.bus_number != config.get('bus_number', 1):
                existing_sensor.bus_number = config.get('bus_number', 1)
                updated = True
            
            if updated:
                existing_sensor.updated_at = datetime.now(timezone.utc)
                db.session.commit()
                return {
                    'sensor_id': sensor_id,
                    'action': 'updated',
                    'message': 'Sensor configuration updated'
                }
            else:
                return {
                    'sensor_id': sensor_id,
                    'action': 'skipped',
                    'message': 'Sensor already exists with same configuration'
                }
        
        else:
            # Create new sensor
            config = sensor_info.get('config', {})
            
            # Prepare multiplexer config if present
            mux_config = {}
            if 'mux_address' in config:
                mux_config['mux_address'] = config['mux_address']
            if 'mux_channel' in config:
                mux_config['mux_channel'] = config['mux_channel']
            
            new_sensor = Sensor(
                id=sensor_id,
                name=sensor_info.get('name', sensor_id),
                sensor_type=sensor_info['sensor_type'],
                description=sensor_info.get('description'),
                location=sensor_info.get('location'),
                i2c_address=config.get('i2c_address'),
                gpio_pin=config.get('pin'),
                bus_number=config.get('bus_number', 1),
                enabled=auto_enable,
                status='unknown',
                calibration_data=mux_config if mux_config else None
            )
            
            db.session.add(new_sensor)
            db.session.commit()
            
            return {
                'sensor_id': sensor_id,
                'action': 'registered',
                'message': f'New sensor registered{"and enabled" if auto_enable else ""}'
            }
    
    def test_sensor_connectivity(self, sensor_id: str) -> Dict[str, Any]:
        """Test if a registered sensor is responsive."""
        sensor = Sensor.query.filter_by(id=sensor_id).first()
        if not sensor:
            return {
                'sensor_id': sensor_id,
                'available': False,
                'error': 'Sensor not found in database'
            }
        
        # Create sensor instance and test connectivity
        config = {
            'i2c_address': sensor.i2c_address,
            'pin': sensor.gpio_pin,
            'bus_number': sensor.bus_number or 1,
        }
        
        # Add multiplexer config if available (stored in calibration_data for now)
        if sensor.calibration_data and isinstance(sensor.calibration_data, dict):
            if 'mux_address' in sensor.calibration_data:
                config['mux_address'] = sensor.calibration_data['mux_address']
            if 'mux_channel' in sensor.calibration_data:
                config['mux_channel'] = sensor.calibration_data['mux_channel']
        
        sensor_instance = sensor_registry.create_sensor(
            sensor.sensor_type, 
            sensor_id, 
            config
        )
        
        if not sensor_instance:
            return {
                'sensor_id': sensor_id,
                'available': False,
                'error': f'Failed to create {sensor.sensor_type} sensor instance'
            }
        
        try:
            is_available = sensor_instance.is_available()
            
            # Update sensor status
            if is_available:
                sensor.status = 'active'
                sensor.error_count = 0
            else:
                sensor.status = 'unavailable'
                sensor.error_count = getattr(sensor, 'error_count', 0) + 1
            
            db.session.commit()
            
            return {
                'sensor_id': sensor_id,
                'available': is_available,
                'status': sensor.status,
                'sensor_type': sensor.sensor_type
            }
            
        except Exception as e:
            sensor.status = 'error'
            sensor.error_count = getattr(sensor, 'error_count', 0) + 1
            db.session.commit()
            
            return {
                'sensor_id': sensor_id,
                'available': False,
                'error': str(e)
            }
    
    def test_all_sensors(self) -> Dict[str, Any]:
        """Test connectivity for all registered sensors."""
        sensors = Sensor.query.all()
        
        results = {
            'total_sensors': len(sensors),
            'available_sensors': 0,
            'unavailable_sensors': 0,
            'error_sensors': 0,
            'sensor_status': []
        }
        
        for sensor in sensors:
            status = self.test_sensor_connectivity(sensor.id)
            results['sensor_status'].append(status)
            
            if status.get('available'):
                results['available_sensors'] += 1
            elif 'error' in status:
                results['error_sensors'] += 1
            else:
                results['unavailable_sensors'] += 1
        
        return results
    
    def get_discovery_status(self) -> Dict[str, Any]:
        """Get current discovery status and statistics."""
        total_sensors = Sensor.query.count()
        active_sensors = Sensor.query.filter_by(status='active').count()
        error_sensors = Sensor.query.filter_by(status='error').count()
        unavailable_sensors = Sensor.query.filter_by(status='unavailable').count()
        enabled_sensors = Sensor.query.filter_by(enabled=True).count()
        
        return {
            'last_discovery': self.last_discovery.isoformat() if self.last_discovery else None,
            'total_sensors': total_sensors,
            'active_sensors': active_sensors,
            'error_sensors': error_sensors,
            'unavailable_sensors': unavailable_sensors,
            'enabled_sensors': enabled_sensors,
            'available_sensor_types': sensor_registry.get_available_types()
        }


# Global discovery service instance
discovery_service = SensorDiscoveryService()
