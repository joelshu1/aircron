# Jobs System Documentation

## Overview

The Jobs system is the core of AirCron, managing scheduled audio playback events. Jobs are stored in `jobs.json` and can be applied to the system crontab for automated execution.

## Job Object Structure

### Complete Job Schema

```javascript
{
    "id": "abc12345",              // 8-character UUID (unique)
    "zone": "All Speakers",        // Target zone
    "days": [1, 2, 3, 4, 5],       // Scheduled days (1=Mon, 7=Sun)
    "time": "09:00",               // Scheduled time (HH:MM, 24-hour)
    "action": "play",              // Action to perform
    "args": {                      // Action-specific arguments
        "uri": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"
    },
    "label": "Morning Playlist",   // Optional display label
    "service": "spotify"           // Music service (spotify/applemusic)
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Auto-generated 8-character UUID |
| `zone` | string | Yes | Target zone (see Zone Types) |
| `days` | number[] | Yes | Array of day integers 1-7 |
| `time` | string | Yes | Time in HH:MM format (00:00-23:59) |
| `action` | string | Yes | Action to perform (see Actions) |
| `args` | object | Conditional | Action-specific arguments |
| `label` | string | No | Human-readable label |
| `service` | string | Yes | "spotify" or "applemusic" |

---

## Zone Types

### 1. All Speakers

Special zone targeting all available speakers:

```json
{"zone": "All Speakers", ...}
```

**Behavior:**
- Connects/disconnects all speakers
- Volume controls application (global) volume

### 2. Custom Zones

User-defined combinations of speakers:

```json
{"zone": "Custom:Office,Conference Room,Lobby", ...}
```

**Format:** `Custom:` followed by comma-separated speaker names

**Behavior:**
- Connects only specified speakers
- Volume controls per-speaker volume in Airfoil

### 3. Individual Speakers

Single speaker zones:

```json
{"zone": "Office", ...}
```

**Behavior:**
- Controls only that speaker
- Volume controls per-speaker volume

---

## Day Numbering

### Convention

AirCron uses ISO-style day numbering:

| Number | Day |
|--------|-----|
| 1 | Monday |
| 2 | Tuesday |
| 3 | Wednesday |
| 4 | Thursday |
| 5 | Friday |
| 6 | Saturday |
| 7 | Sunday |

### Cron Conversion

When applying to cron, days are converted to cron format (0=Sunday):

```python
# AirCron: [1, 2, 3, 4, 5] (Mon-Fri)
# Cron:    1,2,3,4,5

# AirCron: [7] (Sunday)
# Cron:    0

# AirCron: [1, 7] (Mon + Sun)
# Cron:    1,0
```

Conversion happens in `app/cronblock.py:176`:

```python
cron_days = [str(d % 7) for d in job.days]
```

---

## Actions

### play

Start playback of a playlist or track.

**Required args by service:**

| Service | Required Arg | Format |
|---------|--------------|--------|
| spotify | `uri` | `spotify:playlist:...`, `spotify:album:...`, `spotify:track:...` |
| applemusic | `playlist` | Playlist name, ID, or URL |

**Examples:**

```json
// Spotify
{
    "action": "play",
    "args": {"uri": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"},
    "service": "spotify"
}

// Apple Music
{
    "action": "play",
    "args": {"playlist": "Favorites"},
    "service": "applemusic"
}
```

### pause

Pause playback for the specified service.

**Args:** None required

**Example:**

```json
{
    "action": "pause",
    "service": "spotify"
}
```

### resume

Resume paused playback.

**Args:** None required

**Example:**

```json
{
    "action": "resume",
    "service": "spotify"
}
```

### volume

Set volume level.

**Required args:**

| Arg | Type | Range |
|-----|------|-------|
| `volume` | number | 0-100 |

**Volume Scope:**

| Zone | Scope |
|------|-------|
| All Speakers | Global application volume |
| Custom/Individual | Per-speaker volume in Airfoil |

**Example:**

```json
{
    "action": "volume",
    "args": {"volume": 75},
    "zone": "Office"
}
```

### connect

Connect speakers for the specified service.

**Behavior:**
- Disconnects all speakers first (to avoid conflicts)
- Then connects target speakers

**Args:** None required, but `service` must be specified

**Example:**

```json
{
    "action": "connect",
    "service": "spotify",
    "zone": "Office,Conference Room"
}
```

### disconnect

Disconnect speakers.

**Args:** None required, but `service` should be specified

**Example:**

```json
{
    "action": "disconnect",
    "service": "spotify",
    "zone": "All Speakers"
}
```

---

## Job Lifecycle

### 1. Creation

```
User fills form → POST /api/jobs/{zone} → jobs_service.create_job()
    → Validation → JobsStore.add_job() → jobs.json
```

**Validation Steps:**
1. Required fields present
2. Time format valid (HH:MM)
3. Days in range (1-7)
4. Action valid
5. Service valid
6. Action-specific args present
7. No time conflicts with existing jobs
8. Cron syntax valid

### 2. Storage

Jobs are stored in `~/Library/Application Support/AirCron/jobs.json`:

```json
{
    "All Speakers": [
        {"id": "...", "zone": "All Speakers", ...}
    ],
    "Office": [
        {"id": "...", "zone": "Office", ...}
    ],
    "Custom:Office,Conference": [
        {"id": "...", "zone": "Custom:Office,Conference", ...}
    ]
}
```

**Atomic Writes:**
- File locking prevents corruption
- Backup created on each write
- Corrupt files auto-recover from backup

### 3. Cron Application

```
User clicks "Apply" → POST /api/cron/apply → CronManager.apply_jobs_to_cron()
    → Backup crontab → Generate cron lines → Replace AirCron section
```

**Cron Entry Format:**

```
# All Speakers
# Play 09:00
30 8 * * 1,2,3,4,5 /path/to/aircron_run.sh "All Speakers" play "spotify:playlist:..." "" spotify
```

**Breakdown:**
```
30      8    * * 1,2,3,4,5  command
↓       ↓              ↓
minute  hour    days     zone    action    arg1  arg2  service
```

### 4. Execution

When cron triggers:

```
cron → aircron_run.sh "All Speakers" play "uri" "" "spotify"
    → AppleScript to Music.app/Airfoil → Audio output
```

See `docs/cron-system.md` for execution details.

### 5. Deletion

```
User clicks delete → DELETE /api/jobs/{zone}/{id}
    → jobs_service.delete_job() → JobsStore.delete_job()
    → Remove from jobs.json
```

**Note:** Deletion doesn't automatically update cron. User must "Apply" to remove from crontab.

---

## Conflict Detection

### Time Conflicts

Jobs cannot overlap in time and day within the same zone:

```python
# Conflict: Same time, overlapping days, same zone
Job A: Monday 09:00, Office
Job B: Monday, Wednesday 09:00, Office  # CONFLICT!

# No conflict: Different zones
Job A: Monday 09:00, Office
Job B: Monday 09:00, Lobby  # OK - different zones

# No conflict: Different times
Job A: Monday 09:00, Office
Job B: Monday 10:00, Office  # OK - different times
```

**Validation:** Occurs in `JobsStore.add_job()` (`app/jobs_store.py:222-228`)

---

## Job Status

Jobs can have two statuses:

### pending

Job exists in `jobs.json` but not yet applied to crontab.

### applied

Job exists in both `jobs.json` and crontab.

**Status Detection:**

```python
# Compare normalized cron lines
if normalized_cron_line in current_crontab:
    status = "applied"
else:
    status = "pending"
```

---

## API Reference

### Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/jobs/<zone>` | Get jobs for zone |
| POST | `/api/jobs/<zone>` | Create job |
| PUT | `/api/jobs/<zone>/<id>` | Update job |
| DELETE | `/api/jobs/<zone>/<id>` | Delete job |
| GET | `/api/jobs/all` | Get all jobs (flat list) |

### Response Format

Success (200/201):
```json
{
    "id": "abc12345",
    "zone": "All Speakers",
    "days": [1, 2, 3, 4, 5],
    "time": "09:00",
    "action": "play",
    "args": {"uri": "..."},
    "label": "Morning Playlist",
    "service": "spotify"
}
```

Error (400/404/409):
```json
{
    "error": "Human-readable error message"
}
```

---

## Data Migration

Jobs are automatically migrated when adding new fields:

**Example: Service Field Migration**

```python
# jobs_store.py:100-104
for job_list in jobs.values():
    for job_dict in job_list:
        if "service" not in job_dict:
            job_dict["service"] = "spotify"  # Default
            changed = True
```

---

## See Also

- **Cron System**: `docs/cron-system.md`
- **Speaker System**: `docs/speaker-system.md`
- **Service Layer**: `app/services/AGENTS.md`
- **Main Documentation**: `AGENTS.md`
