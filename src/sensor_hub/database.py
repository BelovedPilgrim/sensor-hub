"""Database initialization and utilities."""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def init_db(app):
    """Initialize database with app context."""
    db.init_app(app)
    migrate.init_app(app, db)


def create_tables():
    """Create all database tables."""
    db.create_all()


def drop_tables():
    """Drop all database tables."""
    db.drop_all()


def reset_db():
    """Reset database by dropping and recreating all tables."""
    drop_tables()
    create_tables()
