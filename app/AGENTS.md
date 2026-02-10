# AirCron Backend Architecture

## Overview

The AirCron backend is built on **Flask** using the **application factory pattern**. It follows a clean service-oriented architecture with clear separation between the API layer, business logic (services), and data persistence.

## Application Factory

### Entry Point: `main.py`

The application is launched via `main.py` which:
1. Sets up logging to `~/Library/Logs/AirCron/`
2. Checks for required dependencies (spotify-cli, osascript, cron)
3. Creates and runs the Flask app in a background thread
4. Opens the browser to the web interface

```python
# main.py:71-95
def main() -> None:
    setup_logging()
    check_dependencies()
    flask_app = create_app()
    # ... run in background thread
```

### App Factory: `app/__init__.py`

The `create_app()` function (`app/__init__.py:13-59`) is responsible for:

1. **Flask Configuration**
   - Template and static folder configuration
   - SECRET_KEY (⚠️ hardcoded - should use env var in production)
   - JSON_SORT_KEYS disabled for consistent responses

2. **Application Support Directory**
   - Creates `~/Library/Application Support/AirCron/` if needed
   - Stores jobs.json, playlists.json, and cron backups here

3. **Global Managers Initialization**
   - Initializes the global `cron_manager` instance with the support directory

4. **Blueprint Registration**
   - `views_bp` - HTML routes for HTMX frontend
   - `api_bp` - REST API endpoints (prefixed with `/api`)

## Request Flow

```
HTTP Request
    │
    ├─► /route/path          → views_bp (HTML/HTMX)
    │                              ↓
    │                        Render template
    │                              ↓
    │                        Return HTML partial
    │
    └─► /api/route/path      → api_bp (JSON)
                                   ↓
                             Call service layer
                                   ↓
                             Return JSON response
```

## API Layer: `app/api.py`

The API layer provides thin wrappers around service layer functions. All endpoints return JSON.

### Speaker Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/speakers` | List available speakers |
| POST | `/api/speakers/refresh` | Force refresh speaker list |

### Job Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/jobs/<zone>` | Get jobs for a zone |
| POST | `/api/jobs/<zone>` | Create new job |
| PUT | `/api/jobs/<zone>/<job_id>` | Update existing job |
| DELETE | `/api/jobs/<zone>/<job_id>` | Delete job |
| GET | `/api/jobs/all` | Get all jobs as flat list |

### Cron Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/cron/apply` | Apply jobs to crontab |
| GET | `/api/cron/status` | Get cron sync status |
| GET | `/api/cron/preview` | Preview cron changes |
| GET | `/api/cron/current` | Get current AirCron cron section |
| GET | `/api/cron/all` | Get all cron jobs with status |

### Playlist Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/playlists` | List saved playlists |
| POST | `/api/playlists` | Create new playlist |
| PUT | `/api/playlists/<id>` | Update playlist |
| DELETE | `/api/playlists/<id>` | Delete playlist |

### Control Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/control` | Trigger live control action |

### Status Endpoint

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/status` | Get system status |

## Views Layer: `app/views.py`

The views layer handles HTML routes for the HTMX frontend. These return HTML fragments (partials) for dynamic UI updates.

### Main Routes

| Route | Purpose | Template |
|-------|---------|----------|
| `/` | Main application page | `index.html` |
| `/zone/<zone_name>` | Get jobs for zone (HTMX) | `partials/jobs_list.html` |
| `/zone/<zone_name>?cron=1` | Get cron jobs view (HTMX) | `partials/all_cron_jobs.html` |

### Modal Routes

| Route | Purpose |
|-------|---------|
| `/modal/add/<zone_name>` | Show add job modal |
| `/modal/edit/<zone_name>/<job_id>` | Show edit job modal |
| `/modal/cron/review` | Show cron review modal |
| `/modal/playlist/add` | Show add playlist modal |
| `/modal/playlist/edit/<playlist_id>` | Show edit playlist modal |

## Service Layer Architecture

Services are located in `app/services/` and contain all business logic. Each service is a module of functions that operate on data.

### Service Pattern

All services follow this pattern:
1. Import necessary modules (Flask's `current_app` for config)
2. Define functions that do one thing well
3. Return data structures (dicts, lists) for API layer to serialize
4. Raise `ValueError` for validation errors (caught by API layer)

### Available Services

| Service | File | Responsibilities |
|---------|------|------------------|
| Jobs | `jobs_service.py` | CRUD operations for scheduled jobs |
| Cron | `cron_service.py` | Cron status, preview, and application |
| Control | `control_service.py` | Live audio control actions |
| Speakers | `speakers_service.py` | Speaker discovery and listing |
| Playlists | `playlists_service.py` | Playlist CRUD operations |

See `app/services/AGENTS.md` for detailed service documentation.

## Data Layer

### Jobs Store: `app/jobs_store.py`

The `JobsStore` class manages persistence of scheduled jobs to `jobs.json`.

**Key Features:**
- **Atomic writes** using file locking (`.json.lock`)
- **Automatic backup** to `.json.bak`
- **Data migration** for adding new fields (e.g., `service` field)
- **Corruption recovery** - falls back to backup if main file is corrupt

**Job Object Structure:**
```python
{
    "id": "abc12345",           # UUID-based short ID
    "zone": "All Speakers",      # Target zone
    "days": [1, 2, 3, 4, 5],     # 1=Mon, 7=Sun
    "time": "09:00",             # HH:MM format
    "action": "play",            # play, pause, resume, volume, connect, disconnect
    "args": {"uri": "..."},      # Action-specific arguments
    "label": "Morning Playlist", # Optional label
    "service": "spotify"         # spotify or applemusic
}
```

### Cron Manager: `app/cronblock.py`

The `CronManager` class handles all cron operations.

**Key Features:**
- **Sandboxed editing** - only modifies lines between `# BEGIN AirCron` markers
- **Automatic backup** before any changes
- **Script discovery** - finds `aircron_run.sh` in multiple locations
- **Cron syntax validation** using `croniter`

**Cron Entry Format:**
```
# BEGIN AirCron (auto-generated; do not edit between markers)

# All Speakers
# Play 09:00
30 8 * * 1,2,3,4,5 /path/to/aircron_run.sh "All Speakers" play "spotify:playlist:..." "" spotify

# END AirCron
```

### Speaker Discovery: `app/speakers.py`

Provides AppleScript integration with Airfoil for speaker management.

**Key Functions:**
- `get_available_speakers()` - Returns list of discovered speakers
- `refresh_speakers()` - Forces Airfoil to rescan
- `is_airfoil_running()` - Checks if Airfoil is running

## Configuration

### Application Configuration

Configuration is stored in `app.config`:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | Session encryption (⚠️ hardcoded) |
| `APP_SUPPORT_DIR` | `~/Library/Application Support/AirCron/` |
| `JSON_SORT_KEYS` | `False` (preserve key order) |

### Environment Variables

Currently, the app uses the hardcoded SECRET_KEY. For production, consider:
```python
app.config.update(SECRET_KEY=os.environ.get('AIRCRON_SECRET_KEY', 'dev-key'))
```

## Logging

Logs are written to `~/Library/Logs/AirCron/aircron.log` with format:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

Werkzeug (Flask's server) logs are set to WARNING level to reduce noise.

## Error Handling

### API Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Validation error (missing fields, invalid values) |
| 404 | Resource not found (job, playlist, zone) |
| 409 | Conflict (duplicate job, duplicate playlist name) |
| 500 | Internal server error |

All error responses follow this format:
```json
{
    "error": "Human-readable error message"
}
```

### Service Layer Errors

Services raise `ValueError` for validation errors:
```python
# jobs_service.py:55
if action not in valid_actions:
    raise ValueError(f"Invalid action. Must be one of: {valid_actions}")
```

The API layer catches these and returns appropriate HTTP status codes.

## Security Considerations

### Current Issues

1. **Hardcoded SECRET_KEY** (`app/__init__.py:24`)
2. **No input sanitization** on some API endpoints
3. **No authentication** - assumes local-only access

### Recommendations

1. Use environment variables for sensitive config
2. Add input validation middleware
3. Consider adding authentication for remote access
4. Validate all user input before processing

## Testing

Test files are in `app/tests/`:

- `test_api.py` - API endpoint tests
- `test_jobs_store.py` - Data layer tests

Run tests:
```bash
pytest app/tests/
```

## Development Notes

### Adding a New API Endpoint

1. Create or update the service function in `app/services/`
2. Add the route in `app/api.py` (for JSON) or `app/views.py` (for HTML)
3. Add error handling with try/except blocks
4. Log important operations
5. Add tests in `app/tests/`

### Cron Manager Pattern

The global `cron_manager` is initialized in the app factory. When using it in services:

```python
# Pattern for accessing cron_manager in services
if cronblock.cron_manager is None:
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    cronblock.cron_manager = cronblock.CronManager(app_support_dir)
```

This pattern appears multiple times - consider refactoring to a helper function.

## See Also

- **Service Layer Details**: `app/services/AGENTS.md`
- **Frontend Architecture**: `static/AGENTS.md`
- **Main Documentation**: `AGENTS.md`
