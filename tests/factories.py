"""Test data factories for creating realistic test data."""

import factory
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from sensor_hub.models import Sensor, SensorReading


class SensorFactory(factory.Factory):
    """Factory for creating Sensor test instances."""
    
    class Meta:
        model = Sensor
    
    id = factory.Sequence(lambda n: f"test_sensor_{n:03d}")
    name = factory.Faker("word")
    sensor_type = factory.Iterator(["bme280", "ltr329"])
    description = factory.Faker("sentence", nb_words=10)
    i2c_address = factory.Iterator([0x77, 0x29, 0x48, 0x23])
    bus_number = 1
    poll_interval = factory.Iterator([15, 30, 60, 120])
    enabled = True
    location = factory.Faker("city")
    calibration_data = factory.LazyFunction(
        lambda: {"offset": factory.Faker("pyfloat", min_value=-5, max_value=5).generate()}
    )


class BME280SensorFactory(SensorFactory):
    """Factory for BME280 specific sensors."""
    
    sensor_type = "bme280"
    i2c_address = 0x77
    description = "BME280 Temperature, Humidity, and Pressure Sensor"
    calibration_data = factory.LazyFunction(
        lambda: {
            "offset_temp": factory.Faker("pyfloat", min_value=-2, max_value=2).generate(),
            "offset_humidity": factory.Faker("pyfloat", min_value=-5, max_value=5).generate(),
            "offset_pressure": factory.Faker("pyfloat", min_value=-10, max_value=10).generate()
        }
    )


class LTR329SensorFactory(SensorFactory):
    """Factory for LTR329 specific sensors."""
    
    sensor_type = "ltr329"
    i2c_address = 0x29
    description = "LTR329 Light Sensor"
    calibration_data = factory.LazyFunction(
        lambda: {
            "multiplexer_address": 0x70,
            "multiplexer_channel": factory.Faker("pyint", min_value=0, max_value=7).generate(),
            "gain": factory.Iterator([1, 8, 48, 96])
        }
    )


class SensorReadingFactory(factory.Factory):
    """Factory for creating SensorReading test instances."""
    
    class Meta:
        model = SensorReading
    
    sensor_id = factory.SubFactory(SensorFactory)
    sensor_type = factory.LazyAttribute(lambda obj: obj.sensor_id.sensor_type)
    timestamp = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    status = factory.Iterator(["active", "warning", "error"])


class BME280ReadingFactory(SensorReadingFactory):
    """Factory for BME280 sensor readings."""
    
    sensor_type = "bme280"
    data = factory.LazyFunction(
        lambda: {
            "temperature": factory.Faker("pyfloat", min_value=-40, max_value=85).generate(),
            "humidity": factory.Faker("pyfloat", min_value=0, max_value=100).generate(),
            "pressure": factory.Faker("pyfloat", min_value=300, max_value=1100).generate()
        }
    )


class LTR329ReadingFactory(SensorReadingFactory):
    """Factory for LTR329 sensor readings."""
    
    sensor_type = "ltr329"
    data = factory.LazyFunction(
        lambda: {
            "ch0_light": factory.Faker("pyint", min_value=0, max_value=65535).generate(),
            "ir_light": factory.Faker("pyint", min_value=0, max_value=65535).generate()
        }
    )


def create_realistic_bme280_data(temperature_base: float = 20.0,
                                humidity_base: float = 50.0,
                                pressure_base: float = 1013.25) -> Dict[str, float]:
    """Create realistic BME280 sensor data with natural variations."""
    import random
    
    # Add realistic variations
    temp_variation = random.uniform(-2.0, 2.0)
    humidity_variation = random.uniform(-5.0, 5.0)
    pressure_variation = random.uniform(-10.0, 10.0)
    
    return {
        "temperature": round(temperature_base + temp_variation, 2),
        "humidity": max(0, min(100, round(humidity_base + humidity_variation, 2))),
        "pressure": round(pressure_base + pressure_variation, 2)
    }


def create_realistic_ltr329_data(indoor: bool = True) -> Dict[str, int]:
    """Create realistic LTR329 sensor data for indoor/outdoor conditions."""
    import random
    
    if indoor:
        # Indoor lighting conditions
        ch0_base = random.randint(10, 500)
        ir_ratio = random.uniform(0.3, 0.7)
    else:
        # Outdoor lighting conditions
        ch0_base = random.randint(1000, 65000)
        ir_ratio = random.uniform(0.1, 0.5)
    
    ir_light = int(ch0_base * ir_ratio)
    
    return {
        "ch0_light": ch0_base,
        "ir_light": ir_light
    }


def create_sensor_time_series(sensor_id: str, 
                             sensor_type: str,
                             start_time: datetime,
                             duration_hours: int = 24,
                             interval_minutes: int = 30) -> List[Dict[str, Any]]:
    """Create a time series of sensor readings."""
    readings = []
    current_time = start_time
    end_time = start_time + timedelta(hours=duration_hours)
    interval = timedelta(minutes=interval_minutes)
    
    # Base values for realistic progression
    if sensor_type == "bme280":
        temp_base = 20.0
        humidity_base = 50.0
        pressure_base = 1013.25
    
    while current_time <= end_time:
        if sensor_type == "bme280":
            # Simulate daily temperature/humidity cycle
            hour_of_day = current_time.hour
            temp_cycle = 5.0 * (0.5 - abs(hour_of_day - 14) / 24)  # Peak at 2 PM
            humidity_cycle = -temp_cycle * 2  # Inverse relationship
            
            data = create_realistic_bme280_data(
                temp_base + temp_cycle,
                humidity_base + humidity_cycle,
                pressure_base
            )
        elif sensor_type == "ltr329":
            # Simulate day/night cycle
            hour_of_day = current_time.hour
            is_daylight = 6 <= hour_of_day <= 20
            data = create_realistic_ltr329_data(indoor=not is_daylight)
        else:
            data = {"value": 0}
        
        readings.append({
            "sensor_id": sensor_id,
            "sensor_type": sensor_type,
            "timestamp": current_time,
            "data": data,
            "status": "active"
        })
        
        current_time += interval
    
    return readings


def create_test_scenario_data(scenario: str) -> Dict[str, Any]:
    """Create test data for specific scenarios."""
    scenarios = {
        "normal_operation": {
            "sensors": [
                {
                    "id": "bme280_normal",
                    "sensor_type": "bme280",
                    "data": create_realistic_bme280_data()
                },
                {
                    "id": "ltr329_normal", 
                    "sensor_type": "ltr329",
                    "data": create_realistic_ltr329_data()
                }
            ]
        },
        "extreme_conditions": {
            "sensors": [
                {
                    "id": "bme280_extreme",
                    "sensor_type": "bme280",
                    "data": {
                        "temperature": -30.0,  # Extreme cold
                        "humidity": 5.0,       # Very dry
                        "pressure": 850.0      # Low pressure
                    }
                },
                {
                    "id": "ltr329_extreme",
                    "sensor_type": "ltr329", 
                    "data": {
                        "ch0_light": 65535,    # Maximum light
                        "ir_light": 32767      # High IR
                    }
                }
            ]
        },
        "sensor_errors": {
            "sensors": [
                {
                    "id": "bme280_error",
                    "sensor_type": "bme280",
                    "data": {},
                    "status": "error"
                },
                {
                    "id": "ltr329_warning",
                    "sensor_type": "ltr329",
                    "data": {
                        "ch0_light": 0,
                        "ir_light": 0
                    },
                    "status": "warning"
                }
            ]
        }
    }
    
    return scenarios.get(scenario, scenarios["normal_operation"])


class TestDataManager:
    """Manager class for creating and managing test data."""
    
    def __init__(self, db_session):
        self.db_session = db_session
        self.created_objects = []
    
    def create_sensor(self, **kwargs) -> Sensor:
        """Create a sensor with the given parameters."""
        sensor = SensorFactory(**kwargs)
        self.db_session.add(sensor)
        self.created_objects.append(sensor)
        return sensor
    
    def create_bme280_sensor(self, **kwargs) -> Sensor:
        """Create a BME280 sensor."""
        sensor = BME280SensorFactory(**kwargs)
        self.db_session.add(sensor)
        self.created_objects.append(sensor)
        return sensor
    
    def create_ltr329_sensor(self, **kwargs) -> Sensor:
        """Create an LTR329 sensor."""
        sensor = LTR329SensorFactory(**kwargs)
        self.db_session.add(sensor)
        self.created_objects.append(sensor)
        return sensor
    
    def create_reading(self, sensor: Sensor, **kwargs) -> SensorReading:
        """Create a reading for the given sensor."""
        reading_data = kwargs.copy()
        reading_data['sensor_id'] = sensor.id
        reading_data['sensor_type'] = sensor.sensor_type
        
        if sensor.sensor_type == "bme280":
            reading = BME280ReadingFactory(**reading_data)
        elif sensor.sensor_type == "ltr329":
            reading = LTR329ReadingFactory(**reading_data)
        else:
            reading = SensorReadingFactory(**reading_data)
        
        self.db_session.add(reading)
        self.created_objects.append(reading)
        return reading
    
    def create_time_series(self, sensor: Sensor, hours: int = 24) -> List[SensorReading]:
        """Create a time series of readings for a sensor."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        readings_data = create_sensor_time_series(
            sensor.id, sensor.sensor_type, start_time, hours
        )
        
        readings = []
        for reading_data in readings_data:
            reading = SensorReading(**reading_data)
            self.db_session.add(reading)
            self.created_objects.append(reading)
            readings.append(reading)
        
        return readings
    
    def commit(self):
        """Commit all changes to the database."""
        self.db_session.commit()
    
    def cleanup(self):
        """Clean up all created test objects."""
        for obj in reversed(self.created_objects):
            try:
                self.db_session.delete(obj)
            except:
                pass
        self.created_objects.clear()
        self.db_session.commit()