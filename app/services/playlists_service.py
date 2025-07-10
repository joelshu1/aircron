import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, cast
from uuid import uuid4

from flask import current_app

logger = logging.getLogger(__name__)


def _get_playlists_file() -> Path:
    app_support_dir = current_app.config["APP_SUPPORT_DIR"]
    return Path(app_support_dir) / "playlists.json"


def list_playlists() -> List[Dict[str, Any]]:
    playlists_file = _get_playlists_file()
    if not playlists_file.exists():
        return []
    with playlists_file.open() as f:
        data = cast(Dict[str, Any], json.load(f))
    # Migrate playlists missing 'service' field
    changed = False
    for playlist in data.get("playlists", []):
        if "service" not in playlist:
            playlist["service"] = "spotify"
            changed = True
    if changed:
        with playlists_file.open("w") as f:
            json.dump(data, f, indent=2)
    return cast(List[Dict[str, Any]], data.get("playlists", []))


def create_playlist(data: Dict[str, Any]) -> Dict[str, Any]:
    name = data.get("name")
    if not name or not name.strip():
        raise ValueError("Name is required and cannot be empty")

    service = data.get("service", "spotify")
    valid_services = ["spotify", "applemusic"]
    if service not in valid_services:
        raise ValueError(f"Invalid service. Must be one of: {valid_services}")

    # Additional validation for empty service
    if not service or service.strip() == "":
        raise ValueError("Service cannot be empty")

    if service == "spotify":
        uri_raw = data.get("uri")
        if not uri_raw or not uri_raw.strip():
            raise ValueError("Spotify URI is required")
        uri = uri_raw.strip()
        if not (
            uri.startswith("spotify:")
            and ("playlist:" in uri or "album:" in uri or "track:" in uri)
        ):
            raise ValueError(
                "Invalid Spotify URI format - must be spotify:playlist:, "
                "spotify:album:, or spotify:track:"
            )
    elif service == "applemusic":
        playlist_raw = data.get("playlist")
        if not playlist_raw or not playlist_raw.strip():
            raise ValueError("Apple Music playlist name or ID is required")
        playlist_val = playlist_raw.strip()
        # If it's a URL, extract the last path segment (playlist ID)
        url_match = re.match(
            r"https?://music\.apple\.com/.*/playlist/.*/([a-zA-Z0-9.\-_]+)", playlist_val
        )
        if url_match:
            playlist_id = url_match.group(1)
        else:
            playlist_id = playlist_val
        uri = ""

    playlists_file = _get_playlists_file()
    if playlists_file.exists():
        with playlists_file.open() as f:
            playlists_data = cast(Dict[str, Any], json.load(f))
    else:
        playlists_data = {"playlists": []}

    # Check for duplicate names within the same service
    for playlist in playlists_data["playlists"]:
        if (
            playlist["name"].lower() == data["name"].strip().lower()
            and playlist.get("service", "spotify") == service
        ):
            raise ValueError(
                f"A playlist with the name '{data['name'].strip()}' already exists for {service}"
            )

    new_playlist = {
        "id": str(uuid4())[:8],
        "name": data["name"].strip(),
        "description": data.get("description", "").strip(),
        "uri": uri,
        "service": service,
        "created_at": datetime.now().isoformat(),
    }
    if service == "applemusic":
        new_playlist["playlist"] = playlist_id
    playlists_data["playlists"].append(new_playlist)
    with playlists_file.open("w") as f:
        json.dump(playlists_data, f, indent=2)
    logger.info(f"Created playlist: {new_playlist['name']} ({service})")
    return new_playlist


def update_playlist(playlist_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    playlists_file = _get_playlists_file()
    if not playlists_file.exists():
        raise ValueError("Playlist not found")
    with playlists_file.open() as f:
        playlists_data = cast(Dict[str, Any], json.load(f))
    playlist_to_update = None
    for i, playlist in enumerate(playlists_data["playlists"]):
        if playlist["id"] == playlist_id:
            playlist_to_update = playlist
            break
    if not playlist_to_update:
        raise ValueError("Playlist not found")
    service = data.get("service", playlist_to_update.get("service", "spotify"))
    if "name" in data:
        name = data["name"].strip()
        if not name:
            raise ValueError("Name cannot be empty")
        for playlist in playlists_data["playlists"]:
            if (
                playlist["id"] != playlist_id
                and playlist["name"].lower() == name.lower()
                and playlist.get("service", "spotify") == service
            ):
                raise ValueError("A playlist with this name already exists for this service")
        playlist_to_update["name"] = name
    if "description" in data:
        playlist_to_update["description"] = data["description"].strip()
    if service == "spotify" and "uri" in data:
        uri = data["uri"].strip()
        if not (
            uri.startswith("spotify:")
            and ("playlist:" in uri or "album:" in uri or "track:" in uri)
        ):
            raise ValueError("Invalid Spotify URI format")
        playlist_to_update["uri"] = uri
    if service == "applemusic" and "playlist" in data:
        playlist_to_update["playlist"] = data["playlist"].strip()
    playlist_to_update["service"] = service
    playlist_to_update["updated_at"] = datetime.now().isoformat()
    with playlists_file.open("w") as f:
        json.dump(playlists_data, f, indent=2)
    logger.info(f"Updated playlist: {playlist_to_update['name']} ({service})")
    return cast(Dict[str, Any], playlist_to_update)


def delete_playlist(playlist_id: str) -> Dict[str, Any]:
    playlists_file = _get_playlists_file()
    if not playlists_file.exists():
        raise ValueError("Playlist not found")
    with playlists_file.open() as f:
        playlists_data = cast(Dict[str, Any], json.load(f))
    original_count = len(playlists_data["playlists"])
    playlists_data["playlists"] = [p for p in playlists_data["playlists"] if p["id"] != playlist_id]
    if len(playlists_data["playlists"]) == original_count:
        raise ValueError("Playlist not found")
    with playlists_file.open("w") as f:
        json.dump(playlists_data, f, indent=2)
    logger.info(f"Deleted playlist: {playlist_id}")
    return {"ok": True}
