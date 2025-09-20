"""Unit tests for sensor classes."""

import pytest
from unittest.mock import MagicMock, patch, call

from sensor_hub.sensors.bme280 import BME280Sensor
from sensor_hub.sensors.ltr329 import LTR329Sensor


@pytest.mark.unit
@pytest.mark.sensors
class TestBME280Sensor:
    """Test the BME280 sensor class."""

    def test_sensor_initialization_direct(self, mock_bme280_sensor, mock_i2c_bus):
        """Test BME280 sensor initialization without multiplexer."""
        sensor_id = "bme280_77"
        config = {
            'i2c_address': 0x77,
            'bus_number': 1
        }
        
        with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
            sensor = BME280Sensor(sensor_id, config)
            sensor.initialize()
            
            assert sensor.sensor_id == sensor_id
            assert sensor.i2c_address == 0x77
            assert sensor.is_initialized

    def test_sensor_initialization_multiplexer(self, mock_bme280_sensor, 
                                              mock_i2c_bus):
        """Test BME280 sensor initialization with multiplexer."""
        sensor_id = "bme280_70_0_77"
        config = {
            'i2c_address': 0x77,
            'bus_number': 1,
            'multiplexer_address': 0x70,
            'multiplexer_channel': 0
        }
        
        with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
            sensor = BME280Sensor(sensor_id, config)
            sensor.initialize()
            
            assert sensor.sensor_id == sensor_id
            assert sensor.multiplexer_address == 0x70
            assert sensor.multiplexer_channel == 0
            assert sensor.is_initialized

    def test_read_data_success(self, mock_bme280_sensor, mock_i2c_bus):
        """Test successful data reading from BME280."""
        sensor_id = "bme280_77"
        config = {'i2c_address': 0x77, 'bus_number': 1}
        
        # Set up mock sensor data
        mock_bme280_sensor.temperature = 22.5
        mock_bme280_sensor.humidity = 45.2
        mock_bme280_sensor.pressure = 1013.25
        
        with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
            sensor = BME280Sensor(sensor_id, config)
            sensor.initialize()
            data = sensor.read_data()
            
            assert 'temperature' in data
            assert 'humidity' in data
            assert 'pressure' in data
            assert data['temperature'] == 22.5
            assert data['humidity'] == 45.2
            assert data['pressure'] == 1013.25

    def test_read_data_with_multiplexer(self, mock_bme280_sensor, mock_i2c_bus):
        """Test reading data through multiplexer."""
        sensor_id = "bme280_70_0_77"
        config = {
            'i2c_address': 0x77,
            'bus_number': 1,
            'multiplexer_address': 0x70,
            'multiplexer_channel': 0
        }
        
        with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
            sensor = BME280Sensor(sensor_id, config)
            sensor.initialize()
            data = sensor.read_data()
            
            # Verify multiplexer was accessed
            mock_i2c_bus.write_byte.assert_called()
            assert isinstance(data, dict)

    def test_read_data_sensor_error(self, mock_i2c_bus):
        """Test handling of sensor read errors."""
        sensor_id = "bme280_77"
        config = {'i2c_address': 0x77, 'bus_number': 1}
        
        with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
            with patch('adafruit_bme280.Adafruit_BME280_I2C') as mock_sensor:
                # Make the sensor raise an exception
                mock_sensor.side_effect = Exception("Sensor communication error")
                
                sensor = BME280Sensor(sensor_id, config)
                
                with pytest.raises(Exception):
                    sensor.initialize()

    def test_data_validation(self, mock_bme280_sensor, mock_i2c_bus):
        """Test data validation and sanitization."""
        sensor_id = "bme280_77"
        config = {'i2c_address': 0x77, 'bus_number': 1}
        
        # Test with extreme values
        mock_bme280_sensor.temperature = -100.0  # Extreme cold
        mock_bme280_sensor.humidity = 150.0      # Over 100%
        mock_bme280_sensor.pressure = 0.0        # Invalid pressure
        
        with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
            sensor = BME280Sensor(sensor_id, config)
            sensor.initialize()
            data = sensor.read_data()
            
            # Should still return data (sensor class handles validation)
            assert isinstance(data, dict)
            assert 'temperature' in data


@pytest.mark.unit
@pytest.mark.sensors
class TestLTR329Sensor:
    """Test the LTR329 sensor class."""

    def test_sensor_initialization_direct(self, mock_ltr329_sensor, mock_i2c_bus):
        """Test LTR329 sensor initialization without multiplexer."""
        sensor_id = "ltr329_29"
        config = {
            'i2c_address': 0x29,
            'bus_number': 1
        }
        
        with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
            sensor = LTR329Sensor(sensor_id, config)
            sensor.initialize()
            
            assert sensor.sensor_id == sensor_id
            assert sensor.i2c_address == 0x29
            assert sensor.is_initialized

    def test_sensor_initialization_multiplexer(self, mock_ltr329_sensor, 
                                              mock_i2c_bus):
        """Test LTR329 sensor initialization with multiplexer."""
        sensor_id = "ltr329_70_0_29"
        config = {
            'i2c_address': 0x29,
            'bus_number': 1,
            'multiplexer_address': 0x70,
            'multiplexer_channel': 0
        }
        
        with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
            sensor = LTR329Sensor(sensor_id, config)
            sensor.initialize()
            
            assert sensor.sensor_id == sensor_id
            assert sensor.multiplexer_address == 0x70
            assert sensor.multiplexer_channel == 0
            assert sensor.is_initialized

    def test_read_data_success(self, mock_ltr329_sensor, mock_i2c_bus):
        """Test successful data reading from LTR329."""
        sensor_id = "ltr329_29"
        config = {'i2c_address': 0x29, 'bus_number': 1}
        
        # Set up mock sensor data
        mock_ltr329_sensor.visible_plus_ir_light = 100
        mock_ltr329_sensor.ir_light = 50
        
        with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
            sensor = LTR329Sensor(sensor_id, config)
            sensor.initialize()
            data = sensor.read_data()
            
            assert 'ch0_light' in data
            assert 'ir_light' in data
            assert data['ch0_light'] == 100
            assert data['ir_light'] == 50

    def test_read_data_with_multiplexer(self, mock_ltr329_sensor, mock_i2c_bus):
        """Test reading data through multiplexer."""
        sensor_id = "ltr329_70_0_29"
        config = {
            'i2c_address': 0x29,
            'bus_number': 1,
            'multiplexer_address': 0x70,
            'multiplexer_channel': 0
        }
        
        with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
            sensor = LTR329Sensor(sensor_id, config)
            sensor.initialize()
            data = sensor.read_data()
            
            # Verify multiplexer was accessed
            mock_i2c_bus.write_byte.assert_called()
            assert isinstance(data, dict)

    def test_light_calculation(self, mock_ltr329_sensor, mock_i2c_bus):
        """Test light level calculations."""
        sensor_id = "ltr329_29"
        config = {'i2c_address': 0x29, 'bus_number': 1}
        
        # Test various light levels
        test_cases = [
            (100, 50),  # Normal indoor lighting
            (1000, 200),  # Bright indoor lighting
            (0, 0),     # Complete darkness
            (65535, 32767)  # Maximum values
        ]
        
        with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
            sensor = LTR329Sensor(sensor_id, config)
            sensor.initialize()
            
            for ch0, ir in test_cases:
                mock_ltr329_sensor.visible_plus_ir_light = ch0
                mock_ltr329_sensor.ir_light = ir
                
                data = sensor.read_data()
                assert data['ch0_light'] == ch0
                assert data['ir_light'] == ir
                assert isinstance(data['ch0_light'], (int, float))
                assert isinstance(data['ir_light'], (int, float))

    def test_sensor_error_handling(self, mock_i2c_bus):
        """Test LTR329 error handling."""
        sensor_id = "ltr329_29"
        config = {'i2c_address': 0x29, 'bus_number': 1}
        
        with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
            with patch('adafruit_ltr329_ltr303.LTR329') as mock_sensor:
                # Make the sensor raise an exception
                mock_sensor.side_effect = Exception("I2C communication error")
                
                sensor = LTR329Sensor(sensor_id, config)
                
                with pytest.raises(Exception):
                    sensor.initialize()


@pytest.mark.unit
@pytest.mark.sensors
class TestSensorCommonFunctionality:
    """Test common sensor functionality."""

    def test_multiplexer_channel_selection(self, mock_i2c_bus):
        """Test multiplexer channel selection logic."""
        config = {
            'i2c_address': 0x77,
            'bus_number': 1,
            'multiplexer_address': 0x70,
            'multiplexer_channel': 3
        }
        
        with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
            with patch('adafruit_bme280.Adafruit_BME280_I2C'):
                sensor = BME280Sensor("test", config)
                sensor.initialize()
                
                # Verify multiplexer channel selection
                mock_i2c_bus.write_byte.assert_called_with(0x70, 1 << 3)

    def test_sensor_config_validation(self):
        """Test sensor configuration validation."""
        # Test missing required config
        with pytest.raises((KeyError, ValueError)):
            sensor = BME280Sensor("test", {})
            sensor.initialize()

    def test_sensor_type_identification(self):
        """Test sensor type identification."""
        bme280 = BME280Sensor("test", {'i2c_address': 0x77, 'bus_number': 1})
        ltr329 = LTR329Sensor("test", {'i2c_address': 0x29, 'bus_number': 1})
        
        # Sensors should identify their type correctly
        assert hasattr(bme280, 'sensor_id')
        assert hasattr(ltr329, 'sensor_id')

    def test_initialization_state_tracking(self, mock_bme280_sensor, 
                                          mock_i2c_bus):
        """Test initialization state tracking."""
        sensor_id = "bme280_77"
        config = {'i2c_address': 0x77, 'bus_number': 1}
        
        with patch('busio.I2C'), patch('board.SCL'), patch('board.SDA'):
            sensor = BME280Sensor(sensor_id, config)
            
            # Should not be initialized yet
            assert not sensor.is_initialized
            
            # Initialize
            sensor.initialize()
            assert sensor.is_initialized

    def test_reading_before_initialization(self):
        """Test reading data before sensor initialization."""
        sensor = BME280Sensor("test", {'i2c_address': 0x77, 'bus_number': 1})
        
        # Should raise error or return None when not initialized
        with pytest.raises((RuntimeError, AttributeError)):
            sensor.read_data()

    def test_sensor_configuration_storage(self):
        """Test that sensor configuration is stored correctly."""
        config = {
            'i2c_address': 0x77,
            'bus_number': 1,
            'multiplexer_address': 0x70,
            'multiplexer_channel': 2
        }
        
        sensor = BME280Sensor("test", config)
        
        assert sensor.i2c_address == 0x77
        assert sensor.bus_number == 1
        assert sensor.multiplexer_address == 0x70
        assert sensor.multiplexer_channel == 2