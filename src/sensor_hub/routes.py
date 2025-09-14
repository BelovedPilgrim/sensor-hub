"""Main web interface routes."""

from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timezone, timedelta
import logging

from sensor_hub.models import Sensor, SensorReading, SystemStatus

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Main dashboard page."""
    try:
        # Get all sensors
        sensors = Sensor.query.all()
        
        # Get recent readings for each sensor
        recent_readings = {}
        for sensor in sensors:
            latest = SensorReading.query.filter_by(
                sensor_id=sensor.id
            ).order_by(
                SensorReading.timestamp.desc()
            ).first()
            
            if latest:
                recent_readings[sensor.id] = latest.to_dict()
        
        return render_template(
            'index.html',
            sensors=sensors,
            recent_readings=recent_readings,
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


@main_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return render_template(
        'error.html',
        error="Internal server error",
        page_title='Server Error'
    ), 500
