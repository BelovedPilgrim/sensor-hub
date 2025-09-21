"""MPU-6050 6-axis accelerometer and gyroscope sensor implementation."""

from typing import Dict, Any
import logging
import time

try:
    import smbus2 as smbus
    HAS_MPU6050 = True
except ImportError:
    HAS_MPU6050 = False

from sensor_hub.sensors import SensorInterface
from sensor_hub.logging_config import (
    get_sensor_logger, log_sensor_init, log_sensor_reading, log_sensor_error
)

logger = logging.getLogger(__name__)


class MPU6050Sensor(SensorInterface):
    """MPU-6050 6-axis accelerometer and gyroscope sensor implementation."""

    # MPU-6050 Register Map
    PWR_MGMT_1 = 0x6B
    PWR_MGMT_2 = 0x6C
    CONFIG = 0x1A
    GYRO_CONFIG = 0x1B
    ACCEL_CONFIG = 0x1C
    ACCEL_XOUT_H = 0x3B
    TEMP_OUT_H = 0x41
    GYRO_XOUT_H = 0x43
    WHO_AM_I = 0x75

    def __init__(self, sensor_id: str, config: Dict[str, Any]):
        super().__init__(sensor_id, config)
        self.sensor_logger = get_sensor_logger(sensor_id, 'mpu6050')
        
        self.i2c_address = config.get('i2c_address', 0x68)
        self.mux_address = config.get('mux_address', None)
        self.mux_channel = config.get('mux_channel', None)
        self.mock_mode = config.get('mock_mode', False)
        
        # Sensor scaling factors
        self.accel_scale = 16384.0  # for ±2g range
        self.gyro_scale = 131.0     # for ±250 deg/s range
        
        self.bus = None
        self._initialized = False
        
        try:
            if not self.mock_mode and HAS_MPU6050:
                self._initialize_sensor()
                log_sensor_init(self.sensor_logger, self.sensor_id, 'mpu6050')
                if self.mux_address is not None:
                    log_sensor_init(self.sensor_logger, self.sensor_id,
                                    'mpu6050')
            else:
                log_sensor_init(self.sensor_logger, self.sensor_id, 'mpu6050')
                self._initialized = True

        except Exception as e:
            log_sensor_error(self.sensor_logger, self.sensor_id, 'mpu6050', e)
            self.status = 'error'
            self.error_count += 1

    def _initialize_sensor(self):
        """Initialize the MPU-6050 sensor."""
        self.bus = smbus.SMBus(1)
        
        # Select multiplexer channel if needed
        if self.mux_address is not None and self.mux_channel is not None:
            self._select_mux_channel()
        
        # Wake up the MPU-6050 (it starts in sleep mode)
        self.bus.write_byte_data(self.i2c_address, self.PWR_MGMT_1, 0x00)
        time.sleep(0.1)
        
        # Verify WHO_AM_I register
        who_am_i = self.bus.read_byte_data(self.i2c_address, self.WHO_AM_I)
        if who_am_i != 0x68:
            msg = (f"Invalid WHO_AM_I response: 0x{who_am_i:02x}, "
                   f"expected 0x68")
            raise RuntimeError(msg)
        
        # Configure sensor ranges
        # Set accelerometer range to ±2g
        self.bus.write_byte_data(self.i2c_address, self.ACCEL_CONFIG, 0x00)
        
        # Set gyroscope range to ±250 deg/s
        self.bus.write_byte_data(self.i2c_address, self.GYRO_CONFIG, 0x00)
        
        # Set digital low pass filter
        self.bus.write_byte_data(self.i2c_address, self.CONFIG, 0x03)
        
        time.sleep(0.1)
        self._initialized = True

    def _select_mux_channel(self):
        """Select the appropriate multiplexer channel."""
        if self.mux_address is not None and self.mux_channel is not None:
            self.bus.write_byte(self.mux_address, 1 << self.mux_channel)
            time.sleep(0.01)  # Small delay for channel switching

    def _read_word_2c(self, reg):
        """Read 16-bit signed value from two consecutive registers."""
        if self.mux_address is not None and self.mux_channel is not None:
            self._select_mux_channel()
            
        val = self.bus.read_word_data(self.i2c_address, reg)
        if val >= 0x8000:
            return -((65535 - val) + 1)
        else:
            return val

    def read(self) -> Dict[str, Any]:
        """Read accelerometer, gyroscope, and temperature data."""
        try:
            if self.mock_mode or not HAS_MPU6050:
                return self._get_mock_reading()
            
            if not self._initialized:
                raise RuntimeError("Sensor not initialized")
            
            # Read accelerometer data
            accel_x = (self._read_word_2c(self.ACCEL_XOUT_H) /
                       self.accel_scale)
            accel_y = (self._read_word_2c(self.ACCEL_XOUT_H + 2) /
                       self.accel_scale)
            accel_z = (self._read_word_2c(self.ACCEL_XOUT_H + 4) /
                       self.accel_scale)
            
            # Read temperature data
            temp_raw = self._read_word_2c(self.TEMP_OUT_H)
            temperature = temp_raw / 340.0 + 36.53  # Convert to Celsius
            
            # Read gyroscope data
            gyro_x = self._read_word_2c(self.GYRO_XOUT_H) / self.gyro_scale
            gyro_y = self._read_word_2c(self.GYRO_XOUT_H + 2) / self.gyro_scale
            gyro_z = self._read_word_2c(self.GYRO_XOUT_H + 4) / self.gyro_scale
            
            reading = {
                'accel_x': round(accel_x, 3),
                'accel_y': round(accel_y, 3),
                'accel_z': round(accel_z, 3),
                'gyro_x': round(gyro_x, 2),
                'gyro_y': round(gyro_y, 2),
                'gyro_z': round(gyro_z, 2),
                'temperature': round(temperature, 2),
                'timestamp': time.time()
            }
            
            self.last_reading = reading
            self.status = 'active'
            
            # Log reading data
            log_sensor_reading(self.sensor_logger, self.sensor_id, 'mpu6050',
                               reading)
            
            return reading
            
        except Exception as e:
            log_sensor_error(self.sensor_logger, self.sensor_id, 'mpu6050', e)
            self.error_count += 1
            self.status = 'error'
            return self._handle_error(e)

    def _get_mock_reading(self) -> Dict[str, Any]:
        """Generate mock reading for testing."""
        import random
        
        return {
            'accel_x': round(random.uniform(-1.0, 1.0), 3),
            'accel_y': round(random.uniform(-1.0, 1.0), 3),
            'accel_z': round(random.uniform(0.8, 1.2), 3),  # Gravity
            'gyro_x': round(random.uniform(-10.0, 10.0), 2),
            'gyro_y': round(random.uniform(-10.0, 10.0), 2),
            'gyro_z': round(random.uniform(-10.0, 10.0), 2),
            'temperature': round(random.uniform(20.0, 25.0), 2),
            'timestamp': time.time()
        }

    def is_available(self) -> bool:
        """Check if the MPU-6050 sensor is available."""
        try:
            if self.mock_mode or not HAS_MPU6050:
                return True
            
            if not self.bus:
                self.bus = smbus.SMBus(1)
            
            if self.mux_address is not None and self.mux_channel is not None:
                self._select_mux_channel()
            
            # Try to read WHO_AM_I register
            who_am_i = self.bus.read_byte_data(self.i2c_address, self.WHO_AM_I)
            return who_am_i == 0x68
            
        except Exception as e:
            log_sensor_error(self.sensor_logger, self.sensor_id, 'mpu6050', e)
            return False

    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle sensor reading errors."""
        return {
            'accel_x': None,
            'accel_y': None,
            'accel_z': None,
            'gyro_x': None,
            'gyro_y': None,
            'gyro_z': None,
            'temperature': None,
            'timestamp': time.time(),
            'error': str(error)
        }

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, 'bus') and self.bus:
            try:
                self.bus.close()
            except Exception:
                pass
