import os
import json
import tempfile
import pytest
from pathlib import Path
from flask import Flask
from app import create_app

@pytest.fixture
def client():
    temp_dir = tempfile.TemporaryDirectory()
    app = create_app({
        "TESTING": True,
        "APP_SUPPORT_DIR": Path(temp_dir.name),
    })
    with app.test_client() as client:
        yield client
    temp_dir.cleanup()

def test_speakers_endpoints(client):
    resp = client.get("/api/speakers")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "speakers" in data
    resp = client.post("/api/speakers/refresh")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "speakers" in data

def test_jobs_crud(client):
    zone = "TestZone"
    # Create job
    job_data = {
        "days": [1, 2],
        "time": "07:30",
        "action": "play",
        "args": {"uri": "spotify:playlist:123"},
        "label": "Morning Jazz"
    }
    resp = client.post(f"/api/jobs/{zone}", json=job_data)
    assert resp.status_code == 201
    job = resp.get_json()
    job_id = job["id"]
    # Get jobs for zone
    resp = client.get(f"/api/jobs/{zone}")
    assert resp.status_code == 200
    jobs = resp.get_json()
    assert any(j["id"] == job_id for j in jobs)
    # Update job
    update = {"label": "Evening Jazz"}
    resp = client.put(f"/api/jobs/{zone}/{job_id}", json=update)
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["label"] == "Evening Jazz"
    # Delete job
    resp = client.delete(f"/api/jobs/{zone}/{job_id}")
    assert resp.status_code == 200
    # Confirm deletion
    resp = client.get(f"/api/jobs/{zone}")
    jobs = resp.get_json()
    assert not any(j["id"] == job_id for j in jobs)

def test_cron_endpoints(client):
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

def test_playlists_crud(client):
    # Create
    pl = {"name": "Test Playlist", "uri": "spotify:playlist:abc", "description": "desc"}
    resp = client.post("/api/playlists", json=pl)
    assert resp.status_code == 201
    playlist = resp.get_json()
    # List
    resp = client.get("/api/playlists")
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(p["name"] == "Test Playlist" for p in data.get("playlists", []))
    pid = playlist.get("id") or playlist.get("playlist_id")
    # Update
    update = {"name": "Updated Playlist", "uri": "spotify:playlist:abc", "description": "desc2"}
    resp = client.put(f"/api/playlists/{pid}", json=update)
    assert resp.status_code in (200, 201, 204)
    # Delete
    resp = client.delete(f"/api/playlists/{pid}")
    assert resp.status_code in (200, 204)
    # Confirm deletion
    resp = client.get("/api/playlists")
    data = resp.get_json()
    assert not any(p.get("id") == pid for p in data.get("playlists", []))

def test_jobs_flat(client):
    # Should return jobs as flat list
    resp = client.get("/api/jobs/all")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "jobs" in data

def test_jobs_edge_cases(client):
    zone = "EdgeZone"
    # Missing required fields
    resp = client.post(f"/api/jobs/{zone}", json={"time": "07:30", "action": "play"})
    assert resp.status_code == 400
    # Invalid time
    bad = {"days": [1], "time": "25:00", "action": "play", "args": {"uri": "spotify:playlist:1"}}
    resp = client.post(f"/api/jobs/{zone}", json=bad)
    assert resp.status_code == 400
    # Invalid days
    bad = {"days": [0, 8], "time": "07:30", "action": "play", "args": {"uri": "spotify:playlist:1"}}
    resp = client.post(f"/api/jobs/{zone}", json=bad)
    assert resp.status_code == 400
    # Invalid action
    bad = {"days": [1], "time": "07:30", "action": "foobar", "args": {}}
    resp = client.post(f"/api/jobs/{zone}", json=bad)
    assert resp.status_code == 400
    # Duplicate job (same time/days/zone)
    job = {"days": [1], "time": "07:30", "action": "play", "args": {"uri": "spotify:playlist:1"}}
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

def test_playlists_edge_cases(client):
    # Missing name
    pl = {"uri": "spotify:playlist:abc"}
    resp = client.post("/api/playlists", json=pl)
    assert resp.status_code in (400, 500)
    # Missing uri
    pl = {"name": "No URI"}
    resp = client.post("/api/playlists", json=pl)
    assert resp.status_code in (400, 500)
    # Invalid URI
    pl = {"name": "Bad URI", "uri": "notspotify:foo"}
    resp = client.post("/api/playlists", json=pl)
    assert resp.status_code in (400, 500)
    # Duplicate name
    pl = {"name": "Edge Playlist", "uri": "spotify:playlist:abc"}
    resp = client.post("/api/playlists", json=pl)
    assert resp.status_code == 201
    resp2 = client.post("/api/playlists", json=pl)
    assert resp2.status_code in (400, 409, 500)
    # Update non-existent
    resp = client.put("/api/playlists/notarealid", json={"name": "x", "uri": "spotify:playlist:abc"})
    assert resp.status_code in (400, 404, 500)
    # Delete non-existent
    resp = client.delete("/api/playlists/notarealid")
    assert resp.status_code in (400, 404, 500)

def test_cron_edge_cases(client):
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

def test_speakers_edge_case(client, monkeypatch):
    # Simulate Airfoil not running
    from app.speakers import speaker_discovery
    monkeypatch.setattr(speaker_discovery, "is_airfoil_running", lambda: False)
    speakers = speaker_discovery.get_available_speakers()
    assert "All Speakers" in speakers 