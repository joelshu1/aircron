# Cron System Documentation

## Overview

AirCron integrates with macOS cron to execute scheduled jobs. The system uses a sandboxed approach, only modifying entries between special markers in the crontab, ensuring user's other cron jobs remain untouched.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Frontend Layer                     │
│  ┌───────────────────────────────────────────────┐  │
│  │  "Review & Apply" Button → Cron Review Modal  │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│                 Cron Service Layer                   │
│  ┌───────────────────────────────────────────────┐  │
│  │  cron_service.py                               │  │
│  │  - apply_jobs_to_cron()                        │  │
│  │  - get_cron_status()                           │  │
│  │  - get_cron_preview()                          │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│                 Cron Manager Module                  │
│  ┌───────────────────────────────────────────────┐  │
│  │  cronblock.py (CronManager)                    │  │
│  │  - apply_jobs_to_cron()                        │  │
│  │  - _generate_cron_lines()                      │  │
│  │  - _job_to_cron_line()                         │  │
│  │  - _backup_crontab()                           │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              System Crontab                          │
│  ┌───────────────────────────────────────────────┐  │
│  │  # User's other cron jobs                     │  │
│  │  # BEGIN AirCron (auto-generated...)          │  │
│  │  # AirCron managed entries                    │  │
│  │  # END AirCron                                 │  │
│  │  # More user jobs                             │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Sandboxing

### Marker System

AirCron only modifies lines between special markers:

```
# BEGIN AirCron (auto-generated; do not edit between markers)
# ... AirCron entries ...
# END AirCron
```

**Constants:** `app/cronblock.py:18-20`

```python
AIRCRON_BEGIN = "# BEGIN AirCron (auto-generated; do not edit between markers)"
AIRCRON_END = "# END AirCron"
```

### Apply Process

```
1. Read current crontab
2. Create backup (~/aircron_backup_TIMESTAMP.txt)
3. Find AirCron section (or create at end)
4. Generate new cron lines from jobs.json
5. Replace section with new entries
6. Write new crontab atomically
```

**Code Reference:** `app/cronblock.py:206-252`

## Cron Entry Format

### Structure

```
# {zone}
# {action} {time}
{minute} {hour} * * {days} {full_script_path} "{zone}" {action} "{arg1}" "{arg2}" {service}
```

### Example Entries

```
# All Speakers
# Play 09:00
30 8 * * 1,2,3,4,5 /usr/local/bin/aircron_run.sh "All Speakers" play "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M" "" spotify

# Office
# Pause 17:00
0 17 * * 1,2,3,4,5 /usr/local/bin/aircron_run.sh "Office" pause "" "" spotify

# Conference Room
# Volume 10:00
0 10 * * 1,2,3,4,5 /usr/local/bin/aircron_run.sh "Conference Room" volume "75" "" spotify

# Custom:Office,Lobby
# Connect 08:55
55 8 * * 1,2,3,4,5 /usr/local/bin/aircron_run.sh "Custom:Office,Lobby" connect "" "" spotify
```

### Field Breakdown

| Field | Example | Description |
|-------|---------|-------------|
| minute | `30` | Minute (0-59) |
| hour | `8` | Hour (0-23, 24-hour format) |
| `*` | `*` | Every day of month |
| `*` | `*` | Every month |
| days | `1,2,3,4,5` | Days of week (0=Sun, 6=Sat) |
| script | `/path/to/aircron_run.sh` | Full path to execution script |
| zone | `"All Speakers"` | Target zone (quoted) |
| action | `play` | Action to perform |
| arg1 | `"spotify:playlist:..."` | Action argument (URI, volume, etc.) |
| arg2 | `""` | Reserved for future use |
| service | `spotify` | Music service |

### Day Conversion

**AirCron Format (1=Mon, 7=Sun):**
```python
job.days = [1, 2, 3, 4, 5]  # Monday-Friday
```

**Cron Format (0=Sun):**
```
1,2,3,4,5  # Monday-Friday
```

**Conversion Code:** `app/cronblock.py:176`
```python
cron_days = [str(d % 7) for d in job.days]
# Sunday (7) becomes 0, others unchanged
```

## Execution

### aircron_run.sh

The script that cron executes for each job.

**Location:** Project root (auto-discovered)

**Usage:**
```bash
./aircron_run.sh "{zone}" "{action}" "{arg1}" "{arg2}" "{service}"
```

### Execution Flow

```
cron triggers at scheduled time
    ↓
aircron_run.sh {zone} {action} {arg1} {arg2} {service}
    ↓
1. Parse arguments
2. Determine service (spotify/applemusic)
3. Execute action via AppleScript/CLI
    ↓
Audio output to speakers
```

### Action Implementation

| Action | Spotify Implementation | Apple Music Implementation |
|--------|----------------------|---------------------------|
| play | `spotify play {uri}` | AppleScript to Music.app |
| pause | `spotify pause` | AppleScript pause |
| resume | `spotify resume` | AppleScript play |
| volume | `All Speakers`: Spotify app volume; individual/custom zones: Airfoil speaker volume | `All Speakers`: Music.app sound volume; individual/custom zones: Music.app AirPlay device `sound volume` |
| connect | Airfoil AppleScript | Airfoil AppleScript |
| disconnect | Airfoil AppleScript | Airfoil AppleScript |

## Status Tracking

### Cron Desync Detection

The system detects when `jobs.json` and crontab are out of sync.

**Detection Logic:** `app/services/cron_service.py:38-92`

```python
def get_cron_status():
    # Get current crontab entries
    current_lines = cron_manager._get_current_crontab()
    current_cron_jobs = extract_aircron_entries(current_lines)

    # Get expected entries from jobs.json
    all_jobs = jobs_store.get_all_jobs()
    expected_cron_jobs = [generate_cron_line(job) for job in all_jobs]

    # Compare
    cron_desync = (len(all_jobs) > 0) and (len(current_cron_jobs) == 0)

    return {
        "cron_desync": cron_desync,
        "jobs_match": set(current) == set(expected),
        "needs_apply": len(all_jobs) > 0 and not jobs_match
    }
```

### Status Values

| Status | Description |
|--------|-------------|
| `applied` | Job exists in both jobs.json and crontab |
| `pending` | Job exists in jobs.json but not crontab |
| `desync` | jobs.json has jobs but crontab is empty |

### Frontend Behavior

When `cron_desync == true`:
- Warning banner displayed
- "Apply to Cron" button highlighted
- User prompted to apply changes

## Backup System

### Automatic Backups

Every time crontab is modified, a backup is created.

**Location:** `~/aircron_backup_YYYYMMDDTHHMMSS.txt`

**Format:** Complete crontab contents (not just AirCron section)

**Code Reference:** `app/cronblock.py:98-108`

```python
def _backup_crontab(self, lines: List[str]) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    backup_file = Path.home() / f"aircron_backup_{timestamp}.txt"
    backup_file.write_text("\n".join(lines) + "\n")
```

### Restoration

To restore from backup:
```bash
crontab ~/aircron_backup_20240101T120000.txt
```

## Script Discovery

The `CronManager` searches multiple locations for `aircron_run.sh`:

**Search Order:** `app/cronblock.py:38-80`

1. Current working directory: `./aircron_run.sh`
2. Project root: `{project}/aircron_run.sh`
3. App support directory: `~/Library/Application Support/AirCron/aircron_run.sh`
4. System locations: `/usr/local/bin/aircron_run.sh`, `/usr/bin/aircron_run.sh`

**Fallback:** Uses `/usr/local/bin/aircron_run.sh` if not found elsewhere

## Validation

### Cron Syntax Validation

Before applying jobs, cron syntax is validated using `croniter`.

**Code Reference:** `app/cronblock.py:254-277`

```python
def validate_cron_syntax(self, time: str, days: List[int]) -> bool:
    hour_str, minute_str = time.split(":")
    hour = int(hour_str)
    minute = int(minute_str)

    # Convert days to cron format
    cron_days = [str(d % 7) for d in days]
    days_str = ",".join(sorted(cron_days, key=lambda x: int(x)))

    # Test with croniter
    try:
        croniter(f"{minute} {hour} * * {days_str}")
        return True
    except:
        return False
```

### Validation Points

1. **Job Creation** - Validated before saving to jobs.json
2. **Job Update** - Validated before modifying jobs.json
3. **Cron Apply** - All jobs validated before writing crontab

## API Reference

### Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/cron/apply` | Apply jobs to crontab |
| GET | `/api/cron/status` | Get sync status |
| GET | `/api/cron/preview` | Preview changes |
| GET | `/api/cron/current` | Get current AirCron section |
| GET | `/api/cron/all` | Get all jobs with status |

### Status Response

```json
{
    "has_aircron_section": true,
    "has_jobs_in_cron": true,
    "total_stored_jobs": 15,
    "current_cron_jobs_count": 12,
    "expected_cron_jobs_count": 15,
    "jobs_match": false,
    "needs_apply": true,
    "cron_desync": false,
    "current_cron_jobs": [...],
    "expected_cron_jobs": [...]
}
```

### Preview Response

```json
{
    "has_changes": true,
    "total_changes": 5,
    "timestamp": "2024-01-01T12:00:00",
    "job_details": [
        {
            "zone": "All Speakers",
            "job": {...},
            "cron_line": "...",
            "status": "will_add"
        }
    ]
}
```

## Troubleshooting

### Jobs Not Executing

**Check 1: Verify Crontab**
```bash
crontab -l | grep -A 100 "BEGIN AirCron"
```

**Check 2: Verify Script Permissions**
```bash
ls -l aircron_run.sh
# Should show -rwxr-xr-x (executable)
```

**Check 3: Test Manual Execution**
```bash
./aircron_run.sh "All Speakers" play "spotify:playlist:..." "" "spotify"
```

**Check 4: Check Logs**
```bash
tail -f ~/Library/Logs/AirCron/aircron.log
```

### Crontab Corruption

**Symptoms:** `crontab -l` shows errors or nothing

**Solution:**
```bash
# Find latest backup
ls -lt ~/aircron_backup_*.txt | head -1

# Restore from backup
crontab ~/aircron_backup_YYYYMMDDTHHMMSS.txt
```

### Permission Denied

**Symptoms:** Cron jobs fail with "Permission denied"

**Solution:**
```bash
# Make script executable
chmod +x aircron_run.sh

# Ensure correct ownership
sudo chown $USER:staff aircron_run.sh
```

## See Also

- **Jobs System**: `docs/jobs-system.md`
- **Speaker System**: `docs/speaker-system.md`
- **Service Layer**: `app/services/AGENTS.md`
- **Main Documentation**: `AGENTS.md`
