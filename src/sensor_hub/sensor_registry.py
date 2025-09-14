"""Sensor registry and auto-detection system."""

import logging
from typing import Dict, Type, List, Optional, Any
from abc import ABC
import importlib
import inspect

from sensor_hub.sensors import SensorInterface

logger = logging.getLogger(__name__)


class SensorRegistry:
    """Registry for all available sensor types."""
    
    def __init__(self):
        self._sensor_classes: Dict[str, Type[SensorInterface]] = {}
        self._discovery_handlers: Dict[str, callable] = {}
        self._register_builtin_sensors()
    
    def register_sensor(self, sensor_type: str, sensor_class: Type[SensorInterface]):
        """Register a sensor class."""
        if not issubclass(sensor_class, SensorInterface):
            raise ValueError(f"Sensor class {sensor_class} must inherit from SensorInterface")
        
        self._sensor_classes[sensor_type.lower()] = sensor_class
        logger.info(f"Registered sensor type: {sensor_type}")
    
    def register_discovery_handler(self, sensor_type: str, handler: callable):
        """Register a discovery handler for a sensor type."""
        self._discovery_handlers[sensor_type.lower()] = handler
        logger.info(f"Registered discovery handler for: {sensor_type}")
    
    def get_sensor_class(self, sensor_type: str) -> Optional[Type[SensorInterface]]:
        """Get sensor class by type."""
        return self._sensor_classes.get(sensor_type.lower())
    
    def get_available_types(self) -> List[str]:
        """Get list of available sensor types."""
        return list(self._sensor_classes.keys())
    
    def create_sensor(self, sensor_type: str, sensor_id: str, config: Dict[str, Any]) -> Optional[SensorInterface]:
        """Create a sensor instance."""
        sensor_class = self.get_sensor_class(sensor_type)
        if not sensor_class:
            logger.error(f"Unknown sensor type: {sensor_type}")
            return None
        
        try:
            return sensor_class(sensor_id, config)
        except Exception as e:
            logger.error(f"Failed to create sensor {sensor_id} of type {sensor_type}: {e}")
            return None
    
    def _register_builtin_sensors(self):
        """Register built-in sensor types."""
        try:
            # Import and register BME280
            from sensor_hub.sensors.bme280 import BME280Sensor
            self.register_sensor('bme280', BME280Sensor)
            self.register_discovery_handler('bme280', self._discover_bme280)
        except ImportError as e:
            logger.warning(f"BME280 sensor not available: {e}")
        
        try:
            # Import and register LTR329
            from sensor_hub.sensors.ltr329 import LTR329Sensor
            self.register_sensor('ltr329', LTR329Sensor)
            self.register_discovery_handler('ltr329', self._discover_ltr329)
        except ImportError as e:
            logger.warning(f"LTR329 sensor not available: {e}")
    
    def discover_sensors(self) -> List[Dict[str, Any]]:
        """Discover all available sensors on the system."""
        discovered_sensors = []
        
        for sensor_type, handler in self._discovery_handlers.items():
            try:
                sensors = handler()
                for sensor_info in sensors:
                    sensor_info['sensor_type'] = sensor_type
                    discovered_sensors.append(sensor_info)
            except Exception as e:
                logger.error(f"Error discovering {sensor_type} sensors: {e}")
        
        logger.info(f"Discovered {len(discovered_sensors)} sensors")
        return discovered_sensors
    
    def _discover_bme280(self) -> List[Dict[str, Any]]:
        """Discover BME280 sensors on I2C bus and behind PCA9548 multiplexers."""
        sensors = []
        
        try:
            import subprocess
            result = subprocess.run(['i2cdetect', '-y', '1'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Parse i2cdetect output
                lines = result.stdout.split('\n')[1:]  # Skip header
                detected_addresses = []
                
                for line in lines:
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    
                    row_addr = int(parts[0][:-1], 16)  # Remove ':' and convert
                    
                    for col, cell in enumerate(parts[1:], 0):
                        if cell != '--' and cell != 'UU':
                            addr = row_addr + col
                            detected_addresses.append(addr)
                
                # Ensure all PCA9548 channels are disabled before direct scans
                self._disable_all_multiplexers(detected_addresses)
                
                # First, identify multiplexers and scan their channels
                # Then check for direct BME280 connections on remaining addresses
                multiplexer_addresses = []
                pca9548_addresses = [0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77]
                for mux_addr in detected_addresses:
                    if mux_addr in pca9548_addresses:
                        # Try to verify it's actually a multiplexer by testing channel selection
                        if self._verify_pca9548(mux_addr):
                            multiplexer_addresses.append(mux_addr)
                            # Scan multiplexer channels for BME280 sensors
                            mux_sensors = self._scan_pca9548_channels(mux_addr)
                            sensors.extend(mux_sensors)
                
                # Check for direct BME280 connections (excluding confirmed multiplexers)
                bme280_addresses = [0x76, 0x77]
                for addr in detected_addresses:
                    if addr in bme280_addresses and addr not in multiplexer_addresses:
                        sensors.append({
                            'sensor_id': f'bme280_{addr:02x}',
                            'name': f'BME280 Sensor (0x{addr:02x})',
                            'config': {
                                'i2c_address': addr,
                                'bus_number': 1
                            },
                            'location': 'I2C Direct',
                            'description': 'Temperature, humidity, pressure sensor'
                        })
                        
        except Exception as e:
            logger.debug(f"I2C detection failed for BME280: {e}")
        
        return sensors

    def _disable_all_multiplexers(self, addresses: List[int]):
        """Disable all channels on detected PCA9548 multiplexers."""
        try:
            import smbus2 as smbus
            bus = smbus.SMBus(1)
            
            pca9548_addresses = [0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77]
            for addr in addresses:
                if addr in pca9548_addresses:
                    try:
                        bus.write_byte(addr, 0x00)  # Disable all channels
                    except Exception:
                        pass  # Ignore if not a multiplexer
            bus.close()
        except Exception:
            pass

    def _verify_pca9548(self, address: int) -> bool:
        """Verify if an address is actually a PCA9548 multiplexer."""
        try:
            import smbus2 as smbus
            bus = smbus.SMBus(1)
            
            # Try to select channel 0, then disable all channels
            # PCA9548 should respond without error
            bus.write_byte(address, 0x01)  # Select channel 0
            bus.write_byte(address, 0x00)  # Disable all channels
            bus.close()
            return True
        except Exception:
            return False

    def _scan_pca9548_channels(self, mux_address: int) -> List[Dict[str, Any]]:
        """Scan PCA9548 multiplexer channels for BME280 sensors."""
        sensors = []
        
        try:
            import smbus2 as smbus
            import time
            
            bus = smbus.SMBus(1)
            bme280_addresses = [0x76, 0x77]
            
            for channel in range(8):
                try:
                    # Select channel on multiplexer
                    bus.write_byte(mux_address, 1 << channel)
                    time.sleep(0.05)  # Small delay for channel selection
                    
                    # Check for BME280 on this channel
                    for bme_addr in bme280_addresses:
                        try:
                            bus.read_byte(bme_addr)
                            # Found BME280 on this channel
                            sensor_id = f'bme280_{mux_address:02x}_{channel}_{bme_addr:02x}'
                            sensors.append({
                                'sensor_id': sensor_id,
                                'name': f'BME280 via MUX 0x{mux_address:02x} Ch{channel}',
                                'config': {
                                    'i2c_address': bme_addr,
                                    'bus_number': 1,
                                    'mux_address': mux_address,
                                    'mux_channel': channel
                                },
                                'location': f'PCA9548 0x{mux_address:02x} Channel {channel}',
                                'description': 'Temperature, humidity, pressure sensor'
                            })
                            logger.info(f"Found BME280 at 0x{bme_addr:02x} on MUX "
                                      f"0x{mux_address:02x} channel {channel}")
                        except OSError:
                            pass  # No BME280 at this address on this channel
                            
                except OSError as e:
                    logger.debug(f"Error scanning MUX channel {channel}: {e}")
            
            # Reset multiplexer (disable all channels)
            bus.write_byte(mux_address, 0x00)
            bus.close()
            
        except Exception as e:
            logger.debug(f"Error scanning PCA9548 at 0x{mux_address:02x}: {e}")
        
        return sensors

    def _discover_ltr329(self) -> List[Dict[str, Any]]:
        """Discover LTR-329 ambient light sensors on I2C bus and MUX."""
        discovered_sensors = []
        
        try:
            import subprocess
            import smbus2 as smbus
            import time
            
            # Get list of devices on I2C bus 1
            result = subprocess.run(['i2cdetect', '-y', '1'],
                                    capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.warning("Could not run i2cdetect to scan for sensors")
                return discovered_sensors
            
            # Parse i2cdetect output to find devices
            output_lines = result.stdout.strip().split('\n')[1:]  # Skip header
            detected_addresses = []
            
            for line in output_lines:
                parts = line.split()
                if len(parts) > 1:
                    for addr_str in parts[1:]:  # Skip row label
                        if addr_str != '--' and addr_str != 'UU':
                            try:
                                addr = int(addr_str, 16)
                                detected_addresses.append(addr)
                            except ValueError:
                                pass
            
            addr_list = [hex(addr) for addr in detected_addresses]
            logger.debug(f"Detected I2C addresses: {addr_list}")
            
            # Look for LTR-329 at standard addresses (0x29)
            ltr329_addresses = [0x29]
            
            # First check for direct connections
            for addr in detected_addresses:
                if addr in ltr329_addresses:
                    # Try to verify it's actually an LTR-329
                    try:
                        bus = smbus.SMBus(1)
                        # Try to read the Part ID register
                        part_id = bus.read_byte_data(addr, 0x86)
                        bus.close()
                        
                        # Verify it's an LTR-329 (Part ID should be 0xA0)
                        if part_id == 0xA0:
                            discovered_sensors.append({
                                'sensor_id': f'ltr329_{addr:02x}',
                                'name': f'LTR-329 Light Sensor (0x{addr:02x})',
                                'i2c_address': addr,
                                'bus_number': 1,
                                'description': 'Ambient light sensor'
                            })
                            
                            logger.info(
                                f"Discovered LTR-329 sensor at 0x{addr:02x}"
                            )
                        
                    except OSError:
                        logger.debug(
                            f"Device at 0x{addr:02x} is not an LTR-329"
                        )
            
            # Check multiplexer channels for LTR-329 sensors
            multiplexer_addresses = [
                0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77
            ]
            
            for mux_addr in detected_addresses:
                if mux_addr in multiplexer_addresses:
                    logger.debug(f"Scanning multiplexer at 0x{mux_addr:02x} for LTR-329 sensors")
                    
                    try:
                        bus = smbus.SMBus(1)
                        
                        # Scan each channel (0-7)
                        for channel in range(8):
                            try:
                                # Select channel
                                bus.write_byte(mux_addr, 1 << channel)
                                time.sleep(0.01)
                                
                                # Check for LTR-329 at standard address
                                for ltr_addr in ltr329_addresses:
                                    try:
                                        part_id = bus.read_byte_data(ltr_addr, 0x86)
                                        
                                        # Verify it's an LTR-329 (Part ID should be 0xA0)
                                        if part_id == 0xA0:
                                            sensor_id = f'ltr329_{mux_addr:02x}_{channel}_{ltr_addr:02x}'
                                            discovered_sensors.append({
                                                'sensor_id': sensor_id,
                                                'name': f'LTR-329 Light Sensor (MUX 0x{mux_addr:02x} Ch{channel})',
                                                'i2c_address': ltr_addr,
                                                'mux_address': mux_addr,
                                                'mux_channel': channel,
                                                'bus_number': 1,
                                                'description': 'Ambient light sensor via multiplexer'
                                            })
                                            
                                            logger.info(
                                                f"Discovered LTR-329 sensor on MUX 0x{mux_addr:02x} "
                                                f"channel {channel} at 0x{ltr_addr:02x}"
                                            )
                                    
                                    except OSError:
                                        pass  # No LTR-329 at this address on this channel
                                        
                            except OSError:
                                pass  # Error accessing this channel
                        
                        # Reset multiplexer (disable all channels)
                        bus.write_byte(mux_addr, 0x00)
                        bus.close()
                        
                    except Exception as e:
                        logger.debug(f"Error scanning multiplexer at 0x{mux_addr:02x}: {e}")
                        
        except ImportError:
            logger.warning("smbus2 not available for LTR-329 discovery")
        except Exception as e:
            logger.debug(f"Error during LTR-329 discovery: {e}")
        
        return discovered_sensors


# Global sensor registry instance
sensor_registry = SensorRegistry()
