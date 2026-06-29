# Speaker System Documentation

## Overview

The Speaker system manages discovery and control of AirPlay/Airfoil speakers. It provides integration with Airfoil via AppleScript for multi-room audio distribution.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Frontend Layer                      │
│  ┌────────────────┐  ┌──────────────────────────┐   │
│  │  Control Panel │  │   Schedule View          │   │
│  │  (live control)│  │   (job configuration)    │   │
│  └────────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              Speakers Service Layer                  │
│  ┌──────────────────────────────────────────────┐  │
│  │  speakers_service.py                          │  │
│  │  - list_speakers()                            │  │
│  │  - refresh_speakers()                         │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              Speaker Discovery Module                │
│  ┌──────────────────────────────────────────────┐  │
│  │  speakers.py                                  │  │
│  │  - get_available_speakers()                   │  │
│  │  - refresh_speakers()                         │  │
│  │  - is_airfoil_running()                       │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│                  Airfoil (AppleScript)               │
│  - Speaker discovery                                │
│  - Connection management                            │
│  - Per-speaker volume control                       │
└─────────────────────────────────────────────────────┘
```

## Speaker Discovery

### Discovery Process

1. **Check Airfoil** - Verify Airfoil application is running
2. **AppleScript Query** - Request available speakers from Airfoil
3. **Parse Results** - Extract speaker names
4. **Cache Results** - Store for UI rendering

### Implementation

**Location:** `app/speakers.py`

```python
def get_available_speakers() -> List[str]:
    """Get list of available speakers from Airfoil."""
    if not is_airfoil_running():
        return ["All Speakers"]
    # AppleScript to query Airfoil for speakers
    # Returns: ["Office", "Conference Room", "Lobby", ...]
```

### Refreshing

Speakers can be refreshed on-demand:

```python
def refresh_speakers() -> List[str]:
    """Force Airfoil to rescan for speakers."""
    # Triggers Airfoil speaker discovery
    # Returns updated list
```

**Triggered by:**
- User clicking "Refresh Speakers" button
- Initial application load
- Periodic checks (if implemented)

## Zone Types

### 1. All Speakers

Special zone representing all available speakers.

**Format:** `"All Speakers"`

**Behavior:**
- Always available, even if no speakers discovered
- Targets all speakers simultaneously
- Volume controls application (global) volume
- Cannot be combined with other speakers

**Use Cases:**
- "Play everywhere" scenarios
- Global pause/resume
- Master volume control

### 2. Individual Speakers

Single speaker identified by name.

**Format:** `"Office"`, `"Conference Room"`, etc.

**Behavior:**
- Controls only the named speaker
- Volume controls service-specific per-speaker volume
- Can be combined into custom zones

**Discovery:** Speaker names come from Airfoil

### 3. Custom Zones

User-defined combinations of speakers.

**Format:** `"Custom:Office,Conference Room,Lobby"`

**Prefix:** `"Custom:"`

**Separator:** Comma (`, `)

**Behavior:**
- Connects all listed speakers
- Volume controls per-speaker volume
- Created by multi-select in UI

**Example:**
```
User selects: [Office, Conference Room]
Zone created: "Custom:Office,Conference Room"
```

## Volume Control

### Two Scope Types

#### Global Application Volume

- **Zone:** "All Speakers"
- **Target:** Spotify/Music.app volume
- **Control:** Application-level volume

**Implementation:**
```bash
# Via AppleScript to Music.app/Spotify
osascript -e 'tell application "Spotify" to set sound volume to 75'
```

#### Per-Speaker Volume

- **Zone:** Individual or Custom zones
- **Spotify Target:** Airfoil speaker volume
- **Apple Music Target:** Music.app AirPlay device sound volume
- **Control:** Service-specific per-speaker volume

**Implementation:**
```bash
# Spotify via AppleScript to Airfoil
osascript -e 'tell application "Airfoil" to set volume of speaker "Office" to 75'

# Apple Music via AppleScript to Music.app AirPlay device volume
osascript -e 'tell application "Music" to repeat with d in (every AirPlay device)
    if name of d is "Office" then set sound volume of d to 75
end repeat'
```

### Volume API

**Control Service:** `app/services/control_service.py`

```python
def run_control_action(data):
    if action == "volume":
        volume = data["args"]["volume"]  # 0-100
        zone = data["zone"]

        if zone == "All Speakers":
            # Set app volume
            set_apple_music_volume(volume)
        else:
            # Set service-specific speaker/device volume
            for speaker in parse_zone(zone):
                set_speaker_volume(service, speaker, volume)
```

## Connection Management

### Connect Flow

```
User selects speakers → Click "Connect"
    ↓
Control service → aircron_run.sh connect {zone} {service}
    ↓
1. Disconnect all speakers (cleanup)
2. Connect target speakers via Airfoil
3. Start playback (if applicable)
```

### Disconnect Flow

```
User clicks "Disconnect"
    ↓
Control service → aircron_run.sh disconnect {zone} {service}
    ↓
Disconnect target speakers via Airfoil
```

### Service Awareness

Speakers are connected per-service:
- **Spotify speakers** - Connect when playing Spotify
- **Apple Music speakers** - Connect when playing Apple Music

**Reasoning:** Different apps may have different speaker configurations.

## Apple Music "Ignore" Behavior

### Special Case

Apple Music is treated differently for "All Speakers" operations.

**Git History Note:**
> "adjustment for apple music to be ignored from set all"

**Current Behavior:**

When `zone == "All Speakers"` and `service == "applemusic"`:
- Speaker connection may be skipped
- Focus is on Music.app playback control

**Rationale:** Apple Music's integration works differently than Spotify's CLI approach.

## Frontend Integration

### Speaker Selection

**File:** `static/control-panel.js`

**Components:**
1. Speaker checkbox list
2. "All Speakers" checkbox with mutual exclusion
3. Zone building from selection

**Zone Building Logic:**

```javascript
function buildZoneFromSelection(root) {
    const selected = Array.from(root.querySelectorAll("input:checked"))
        .map(cb => cb.value);

    if (selected.includes("All Speakers")) return "All Speakers";
    if (selected.length === 1) return selected[0];
    return `Custom:${selected.join(",")}`;
}
```

### "All Speakers" UI Logic

When "All Speakers" is checked:
- Individual checkboxes disabled
- Visual opacity reduced
- Zone becomes "All Speakers"

```javascript
function updateSpeakerCheckboxes(root) {
    const allBox = root.querySelector('input[value="All Speakers"]');
    const others = Array.from(root.querySelectorAll("input"))
        .filter(cb => cb.value !== "All Speakers");

    if (allBox.checked) {
        others.forEach(cb => {
            cb.checked = false;
            cb.disabled = true;
            cb.parentElement.classList.add("opacity-50");
        });
    } else {
        others.forEach(cb => {
            cb.disabled = false;
            cb.parentElement.classList.remove("opacity-50");
        });
    }
}
```

## API Reference

### Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/speakers` | List available speakers |
| POST | `/api/speakers/refresh` | Force speaker refresh |

### Response Format

**Success:**
```json
{
    "speakers": ["Office", "Conference Room", "Lobby", "Kitchen"]
}
```

**Error:**
```json
{
    "error": "Failed to list speakers"
}
```

## Troubleshooting

### No Speakers Discovered

**Symptoms:** Speaker list only shows "All Speakers"

**Possible Causes:**
1. Airfoil not running
2. No AirPlay speakers on network
3. AppleScript permissions denied

**Solutions:**
1. Start Airfoil application
2. Check network for AirPlay devices
3. Grant AppleScript permissions in System Settings

### Speakers Won't Connect

**Symptoms:** Connect action fails silently

**Possible Causes:**
1. Speakers already connected to another source
2. Network issues
3. Airfoil not responding

**Solutions:**
1. Check Airfoil speaker status
2. Restart Airfoil
3. Verify network connectivity

### Volume Not Changing

**Symptoms:** Volume action has no effect

**Possible Causes:**
1. Wrong volume scope (global vs per-speaker)
2. Application not running
3. Airfoil speaker disconnected or Music.app AirPlay device name mismatch
4. AppleScript command failed; see `~/Library/Logs/AirCron/cron.log`

**Solutions:**
1. Verify zone matches intended scope
2. Start Spotify/Music.app
3. Check speaker connection status
4. For Apple Music, verify the selected name matches a Music.app AirPlay device name

## See Also

- **Jobs System**: `docs/jobs-system.md`
- **Cron System**: `docs/cron-system.md`
- **Service Layer**: `app/services/AGENTS.md`
- **Frontend Architecture**: `static/AGENTS.md`
