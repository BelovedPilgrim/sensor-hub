"""Sensor Hub Flask Application."""

from flask import Flask
from flask_cors import CORS

from sensor_hub.database import db, migrate
from sensor_hub.config import Config


def create_app(config_class=Config):
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    # Register blueprints
    from sensor_hub.routes import main_bp
    from sensor_hub.api import api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # Register CLI commands
    from sensor_hub.cli import (
        init_db_command,
        discover_sensors_command,
        test_sensors_command,
        status_command,
        start_scheduler_command
    )
    app.cli.add_command(init_db_command)
    app.cli.add_command(discover_sensors_command)
    app.cli.add_command(test_sensors_command)
    app.cli.add_command(status_command)
    app.cli.add_command(start_scheduler_command)

    return app


# Import models to ensure they're registered with SQLAlchemy
from sensor_hub import models  # noqa: F401, E402
