#!/usr/bin/env python3
"""Simple test of LTR329 functionality with multiplexer."""

import sys
sys.path.insert(0, 'src')

from sensor_hub.sensors.ltr329 import LTR329Sensor

def test_ltr329():
    """Test LTR329 with actual configuration."""
    config = {
        'i2c_address': 0x29,
        'mux_address': 0x70,
        'mux_channel': 0,
        'mock_mode': False
    }
    
    sensor = LTR329Sensor('test_ltr329', config)
    
    print(f"Sensor status: {sensor.status}")
    print(f"Is available: {sensor.is_available()}")
    
    if sensor.is_available():
        for i in range(3):
            reading = sensor.read()
            print(f"Reading {i+1}: {reading}")
            import time
            time.sleep(1)
    else:
        print("Sensor not available")

if __name__ == "__main__":
    test_ltr329()