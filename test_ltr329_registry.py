#!/usr/bin/env python3
"""Test LTR329 sensor integration with sensor registry."""

import sys
import os

# Add the sensor_hub src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sensor_hub.sensor_registry import sensor_registry


def test_ltr329_registry():
    """Test LTR329 sensor integration with the registry."""
    print("Testing LTR329 sensor registry integration...")
    
    # Check if LTR329 is registered
    available_types = sensor_registry.get_available_types()
    print(f"Available sensor types: {available_types}")
    
    if 'ltr329' in available_types:
        print("✓ LTR329 sensor type is registered")
    else:
        print("✗ LTR329 sensor type is NOT registered")
        return
    
    # Get the LTR329 sensor class
    ltr329_class = sensor_registry.get_sensor_class('ltr329')
    print(f"LTR329 sensor class: {ltr329_class}")
    
    # Create a sensor instance using the registry
    config = {
        'i2c_address': 0x29,
        'bus_number': 1,
        'mock_mode': True
    }
    
    sensor = sensor_registry.create_sensor('ltr329', 'test_registry_ltr329', config)
    if sensor:
        print("✓ Successfully created LTR329 sensor via registry")
        
        # Test the sensor
        print(f"Sensor type: {sensor.get_sensor_type()}")
        print(f"Sensor available: {sensor.is_available()}")
        
        # Take a reading
        reading = sensor.read()
        print(f"Sample reading: {reading}")
        
    else:
        print("✗ Failed to create LTR329 sensor via registry")
    
    # Test discovery for LTR329 (will be mock since no hardware)
    print("\nTesting LTR329 discovery...")
    discovered = sensor_registry._discover_ltr329()
    print(f"Discovered LTR329 sensors: {len(discovered)}")
    for sensor_info in discovered:
        print(f"  - {sensor_info}")


if __name__ == "__main__":
    test_ltr329_registry()