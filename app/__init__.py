"""AirCron Flask application factory."""

import logging
from pathlib import Path

from flask import Flask

from .api import api_bp
from .views import views_bp


def create_app() -> Flask:
    """Create and configure Flask application."""
    # Get the directory where this module is located
    import os
    app_dir = Path(__file__).parent.parent
    
    app = Flask(
        __name__,
        template_folder=str(app_dir / "templates"),
        static_folder=str(app_dir / "static")
    )
    
    # Configure app
    app.config.update(
        SECRET_KEY="aircron-dev-key",  # Change for production
        JSON_SORT_KEYS=False,
    )
    
    # Setup application support directory
    app_support_dir = Path.home() / "Library" / "Application Support" / "AirCron"
    app_support_dir.mkdir(parents=True, exist_ok=True)
    app.config["APP_SUPPORT_DIR"] = app_support_dir
    
    # Initialize global managers with app context
    with app.app_context():
        from .cronblock import cron_manager
        if cron_manager is None:
            from .cronblock import CronManager
            import app.cronblock as cronblock_module
            cronblock_module.cron_manager = CronManager(app_support_dir)
    
    # Register blueprints
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    
    # Setup logging
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    
    return app 