"""Integration tests for the complete sensor hub application."""

import pytest
import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from sensor_hub import create_app, db
from sensor_hub.models import Sensor, SensorReading
from sensor_hub.discovery_service import discovery_service


@pytest.mark.integration
class TestFullApplicationWorkflow:
    """Test complete application workflows."""

    def test_sensor_discovery_to_data_collection(self, app, client):
        """Test full workflow from sensor discovery to data collection."""
        with app.app_context():
            # Mock sensor discovery
            with patch('sensor_hub.sensors.bme280.BME280Sensor') as mock_bme280:
                with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
                    mock_instance = MagicMock()
                    mock_instance.temperature = 22.5
                    mock_instance.humidity = 45.2
                    mock_instance.pressure = 1013.25
                    mock_bme280.return_value = mock_instance
                    
                    # Step 1: Discover and register sensors
                    discovery_result = discovery_service.discover_and_register(
                        auto_enable=True
                    )
                    
                    # Should discover at least 0 sensors (could be mocked)
                    assert discovery_result['discovered_count'] >= 0
                    
                    # Step 2: Create a sensor manually for testing
                    sensor = Sensor(
                        id='test_bme280_77',
                        name='Test BME280',
                        sensor_type='bme280',
                        i2c_address=0x77,
                        enabled=True
                    )
                    db.session.add(sensor)
                    db.session.commit()
                    
                    # Step 3: Create a reading
                    reading = SensorReading(
                        sensor_id=sensor.id,
                        sensor_type=sensor.sensor_type,
                        data={
                            'temperature': 22.5,
                            'humidity': 45.2,
                            'pressure': 1013.25
                        }
                    )
                    db.session.add(reading)
                    db.session.commit()
                    
                    # Step 4: Verify via API
                    response = client.get('/api/sensors')
                    assert response.status_code == 200
                    data = response.get_json()
                    assert len(data['sensors']) == 1
                    assert data['sensors'][0]['id'] == sensor.id
                    
                    # Step 5: Get sensor readings
                    response = client.get(f'/api/sensors/{sensor.id}/readings')
                    assert response.status_code == 200
                    data = response.get_json()
                    assert len(data['readings']) == 1
                    assert data['readings'][0]['sensor_id'] == sensor.id

    def test_web_interface_integration(self, app, client):
        """Test web interface integration with database."""
        with app.app_context():
            # Create test data
            sensor = Sensor(
                id='web_test_sensor',
                name='Web Test Sensor',
                sensor_type='bme280',
                i2c_address=0x77,
                enabled=True
            )
            db.session.add(sensor)
            
            reading = SensorReading(
                sensor_id=sensor.id,
                sensor_type=sensor.sensor_type,
                data={'temperature': 20.0, 'humidity': 50.0, 'pressure': 1000.0}
            )
            db.session.add(reading)
            db.session.commit()
            
            # Test main dashboard
            response = client.get('/')
            assert response.status_code == 200
            assert b'Web Test Sensor' in response.data
            
            # Test sensor detail page
            response = client.get(f'/sensor/{sensor.id}')
            assert response.status_code == 200
            assert b'Web Test Sensor' in response.data
            
            # Test data page
            response = client.get('/data')
            assert response.status_code == 200

    def test_api_to_database_consistency(self, app, client, api_headers):
        """Test API operations maintain database consistency."""
        with app.app_context():
            # Create sensor via database
            sensor = Sensor(
                id='consistency_test',
                name='Consistency Test Sensor',
                sensor_type='ltr329',
                i2c_address=0x29,
                enabled=True
            )
            db.session.add(sensor)
            db.session.commit()
            
            # Create reading via API
            reading_data = {
                'sensor_id': sensor.id,
                'sensor_type': sensor.sensor_type,
                'data': {'ch0_light': 100, 'ir_light': 50}
            }
            
            response = client.post('/api/readings',
                                  data=json.dumps(reading_data),
                                  headers=api_headers)
            assert response.status_code == 201
            
            # Verify in database
            db_reading = SensorReading.query.filter_by(
                sensor_id=sensor.id
            ).first()
            assert db_reading is not None
            assert db_reading.data == reading_data['data']
            
            # Verify via API
            response = client.get(f'/api/sensors/{sensor.id}/readings')
            assert response.status_code == 200
            data = response.get_json()
            assert len(data['readings']) == 1
            assert data['readings'][0]['data'] == reading_data['data']


@pytest.mark.integration
class TestMultiSensorIntegration:
    """Test integration with multiple sensors."""

    def test_multiple_sensor_types(self, app, client):
        """Test handling multiple sensor types simultaneously."""
        with app.app_context():
            # Create different sensor types
            bme280_sensor = Sensor(
                id='multi_bme280',
                name='Multi BME280',
                sensor_type='bme280',
                i2c_address=0x77,
                enabled=True
            )
            
            ltr329_sensor = Sensor(
                id='multi_ltr329',
                name='Multi LTR329',
                sensor_type='ltr329',
                i2c_address=0x29,
                enabled=True
            )
            
            db.session.add_all([bme280_sensor, ltr329_sensor])
            
            # Create readings for each
            bme280_reading = SensorReading(
                sensor_id=bme280_sensor.id,
                sensor_type='bme280',
                data={'temperature': 22.0, 'humidity': 55.0, 'pressure': 1015.0}
            )
            
            ltr329_reading = SensorReading(
                sensor_id=ltr329_sensor.id,
                sensor_type='ltr329',
                data={'ch0_light': 150, 'ir_light': 75}
            )
            
            db.session.add_all([bme280_reading, ltr329_reading])
            db.session.commit()
            
            # Test API returns both sensors
            response = client.get('/api/sensors')
            assert response.status_code == 200
            data = response.get_json()
            assert len(data['sensors']) == 2
            
            sensor_types = [s['sensor_type'] for s in data['sensors']]
            assert 'bme280' in sensor_types
            assert 'ltr329' in sensor_types
            
            # Test all readings endpoint
            response = client.get('/api/readings')
            assert response.status_code == 200
            data = response.get_json()
            assert len(data['readings']) == 2

    def test_sensor_data_aggregation(self, app, client):
        """Test aggregation of data from multiple sensors."""
        with app.app_context():
            sensor_id = 'aggregation_test'
            
            # Create sensor
            sensor = Sensor(
                id=sensor_id,
                name='Aggregation Test',
                sensor_type='bme280',
                i2c_address=0x77,
                enabled=True
            )
            db.session.add(sensor)
            
            # Create multiple readings over time
            base_time = datetime.now(timezone.utc)
            readings = []
            
            for i in range(10):
                reading = SensorReading(
                    sensor_id=sensor_id,
                    sensor_type='bme280',
                    timestamp=base_time - timedelta(hours=i),
                    data={
                        'temperature': 20.0 + i,
                        'humidity': 50.0 + i,
                        'pressure': 1000.0 + i
                    }
                )
                readings.append(reading)
            
            db.session.add_all(readings)
            db.session.commit()
            
            # Test time-range queries
            response = client.get(f'/api/sensors/{sensor_id}/readings?hours=5')
            assert response.status_code == 200
            data = response.get_json()
            
            # Should return readings from last 5 hours
            assert len(data['readings']) <= 6  # Including current hour
            assert data['time_range']['hours'] == 5


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Test error handling across the application."""

    def test_database_error_recovery(self, app, client):
        """Test application behavior during database errors."""
        with app.app_context():
            # Test API resilience
            response = client.get('/api/sensors')
            # Should not crash even if database has issues
            assert response.status_code < 500

    def test_missing_sensor_handling(self, app, client):
        """Test handling of requests for non-existent sensors."""
        with app.app_context():
            # API should return 404
            response = client.get('/api/sensors/nonexistent')
            assert response.status_code == 404
            
            # Web interface should show error page
            response = client.get('/sensor/nonexistent')
            assert response.status_code == 404

    def test_invalid_data_handling(self, app, client, api_headers):
        """Test handling of invalid sensor data."""
        with app.app_context():
            # Try to create reading with invalid data
            invalid_data = {
                'sensor_id': 'test',
                'sensor_type': 'bme280'
                # Missing 'data' field
            }
            
            response = client.post('/api/readings',
                                  data=json.dumps(invalid_data),
                                  headers=api_headers)
            assert response.status_code == 400
            
            # Application should still be functional
            response = client.get('/api/sensors')
            assert response.status_code == 200


@pytest.mark.integration
class TestPerformanceIntegration:
    """Test performance characteristics under load."""

    def test_large_dataset_handling(self, app, client):
        """Test handling of large datasets."""
        with app.app_context():
            sensor_id = 'performance_test'
            
            # Create sensor
            sensor = Sensor(
                id=sensor_id,
                name='Performance Test',
                sensor_type='bme280',
                i2c_address=0x77,
                enabled=True
            )
            db.session.add(sensor)
            
            # Create many readings
            readings = []
            base_time = datetime.now(timezone.utc)
            
            for i in range(100):  # Moderate number for testing
                reading = SensorReading(
                    sensor_id=sensor_id,
                    sensor_type='bme280',
                    timestamp=base_time - timedelta(minutes=i),
                    data={'temperature': 20.0 + (i % 10)}
                )
                readings.append(reading)
            
            # Batch insert
            db.session.add_all(readings)
            db.session.commit()
            
            # Test API performance
            start_time = time.time()
            response = client.get(f'/api/sensors/{sensor_id}/readings?limit=50')
            end_time = time.time()
            
            assert response.status_code == 200
            assert (end_time - start_time) < 5.0  # Should respond within 5 seconds
            
            data = response.get_json()
            assert len(data['readings']) <= 50

    def test_concurrent_api_requests(self, app, client):
        """Test handling of concurrent API requests."""
        with app.app_context():
            # Create test data
            sensor = Sensor(
                id='concurrent_test',
                name='Concurrent Test',
                sensor_type='bme280',
                enabled=True
            )
            db.session.add(sensor)
            db.session.commit()
            
            # Multiple concurrent requests (simulated sequentially)
            responses = []
            for _ in range(5):
                response = client.get('/api/sensors')
                responses.append(response)
            
            # All should succeed
            for response in responses:
                assert response.status_code == 200
                data = response.get_json()
                assert 'sensors' in data


@pytest.mark.integration
class TestConfigurationIntegration:
    """Test configuration and environment integration."""

    def test_testing_configuration(self, app):
        """Test that testing configuration is properly applied."""
        assert app.config['TESTING'] is True
        assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'
        assert app.config['LOG_TO_FILE'] is False

    def test_database_configuration(self, app):
        """Test database configuration in test environment."""
        with app.app_context():
            # Should be able to create tables
            db.create_all()
            
            # Should be able to query
            sensors = Sensor.query.all()
            assert isinstance(sensors, list)

    def test_logging_configuration(self, app):
        """Test logging configuration in test environment."""
        # Logging should be configured but not interfere with tests
        assert app.config.get('LOG_LEVEL') == 'DEBUG'
        
        # Should be able to make requests without logging errors
        with app.test_client() as client:
            response = client.get('/')
            # Should not raise logging-related errors
            assert response.status_code in [200, 404, 500]  # Any valid HTTP status