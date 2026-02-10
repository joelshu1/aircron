"""AirCron Flask application factory."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask

from .api import api_bp
from .views import views_bp


def _validate_app_support_dir(app_support_dir: Path) -> Path:
    """Validate and resolve the application support directory.

    Args:
        app_support_dir: Path to validate

    Returns:
        The resolved, absolute path

    Raises:
        ValueError: If the path is invalid or unsafe
    """
    try:
        resolved = app_support_dir.resolve()
    except Exception as e:
        raise ValueError(f"Invalid APP_SUPPORT_DIR path: {e}")

    # Ensure the path is within the user's home directory or a safe system location
    home_dir = Path.home()
    safe_parents = [home_dir, Path("/usr/local"), Path("/opt")]

    is_safe = False
    for safe_parent in safe_parents:
        try:
            resolved.relative_to(safe_parent)
            is_safe = True
            break
        except ValueError:
            continue

    if not is_safe:
        raise ValueError(
            f"APP_SUPPORT_DIR must be within user home directory or safe system location. Got: {resolved}"
        )

    return resolved


def create_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    """Create and configure Flask application."""
    # Get the directory where this module is located
    app_dir = Path(__file__).parent.parent

    app = Flask(
        __name__, template_folder=str(app_dir / "templates"), static_folder=str(app_dir / "static")
    )

    # Configure app
    # SECRET_KEY is required by Flask but not used by this app (no sessions/cookies)
    # Set a default to avoid Flask warnings
    app.config.update(
        SECRET_KEY="dev-only-not-for-production",
        JSON_SORT_KEYS=False,
    )
    if config:
        app.config.update(config)

    # Setup application support directory
    app_support_dir = app.config.get("APP_SUPPORT_DIR")
    if not app_support_dir:
        app_support_dir = Path.home() / "Library" / "Application Support" / "AirCron"
    else:
        app_support_dir = Path(app_support_dir)

    # Validate the path is safe
    app_support_dir = _validate_app_support_dir(app_support_dir)

    # Create directory if it doesn't exist
    app_support_dir.mkdir(parents=True, exist_ok=True)
    app.config["APP_SUPPORT_DIR"] = app_support_dir

    # Initialize global managers with app context
    with app.app_context():
        from .cronblock import cron_manager

        if cron_manager is None:
            import app.cronblock as cronblock_module

            from .cronblock import CronManager

            cronblock_module.cron_manager = CronManager(app_support_dir)

    # Register blueprints
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    # Setup logging
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    return app
