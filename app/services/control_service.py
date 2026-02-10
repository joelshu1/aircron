import logging
import re
import shlex
import subprocess
from typing import Any, Dict

from flask import current_app

from .. import cronblock

logger = logging.getLogger(__name__)

VALID_ACTIONS = {"play", "pause", "resume", "volume", "connect", "disconnect"}
VALID_SERVICES = {"spotify", "applemusic"}
MAX_ZONE_LENGTH = 255
ZONE_PATTERN = re.compile(r"^[\w\s:,()\-]+$")


def _validate_zone(zone: str) -> str:
    """Validate zone name for safety.

    Args:
        zone: The zone name to validate

    Returns:
        The validated and stripped zone name

    Raises:
        ValueError: If zone is invalid
    """
    if not zone or not isinstance(zone, str):
        raise ValueError("Zone is required")
    zone = zone.strip()
    if len(zone) > MAX_ZONE_LENGTH:
        raise ValueError(f"Zone name too long (max {MAX_ZONE_LENGTH} characters)")
    # Allow letters, numbers, spaces, commas, colons, parentheses, hyphens
    if not ZONE_PATTERN.match(zone):
        raise ValueError("Zone contains invalid characters")
    return zone


def _get_script_path() -> str:
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    manager = cronblock.CronManager(app_support_dir)
    return manager._get_aircron_script_path()


def _run_script(zone: str, action: str, arg1: str, service: str) -> None:
    """Run the aircron_run.sh script with sanitized arguments.

    Args:
        zone: The speaker zone (will be validated and sanitized)
        action: The action to perform
        arg1: First argument (e.g., playlist URI or volume)
        service: Music service (spotify or applemusic)

    Raises:
        RuntimeError: If the script fails
        ValueError: If zone validation fails
    """
    # Validate and sanitize zone
    zone = _validate_zone(zone)

    script = _get_script_path()
    # Use shlex.quote to properly escape all string arguments for shell safety
    cmd = [script, shlex.quote(zone), shlex.quote(action), shlex.quote(arg1 or ""), "", shlex.quote(service)]
    logger.info(f"[control_service] Running: {cmd}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Control command failed")


def run_control_action(data: Dict[str, Any]) -> Dict[str, Any]:
    """Run a control action with validation.

    Args:
        data: Dictionary containing action, service, zone, and args

    Returns:
        Dictionary with ok status

    Raises:
        ValueError: If validation fails
        RuntimeError: If script execution fails
    """
    action = data.get("action")
    service = data.get("service", "spotify")
    zone = data.get("zone", "All Speakers")
    args = data.get("args", {}) or {}

    if action not in VALID_ACTIONS:
        raise ValueError("Invalid action")
    if service not in VALID_SERVICES:
        raise ValueError("Invalid service")

    # Validate zone early (will be validated again in _run_script for defense in depth)
    zone = _validate_zone(zone)

    arg1 = ""
    if action == "play":
        if service == "spotify":
            arg1 = args.get("uri", "")
        else:
            arg1 = args.get("playlist", "")
        if not arg1:
            raise ValueError("Play action requires a playlist/URI")
    elif action == "volume":
        if "volume" not in args:
            raise ValueError("Volume action requires 'volume'")
        try:
            volume_val = int(args.get("volume"))
        except (TypeError, ValueError):
            raise ValueError("Volume must be an integer 0-100")
        if volume_val < 0 or volume_val > 100:
            raise ValueError("Volume must be between 0 and 100")
        arg1 = str(volume_val)

    if action == "connect":
        _run_script(zone, "disconnect", "", service)

    _run_script(zone, action, arg1, service)
    return {"ok": True}
