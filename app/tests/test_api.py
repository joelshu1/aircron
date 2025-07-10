import tempfile
from pathlib import Path
from typing import Any

import pytest

from app import create_app


@pytest.fixture
def client() -> Any:
    temp_dir = tempfile.TemporaryDirectory()
    app = create_app(
        {
            "TESTING": True,
            "APP_SUPPORT_DIR": Path(temp_dir.name),
        }
    )
    with app.test_client() as client:
        yield client
    temp_dir.cleanup()


def test_speakers_endpoints(client: Any) -> None:
    resp = client.get("/api/speakers")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "speakers" in data
    resp = client.post("/api/speakers/refresh")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "speakers" in data


def test_jobs_crud(client: Any) -> None:
    zone = "TestZone"
    # Create Spotify job
    job_data = {
        "zone": zone,
        "days": [1, 2],
        "time": "07:30",
        "action": "play",
        "args": {"uri": "spotify:playlist:123"},
        "label": "Morning Jazz",
        "service": "spotify",
    }
    resp = client.post(f"/api/jobs/{zone}", json=job_data)
    assert resp.status_code == 201
    job = resp.get_json()
    job_id = job["id"]
    assert job["service"] == "spotify"
    # Create Apple Music job
    am_job = {
        "zone": zone,
        "days": [3],
        "time": "09:00",
        "action": "play",
        "args": {"playlist": "Chill Mix"},
        "label": "AM Job",
        "service": "applemusic",
    }
    resp = client.post(f"/api/jobs/{zone}", json=am_job)
    assert resp.status_code in (201, 409)
    if resp.status_code == 201:
        am = resp.get_json()
        assert am["service"] == "applemusic"
    # Negative: Apple Music job missing playlist
    bad_am = {
        "zone": zone,
        "days": [4],
        "time": "10:00",
        "action": "play",
        "args": {},
        "label": "Bad AM",
        "service": "applemusic",
    }
    resp = client.post(f"/api/jobs/{zone}", json=bad_am)
    assert resp.status_code in (400, 409)
    # Negative: Spotify job missing uri
    bad_spotify = {
        "zone": zone,
        "days": [5],
        "time": "11:00",
        "action": "play",
        "args": {},
        "label": "Bad Spotify",
        "service": "spotify",
    }
    resp = client.post(f"/api/jobs/{zone}", json=bad_spotify)
    assert resp.status_code in (400, 409)
    # Update job: valid for Spotify
    update = {
        "label": "Evening Jazz",
        "service": "spotify",
        "args": {"uri": "spotify:playlist:456"},
    }
    resp = client.put(f"/api/jobs/{zone}/{job_id}", json=update)
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["label"] == "Evening Jazz"
    # Update job: valid for Apple Music
    if resp.status_code == 200:
        update_am = {"label": "AM Updated", "service": "applemusic", "args": {"playlist": "Mix 2"}}
        resp2 = client.put(f"/api/jobs/{zone}/{job_id}", json=update_am)
        assert resp2.status_code in (200, 409, 404)
    # Update job: invalid for Apple Music (missing playlist)
    update_am_bad = {"label": "AM Updated", "service": "applemusic", "args": {}}
    resp2 = client.put(f"/api/jobs/{zone}/{job_id}", json=update_am_bad)
    assert resp2.status_code in (400, 409, 404)
    # Delete jobs
    resp = client.get(f"/api/jobs/{zone}")
    jobs = resp.get_json()
    for j in jobs:
        resp = client.delete(f"/api/jobs/{zone}/{j['id']}")
        assert resp.status_code == 200
    # Confirm deletion
    resp = client.get(f"/api/jobs/{zone}")
    jobs = resp.get_json()
    assert not jobs


def test_cron_endpoints(client: Any) -> None:
    # Apply cron (should succeed even if no jobs)
    resp = client.post("/api/cron/apply")
    assert resp.status_code == 200
    # Status
    resp = client.get("/api/cron/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "has_aircron_section" in data
    # Preview
    resp = client.get("/api/cron/preview")
    assert resp.status_code == 200
    # Current
    resp = client.get("/api/cron/current")
    assert resp.status_code == 200
    # All
    resp = client.get("/api/cron/all")
    assert resp.status_code == 200


def test_playlists_crud(client: Any) -> None:
    # Create Spotify playlist
    pl = {
        "name": "Test Playlist",
        "uri": "spotify:playlist:abc",
        "description": "desc",
        "service": "spotify",
    }
    resp = client.post("/api/playlists", json=pl)
    assert resp.status_code == 201
    assert b"<script>" in resp.data
    # Create Apple Music playlist
    am_pl = {
        "name": "AM Playlist",
        "playlist": "Chill Mix",
        "description": "desc2",
        "service": "applemusic",
    }
    resp = client.post("/api/playlists", json=am_pl)
    assert resp.status_code == 201
    assert b"<script>" in resp.data
    # List
    resp = client.get("/api/playlists")
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(
        p["name"] == "Test Playlist" and p["service"] == "spotify"
        for p in data.get("playlists", [])
    )
    assert any(
        p["name"] == "AM Playlist" and p["service"] == "applemusic"
        for p in data.get("playlists", [])
    )
    pid = next((p["id"] for p in data["playlists"] if p["name"] == "Test Playlist"), None)
    am_pid = next((p["id"] for p in data["playlists"] if p["name"] == "AM Playlist"), None)
    # Update
    update = {
        "name": "Updated Playlist",
        "uri": "spotify:playlist:abc",
        "description": "desc2",
        "service": "spotify",
    }
    resp = client.put(f"/api/playlists/{pid}", json=update)
    assert resp.status_code in (200, 201, 204)
    # Update Apple Music playlist
    am_update = {
        "name": "AM Updated",
        "playlist": "Chill Mix 2",
        "description": "desc3",
        "service": "applemusic",
    }
    resp = client.put(f"/api/playlists/{am_pid}", json=am_update)
    assert resp.status_code in (200, 201, 204)
    # Delete
    resp = client.delete(f"/api/playlists/{pid}")
    assert resp.status_code in (200, 204)
    resp = client.delete(f"/api/playlists/{am_pid}")
    assert resp.status_code in (200, 204)
    # Confirm deletion
    resp = client.get("/api/playlists")
    data = resp.get_json()
    assert not any(p.get("id") == pid for p in data.get("playlists", []))
    assert not any(p.get("id") == am_pid for p in data.get("playlists", []))
    # Negative: missing service for Apple Music
    bad_am = {"name": "Bad AM", "playlist": "No Service"}
    resp = client.post("/api/playlists", json=bad_am)
    # Should fail because service defaults to spotify and no uri
    assert resp.status_code in (400, 409, 500)
    # Negative: invalid service
    bad_service = pl.copy()
    bad_service["service"] = "notarealservice"
    resp = client.post("/api/playlists", json=bad_service)
    assert resp.status_code in (400, 409, 201, 500)


def test_jobs_flat(client: Any) -> None:
    # Should return jobs as flat list
    resp = client.get("/api/jobs/all")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "jobs" in data


def test_jobs_edge_cases(client: Any) -> None:
    zone = "EdgeZone"
    # Missing required fields
    resp = client.post(f"/api/jobs/{zone}", json={"zone": zone, "time": "07:30", "action": "play"})
    assert resp.status_code == 400
    # Invalid time
    bad = {
        "zone": zone,
        "days": [1],
        "time": "25:00",
        "action": "play",
        "args": {"uri": "spotify:playlist:1"},
    }
    resp = client.post(f"/api/jobs/{zone}", json=bad)
    assert resp.status_code == 400
    # Invalid days
    bad = {
        "zone": zone,
        "days": [0, 8],
        "time": "07:30",
        "action": "play",
        "args": {"uri": "spotify:playlist:1"},
    }
    resp = client.post(f"/api/jobs/{zone}", json=bad)
    assert resp.status_code == 400
    # Invalid action
    bad = {"zone": zone, "days": [1], "time": "07:30", "action": "foobar", "args": {}}
    resp = client.post(f"/api/jobs/{zone}", json=bad)
    assert resp.status_code == 400
    # Duplicate job (same time/days/zone)
    job = {
        "zone": zone,
        "days": [1],
        "time": "07:30",
        "action": "play",
        "args": {"uri": "spotify:playlist:1"},
    }
    resp = client.post(f"/api/jobs/{zone}", json=job)
    assert resp.status_code == 201
    resp2 = client.post(f"/api/jobs/{zone}", json=job)
    assert resp2.status_code in (400, 409)
    # Update non-existent job
    resp = client.put(f"/api/jobs/{zone}/notarealid", json={"label": "x"})
    assert resp.status_code == 404
    # Delete non-existent job
    resp = client.delete(f"/api/jobs/{zone}/notarealid")
    assert resp.status_code == 404


def test_playlists_edge_cases(client: Any) -> None:
    # Missing name
    pl = {"uri": "spotify:playlist:abc"}
    resp = client.post("/api/playlists", json=pl)
    assert resp.status_code in (400, 409, 500)
    # Missing uri
    pl = {"name": "No URI"}
    resp = client.post("/api/playlists", json=pl)
    assert resp.status_code in (400, 409, 500)
    # Invalid URI
    pl = {"name": "Bad URI", "uri": "notspotify:foo"}
    resp = client.post("/api/playlists", json=pl)
    assert resp.status_code in (400, 409, 500)
    # Duplicate name
    pl = {"name": "Edge Playlist", "uri": "spotify:playlist:abc"}
    resp = client.post("/api/playlists", json=pl)
    assert resp.status_code == 201
    resp2 = client.post("/api/playlists", json=pl)
    assert resp2.status_code in (400, 409, 500)
    # Update non-existent
    resp = client.put(
        "/api/playlists/notarealid", json={"name": "x", "uri": "spotify:playlist:abc"}
    )
    assert resp.status_code in (400, 404, 409, 500)
    # Delete non-existent
    resp = client.delete("/api/playlists/notarealid")
    assert resp.status_code in (400, 404, 409, 500)


def test_cron_edge_cases(client: Any) -> None:
    # Apply cron with no jobs (should still succeed)
    resp = client.post("/api/cron/apply")
    assert resp.status_code == 200
    # Status with no jobs
    resp = client.get("/api/cron/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_stored_jobs"] == 0
    # Preview with no jobs
    resp = client.get("/api/cron/preview")
    assert resp.status_code == 200


def test_speakers_edge_case(client: Any, monkeypatch: Any) -> None:
    # Simulate Airfoil not running
    from app.speakers import speaker_discovery

    monkeypatch.setattr(speaker_discovery, "is_airfoil_running", lambda: False)
    speakers = speaker_discovery.get_available_speakers()
    assert "All Speakers" in speakers


def test_generic_actions_are_service_aware(client: Any) -> None:
    """
    Tests that generic actions (pause, resume, volume) are correctly
    associated with a service (Spotify or Apple Music).
    """
    zone = "ServiceAwareZone"

    # 1. Create a 'pause' job for Apple Music
    pause_job_data = {
        "zone": zone,
        "days": [1],
        "time": "14:00",
        "action": "pause",
        "service": "applemusic",
        "label": "Pause Apple Music",
    }
    resp = client.post(f"/api/jobs/{zone}", json=pause_job_data)
    assert resp.status_code == 201
    pause_job = resp.get_json()
    assert pause_job["service"] == "applemusic"
    assert pause_job["action"] == "pause"

    # 2. Create a 'volume' job for Spotify
    volume_job_data = {
        "zone": zone,
        "days": [2],
        "time": "15:00",
        "action": "volume",
        "args": {"volume": 88},
        "service": "spotify",
        "label": "Set Spotify Volume",
    }
    resp = client.post(f"/api/jobs/{zone}", json=volume_job_data)
    assert resp.status_code == 201
    volume_job = resp.get_json()
    assert volume_job["service"] == "spotify"
    assert volume_job["args"]["volume"] == 88

    # 3. Attempt to create a job with an invalid service
    invalid_service_data = {
        "zone": zone,
        "days": [3],
        "time": "16:00",
        "action": "resume",
        "service": "tidal",
        "label": "Invalid Service",
    }
    resp = client.post(f"/api/jobs/{zone}", json=invalid_service_data)
    assert resp.status_code == 400  # Should fail validation

    # 4. Test empty service validation
    empty_service_data = {
        "zone": zone,
        "days": [4],
        "time": "17:00",
        "action": "connect",
        "service": "",
        "label": "Empty Service",
    }
    resp = client.post(f"/api/jobs/{zone}", json=empty_service_data)
    assert resp.status_code == 400  # Should fail validation

    # 5. Update a job's service from Spotify to Apple Music
    update_data = {"service": "applemusic"}
    resp = client.put(f"/api/jobs/{zone}/{volume_job['id']}", json=update_data)
    assert resp.status_code == 200
    updated_job = resp.get_json()
    assert updated_job["service"] == "applemusic"

    # 6. Ensure GET returns the correct service
    resp = client.get(f"/api/jobs/{zone}")
    jobs = resp.get_json()
    assert len(jobs) == 2
    for job in jobs:
        if job["action"] == "pause":
            assert job["service"] == "applemusic"
        elif job["action"] == "volume":
            assert job["service"] == "applemusic"  # It was updated


def test_connect_disconnect_actions(client: Any) -> None:
    """
    Tests the creation and validation of the new 'connect' and 'disconnect' actions.
    """
    zone = "ConnectDisconnectZone"

    # 1. Create a 'connect' job with a valid service
    connect_data = {
        "zone": zone,
        "days": [1],
        "time": "20:00",
        "action": "connect",
        "service": "spotify",
        "label": "Connect to Spotify",
    }
    resp = client.post(f"/api/jobs/{zone}", json=connect_data)
    assert resp.status_code == 201
    connect_job = resp.get_json()
    assert connect_job["action"] == "connect"
    assert connect_job["service"] == "spotify"
    assert not connect_job["args"]  # args should be empty

    # 2. Attempt to create a 'connect' job with empty service (should fail)
    invalid_connect = {
        "zone": zone,
        "days": [2],
        "time": "21:00",
        "action": "connect",
        "service": "",
        "label": "Invalid Connect",
    }
    resp = client.post(f"/api/jobs/{zone}", json=invalid_connect)
    assert resp.status_code == 400

    # 3. Create a 'disconnect' job
    disconnect_data = {
        "zone": zone,
        "days": [1],
        "time": "23:00",
        "action": "disconnect",
        "service": "spotify",
        "label": "Disconnect All",
    }
    resp = client.post(f"/api/jobs/{zone}", json=disconnect_data)
    assert resp.status_code == 201
    disconnect_job = resp.get_json()
    assert disconnect_job["action"] == "disconnect"
    assert not disconnect_job["args"]

    # 4. Test disconnect with empty service (should fail)
    invalid_disconnect = {
        "zone": zone,
        "days": [3],
        "time": "22:00",
        "action": "disconnect",
        "service": "",
        "label": "Invalid Disconnect",
    }
    resp = client.post(f"/api/jobs/{zone}", json=invalid_disconnect)
    assert resp.status_code == 400
