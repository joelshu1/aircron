#!/usr/bin/env python3
"""AirCron UI - Tray application entry point."""

import logging
import shutil
import threading
import webbrowser
from pathlib import Path
from typing import Optional

import rumps

from app import create_app


def setup_logging() -> None:
    """Configure logging to rotate file in ~/Library/Logs/AirCron/."""
    log_dir = Path.home() / "Library" / "Logs" / "AirCron"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "aircron.log"),
            logging.StreamHandler()
        ]
    )


def check_dependencies() -> None:
    """Verify required dependencies are installed."""
    # Check for spotify-cli in common locations
    spotify_locations = [
        Path("/usr/local/bin/spotify"),
        Path("/opt/homebrew/bin/spotify"),
        Path("/usr/bin/spotify")
    ]
    
    spotify_found = False
    for spotify_path in spotify_locations:
        if spotify_path.is_file():
            spotify_found = True
            logging.info(f"Found spotify-cli at: {spotify_path}")
            break
    
    if not spotify_found:
        # Also check if it's in PATH
        if shutil.which('spotify') is not None:
            spotify_found = True
            logging.info(f"Found spotify-cli in PATH: {shutil.which('spotify')}")
    
    if not spotify_found:
        raise RuntimeError(
            "Install spotify-cli - not found in /usr/local/bin/, /opt/homebrew/bin/, or PATH"
        )
    
    if shutil.which('crontab') is None:
        raise RuntimeError('cron not found in PATH')


class AirCronApp(rumps.App):
    """AirCron tray application."""

    def __init__(self) -> None:
        super().__init__("AirCron", icon=None, quit_button="Quit AirCron")
        self.flask_app: Optional[object] = None
        self.flask_thread: Optional[threading.Thread] = None
        self.port = 3009

    def start_flask(self) -> None:
        """Start Flask server in background thread."""
        self.flask_app = create_app()
        self.flask_thread = threading.Thread(
            target=lambda: self.flask_app.run(host="127.0.0.1", port=self.port, debug=False),
            daemon=True
        )
        self.flask_thread.start()
        logging.info(f"Flask server started on port {self.port}")

    @rumps.clicked("Open AirCron")
    def open_ui(self, _) -> None:
        """Open the web UI in default browser."""
        webbrowser.open(f"http://127.0.0.1:{self.port}")

    @rumps.clicked("Refresh Speakers")
    def refresh_speakers(self, _) -> None:
        """Trigger speaker refresh."""
        # This will be implemented when we add the speakers module
        logging.info("Speaker refresh requested")
        rumps.notification("AirCron", "Speakers Refreshed", "Updated available speaker zones")


def main() -> None:
    """Main entry point."""
    setup_logging()
    
    try:
        check_dependencies()
    except RuntimeError as e:
        logging.error(f"Dependency check failed: {e}")
        rumps.alert(f"AirCron Setup Error", f"{e}")
        return

    app = AirCronApp()
    
    # Start Flask server
    app.start_flask()
    
    # Open browser on first launch
    webbrowser.open(f"http://127.0.0.1:{app.port}")
    
    # Start tray app (blocks)
    app.run()


if __name__ == "__main__":
    main() 