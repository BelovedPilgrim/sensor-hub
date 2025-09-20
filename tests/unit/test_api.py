"""Unit tests for API endpoints."""

import pytest
import json
from datetime import datetime, timezone, timedelta

from ..conftest import (
    assert_api_response_success,
    assert_api_response_error,
    create_test_readings_batch
)


@pytest.mark.unit
@pytest.mark.api
class TestSensorsAPI:
    """Test the sensors API endpoints."""

    def test_get_sensors_empty(self, client, api_headers):
        """Test getting sensors when none exist."""
        response = client.get('/api/sensors', headers=api_headers)
        data = assert_api_response_success(response)
        
        assert 'sensors' in data
        assert len(data['sensors']) == 0

    def test_get_sensors_with_data(self, client, api_headers, create_test_sensor):
        """Test getting sensors when they exist."""
        # Create test sensors
        sensor1 = create_test_sensor({'id': 'sensor_1', 'name': 'Test Sensor 1'})
        sensor2 = create_test_sensor({'id': 'sensor_2', 'name': 'Test Sensor 2'})
        
        response = client.get('/api/sensors', headers=api_headers)
        data = assert_api_response_success(response)
        
        assert len(data['sensors']) == 2
        sensor_ids = [s['id'] for s in data['sensors']]
        assert sensor1.id in sensor_ids
        assert sensor2.id in sensor_ids

    def test_get_sensor_by_id_success(self, client, api_headers, 
                                     create_test_sensor):
        """Test getting a specific sensor by ID."""
        sensor = create_test_sensor()
        
        response = client.get(f'/api/sensors/{sensor.id}', headers=api_headers)
        data = assert_api_response_success(response)
        
        assert 'sensor' in data
        assert data['sensor']['id'] == sensor.id
        assert data['sensor']['name'] == sensor.name

    def test_get_sensor_by_id_not_found(self, client, api_headers):
        """Test getting a non-existent sensor."""
        response = client.get('/api/sensors/non_existent', headers=api_headers)
        assert_api_response_error(response, 404)

    def test_get_sensor_with_latest_reading(self, client, api_headers,
                                           create_test_sensor, 
                                           create_test_reading):
        """Test getting sensor includes latest reading."""
        sensor = create_test_sensor()
        reading = create_test_reading({'sensor_id': sensor.id})
        
        response = client.get(f'/api/sensors/{sensor.id}', headers=api_headers)
        data = assert_api_response_success(response)
        
        assert 'latest_reading' in data['sensor']
        latest = data['sensor']['latest_reading']
        assert latest['id'] == reading.id
        assert latest['sensor_id'] == sensor.id


@pytest.mark.unit
@pytest.mark.api
class TestReadingsAPI:
    """Test the readings API endpoints."""

    def test_get_sensor_readings_success(self, client, api_headers,
                                        create_test_sensor, 
                                        create_test_reading):
        """Test getting readings for a specific sensor."""
        sensor = create_test_sensor()
        reading = create_test_reading({'sensor_id': sensor.id})
        
        response = client.get(f'/api/sensors/{sensor.id}/readings',
                             headers=api_headers)
        data = assert_api_response_success(response)
        
        assert 'readings' in data
        assert len(data['readings']) == 1
        assert data['readings'][0]['id'] == reading.id

    def test_get_sensor_readings_with_parameters(self, client, api_headers,
                                                create_test_sensor,
                                                test_db_session):
        """Test getting readings with query parameters."""
        sensor = create_test_sensor()
        
        # Create multiple readings
        readings_data = create_test_readings_batch(sensor.id, count=10)
        for reading_data in readings_data:
            from sensor_hub.models import SensorReading
            reading = SensorReading(**reading_data)
            test_db_session.add(reading)
        test_db_session.commit()
        
        # Test with hours parameter
        response = client.get(f'/api/sensors/{sensor.id}/readings?hours=12',
                             headers=api_headers)
        data = assert_api_response_success(response)
        
        assert 'time_range' in data
        assert data['time_range']['hours'] == 12

    def test_get_sensor_readings_limit(self, client, api_headers,
                                      create_test_sensor, test_db_session):
        """Test readings limit parameter."""
        sensor = create_test_sensor()
        
        # Create many readings
        readings_data = create_test_readings_batch(sensor.id, count=50)
        for reading_data in readings_data:
            from sensor_hub.models import SensorReading
            reading = SensorReading(**reading_data)
            test_db_session.add(reading)
        test_db_session.commit()
        
        # Test limit
        response = client.get(f'/api/sensors/{sensor.id}/readings?limit=10',
                             headers=api_headers)
        data = assert_api_response_success(response)
        
        assert len(data['readings']) <= 10

    def test_get_all_readings(self, client, api_headers, create_test_sensor,
                             create_test_reading):
        """Test getting all readings from all sensors."""
        sensor1 = create_test_sensor({'id': 'sensor_1'})
        sensor2 = create_test_sensor({'id': 'sensor_2'})
        
        reading1 = create_test_reading({'sensor_id': sensor1.id})
        reading2 = create_test_reading({'sensor_id': sensor2.id})
        
        response = client.get('/api/readings', headers=api_headers)
        data = assert_api_response_success(response)
        
        assert len(data['readings']) == 2
        reading_ids = [r['id'] for r in data['readings']]
        assert reading1.id in reading_ids
        assert reading2.id in reading_ids

    def test_create_reading_success(self, client, api_headers):
        """Test creating a new reading via POST."""
        reading_data = {
            'sensor_id': 'test_sensor',
            'sensor_type': 'bme280',
            'data': {
                'temperature': 22.5,
                'humidity': 45.2,
                'pressure': 1013.25
            },
            'status': 'active'
        }
        
        response = client.post('/api/readings',
                              data=json.dumps(reading_data),
                              headers=api_headers)
        data = assert_api_response_success(response, 201)
        
        assert 'reading' in data
        created = data['reading']
        assert created['sensor_id'] == reading_data['sensor_id']
        assert created['data'] == reading_data['data']

    def test_create_reading_missing_fields(self, client, api_headers):
        """Test creating reading with missing required fields."""
        incomplete_data = {
            'sensor_id': 'test_sensor'
            # Missing sensor_type and data
        }
        
        response = client.post('/api/readings',
                              data=json.dumps(incomplete_data),
                              headers=api_headers)
        assert_api_response_error(response, 400)

    def test_create_reading_no_json(self, client, api_headers):
        """Test creating reading without JSON data."""
        response = client.post('/api/readings', headers=api_headers)
        assert_api_response_error(response, 400)

    def test_create_reading_invalid_json(self, client):
        """Test creating reading with invalid JSON."""
        response = client.post('/api/readings',
                              data='invalid json',
                              headers={'Content-Type': 'application/json'})
        assert response.status_code >= 400


@pytest.mark.unit
@pytest.mark.api
class TestStatusAPI:
    """Test the system status API."""

    def test_get_system_status(self, client, api_headers):
        """Test getting system status."""
        response = client.get('/api/status', headers=api_headers)
        data = assert_api_response_success(response)
        
        # Should contain basic status information
        assert 'status' in data
        assert 'timestamp' in data


@pytest.mark.unit
@pytest.mark.api
class TestAPIErrorHandling:
    """Test API error handling."""

    def test_api_404_handler(self, client, api_headers):
        """Test API 404 error handler."""
        response = client.get('/api/nonexistent', headers=api_headers)
        data = assert_api_response_error(response, 404)
        
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_api_method_not_allowed(self, client, api_headers):
        """Test method not allowed on API endpoints."""
        # Try DELETE on sensors endpoint (not allowed)
        response = client.delete('/api/sensors', headers=api_headers)
        assert response.status_code == 405

    def test_invalid_sensor_id_format(self, client, api_headers):
        """Test handling of invalid sensor ID formats."""
        # Test with various invalid characters
        invalid_ids = ['sensor with spaces', 'sensor/with/slashes', '']
        
        for invalid_id in invalid_ids:
            if invalid_id:  # Skip empty string as it changes the URL
                response = client.get(f'/api/sensors/{invalid_id}',
                                     headers=api_headers)
                # Should handle gracefully (404 or 400)
                assert response.status_code >= 400


@pytest.mark.unit
@pytest.mark.api
class TestAPIParameterValidation:
    """Test API parameter validation."""

    def test_hours_parameter_validation(self, client, api_headers,
                                       create_test_sensor):
        """Test validation of hours parameter."""
        sensor = create_test_sensor()
        
        # Test invalid hours values
        invalid_hours = [-1, 0, 200, 'abc']
        
        for hours in invalid_hours:
            response = client.get(f'/api/sensors/{sensor.id}/readings?hours={hours}',
                                 headers=api_headers)
            data = assert_api_response_success(response)
            # Should use default value or valid range
            if 'time_range' in data:
                assert 1 <= data['time_range']['hours'] <= 168

    def test_limit_parameter_validation(self, client, api_headers,
                                       create_test_sensor):
        """Test validation of limit parameter."""
        sensor = create_test_sensor()
        
        # Test invalid limit values
        invalid_limits = [-1, 0, 50000, 'abc']
        
        for limit in invalid_limits:
            response = client.get(f'/api/sensors/{sensor.id}/readings?limit={limit}',
                                 headers=api_headers)
            # Should either succeed with corrected value or return error
            assert response.status_code < 500  # No server errors

    def test_json_content_type_handling(self, client):
        """Test handling of different content types."""
        reading_data = {
            'sensor_id': 'test',
            'sensor_type': 'bme280',
            'data': {'temp': 20}
        }
        
        # Test with correct content type
        response = client.post('/api/readings',
                              data=json.dumps(reading_data),
                              headers={'Content-Type': 'application/json'})
        assert response.status_code < 500
        
        # Test with wrong content type
        response = client.post('/api/readings',
                              data=json.dumps(reading_data),
                              headers={'Content-Type': 'text/plain'})
        # Should handle gracefully
        assert response.status_code < 500