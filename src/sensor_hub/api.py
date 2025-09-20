"""API blueprint for sensor data endpoints."""

from flask import Blueprint, jsonify, request
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import logging

from sensor_hub.database import db
from sensor_hub.models import SensorReading, Sensor, SystemStatus

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/sensors', methods=['GET'])
def get_sensors():
    """Get all registered sensors."""
    try:
        sensors = Sensor.query.all()
        return jsonify({
            'sensors': [sensor.to_dict() for sensor in sensors],
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Error fetching sensors: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@api_bp.route('/sensors/<sensor_id>', methods=['GET'])
def get_sensor(sensor_id: str):
    """Get a specific sensor by ID."""
    try:
        sensor = Sensor.query.filter_by(id=sensor_id).first()
        if not sensor:
            return jsonify({
                'error': 'Sensor not found',
                'status': 'error'
            }), 404
        
        # Get sensor data and include latest reading
        sensor_data = sensor.to_dict()
        latest_reading = sensor.get_latest_reading()
        if latest_reading:
            sensor_data['latest_reading'] = latest_reading.to_dict()
        
        return jsonify({
            'sensor': sensor_data,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Error fetching sensor {sensor_id}: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@api_bp.route('/sensors/<sensor_id>/readings', methods=['GET'])
def get_sensor_readings(sensor_id: str):
    """Get readings for a specific sensor."""
    try:
        # Parse query parameters
        hours = request.args.get('hours', default=24, type=int)
        limit = request.args.get('limit', default=1000, type=int)
        
        # Validate parameters
        if hours < 1 or hours > 168:  # Max 1 week
            hours = 24
        if limit < 1 or limit > 10000:
            limit = 1000
        
        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        # Query readings
        query = SensorReading.query.filter(
            SensorReading.sensor_id == sensor_id,
            SensorReading.timestamp >= start_time,
            SensorReading.timestamp <= end_time
        ).order_by(SensorReading.timestamp.desc()).limit(limit)
        
        readings = query.all()
        
        return jsonify({
            'readings': [reading.to_dict() for reading in readings],
            'sensor_id': sensor_id,
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'hours': hours
            },
            'count': len(readings),
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error fetching readings for sensor {sensor_id}: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@api_bp.route('/readings', methods=['GET'])
def get_all_readings():
    """Get recent readings from all sensors."""
    try:
        hours = request.args.get('hours', default=1, type=int)
        limit = request.args.get('limit', default=100, type=int)
        
        # Validate parameters
        if hours < 1 or hours > 24:
            hours = 1
        if limit < 1 or limit > 1000:
            limit = 100
        
        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        # Query recent readings
        readings = SensorReading.query.filter(
            SensorReading.timestamp >= start_time
        ).order_by(
            SensorReading.timestamp.desc()
        ).limit(limit).all()
        
        return jsonify({
            'readings': [reading.to_dict() for reading in readings],
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'hours': hours
            },
            'count': len(readings),
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error fetching all readings: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@api_bp.route('/status', methods=['GET'])
def get_system_status():
    """Get current system status."""
    try:
        # Get latest system status
        system_status = SystemStatus.query.order_by(
            SystemStatus.timestamp.desc()
        ).first()
        
        # Get sensor summary
        sensors = Sensor.query.all()
        sensor_summary = {
            'total': len(sensors),
            'active': len([s for s in sensors if s.status == 'active']),
            'error': len([s for s in sensors if s.status == 'error']),
            'unavailable': len([s for s in sensors if s.status == 'unavailable'])
        }
        
        # Get recent readings count
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_readings = SensorReading.query.filter(
            SensorReading.timestamp >= one_hour_ago
        ).count()
        
        response = {
            'system_status': system_status.to_dict() if system_status else None,
            'sensor_summary': sensor_summary,
            'recent_readings': recent_readings,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'success'
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error fetching system status: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@api_bp.route('/readings', methods=['POST'])
def create_reading():
    """Create a new sensor reading."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'No data provided',
                'status': 'error'
            }), 400
        
        # Validate required fields
        required_fields = ['sensor_id', 'sensor_type', 'data']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {missing_fields}',
                'status': 'error'
            }), 400
        
        # Create reading
        reading = SensorReading(
            sensor_id=data['sensor_id'],
            sensor_type=data['sensor_type'],
            data=data['data'],
            timestamp=datetime.now(timezone.utc),
            status=data.get('status', 'active')
        )
        
        db.session.add(reading)
        db.session.commit()
        
        return jsonify({
            'reading': reading.to_dict(),
            'status': 'success'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating reading: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@api_bp.errorhandler(404)
def api_not_found(error):
    """Handle 404 errors for API routes."""
    return jsonify({
        'error': 'Endpoint not found',
        'status': 'error'
    }), 404


@api_bp.errorhandler(500)
def api_internal_error(error):
    """Handle 500 errors for API routes."""
    return jsonify({
        'error': 'Internal server error',
        'status': 'error'
    }), 500
