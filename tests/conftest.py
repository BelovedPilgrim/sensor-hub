"""Test configuration and utilities."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from sensor_hub import create_app, db
from sensor_hub.config import TestingConfig
from sensor_hub.models import Sensor, SensorReading


class TestConfig(TestingConfig):
    """Enhanced testing configuration."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    LOG_LEVEL = 'DEBUG'
    LOG_TO_FILE = False
    SECRET_KEY = 'test-secret-key'


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    test_app = create_app(TestConfig)
    test_app.config['TESTING'] = True
    
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope='function') 
def test_db_session(app):
    """Create a database session for testing."""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        db.session.configure(bind=connection)
        
        yield db.session
        
        transaction.rollback()
        connection.close()
        db.session.remove()


@pytest.fixture
def sample_sensor_data():
    """Sample sensor data for testing."""
    return {
        'id': 'test_sensor_001',
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


@pytest.fixture
def sample_reading_data():
    """Sample reading data for testing."""
    return {
        'sensor_id': 'test_sensor_001',
        'sensor_type': 'bme280',
        'timestamp': datetime.now(timezone.utc),
        'data': {
            'temperature': 22.5,
            'humidity': 45.2,
            'pressure': 1013.25
        },
        'status': 'active'
    }


@pytest.fixture
def sample_ltr329_data():
    """Sample LTR329 sensor data for testing."""
    return {
        'id': 'ltr329_70_0_29',
        'name': 'Test LTR329 Light Sensor', 
        'sensor_type': 'ltr329',
        'description': 'Test light sensor via multiplexer',
        'i2c_address': 0x29,
        'bus_number': 1,
        'poll_interval': 30,
        'enabled': True,
        'location': 'Test Setup',
        'calibration_data': {
            'multiplexer_address': 0x70,
            'multiplexer_channel': 0
        }
    }


@pytest.fixture
def create_test_sensor(test_db_session, sample_sensor_data):
    """Create a test sensor in the database."""
    import time
    
    def _create_sensor(data=None):
        sensor_data = sample_sensor_data.copy()
        if data:
            sensor_data.update(data)
        
        # Make sensor ID unique for each test to avoid conflicts
        timestamp = str(int(time.time() * 1000000))  # microseconds
        sensor_data['id'] = f"test_sensor_{timestamp}"
        
        sensor = Sensor(**sensor_data)
        test_db_session.add(sensor)
        test_db_session.commit()
        return sensor
    
    return _create_sensor


@pytest.fixture
def create_test_reading(test_db_session, sample_reading_data):
    """Create a test reading in the database."""
    def _create_reading(data=None):
        reading_data = sample_reading_data.copy()
        if data:
            reading_data.update(data)
        
        reading = SensorReading(**reading_data)
        test_db_session.add(reading)
        test_db_session.commit()
        return reading
    
    return _create_reading


@pytest.fixture
def mock_i2c_bus():
    """Mock I2C bus for sensor testing."""
    with patch('smbus2.SMBus') as mock_bus:
        mock_instance = MagicMock()
        mock_bus.return_value.__enter__.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_bme280_sensor():
    """Mock BME280 sensor for testing."""
    with patch('adafruit_bme280.Adafruit_BME280_I2C') as mock_sensor:
        mock_instance = MagicMock()
        mock_instance.temperature = 22.5
        mock_instance.humidity = 45.2
        mock_instance.pressure = 1013.25
        mock_sensor.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_ltr329_sensor():
    """Mock LTR329 sensor for testing."""
    with patch('adafruit_ltr329_ltr303.LTR329') as mock_sensor:
        mock_instance = MagicMock()
        mock_instance.visible_plus_ir_light = 100
        mock_instance.ir_light = 50
        mock_sensor.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def api_headers():
    """Standard headers for API requests."""
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }


def create_test_readings_batch(sensor_id: str, count: int = 10, 
                              hours_back: int = 24) -> list:
    """Create a batch of test readings."""
    readings = []
    start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    interval = timedelta(hours=hours_back) / count
    
    for i in range(count):
        timestamp = start_time + (interval * i)
        reading_data = {
            'sensor_id': sensor_id,
            'sensor_type': 'bme280',
            'timestamp': timestamp,
            'data': {
                'temperature': 20.0 + (i * 0.5),  # Gradual increase
                'humidity': 40.0 + (i * 1.0),     # Gradual increase  
                'pressure': 1010.0 + (i * 0.2)    # Gradual increase
            },
            'status': 'active'
        }
        readings.append(reading_data)
    
    return readings


def assert_sensor_data_equal(sensor1: Sensor, sensor2: Dict[str, Any]):
    """Assert that sensor object matches expected data."""
    assert sensor1.id == sensor2['id']
    assert sensor1.name == sensor2['name']
    assert sensor1.sensor_type == sensor2['sensor_type']
    assert sensor1.i2c_address == sensor2.get('i2c_address')
    assert sensor1.enabled == sensor2.get('enabled', True)


def assert_reading_data_valid(reading: SensorReading, expected_sensor_id: str):
    """Assert that reading has valid structure."""
    assert reading.sensor_id == expected_sensor_id
    assert reading.timestamp is not None
    assert isinstance(reading.data, dict)
    assert reading.status in ['active', 'error', 'warning']


def assert_api_response_success(response, expected_status=200):
    """Assert that API response is successful."""
    assert response.status_code == expected_status
    data = response.get_json()
    assert data is not None
    assert data.get('status') == 'success'
    return data


def assert_api_response_error(response, expected_status=400):
    """Assert that API response is an error."""
    assert response.status_code >= expected_status
    data = response.get_json()
    assert data is not None
    assert data.get('status') == 'error'
    assert 'error' in data
    return data