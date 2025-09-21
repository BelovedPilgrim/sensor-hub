"""Main web interface routes."""

from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timezone, timedelta
import logging
import time

from sensor_hub.models import Sensor, SensorReading, SystemStatus
from sensor_hub.sensor_registry import SensorRegistry

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Main dashboard page."""
    try:
        # Get all sensors
        sensors = Sensor.query.all()
        
        # Get real-time readings for each sensor (like the API does)
        sensor_registry = SensorRegistry()
        recent_readings = {}
        
        for sensor in sensors:
            try:
                config = {'i2c_address': sensor.i2c_address}
                if sensor.calibration_data:
                    config.update(sensor.calibration_data)
                
                sensor_class = sensor_registry.get_sensor_class(sensor.sensor_type)
                if sensor_class:
                    sensor_instance = sensor_class(sensor.id, config)
                    reading = sensor_instance.read()
                    
                    if reading and 'error' not in reading:
                        # Handle different sensor response formats
                        if 'data' in reading:
                            # BME280 format: nested data structure
                            sensor_data = reading['data']
                            timestamp = reading.get('timestamp')
                            if isinstance(timestamp, datetime):
                                timestamp = timestamp.timestamp()
                        else:
                            # LTR329/MPU6050 format: flat structure
                            sensor_data = reading
                            timestamp = reading.get('timestamp', datetime.now(timezone.utc).timestamp())
                        
                        recent_readings[sensor.id] = {
                            'sensor_id': sensor.id,
                            'sensor_type': sensor.sensor_type,
                            'data': sensor_data,
                            'timestamp': timestamp,
                            'status': 'active'
                        }
                    else:
                        recent_readings[sensor.id] = {
                            'sensor_id': sensor.id,
                            'sensor_type': sensor.sensor_type,
                            'data': {},
                            'timestamp': datetime.now(timezone.utc).timestamp(),
                            'status': 'error'
                        }
                        
            except Exception as e:
                logger.error(f"Error reading sensor {sensor.id}: {e}")
                recent_readings[sensor.id] = {
                    'sensor_id': sensor.id,
                    'sensor_type': sensor.sensor_type,
                    'data': {},
                    'timestamp': datetime.now(timezone.utc).timestamp(),
                    'status': 'error'
                }
        
        # Calculate real-time status counts
        status_counts = {
            'total': len(sensors),
            'active': 0,
            'error': 0,
            'unavailable': 0
        }
        
        for sensor in sensors:
            if sensor.id in recent_readings:
                status = recent_readings[sensor.id]['status']
            else:
                status = sensor.status
            
            if status == 'active':
                status_counts['active'] += 1
            elif status == 'error':
                status_counts['error'] += 1
            elif status == 'unavailable':
                status_counts['unavailable'] += 1
        
        return render_template(
            'index.html',
            sensors=sensors,
            recent_readings=recent_readings,
            status_counts=status_counts,
            page_title='Sensor Hub Dashboard'
        )
        
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template(
            'error.html',
            error="Failed to load dashboard",
            page_title='Error'
        ), 500


@main_bp.route('/sensor/<sensor_id>')
def sensor_detail(sensor_id: str):
    """Detailed view for a specific sensor."""
    try:
        # Get sensor info
        sensor = Sensor.query.filter_by(id=sensor_id).first()
        if not sensor:
            return render_template(
                'error.html',
                error=f"Sensor '{sensor_id}' not found",
                page_title='Sensor Not Found'
            ), 404
        
        # Get recent readings
        hours = request.args.get('hours', default=24, type=int)
        if hours < 1 or hours > 168:  # Max 1 week
            hours = 24
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        readings = SensorReading.query.filter(
            SensorReading.sensor_id == sensor_id,
            SensorReading.timestamp >= start_time
        ).order_by(
            SensorReading.timestamp.desc()
        ).limit(1000).all()
        
        # Convert readings to dictionaries for JSON serialization in JavaScript
        readings_json = [reading.to_dict() for reading in readings]
        
        return render_template(
            'sensor_detail.html',
            sensor=sensor,
            readings=readings,
            readings_json=readings_json,
            hours=hours,
            page_title=f'Sensor: {sensor.name or sensor_id}'
        )
        
    except Exception as e:
        logger.error(f"Error loading sensor detail for {sensor_id}: {e}")
        return render_template(
            'error.html',
            error="Failed to load sensor details",
            page_title='Error'
        ), 500


@main_bp.route('/data')
def data_view():
    """Data exploration and export page."""
    try:
        # Get all sensors for filter options
        sensors = Sensor.query.all()
        
        # Get query parameters
        sensor_filter = request.args.get('sensor')
        hours = request.args.get('hours', default=24, type=int)
        
        if hours < 1 or hours > 168:
            hours = 24
        
        # Build query
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        query = SensorReading.query.filter(
            SensorReading.timestamp >= start_time
        )
        
        if sensor_filter:
            query = query.filter(SensorReading.sensor_id == sensor_filter)
        
        readings = query.order_by(
            SensorReading.timestamp.desc()
        ).limit(5000).all()
        
        return render_template(
            'data.html',
            sensors=sensors,
            readings=readings,
            selected_sensor=sensor_filter,
            hours=hours,
            page_title='Data Explorer'
        )
        
    except Exception as e:
        logger.error(f"Error loading data view: {e}")
        return render_template(
            'error.html',
            error="Failed to load data view",
            page_title='Error'
        ), 500


@main_bp.route('/status')
def system_status():
    """System status and health page."""
    try:
        # Get latest system status
        latest_status = SystemStatus.query.order_by(
            SystemStatus.timestamp.desc()
        ).first()
        
        # Get sensor statistics
        sensors = Sensor.query.all()
        sensor_stats = {
            'total': len(sensors),
            'active': len([s for s in sensors if s.status == 'active']),
            'error': len([s for s in sensors if s.status == 'error']),
            'unavailable': len([s for s in sensors if s.status == 'unavailable'])
        }
        
        # Get reading statistics for the last 24 hours
        one_day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_readings = SensorReading.query.filter(
            SensorReading.timestamp >= one_day_ago
        ).count()
        
        # Get readings per sensor
        readings_per_sensor = {}
        for sensor in sensors:
            count = SensorReading.query.filter(
                SensorReading.sensor_id == sensor.id,
                SensorReading.timestamp >= one_day_ago
            ).count()
            readings_per_sensor[sensor.id] = count
        
        return render_template(
            'status.html',
            system_status=latest_status,
            sensor_stats=sensor_stats,
            recent_readings=recent_readings,
            readings_per_sensor=readings_per_sensor,
            sensors=sensors,
            page_title='System Status'
        )
        
    except Exception as e:
        logger.error(f"Error loading system status: {e}")
        return render_template(
            'error.html',
            error="Failed to load system status",
            page_title='Error'
        ), 500


@main_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template(
        'error.html',
        error="Page not found",
        page_title='Not Found'
    ), 404


@main_bp.route('/dashboard')
def dashboard():
    """Data visualization dashboard."""
    return render_template(
        'dashboard.html',
        page_title='Sensor Dashboard'
    )


@main_bp.route('/api/sensors/current')
def api_current_sensors():
    """API endpoint for current sensor data."""
    try:
        sensors = Sensor.query.all()
        sensor_registry = SensorRegistry()
        
        result = {
            'sensors': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        for sensor in sensors:
            sensor_data = {
                'sensor_id': sensor.id,
                'sensor_type': sensor.sensor_type,
                'name': sensor.name,
                'status': sensor.status,
                'location': sensor.location,
                'latest_reading': None
            }
            
            # Get real-time reading
            try:
                config = {'i2c_address': sensor.i2c_address}
                if sensor.calibration_data:
                    config.update(sensor.calibration_data)
                
                sensor_class = sensor_registry.get_sensor_class(sensor.sensor_type)
                if sensor_class:
                    sensor_instance = sensor_class(sensor.id, config)
                    reading = sensor_instance.read()
                    
                    if reading and 'error' not in reading:
                        sensor_data['latest_reading'] = reading
                        sensor_data['status'] = 'active'
                    else:
                        sensor_data['status'] = 'error'
                        
            except Exception as e:
                logger.error(f"Error reading sensor {sensor.id}: {e}")
                sensor_data['status'] = 'error'
            
            result['sensors'].append(sensor_data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in API endpoint: {e}")
        return jsonify({'error': str(e)}), 500


@main_bp.route('/api/sensors/<sensor_id>/history')
def api_sensor_history(sensor_id: str):
    """API endpoint for sensor historical data."""
    try:
        # Get time range from query parameters
        hours = request.args.get('hours', 24, type=int)
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Get historical readings
        readings = SensorReading.query.filter(
            SensorReading.sensor_id == sensor_id,
            SensorReading.timestamp >= start_time
        ).order_by(SensorReading.timestamp.desc()).limit(100).all()
        
        result = {
            'sensor_id': sensor_id,
            'readings': [reading.to_dict() for reading in reversed(readings)],
            'count': len(readings),
            'time_range_hours': hours
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting sensor history: {e}")
        return jsonify({'error': str(e)}), 500


@main_bp.route('/api/system/stats')
def api_system_stats():
    """API endpoint for system statistics."""
    try:
        sensors = Sensor.query.all()
        total_sensors = len(sensors)
        active_sensors = len([s for s in sensors if s.status == 'active'])
        
        # Get recent reading count
        last_hour = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_readings = SensorReading.query.filter(
            SensorReading.timestamp >= last_hour
        ).count()
        
        # Get system status
        latest_status = SystemStatus.query.order_by(
            SystemStatus.timestamp.desc()
        ).first()
        
        result = {
            'total_sensors': total_sensors,
            'active_sensors': active_sensors,
            'error_sensors': total_sensors - active_sensors,
            'recent_readings': recent_readings,
            'system_status': latest_status.to_dict() if latest_status else None,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return jsonify({'error': str(e)}), 500


@main_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template(
        'error.html',
        error="Page not found",
        page_title='Not Found'
    ), 404


@main_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return render_template(
        'error.html',
        error="Internal server error",
        page_title='Server Error'
    ), 500
