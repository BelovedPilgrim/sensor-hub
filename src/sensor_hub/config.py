"""Configuration settings for Sensor Hub."""

import os
from pathlib import Path

basedir = Path(__file__).parent.parent.parent


class Config:
    """Base configuration."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{basedir}/sensor_hub.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
    }
    
    # Sensor settings
    SENSOR_POLL_INTERVAL = int(os.environ.get('SENSOR_POLL_INTERVAL', '30'))  # seconds
    I2C_BUS = int(os.environ.get('I2C_BUS', '1'))
    GPIO_MODE = os.environ.get('GPIO_MODE', 'BCM')
    
    # API settings
    API_RATE_LIMIT = os.environ.get('API_RATE_LIMIT', '100 per hour')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', str(basedir / 'logs' / 'sensor_hub.log'))
    
    # Timezone
    TIMEZONE = os.environ.get('TIMEZONE', 'UTC')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or f'sqlite:///{basedir}/sensor_hub_dev.db'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{basedir}/sensor_hub.db'


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
