# AirCron Service Layer Reference

## Overview

The service layer (`app/services/`) contains all business logic for AirCron. Services are stateless modules of functions that operate on data and coordinate between the API layer and data persistence.

## Design Principles

1. **Single Responsibility** - Each service handles one domain
2. **Stateless** - No class instances, just functions
3. **Return Data** - Return dicts/lists for JSON serialization
4. **Raise ValueError** - For validation errors (API layer handles HTTP status)

---

## Jobs Service

**File**: `jobs_service.py`

Handles CRUD operations for scheduled jobs.

### Functions

#### `get_jobs_for_zone(zone: str) -> List[Dict[str, Any]]`

Returns all jobs for a specific zone as dictionaries.

```python
# Usage
jobs = jobs_service.get_jobs_for_zone("All Speakers")
# Returns: [{"id": "...", "zone": "All Speakers", "time": "09:00", ...}]
```

#### `create_job(zone: str, data: Dict[str, Any]) -> Dict[str, Any]`

Creates a new job with validation.

**Validation Rules:**
- Required fields: `days`, `time`, `action`
- Time format: `HH:MM` (00-23, 00-59)
- Days: List of integers 1-7 (1=Monday, 7=Sunday)
- Valid actions: `play`, `pause`, `resume`, `volume`, `connect`, `disconnect`
- Valid services: `spotify`, `applemusic`
- `play` action requires:
  - Spotify: `uri` in args (spotify:playlist:, spotify:album:, spotify:track:)
  - Apple Music: `playlist` in args
- `volume` action requires `volume` in args (0-100)
- `connect`/`disconnect` require valid service

**Raises ValueError** for:
- Invalid time format
- Invalid day values
- Invalid action/service
- Missing required arguments
- Cron syntax validation failure
- Time conflicts with existing jobs

```python
# Example
job = jobs_service.create_job("All Speakers", {
    "days": [1, 2, 3, 4, 5],
    "time": "09:00",
    "action": "play",
    "args": {"uri": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"},
    "label": "Morning Playlist",
    "service": "spotify"
})
```

#### `update_job(zone: str, job_id: str, data: Dict[str, Any]) -> Dict[str, Any]`

Updates an existing job. Same validation as `create_job()`.

**Special Handling:**
- If `zone` in data differs from URL zone, moves job to new zone
- Preserves existing values for fields not in data

**Raises ValueError** for:
- Job not found
- All validation errors from `create_job()`

#### `delete_job(zone: str, job_id: str) -> None`

Deletes a job from its zone.

**Raises ValueError** if job not found.

#### `get_all_jobs_flat() -> List[Dict[str, Any]]`

Returns all jobs from all zones as a flat list with zone names included.

```python
# Returns
[
    {"id": "...", "zone": "All Speakers", "time": "09:00", ...},
    {"id": "...", "zone": "Office", "time": "10:00", ...},
]
```

---

## Cron Service

**File**: `cron_service.py`

Manages cron integration and status tracking.

### Functions

#### `apply_jobs_to_cron() -> Dict[str, Any]`

Applies all jobs from jobs.json to the system crontab.

**Process:**
1. Loads all jobs from JobsStore
2. Generates cron lines via CronManager
3. Backs up current crontab
4. Replaces AirCron section in crontab

**Returns:** `{"ok": True}`

#### `get_cron_status() -> Dict[str, Any]`

Compares jobs.json with current crontab to detect desync.

**Returns:**
```python
{
    "has_aircron_section": bool,      # AirCron markers exist
    "has_jobs_in_cron": bool,         # Jobs exist between markers
    "total_stored_jobs": int,         # Jobs in jobs.json
    "current_cron_jobs_count": int,   # Jobs in crontab
    "expected_cron_jobs_count": int,  # Should match total_stored_jobs
    "jobs_match": bool,               # Current cron matches expected
    "needs_apply": bool,              # True if jobs != cron
    "cron_desync": bool,              # True if jobs.json has jobs but cron is empty
    "current_cron_jobs": List[str],   # Normalized current cron lines
    "expected_cron_jobs": List[str],  # Normalized expected cron lines
}
```

**Frontend Usage:** Use `cron_desync` to prompt user to apply jobs.

#### `get_cron_preview() -> Dict[str, Any]`

Generates a preview of changes that will be made when applying to cron.

**Returns:**
```python
{
    "has_changes": bool,
    "total_changes": int,
    "timestamp": str,
    "job_details": [
        {
            "zone": str,
            "job": Dict or None,  # Job object if adding
            "cron_line": str,     # Normalized cron line
            "status": str         # "will_add", "will_remove", "unchanged"
        },
        ...
    ]
}
```

#### `get_current_cron_jobs() -> Dict[str, Any]`

Returns the raw AirCron section from crontab.

**Returns:**
```python
{
    "aircron_section": List[str],  # Raw lines from crontab
    "has_section": bool,
    "total_lines": int
}
```

#### `get_all_cron_jobs() -> Dict[str, Any]`

Returns all jobs with their applied/pending status.

**Returns:**
```python
{
    "zones": {
        "All Speakers": [
            {"id": "...", "status": "applied", ...},
            {"id": "...", "status": "pending", ...},
        ],
        ...
    },
    "total_jobs": int,
    "has_jobs": bool
}
```

---

## Control Service

**File**: `control_service.py`

Handles live (immediate) audio control actions.

### Functions

#### `run_control_action(data: Dict[str, Any]) -> Dict[str, Any]`

Executes an immediate control action via `aircron_run.sh`.

**Parameters:**
```python
{
    "action": str,      # play, pause, resume, volume, connect, disconnect
    "service": str,     # spotify, applemusic (default: spotify)
    "zone": str,        # Target zone (default: "All Speakers")
    "args": Dict        # Action-specific arguments
}
```

**Action Requirements:**
- `play`: Requires `uri` (Spotify) or `playlist` (Apple Music) in args
- `volume`: Requires `volume` in args (integer 0-100)
- Other actions: No args required

**Special Behavior:**
- `connect` first disconnects all speakers before connecting

**Raises ValueError** for:
- Invalid action/service
- Missing zone
- Missing required arguments

**Returns:** `{"ok": True}`

---

## Speakers Service

**File**: `speakers_service.py`

Simple wrapper around speaker discovery.

### Functions

#### `list_speakers() -> List[str]`

Returns list of available speaker names.

Delegates to `speaker_discovery.get_available_speakers()`.

#### `refresh_speakers() -> Dict[str, Any]`

Forces Airfoil to rescan for speakers.

**Returns:**
```python
{
    "speakers": List[str],
    "refreshed": True
}
```

---

## Playlists Service

**File**: `playlists_service.py`

Manages saved playlists for quick access.

### Data Location

`~/Library/Application Support/AirCron/playlists.json`

### Playlist Structure

```python
{
    "playlists": [
        {
            "id": "abc12345",           # Short UUID
            "name": "Morning Mix",       # Display name
            "description": "...",        # Optional description
            "uri": "spotify:playlist:...",  # Spotify URI (empty for Apple Music)
            "playlist": "...",           # Apple Music playlist/name
            "service": "spotify",        # spotify or applemusic
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-02T12:00:00"  # Only if updated
        }
    ]
}
```

### Functions

#### `list_playlists() -> List[Dict[str, Any]]`

Returns all playlists with automatic migration for missing `service` field.

#### `create_playlist(data: Dict[str, Any]) -> Dict[str, Any]`

Creates a new playlist.

**Validation:**
- `name` required, non-empty
- `service` must be valid (defaults to "spotify")
- Spotify requires `uri` starting with `spotify:playlist:`, `spotify:album:`, or `spotify:track:`
- Apple Music requires `playlist` (name or URL)
- URL format: `https://music.apple.com/.../playlist/.../id` (extracts ID)
- Duplicate names within same service are rejected

**Raises ValueError** for validation failures.

#### `update_playlist(playlist_id: str, data: Dict[str, Any]) -> Dict[str, Any]`

Updates an existing playlist.

**Validation:** Same rules as `create_playlist()`, plus duplicate name check (excluding current).

**Raises ValueError** if playlist not found or validation fails.

#### `delete_playlist(playlist_id: str) -> Dict[str, Any]`

Deletes a playlist.

**Returns:** `{"ok": True}`

**Raises ValueError** if playlist not found.

---

## Service Interaction Patterns

### Cron Manager Access Pattern

Multiple services need to access the global `cron_manager`. This pattern is used:

```python
from .. import cronblock

if cronblock.cron_manager is None:
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    cronblock.cron_manager = cronblock.CronManager(app_support_dir)
```

**TODO:** Refactor to a helper function `get_cron_manager()`.

### App Support Directory Pattern

All services access the support directory via Flask config:

```python
from flask import current_app

app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
```

This ensures the path is consistent throughout the application.

---

## Validation Rules Reference

### Time Format

- Must be `HH:MM` (24-hour format)
- Hour: 00-23
- Minute: 00-59

### Day Values

- Integers 1-7
- 1 = Monday
- 7 = Sunday
- Converted to cron format (0=Sunday) when generating cron entries

### Actions

| Action | Description | Required Args |
|--------|-------------|---------------|
| `play` | Start playback | `uri` (Spotify) or `playlist` (Apple Music) |
| `pause` | Pause playback | None |
| `resume` | Resume playback | None |
| `volume` | Set volume | `volume` (0-100) |
| `connect` | Connect speakers | `service` must be specified |
| `disconnect` | Disconnect speakers | `service` must be specified |

### Services

- `spotify` - Spotify integration
- `applemusic` - Apple Music integration

### Volume

- Integer 0-100
- For "All Speakers": Sets global app volume
- For specific zones: Sets per-speaker volume in Airfoil

### Spotify URI Format

Must start with:
- `spotify:playlist:` - Playlist
- `spotify:album:` - Album
- `spotify:track:` - Single track

### Apple Music Playlist

Can be:
- Playlist name (exact match)
- Playlist URL (extracts ID)
- Playlist ID

---

## Error Handling

All services raise `ValueError` for validation errors. The API layer (`app/api.py`) catches these and returns appropriate HTTP status codes:

- **400 Bad Request** - Validation errors
- **404 Not Found** - Resource not found
- **409 Conflict** - Duplicate/conflict errors

---

## Logging

Services use the standard logging module:

```python
import logging

logger = logging.getLogger(__name__)
logger.info("[service_name] Message")
```

Important operations are logged with context for debugging.

---

## See Also

- **Backend Architecture**: `app/AGENTS.md`
- **Main Documentation**: `AGENTS.md`
- **Jobs System**: `docs/jobs-system.md`
- **Cron System**: `docs/cron-system.md`
