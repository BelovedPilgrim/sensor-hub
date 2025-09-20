"""LTR-329 ambient light sensor implementation."""


from typing import Dict, Any
import logging
import time
import random

import board
import busio
try:
    import adafruit_ltr329_ltr303
    import smbus2 as smbus
    HAS_LTR329 = True
except ImportError:
    HAS_LTR329 = False

from sensor_hub.sensors import SensorInterface
from sensor_hub.logging_config import (
    get_sensor_logger, log_sensor_init, log_sensor_reading, log_sensor_error
)

logger = logging.getLogger(__name__)


class LTR329Sensor(SensorInterface):
    """LTR-329 ambient light sensor implementation using Adafruit library."""

    def __init__(self, sensor_id: str, config: Dict[str, Any]):
        super().__init__(sensor_id, config)
        self.i2c_address = config.get('i2c_address', 0x29)
        self.mux_address = config.get('mux_address', None)
        self.mux_channel = config.get('mux_channel', None)
        self.bus_number = config.get('bus_number', 1)
        self.mock_mode = config.get('mock_mode', False)
        self._mock_base_lux = 150.0
        self._mock_time_offset = 0
        self.ltr = None
        self.i2c_bus = None
        
        # Create sensor-specific logger
        self.logger = get_sensor_logger(__name__, sensor_id, 'ltr329')

        if HAS_LTR329 and not self.mock_mode:
            try:
                # If using a multiplexer, set up the channel
                if self.mux_address is not None and self.mux_channel is not None:
                    self.i2c_bus = smbus.SMBus(self.bus_number)
                    self._select_mux_channel()
                
                # Use Blinka's I2C interface
                i2c = busio.I2C(board.SCL, board.SDA)
                self.ltr = adafruit_ltr329_ltr303.LTR329(
                    i2c, address=self.i2c_address
                )
                self.status = 'active'
                log_sensor_init(self.logger, sensor_id, 'ltr329', success=True)
                
                if self.mux_address:
                    self.logger.info(
                        "Initialized via multiplexer at 0x%02x channel %d",
                        self.mux_address, self.mux_channel
                    )
            except Exception as e:
                self.status = 'error'
                self.ltr = None
                log_sensor_init(self.logger, sensor_id, 'ltr329', 
                              success=False, error=str(e))
        else:
            if self.mock_mode:
                self.logger.info("Running in mock mode")
                self.status = 'mock'
            else:
                self.logger.warning("Hardware not available, using mock data")
                self.status = 'mock'
    
    def _select_mux_channel(self):
        """Select the multiplexer channel for this sensor."""
        if self.i2c_bus and self.mux_address and self.mux_channel is not None:
            try:
                # Set the multiplexer channel
                self.i2c_bus.write_byte(self.mux_address, 1 << self.mux_channel)
                logger.debug(
                    "Selected MUX 0x%02x channel %d for LTR329 %s",
                    self.mux_address, self.mux_channel, self.sensor_id
                )
            except Exception as e:
                logger.error(
                    "Failed to select MUX channel for LTR329 %s: %s",
                    self.sensor_id, e
                )
                raise
    
    def read(self) -> Dict[str, Any]:
        """
        Read ambient light level and IR data from the sensor using Adafruit
        library.
        """
        try:
            if self.ltr and self.status == 'active':
                # Select multiplexer channel if needed
                if self.mux_address is not None and self.mux_channel is not None:
                    self._select_mux_channel()
                
                # Adafruit LTR329 API: visible_plus_ir_light and ir_light
                visible_plus_ir = self.ltr.visible_plus_ir_light
                ir_light = self.ltr.ir_light
                
                # Use visible+IR as the main light level
                lux = visible_plus_ir
                
                # Log successful reading
                log_sensor_reading(self.logger, self.sensor_id, 'ltr329', {
                    'light_level': lux,
                    'ir_level': ir_light
                })
            else:
                lux, ir_light = self._read_mock_lux_and_ir()
                self.logger.debug("Mock reading generated: %.2f lux, %.2f IR", 
                                lux, ir_light)

            reading = {
                'light_level': round(lux, 2),        # Visible+IR light level
                'ir_level': round(ir_light, 2),      # IR light level
                'temperature': None,
                'humidity': None,
                'pressure': None,
                'proximity': None,
                'timestamp': time.time()
            }
            self.last_reading = reading
            return reading
        except Exception as e:
            self.error_count += 1
            log_sensor_error(self.logger, self.sensor_id, 'ltr329', e)
            return self._handle_error(e)
    
    # Hardware reading helpers are not needed with Adafruit library
    
    def _read_mock_lux_and_ir(self) -> tuple[float, float]:
        """Generate realistic mock visible+IR and IR readings as raw values."""
        import math
        
        # Simulate day/night cycle with some randomness
        current_time = time.time() + self._mock_time_offset
        
        # Create a sine wave for day/night simulation (24 hour cycle)
        hour_of_day = (current_time % 86400) / 3600  # 0-24 hours
        # Peak at noon
        day_cycle = math.sin((hour_of_day - 6) * math.pi / 12)
        
        # CH0 (visible+IR) raw values: range from 20 (night) to 3000 (day)
        base_ch0 = 20 + max(0, day_cycle) * 2980
        
        # Add some random variation
        variation = random.uniform(0.8, 1.2)
        ch0_value = base_ch0 * variation
        
        # Add occasional "cloud" effects
        if random.random() < 0.1:  # 10% chance of cloud
            ch0_value *= random.uniform(0.3, 0.7)
        
        # CH1 (IR only) raw values: should be less than CH0
        # Typical ratio is 0.1 to 0.8 depending on light source
        ir_ratio = random.uniform(0.2, 0.7)
        ch1_value = ch0_value * ir_ratio
        
        # Add night IR from heat sources
        if day_cycle < 0:  # Night time
            ch1_value += random.uniform(10, 50)
        
        # Add random variation to IR
        ir_variation = random.uniform(0.8, 1.2)
        ch1_value *= ir_variation
        
        # Ensure CH1 <= CH0 (physical constraint)
        ch1_value = min(ch1_value, ch0_value)
        
        return max(10.0, ch0_value), max(5.0, ch1_value)
    
    def is_available(self) -> bool:
        """Check if the LTR-329 sensor is available."""
        if self.status == 'mock':
            return True
        if not self.ltr:
            return False
        try:
            # Select multiplexer channel if needed
            if self.mux_address is not None and self.mux_channel is not None:
                self._select_mux_channel()
            
            # Try to read a value
            _ = self.ltr.visible_plus_ir_light
            return True
        except Exception as e:
            logger.debug(f"LTR-329 {self.sensor_id} not available: {e}")
            return False
    
    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle sensor read errors."""
        return {
            'light_level': None,
            'ir_level': None,
            'temperature': None,
            'humidity': None,
            'pressure': None,
            'proximity': None,
            'error': str(error)
        }
