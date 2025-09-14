"""LTR-329 ambient light sensor implementation."""

from typing import Dict, Any
import logging
import time
import random

try:
    import smbus2 as smbus
    HAS_LTR329 = True
except ImportError:
    HAS_LTR329 = False

from sensor_hub.sensors import SensorInterface

logger = logging.getLogger(__name__)


class LTR329Sensor(SensorInterface):
    """LTR-329 ambient light sensor implementation."""
    
    # LTR-329 I2C registers
    CONTROL_REG = 0x80
    MEAS_RATE_REG = 0x85
    DATA_CH1_LOW = 0x88
    DATA_CH1_HIGH = 0x89
    DATA_CH0_LOW = 0x8A
    DATA_CH0_HIGH = 0x8B
    STATUS_REG = 0x8C
    
    # Configuration values
    CONTROL_ACTIVE = 0x01
    CONTROL_STANDBY = 0x00
    MEAS_RATE_500MS = 0x03  # 500ms integration time, 500ms measurement rate
    
    def __init__(self, sensor_id: str, config: Dict[str, Any]):
        super().__init__(sensor_id, config)
        self.i2c_address = config.get('i2c_address', 0x29)
        self.mux_address = config.get('mux_address', None)
        self.mux_channel = config.get('mux_channel', None)
        self.bus_number = config.get('bus_number', 1)
        self.i2c_bus = None
        self.mock_mode = config.get('mock_mode', False)
        
        # Mock sensor state for development
        self._mock_base_lux = 150.0
        self._mock_time_offset = 0
        
        if HAS_LTR329 and not self.mock_mode:
            try:
                self.i2c_bus = smbus.SMBus(self.bus_number)
                
                # If using a multiplexer, set up the channel
                if (self.mux_address is not None and
                        self.mux_channel is not None):
                    self._select_mux_channel()
                
                self._initialize_hardware()
                self.status = 'active'
                
                if self.mux_address:
                    logger.info(
                        f"LTR329 {sensor_id} initialized at "
                        f"0x{self.i2c_address:02x} via MUX "
                        f"0x{self.mux_address:02x} channel {self.mux_channel}"
                    )
                else:
                    logger.info(
                        f"LTR329 {sensor_id} initialized at "
                        f"0x{self.i2c_address:02x}"
                    )
            except Exception as e:
                logger.error(f"Failed to initialize LTR329 {sensor_id}: {e}")
                self.status = 'error'
                self.i2c_bus = None
        else:
            # Mock mode or no hardware available
            if self.mock_mode:
                logger.info(f"LTR329 {sensor_id} running in mock mode")
            else:
                logger.warning(
                    f"LTR329 {sensor_id} hardware not available, "
                    "using mock data"
                )
            self.status = 'mock'
    
    def _select_mux_channel(self):
        """Select multiplexer channel if using one."""
        try:
            self.i2c_bus.write_byte(self.mux_address, 1 << self.mux_channel)
            time.sleep(0.01)  # Small delay for channel selection
        except Exception as e:
            logger.error(
                f"Failed to select MUX channel {self.mux_channel}: {e}"
            )
    
    def _initialize_hardware(self):
        """Initialize the hardware LTR-329 sensor."""
        try:
            # Set to active mode
            self.i2c_bus.write_byte_data(
                self.i2c_address, self.CONTROL_REG, self.CONTROL_ACTIVE
            )
            
            # Set measurement rate (500ms integration time)
            self.i2c_bus.write_byte_data(
                self.i2c_address, self.MEAS_RATE_REG, self.MEAS_RATE_500MS
            )
            
            # Wait for sensor to become ready
            time.sleep(0.5)
            
            # Verify sensor is responding
            status = self.i2c_bus.read_byte_data(
                self.i2c_address, self.STATUS_REG
            )
            logger.debug(
                f"LTR-329 {self.sensor_id} status register: 0x{status:02X}"
            )
            
            logger.debug(
                f"LTR-329 {self.sensor_id} hardware configured successfully"
            )
            
        except Exception as e:
            logger.error(f"Failed to configure LTR-329 {self.sensor_id}: {e}")
            raise
    
    def read(self) -> Dict[str, Any]:
        """Read ambient light level and IR data from the sensor."""
        try:
            if self.i2c_bus and self.status == 'active':
                # If using multiplexer, select channel first
                if self.mux_address is not None:
                    self._select_mux_channel()
                
                visible_plus_ir, ir_data = self._read_hardware_lux_and_ir()
                logger.debug(
                    f"LTR-329 {self.sensor_id} hardware reading: "
                    f"Visible+IR={visible_plus_ir:.0f}, IR={ir_data:.0f}"
                )
            else:
                # Use mock data
                visible_plus_ir, ir_data = self._read_mock_lux_and_ir()
                logger.debug(
                    f"LTR-329 {self.sensor_id} mock reading: "
                    f"Visible+IR={visible_plus_ir:.0f}, IR={ir_data:.0f}"
                )
            
            reading = {
                # Raw channel values (matches Adafruit library approach)
                'light_level': round(visible_plus_ir, 0),  # CH0 visible+IR
                'ir_level': round(ir_data, 0),             # CH1 IR only
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
            logger.error(f"Error reading LTR-329 {self.sensor_id}: {e}")
            return self._handle_error(e)
    
    def _read_hardware_lux_and_ir(self) -> tuple[float, float]:
        """Read both visible light (lux) and IR data from hardware."""
        try:
            # Check if data is ready
            status = self.i2c_bus.read_byte_data(
                self.i2c_address, self.STATUS_REG
            )
            if not (status & 0x04):  # Data valid bit
                logger.debug(
                    f"LTR-329 {self.sensor_id} data not ready, "
                    f"status: 0x{status:02X}"
                )
                time.sleep(0.1)  # Wait a bit and try again
                
            # Read Channel 0 (visible + IR)
            ch0_low = self.i2c_bus.read_byte_data(
                self.i2c_address, self.DATA_CH0_LOW
            )
            ch0_high = self.i2c_bus.read_byte_data(
                self.i2c_address, self.DATA_CH0_HIGH
            )
            ch0_data = (ch0_high << 8) | ch0_low
            
            # Read Channel 1 (IR only)
            ch1_low = self.i2c_bus.read_byte_data(
                self.i2c_address, self.DATA_CH1_LOW
            )
            ch1_high = self.i2c_bus.read_byte_data(
                self.i2c_address, self.DATA_CH1_HIGH
            )
            ch1_data = (ch1_high << 8) | ch1_low
            
            logger.debug(
                f"LTR-329 {self.sensor_id} raw data: "
                f"CH0={ch0_data}, CH1={ch1_data}"
            )
            
            # Calculate visible+IR using raw channel data
            visible_plus_ir = self._calculate_visible_plus_ir(ch0_data)
            
            # IR data is directly from channel 1 (raw)
            ir_data = self._calculate_ir(ch1_data)
            
            return visible_plus_ir, ir_data
            
        except Exception as e:
            logger.error(
                f"Failed to read LTR-329 {self.sensor_id} hardware data: {e}"
            )
            raise
    
    def _calculate_visible_plus_ir(self, ch0: int) -> float:
        """Return raw visible+IR channel data like Adafruit library."""
        # CH0 contains visible + IR light
        # Return raw 16-bit value (0-65535) to match Adafruit approach
        return float(ch0)
    
    def _calculate_ir(self, ch1: int) -> float:
        """Return raw IR intensity from channel 1 reading."""
        # Return raw IR channel data (16-bit value 0-65535)
        # This matches the Adafruit library approach where IR is provided
        # as raw values for user interpretation
        return float(ch1)
    
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
            
        if not self.i2c_bus:
            return False
            
        try:
            # If using multiplexer, select channel first
            if self.mux_address is not None:
                self._select_mux_channel()
            
            # Try to read the status register
            self.i2c_bus.read_byte_data(
                self.i2c_address, self.STATUS_REG
            )
            return True
        except Exception as e:
            logger.debug(f"LTR-329 {self.sensor_id} not available: {e}")
            return False
    
    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle sensor read errors."""
        return {
            'light_level': None,
            'temperature': None,
            'humidity': None,
            'pressure': None,
            'proximity': None,
            'error': str(error)
        }
