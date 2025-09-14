"""Base sensor interface for Sensor Hub."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SensorInterface(ABC):
    """Abstract base class for all sensor implementations."""
    
    def __init__(self, sensor_id: str, config: Dict[str, Any]):
        """Initialize sensor with ID and configuration."""
        self.sensor_id = sensor_id
        self.config = config
        self.last_reading = None
        self.error_count = 0
        self.status = 'unknown'
        
    @abstractmethod
    def read(self) -> Dict[str, Any]:
        """Read current sensor values."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if sensor hardware is available and responding."""
        pass
    
    def get_sensor_type(self) -> str:
        """Return the sensor type identifier."""
        return self.__class__.__name__.replace('Sensor', '').lower()
    
    def get_info(self) -> Dict[str, Any]:
        """Get sensor information and current status."""
        return {
            'sensor_id': self.sensor_id,
            'sensor_type': self.get_sensor_type(),
            'config': self.config,
            'status': self.status,
            'error_count': self.error_count,
            'last_reading': self.last_reading
        }
    
    def reset_errors(self) -> None:
        """Reset error count."""
        self.error_count = 0
        
    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle sensor reading errors."""
        self.error_count += 1
        self.status = 'error'
        logger.error(f"Sensor {self.sensor_id} error: {error}")
        
        return {
            'sensor_id': self.sensor_id,
            'error': str(error),
            'status': 'error',
            'timestamp': None,
            'data': {}
        }


class MockSensor(SensorInterface):
    """Mock sensor for testing and development."""
    
    def __init__(self, sensor_id: str, config: Dict[str, Any]):
        super().__init__(sensor_id, config)
        self.status = 'active'
        
    def read(self) -> Dict[str, Any]:
        """Return mock sensor data."""
        import random
        from datetime import datetime, timezone
        
        data = {
            'temperature': round(random.uniform(18.0, 28.0), 2),
            'humidity': round(random.uniform(40.0, 80.0), 2),
            'pressure': round(random.uniform(1000.0, 1030.0), 2)
        }
        
        self.last_reading = {
            'sensor_id': self.sensor_id,
            'timestamp': datetime.now(timezone.utc),
            'data': data,
            'status': 'active'
        }
        
        return self.last_reading
    
    def is_available(self) -> bool:
        """Mock sensor is always available."""
        return True
