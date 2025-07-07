import logging
import json
from typing import List, Dict, Any
from pathlib import Path
from flask import current_app
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)

def _get_playlists_file() -> Path:
    app_support_dir = current_app.config["APP_SUPPORT_DIR"]
    return Path(app_support_dir) / "playlists.json"

def list_playlists() -> List[Dict[str, Any]]:
    playlists_file = _get_playlists_file()
    if not playlists_file.exists():
        return []
    with playlists_file.open() as f:
        data = json.load(f)
    return data.get("playlists", [])

def create_playlist(data: Dict[str, Any]) -> Dict[str, Any]:
    if not data.get("name"):
        raise ValueError("Name is required")
    if not data.get("uri"):
        raise ValueError("URI is required")
    uri = data["uri"].strip()
    if not (uri.startswith("spotify:") and ("playlist:" in uri or "album:" in uri or "track:" in uri)):
        raise ValueError("Invalid Spotify URI format")
    playlists_file = _get_playlists_file()
    if playlists_file.exists():
        with playlists_file.open() as f:
            playlists_data = json.load(f)
    else:
        playlists_data = {"playlists": []}
    for playlist in playlists_data["playlists"]:
        if playlist["name"].lower() == data["name"].strip().lower():
            raise ValueError("A playlist with this name already exists")
    new_playlist = {
        "id": str(uuid4())[:8],
        "name": data["name"].strip(),
        "description": data.get("description", "").strip(),
        "uri": uri,
        "created_at": datetime.now().isoformat()
    }
    playlists_data["playlists"].append(new_playlist)
    with playlists_file.open("w") as f:
        json.dump(playlists_data, f, indent=2)
    logger.info(f"Created playlist: {new_playlist['name']}")
    return new_playlist

def update_playlist(playlist_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    playlists_file = _get_playlists_file()
    if not playlists_file.exists():
        raise ValueError("Playlist not found")
    with playlists_file.open() as f:
        playlists_data = json.load(f)
    playlist_to_update = None
    for i, playlist in enumerate(playlists_data["playlists"]):
        if playlist["id"] == playlist_id:
            playlist_to_update = playlist
            playlist_index = i
            break
    if not playlist_to_update:
        raise ValueError("Playlist not found")
    if "name" in data:
        name = data["name"].strip()
        if not name:
            raise ValueError("Name cannot be empty")
        for playlist in playlists_data["playlists"]:
            if playlist["id"] != playlist_id and playlist["name"].lower() == name.lower():
                raise ValueError("A playlist with this name already exists")
        playlist_to_update["name"] = name
    if "description" in data:
        playlist_to_update["description"] = data["description"].strip()
    if "uri" in data:
        uri = data["uri"].strip()
        if not (uri.startswith("spotify:") and ("playlist:" in uri or "album:" in uri or "track:" in uri)):
            raise ValueError("Invalid Spotify URI format")
        playlist_to_update["uri"] = uri
    playlist_to_update["updated_at"] = datetime.now().isoformat()
    with playlists_file.open("w") as f:
        json.dump(playlists_data, f, indent=2)
    logger.info(f"Updated playlist: {playlist_to_update['name']}")
    return playlist_to_update

def delete_playlist(playlist_id: str) -> Dict[str, Any]:
    playlists_file = _get_playlists_file()
    if not playlists_file.exists():
        raise ValueError("Playlist not found")
    with playlists_file.open() as f:
        playlists_data = json.load(f)
    original_count = len(playlists_data["playlists"])
    playlists_data["playlists"] = [p for p in playlists_data["playlists"] if p["id"] != playlist_id]
    if len(playlists_data["playlists"]) == original_count:
        raise ValueError("Playlist not found")
    with playlists_file.open("w") as f:
        json.dump(playlists_data, f, indent=2)
    logger.info(f"Deleted playlist: {playlist_id}")
    return {"ok": True} 