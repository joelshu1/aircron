#!/usr/bin/env python3
"""AirCron UI - Flask server entry point (no tray)."""

import logging
import shutil
import threading
import webbrowser
from pathlib import Path

from app import create_app


def setup_logging() -> None:
    """Configure logging to rotate file in ~/Library/Logs/AirCron/."""
    log_dir = Path.home() / "Library" / "Logs" / "AirCron"
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_dir / "aircron.log"), logging.StreamHandler()],
    )


def check_dependencies() -> None:
    """Verify required dependencies are installed."""
    # Check for spotify-cli in common locations
    spotify_locations = [
        Path("/usr/local/bin/spotify"),
        Path("/opt/homebrew/bin/spotify"),
        Path("/usr/bin/spotify"),
    ]

    spotify_found = False
    for spotify_path in spotify_locations:
        if spotify_path.is_file():
            spotify_found = True
            logging.info(f"Found spotify-cli at: {spotify_path}")
            break

    if not spotify_found:
        # Also check if it's in PATH
        if shutil.which("spotify") is not None:
            spotify_found = True
            logging.info(f"Found spotify-cli in PATH: {shutil.which('spotify')}")

    if not spotify_found:
        raise RuntimeError(
            "Install spotify-cli - not found in /usr/local/bin/, /opt/homebrew/bin/, or PATH"
        )

    if shutil.which("crontab") is None:
        raise RuntimeError("cron not found in PATH")


def main() -> None:
    """Main entry point (no tray)."""
    setup_logging()

    try:
        check_dependencies()
    except RuntimeError as e:
        logging.error(f"Dependency check failed: {e}")
        return

    flask_app = create_app()
    port = 3009

    def run_flask():
        flask_app.run(host="127.0.0.1", port=port, debug=False)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info(f"Flask server started on port {port}")

    # Open browser on first launch
    webbrowser.open(f"http://127.0.0.1:{port}")

    # Wait for Flask thread to finish (block main thread)
    flask_thread.join()


if __name__ == "__main__":
    main()
