"""BME280 temperature, humidity, and pressure sensor implementation."""

from typing import Dict, Any
import logging

try:
    import board
    import busio
    import adafruit_bme280.basic as adafruit_bme280
    import smbus2 as smbus
    HAS_BME280 = True
except ImportError:
    HAS_BME280 = False

from sensor_hub.sensors import SensorInterface

logger = logging.getLogger(__name__)


class BME280Sensor(SensorInterface):
    """BME280 environmental sensor implementation."""
    
    def __init__(self, sensor_id: str, config: Dict[str, Any]):
        super().__init__(sensor_id, config)
        self.i2c_address = config.get('i2c_address', 0x77)
        self.mux_address = config.get('mux_address', None)
        self.mux_channel = config.get('mux_channel', None)
        self.bus_number = config.get('bus_number', 1)
        self.bme280 = None
        self.i2c_bus = None
        
        if HAS_BME280:
            try:
                # If using a multiplexer, set up the channel
                if self.mux_address is not None and self.mux_channel is not None:
                    self.i2c_bus = smbus.SMBus(self.bus_number)
                    self._select_mux_channel()
                
                i2c = busio.I2C(board.SCL, board.SDA)
                self.bme280 = adafruit_bme280.Adafruit_BME280_I2C(
                    i2c, address=self.i2c_address
                )
                self.status = 'active'
                if self.mux_address:
                    logger.info(f"BME280 {sensor_id} initialized at 0x{self.i2c_address:02x} "
                              f"via MUX 0x{self.mux_address:02x} channel {self.mux_channel}")
                else:
                    logger.info(f"BME280 {sensor_id} initialized at 0x{self.i2c_address:02x}")
            except Exception as e:
                logger.error(f"Failed to initialize BME280 {sensor_id}: {e}")
                self.status = 'error'
        else:
            logger.warning("BME280 libraries not available")
            self.status = 'unavailable'
    
    def _select_mux_channel(self):
        """Select the appropriate channel on the PCA9548 multiplexer."""
        if self.i2c_bus and self.mux_address and self.mux_channel is not None:
            try:
                channel_mask = 1 << self.mux_channel
                self.i2c_bus.write_byte(self.mux_address, channel_mask)
            except Exception as e:
                logger.error(f"Failed to select MUX channel {self.mux_channel}: {e}")
    
    def read(self) -> Dict[str, Any]:
        """Read temperature, humidity, and pressure from BME280."""
        if not HAS_BME280 or not self.bme280:
            return self._handle_error(Exception("BME280 not available"))
        
        try:
            # Select multiplexer channel if needed
            if self.mux_address is not None:
                self._select_mux_channel()
            
            from datetime import datetime, timezone
            
            temperature = round(self.bme280.temperature, 2)
            humidity = round(self.bme280.relative_humidity, 2)
            pressure = round(self.bme280.pressure, 2)
            
            # Calculate dew point
            dew_point = self._calculate_dew_point(temperature, humidity)
            
            data = {
                'temperature': temperature,
                'humidity': humidity,
                'pressure': pressure,
                'dew_point': dew_point
            }
            
            self.last_reading = {
                'sensor_id': self.sensor_id,
                'sensor_type': self.get_sensor_type(),
                'timestamp': datetime.now(timezone.utc),
                'data': data,
                'status': 'active'
            }
            
            self.status = 'active'
            return self.last_reading
            
        except Exception as e:
            return self._handle_error(e)
    
    def is_available(self) -> bool:
        """Check if BME280 sensor is available."""
        if not HAS_BME280:
            return False
            
        try:
            if self.bme280:
                # Try to read temperature to verify sensor is responding
                _ = self.bme280.temperature
                return True
        except Exception as e:
            logger.debug(f"BME280 availability check failed: {e}")
            
        return False
    
    def _calculate_dew_point(self, temperature: float, humidity: float) -> float:
        """Calculate dew point using Magnus formula."""
        import math
        
        if humidity <= 0:
            return 0.0
            
        try:
            # Magnus formula coefficients
            a = 17.27
            b = 237.7
            
            alpha = ((a * temperature) / (b + temperature)) + math.log(humidity / 100.0)
            dew_point = (b * alpha) / (a - alpha)
            
            return round(dew_point, 2)
        except (ValueError, ZeroDivisionError):
            return 0.0
