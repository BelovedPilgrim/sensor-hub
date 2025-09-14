#!/usr/bin/env python3
"""Test script for LTR329 sensor in mock mode."""

import sys
import os

# Add the sensor_hub src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sensor_hub.sensors.ltr329 import LTR329Sensor


def test_ltr329_mock():
    """Test LTR329 sensor in mock mode."""
    print("Testing LTR329 sensor in mock mode...")
    
    # Create sensor configuration for mock mode
    config = {
        'i2c_address': 0x29,
        'bus_number': 1,
        'mock_mode': True
    }
    
    # Create sensor instance
    sensor = LTR329Sensor('test_ltr329', config)
    
    # Test sensor availability
    print(f"Sensor available: {sensor.is_available()}")
    print(f"Sensor status: {sensor.status}")
    print(f"Sensor type: {sensor.get_sensor_type()}")
    
    # Test sensor info
    info = sensor.get_info()
    print(f"Sensor info: {info}")
    
    # Take a few readings
    print("\nTaking mock readings:")
    for i in range(3):
        reading = sensor.read()
        print(f"Reading {i+1}: {reading}")
    
    print("\nLTR329 mock test completed successfully!")


if __name__ == "__main__":
    test_ltr329_mock()