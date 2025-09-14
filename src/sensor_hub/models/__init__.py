"""Database models for Sensor Hub."""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sensor_hub import db


class SensorReading(db.Model):
    """Model for storing sensor readings."""
    
    __tablename__ = 'sensor_readings'
    
    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.String(50), nullable=False, index=True)
    sensor_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(
        db.DateTime, 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    
    # Environmental data
    temperature = db.Column(db.Float, nullable=True)
    humidity = db.Column(db.Float, nullable=True)
    pressure = db.Column(db.Float, nullable=True)
    
    # Light and proximity data
    light_level = db.Column(db.Float, nullable=True)
    ir_level = db.Column(db.Float, nullable=True)
    proximity = db.Column(db.Integer, nullable=True)
    
    # Generic JSON field for additional sensor data
    data = db.Column(db.JSON, nullable=True)
    
    # Status fields
    status = db.Column(db.String(20), default='active')
    error_message = db.Column(db.Text, nullable=True)
    
    def __repr__(self) -> str:
        return f'<SensorReading {self.sensor_id}:{self.timestamp}>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert reading to dictionary."""
        return {
            'id': self.id,
            'sensor_id': self.sensor_id,
            'sensor_type': self.sensor_type,
            'timestamp': self.timestamp.isoformat(),
            'temperature': self.temperature,
            'humidity': self.humidity,
            'pressure': self.pressure,
            'light_level': self.light_level,
            'ir_level': self.ir_level,
            'proximity': self.proximity,
            'data': self.data,
            'status': self.status,
            'error_message': self.error_message
        }


class Sensor(db.Model):
    """Model for sensor configuration."""
    
    __tablename__ = 'sensors'
    
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sensor_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Hardware configuration
    i2c_address = db.Column(db.Integer, nullable=True)
    gpio_pin = db.Column(db.Integer, nullable=True)
    bus_number = db.Column(db.Integer, default=1)
    
    # Settings
    poll_interval = db.Column(db.Integer, default=30)  # seconds
    enabled = db.Column(db.Boolean, default=True)
    calibration_data = db.Column(db.JSON, nullable=True)
    
    # Metadata
    location = db.Column(db.String(100), nullable=True)
    created_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime, 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Status tracking
    last_reading_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='unknown')
    error_count = db.Column(db.Integer, default=0)
    
    def __repr__(self) -> str:
        return f'<Sensor {self.id}:{self.name}>'
    
    @property
    def sensor_id(self):
        """Backward compatibility property."""
        return self.id
    
    @property
    def last_reading_time(self):
        """Backward compatibility property."""
        return self.last_reading_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sensor to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'sensor_type': self.sensor_type,
            'description': self.description,
            'i2c_address': self.i2c_address,
            'gpio_pin': self.gpio_pin,
            'bus_number': self.bus_number,
            'poll_interval': self.poll_interval,
            'enabled': self.enabled,
            'calibration_data': self.calibration_data,
            'location': self.location,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_reading_at': self.last_reading_at.isoformat() if self.last_reading_at else None,
            'last_reading_time': (
                self.last_reading_time.isoformat()
                if self.last_reading_time else None
            ),
            'status': self.status,
            'error_count': self.error_count
        }
    
    def get_latest_reading(self) -> Optional['SensorReading']:
        """Get the most recent reading for this sensor."""
        return SensorReading.query.filter_by(
            sensor_id=self.id
        ).order_by(
            SensorReading.timestamp.desc()
        ).first()


class SystemStatus(db.Model):
    """Model for tracking system status and health."""
    
    __tablename__ = 'system_status'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(
        db.DateTime, 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )
    
    # System metrics
    cpu_usage = db.Column(db.Float, nullable=True)
    memory_usage = db.Column(db.Float, nullable=True)
    disk_usage = db.Column(db.Float, nullable=True)
    temperature = db.Column(db.Float, nullable=True)  # System temperature
    
    # Network status
    network_status = db.Column(db.String(20), default='unknown')
    
    # Application status
    active_sensors = db.Column(db.Integer, default=0)
    failed_sensors = db.Column(db.Integer, default=0)
    total_readings = db.Column(db.Integer, default=0)
    
    def __repr__(self) -> str:
        return f'<SystemStatus {self.timestamp}>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert system status to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage,
            'temperature': self.temperature,
            'network_status': self.network_status,
            'active_sensors': self.active_sensors,
            'failed_sensors': self.failed_sensors,
            'total_readings': self.total_readings
        }
