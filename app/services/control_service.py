import logging
import subprocess
from typing import Any, Dict

from flask import current_app

from .. import cronblock

logger = logging.getLogger(__name__)

VALID_ACTIONS = {"play", "pause", "resume", "volume", "connect", "disconnect"}
VALID_SERVICES = {"spotify", "applemusic"}


def _get_script_path() -> str:
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    manager = cronblock.CronManager(app_support_dir)
    return manager._get_aircron_script_path()


def _run_script(zone: str, action: str, arg1: str, service: str) -> None:
    script = _get_script_path()
    cmd = [script, zone, action, arg1 or "", "", service]
    logger.info(f"[control_service] Running: {cmd}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Control command failed")


def run_control_action(data: Dict[str, Any]) -> Dict[str, Any]:
    action = data.get("action")
    service = data.get("service", "spotify")
    zone = data.get("zone", "All Speakers")
    args = data.get("args", {}) or {}

    if action not in VALID_ACTIONS:
        raise ValueError("Invalid action")
    if service not in VALID_SERVICES:
        raise ValueError("Invalid service")
    if not zone or not isinstance(zone, str):
        raise ValueError("Zone is required")

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
