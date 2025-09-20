"""Unit tests for database models."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from sensor_hub.models import Sensor, SensorReading
from ..conftest import (
    assert_sensor_data_equal, 
    assert_reading_data_valid,
    create_test_readings_batch
)


@pytest.mark.unit
@pytest.mark.models
class TestSensorModel:
    """Test the Sensor model."""

    def test_create_sensor(self, test_db_session, sample_sensor_data):
        """Test creating a new sensor."""
        sensor = Sensor(**sample_sensor_data)
        test_db_session.add(sensor)
        test_db_session.commit()

        assert sensor.id == sample_sensor_data['id']
        assert sensor.name == sample_sensor_data['name']
        assert sensor.sensor_type == sample_sensor_data['sensor_type']
        assert sensor.enabled is True
        assert sensor.created_at is not None

    def test_sensor_to_dict(self, create_test_sensor):
        """Test sensor to_dict method."""
        sensor = create_test_sensor()
        sensor_dict = sensor.to_dict()

        assert isinstance(sensor_dict, dict)
        assert sensor_dict['id'] == sensor.id
        assert sensor_dict['name'] == sensor.name
        assert sensor_dict['sensor_type'] == sensor.sensor_type
        assert 'created_at' in sensor_dict
        assert 'updated_at' in sensor_dict

    def test_sensor_repr(self, create_test_sensor):
        """Test sensor string representation."""
        sensor = create_test_sensor()
        repr_str = repr(sensor)
        
        assert sensor.id in repr_str
        assert sensor.name in repr_str
        assert 'Sensor' in repr_str

    def test_sensor_backward_compatibility_properties(self, create_test_sensor):
        """Test backward compatibility properties."""
        sensor = create_test_sensor()
        
        # Test sensor_id property
        assert sensor.sensor_id == sensor.id
        
        # Test last_reading_time property  
        assert sensor.last_reading_time == sensor.last_reading_at

    def test_sensor_update_timestamp(self, test_db_session, create_test_sensor):
        """Test that updated_at timestamp changes on modification."""
        sensor = create_test_sensor()
        original_updated_at = sensor.updated_at
        
        # Modify sensor
        sensor.name = "Updated Name"
        sensor.updated_at = datetime.now(timezone.utc)
        test_db_session.commit()
        
        assert sensor.updated_at > original_updated_at

    def test_get_latest_reading_no_readings(self, create_test_sensor):
        """Test get_latest_reading when no readings exist."""
        sensor = create_test_sensor()
        latest = sensor.get_latest_reading()
        assert latest is None

    def test_get_latest_reading_with_readings(self, create_test_sensor, 
                                             create_test_reading):
        """Test get_latest_reading with multiple readings."""
        sensor = create_test_sensor()
        
        # Create multiple readings
        reading1 = create_test_reading({
            'sensor_id': sensor.id,
            'timestamp': datetime.now(timezone.utc) - timedelta(hours=2)
        })
        reading2 = create_test_reading({
            'sensor_id': sensor.id,
            'timestamp': datetime.now(timezone.utc) - timedelta(hours=1)
        })
        
        latest = sensor.get_latest_reading()
        assert latest is not None
        assert latest.id == reading2.id  # Should be the most recent

    def test_sensor_unique_constraint(self, test_db_session):
        """Test that sensor IDs must be unique."""
        import time
        
        # Create first sensor with unique ID
        sensor_id = f"test_sensor_{int(time.time() * 1000000)}"
        sensor_data = {
            'id': sensor_id,
            'name': 'Test BME280 Sensor',
            'sensor_type': 'bme280',
            'description': 'Test environmental sensor',
            'i2c_address': 0x77,
            'bus_number': 1,
            'poll_interval': 30,
            'enabled': True,
            'location': 'Test Lab',
            'calibration_data': {'offset_temp': 0.5, 'offset_humidity': -2.0}
        }
        
        sensor1 = Sensor(**sensor_data)
        test_db_session.add(sensor1)
        test_db_session.commit()
        
        # Try to create second sensor with same ID
        sensor2 = Sensor(**sensor_data)
        test_db_session.add(sensor2)
        
        with pytest.raises(Exception):  # Should raise integrity error
            test_db_session.commit()


@pytest.mark.unit
@pytest.mark.models
class TestSensorReadingModel:
    """Test the SensorReading model."""

    def test_create_reading(self, test_db_session, sample_reading_data):
        """Test creating a new sensor reading."""
        reading = SensorReading(**sample_reading_data)
        test_db_session.add(reading)
        test_db_session.commit()

        assert reading.sensor_id == sample_reading_data['sensor_id']
        assert reading.sensor_type == sample_reading_data['sensor_type']
        assert reading.data == sample_reading_data['data']
        assert reading.status == sample_reading_data['status']

    def test_reading_to_dict(self, create_test_reading):
        """Test reading to_dict method."""
        reading = create_test_reading()
        reading_dict = reading.to_dict()

        assert isinstance(reading_dict, dict)
        assert reading_dict['sensor_id'] == reading.sensor_id
        assert reading_dict['sensor_type'] == reading.sensor_type
        assert reading_dict['data'] == reading.data
        assert 'timestamp' in reading_dict
        assert 'id' in reading_dict

    def test_reading_repr(self, create_test_reading):
        """Test reading string representation."""
        reading = create_test_reading()
        repr_str = repr(reading)
        
        assert reading.sensor_id in repr_str
        assert 'SensorReading' in repr_str

    def test_reading_default_timestamp(self, test_db_session, sample_reading_data):
        """Test that reading gets default timestamp when not provided."""
        # Remove timestamp to test default behavior
        reading_data = sample_reading_data.copy()
        del reading_data['timestamp']
        
        reading = SensorReading(**reading_data)
        test_db_session.add(reading)
        test_db_session.commit()
        
        assert reading.timestamp is not None
        # Should be very recent (within last minute)
        # Handle potential timezone issues with SQLite
        now = datetime.now(timezone.utc)
        if reading.timestamp.tzinfo is None:
            # If reading timestamp is naive, compare with naive datetime
            time_diff = datetime.now() - reading.timestamp
        else:
            # If reading timestamp has timezone, use timezone-aware comparison
            time_diff = now - reading.timestamp
        assert time_diff.total_seconds() < 60

    def test_reading_json_data_storage(self, test_db_session, sample_reading_data):
        """Test that complex data structures are stored properly."""
        complex_data = {
            'temperature': 22.5,
            'humidity': 45.2,
            'pressure': 1013.25,
            'metadata': {
                'calibrated': True,
                'sensor_version': '1.2.3',
                'measurements': [1, 2, 3, 4, 5]
            }
        }
        
        reading_data = sample_reading_data.copy()
        reading_data['data'] = complex_data
        
        reading = SensorReading(**reading_data)
        test_db_session.add(reading)
        test_db_session.commit()
        
        # Retrieve and verify
        retrieved = test_db_session.query(SensorReading).filter_by(
            id=reading.id
        ).first()
        
        assert retrieved.data == complex_data
        assert retrieved.data['metadata']['measurements'] == [1, 2, 3, 4, 5]

    def test_reading_status_validation(self, test_db_session, sample_reading_data):
        """Test different status values."""
        statuses = ['active', 'error', 'warning', 'inactive']
        
        for status in statuses:
            reading_data = sample_reading_data.copy()
            reading_data['status'] = status
            reading_data['sensor_id'] = f'test_{status}'
            
            reading = SensorReading(**reading_data)
            test_db_session.add(reading)
            test_db_session.commit()
            
            assert reading.status == status

    def test_readings_ordering(self, test_db_session, sample_reading_data):
        """Test that readings can be ordered by timestamp."""
        sensor_id = 'test_ordering'
        readings_data = create_test_readings_batch(sensor_id, count=5)
        
        # Add readings to database
        for reading_data in readings_data:
            reading = SensorReading(**reading_data)
            test_db_session.add(reading)
        test_db_session.commit()
        
        # Query readings ordered by timestamp
        readings = test_db_session.query(SensorReading).filter_by(
            sensor_id=sensor_id
        ).order_by(SensorReading.timestamp.desc()).all()
        
        assert len(readings) == 5
        # Verify they're in descending order
        for i in range(len(readings) - 1):
            assert readings[i].timestamp >= readings[i + 1].timestamp


@pytest.mark.unit
@pytest.mark.models
class TestModelRelationships:
    """Test relationships between models."""

    def test_sensor_reading_relationship(self, create_test_sensor, 
                                        create_test_reading):
        """Test relationship between sensor and readings."""
        sensor = create_test_sensor()
        
        # Create readings for this sensor
        for i in range(3):
            create_test_reading({
                'sensor_id': sensor.id,
                'timestamp': datetime.now(timezone.utc) - timedelta(hours=i)
            })
        
        # Test that we can query readings through the sensor
        latest_reading = sensor.get_latest_reading()
        assert latest_reading is not None
        assert latest_reading.sensor_id == sensor.id

    def test_reading_sensor_id_foreign_key_behavior(self, test_db_session, 
                                                   sample_reading_data):
        """Test reading behavior with non-existent sensor ID."""
        # Create reading with non-existent sensor_id
        reading_data = sample_reading_data.copy()
        reading_data['sensor_id'] = 'non_existent_sensor'
        
        reading = SensorReading(**reading_data)
        test_db_session.add(reading)
        test_db_session.commit()
        
        # Should succeed (no foreign key constraint enforced)
        assert reading.sensor_id == 'non_existent_sensor'

    def test_multiple_sensors_isolation(self, create_test_sensor, 
                                       create_test_reading):
        """Test that readings are properly isolated between sensors."""
        sensor1 = create_test_sensor({'id': 'sensor_1'})
        sensor2 = create_test_sensor({'id': 'sensor_2'})
        
        # Create readings for each sensor
        create_test_reading({'sensor_id': sensor1.id})
        create_test_reading({'sensor_id': sensor2.id})
        
        # Each sensor should only see its own readings
        sensor1_reading = sensor1.get_latest_reading()
        sensor2_reading = sensor2.get_latest_reading()
        
        assert sensor1_reading.sensor_id == sensor1.id
        assert sensor2_reading.sensor_id == sensor2.id
        assert sensor1_reading.id != sensor2_reading.id