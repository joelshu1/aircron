# AirCron Frontend Architecture

## Overview

The AirCron frontend is built with **modular vanilla JavaScript** and **HTMX**. It follows a clean architecture with separation of concerns, avoiding framework complexity while maintaining maintainability.

## Technology Stack

- **HTMX** - Dynamic HTML updates without heavy JavaScript
- **Tailwind CSS** - Utility-first styling
- **Vanilla JavaScript (ES6+)** - No frameworks, modular design
- **Jinja2 Templates** - Server-side rendering

## Module Organization

The frontend is split into focused modules (584 lines total across 6 files):

```
static/
├── app.js                # Main coordinator (18 lines)
├── app-core.js           # Core utilities (27 lines)
├── notifications.js      # Toast notification system (36 lines)
├── modal-manager.js      # Modal operations (349 lines)
├── schedule-view.js      # Schedule grid visualization (154 lines)
└── control-panel.js      # Control panel drawer (259 lines)
```

### Loading Order

Modules are loaded in `templates/base.html` in this order:
1. `app-core.js` - Core utilities and state
2. `notifications.js` - Toast system
3. `modal-manager.js` - Modal operations
4. `schedule-view.js` - Schedule visualization
5. `control-panel.js` - Control panel
6. `app.js` - Main coordinator

---

## Global Namespace

All modules extend the `window.AirCron` namespace:

```javascript
window.AirCron = window.AirCron || {};
```

### Global State

Located in `app-core.js:6-11`:

```javascript
window.AirCron.state = {
    jobs: [],          // All jobs loaded from API
    speakers: [],      // Available speakers
    filters: [],       // Active zone filters
    selectedDay: 1,    // Currently selected day (1-7)
};
```

### Other Global Variables

- `window.allJobs` - Flat list of all jobs (used by schedule-view.js)
- `window.currentZone` - Currently viewed zone (for refresh)

---

## Module Reference

### app-core.js

**Purpose:** Core utilities and shared functions

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `window.AirCron.closeModal()` | Close active modal |
| `window.AirCron.openModal(url)` | Open modal via HTMX or fetch |
| `window.AirCron.showStatus(message, type)` | Show status message in `#status-message` |
| `window.AirCron.applyCron()` | Apply jobs to cron via API |
| `window.AirCron.refreshSpeakers()` | Refresh speaker list from API |

**Known Issue:** Duplicate `closeModal()` implementation exists in `modal-manager.js:206-215`. The modal-manager version removes and recreates the DOM element, while app-core just clears innerHTML.

---

### notifications.js

**Purpose:** Toast notification system

**Key Function:**

```javascript
window.AirCron.showNotification(message, type = "info")
```

**Types:** `info`, `success`, `error`, `warning`

**Behavior:** Auto-removes after 4 seconds, includes dismiss button

---

### app.js

**Purpose:** Main coordinator and global functions

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `window.editPlaylist(id)` | Open edit playlist modal |
| `window.deletePlaylist(id)` | Delete playlist with confirmation |

---

### schedule-view.js

**Purpose:** Schedule grid visualization and job management

**State:** Uses `window.AirCron.state` for local state

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `window.AirCron.refreshJobs()` | Load all jobs from API |
| `window.AirCron.renderFilters()` | Render zone filter checkboxes |
| `window.AirCron.openAddSchedule({day, time})` | Open add job modal with prefill |

**Components:**

- **Hourly Table** (`renderHourlyTable()`) - 24-hour grid showing jobs
- **Filter Pills** - Active zone filters with remove buttons
- **Filter Panel** - Checkbox list for zone selection
- **Tooltip** - Speaker list on hover for custom zones

**Job Cards in Schedule:**

Each job displays:
- Label or action name
- Time
- Service icon (🎵 Spotify, 🍎 Apple Music)
- Zone name
- Speaker count for custom zones
- Edit and delete buttons

**Event Handlers:**

- Row click → Open add job modal with pre-filled time
- Edit button → Open edit modal
- Delete button → Confirm and delete via API

---

### control-panel.js

**Purpose:** Live audio control drawer

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `window.AirCron.toggleControlPanel(open)` | Open/close drawer |
| `window.AirCron.renderControlPanelSpeakers()` | Render speaker checkboxes |
| `sendControlAction(action, args, options)` | Send control command to API |

**UI Components:**

1. **Service Selector** - Spotify/Apple Music toggle
2. **Playlist Dropdown** - Saved playlists for selected service
3. **Speaker Checkboxes** - Multi-select with "All Speakers" logic
4. **Control Buttons** - Connect, Disconnect, Play, Pause
5. **Volume Control** - Slider with global/per-speaker toggle

**"All Speakers" Logic:**

When "All Speakers" is checked:
- Individual speakers are disabled
- Zone becomes "All Speakers"
- Volume applies to global app volume

**Volume Target Toggle:**

- **Global** - Sets application volume (Spotify/Music.app)
- **Per-Speaker** - Sets Airfoil speaker volume (requires specific speakers)

---

### modal-manager.js

**Purpose:** Modal operations and cron review UI

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `window.AirCron.showCronReviewModal()` | Open cron review modal |
| `window.AirCron.initCronReviewModal()` | Initialize modal after HTMX load |
| `window.AirCron.formatJobCard(jobDetail, statusType)` | Format job card HTML |
| `window.AirCron.formatJobDiff(diffs)` | Format change diff HTML |

**Cron Review Modal Flow:**

1. User clicks "Review & Apply"
2. `showCronReviewModal()` loads modal via HTMX
3. `initCronReviewModal()` fetches preview from API
4. Jobs grouped by status: will_add, will_remove, unchanged
5. "Apply Changes" button calls `/api/cron/apply`

**Status Badges:**

| Status | Color | Description |
|--------|-------|-------------|
| will_add | Green | Job will be added to crontab |
| will_remove | Red | Job will be removed from crontab |
| unchanged | Gray | No changes to this job |

---

## HTMX Integration

HTMX is used for dynamic content loading without page refreshes.

### Modal Loading

Modals are loaded via HTMX:

```html
<button hx-get="/modal/add/All%20Speakers"
        hx-target="#modal-container"
        hx-swap="innerHTML">
    Add Job
</button>
```

### Zone Content Loading

Zone content is loaded dynamically:

```html
<div hx-get="/zone/Office"
     hx-target="#zone-content"
     hx-trigger="load">
    <!-- Office zone jobs -->
</div>
```

### HTMX Configuration

```html
<meta name="htmx-config" content='{"defaultSwapStyle":"innerHTML"}'>
```

---

## Modal System

### Modal Container

```html
<div id="modal-container"></div>
```

Created in `<body>` if missing.

### Modal Lifecycle

1. **Open** - `openModal(url)` or HTMX request
2. **Load** - HTML inserted into `#modal-container`
3. **Initialize** - Module-specific init functions called
4. **Close** - `closeModal()` clears or removes container

### Modal Types

| Type | Route | Purpose |
|------|-------|---------|
| Add Job | `/modal/add/<zone>` | Create new job |
| Edit Job | `/modal/edit/<zone>/<id>` | Edit existing job |
| Cron Review | `/modal/cron/review` | Review cron changes |
| Add Playlist | `/modal/playlist/add` | Create playlist |
| Edit Playlist | `/modal/playlist/edit/<id>` | Edit playlist |

---

## API Communication

### Fetch Wrapper Pattern

Most modules use bare `fetch()` with Promise chains:

```javascript
fetch("/api/jobs/all")
    .then(r => r.json())
    .then(data => {
        // Handle data
    })
    .catch(err => {
        // Handle error
    });
```

**TODO:** Consider adding a centralized fetch wrapper with error handling.

### Error Handling

API errors are displayed via notifications:

```javascript
.catch(err => {
    if (window.AirCron.showNotification) {
        window.AirCron.showNotification(err.message, "error");
    }
});
```

---

## State Management

### Current Pattern

State is scattered across:
- `window.AirCron.state` - Global state object
- Local variables in modules (e.g., `state` in schedule-view.js)
- Module-level closures (e.g., `reviewData` in initCronReviewModal)

### State Updates

After data changes:
1. Update global state
2. Re-render affected components
3. Show success notification

**Example - After Job Delete:**
```javascript
window.AirCron.refreshJobs();  // Reload from API
window.AirCron.applyCron();    // Prompt to apply
```

---

## Styling

### Tailwind CSS

All styling uses Tailwind utility classes. Common patterns:

| Purpose | Classes |
|---------|---------|
| Buttons | `px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600` |
| Inputs | `border rounded px-3 py-2` |
| Cards | `border rounded-lg p-4` |
| Modals | `fixed inset-0 bg-black bg-opacity-50` |

### Color Coding

| Type | Colors |
|------|--------|
| Success | `bg-green-500`, `text-green-800` |
| Error | `bg-red-500`, `text-red-800` |
| Warning | `bg-yellow-500`, `text-yellow-800` |
| Info | `bg-blue-500`, `text-blue-800` |

---

## Known Issues

1. **Duplicate closeModal()** - Two implementations in app-core.js and modal-manager.js
2. **Promise Chains** - No async/await usage
3. **Large Functions** - `initCronReviewModal()` is 340+ lines
4. **Inline HTML** - Extensive HTML strings in JavaScript
5. **Mixed State** - State scattered across global and local variables

---

## Development Guidelines

### Adding New Features

1. **Choose module** - Use existing or create new module
2. **Extend namespace** - `window.AirCron.newFunction = ...`
3. **Use notifications** - Show feedback via `showNotification()`
4. **Handle errors** - Always include `.catch()` on fetch calls
5. **Update state** - Keep `window.AirCron.state` in sync

### Naming Conventions

- Functions: camelCase (`refreshJobs()`)
- Events: kebab-case (`data-zone-name`)
- IDs: kebab-case (`schedule-hourly-table`)
- Classes: Tailwind utilities only

### Code Organization

- Keep functions focused and under 50 lines
- Use module closures for private state
- Export public functions via `window.AirCron`
- Include JSDoc comments for complex functions

---

## See Also

- **Backend Architecture**: `app/AGENTS.md`
- **Service Layer**: `app/services/AGENTS.md`
- **Main Documentation**: `AGENTS.md`
- **Cron System**: `docs/cron-system.md`
