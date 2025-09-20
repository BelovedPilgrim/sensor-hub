"""Centralized logging configuration for Sensor Hub."""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional


class SensorHubFormatter(logging.Formatter):
    """Custom formatter for Sensor Hub with colored output for console."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green  
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def __init__(self, use_colors: bool = False):
        """Initialize formatter with optional color support."""
        self.use_colors = use_colors
        super().__init__()
    
    def format(self, record):
        """Format log record with optional colors."""
        # Add sensor context if available
        sensor_id = getattr(record, 'sensor_id', None)
        sensor_type = getattr(record, 'sensor_type', None)
        
        # Build the log message format
        timestamp = self.formatTime(record, '%Y-%m-%d %H:%M:%S')
        level = record.levelname
        logger_name = record.name
        message = record.getMessage()
        
        # Add exception info if present
        if record.exc_info:
            message += '\n' + self.formatException(record.exc_info)
        
        # Build context info
        context_parts = []
        if sensor_id:
            context_parts.append(f"sensor:{sensor_id}")
        if sensor_type:
            context_parts.append(f"type:{sensor_type}")
        
        context = f"[{', '.join(context_parts)}]" if context_parts else ""
        
        # Apply colors for console output
        if self.use_colors and sys.stderr.isatty():
            color = self.COLORS.get(level, '')
            reset = self.COLORS['RESET']
            level = f"{color}{level}{reset}"
        
        # Format final message
        if context:
            return f"{timestamp} | {level:8} | {logger_name:25} | {context:20} | {message}"
        else:
            return f"{timestamp} | {level:8} | {logger_name:25} | {message}"


def setup_logging(
    log_level: str = 'INFO',
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
    enable_colors: bool = True
) -> None:
    """
    Configure comprehensive logging for Sensor Hub.
    
    Args:
        log_level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        log_file: Path to log file (None to disable file logging)
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        enable_console: Whether to log to console
        enable_colors: Whether to use colors in console output
    """
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set root logger level
    root_logger.setLevel(numeric_level)
    
    # Create handlers
    handlers = []
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(SensorHubFormatter(use_colors=enable_colors))
        handlers.append(console_handler)
    
    # File handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(SensorHubFormatter(use_colors=False))
        handlers.append(file_handler)
    
    # Add handlers to root logger
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Configure specific loggers with appropriate levels
    configure_module_loggers(numeric_level)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, File: {log_file}")


def configure_module_loggers(base_level: int) -> None:
    """Configure specific loggers for different modules."""
    
    # Sensor Hub modules - use base level
    sensor_hub_modules = [
        'sensor_hub',
        'sensor_hub.sensors',
        'sensor_hub.routes',
        'sensor_hub.api',
        'sensor_hub.cli',
        'sensor_hub.database',
        'sensor_hub.sensor_registry',
        'sensor_hub.discovery_service'
    ]
    
    for module in sensor_hub_modules:
        logging.getLogger(module).setLevel(base_level)
    
    # Third-party libraries - set to WARNING to reduce noise
    external_modules = [
        'werkzeug',
        'flask',
        'urllib3',
        'requests',
        'sqlalchemy',
        'alembic'
    ]
    
    for module in external_modules:
        logging.getLogger(module).setLevel(logging.WARNING)
    
    # Hardware-related modules - keep at INFO for troubleshooting
    hardware_modules = [
        'adafruit_bme280',
        'adafruit_ltr329_ltr303',
        'board',
        'busio'
    ]
    
    for module in hardware_modules:
        logging.getLogger(module).setLevel(max(base_level, logging.INFO))


def get_sensor_logger(name: str, sensor_id: str = None, sensor_type: str = None):
    """
    Get a logger with sensor context.
    
    Args:
        name: Logger name (usually __name__)
        sensor_id: Optional sensor ID for context
        sensor_type: Optional sensor type for context
        
    Returns:
        Logger with sensor context
    """
    logger = logging.getLogger(name)
    
    # Create a wrapper that adds sensor context to log records
    class SensorLoggerAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            extra = kwargs.get('extra', {})
            if sensor_id:
                extra['sensor_id'] = sensor_id
            if sensor_type:
                extra['sensor_type'] = sensor_type
            kwargs['extra'] = extra
            return msg, kwargs
    
    return SensorLoggerAdapter(logger, {})


def log_sensor_event(logger, level: str, sensor_id: str, sensor_type: str, 
                    event: str, details: str = None, **kwargs):
    """
    Log a sensor-specific event with structured format.
    
    Args:
        logger: Logger instance
        level: Log level ('info', 'warning', 'error', etc.)
        sensor_id: Sensor identifier
        sensor_type: Type of sensor
        event: Event description
        details: Optional additional details
        **kwargs: Additional context data
    """
    log_func = getattr(logger, level.lower())
    
    message = f"{event}"
    if details:
        message += f" - {details}"
    
    # Add context data
    if kwargs:
        context_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        message += f" ({context_str})"
    
    log_func(message, extra={
        'sensor_id': sensor_id,
        'sensor_type': sensor_type
    })


# Convenience functions for common logging patterns
def log_sensor_init(logger, sensor_id: str, sensor_type: str, success: bool = True, error: str = None):
    """Log sensor initialization."""
    if success:
        log_sensor_event(logger, 'info', sensor_id, sensor_type, 
                        "Sensor initialized successfully")
    else:
        log_sensor_event(logger, 'error', sensor_id, sensor_type, 
                        "Sensor initialization failed", error)


def log_sensor_reading(logger, sensor_id: str, sensor_type: str, data: dict):
    """Log successful sensor reading."""
    # Format data for logging (avoid sensitive info)
    formatted_data = {k: f"{v:.2f}" if isinstance(v, float) else str(v) 
                     for k, v in data.items() if v is not None}
    
    log_sensor_event(logger, 'debug', sensor_id, sensor_type, 
                    "Reading captured", data=formatted_data)


def log_sensor_error(logger, sensor_id: str, sensor_type: str, error: Exception):
    """Log sensor error with exception details."""
    log_sensor_event(logger, 'error', sensor_id, sensor_type, 
                    "Sensor error occurred", str(error), 
                    exception_type=type(error).__name__)