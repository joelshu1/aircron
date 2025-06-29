AirCron UI — Project Specification (v2.1, 2025-07-01)

Purpose — Replace manual script-editing & crontab -e with a lightweight menu-bar app that lets non-technical users schedule Spotify-CLI / Airfoil actions per speaker zone on a macOS 10.13 machine.

Audience — Developers building & maintaining the app; tech-savvy operators deploying it on the hotel's Mac Mini.

⸻

1 Scope & Goals

ID Goal
G-1 Discover active Airfoil speaker zones at runtime.
G-2 Show / edit schedules per zone and a global "All Speakers" group.
G-3 Persist schedules to a JSON store and to cron lines inside a sandboxed block: # BEGIN AirCron … # END AirCron.
G-4 Execute actions via an existing shell wrapper aircron_run.sh (already on disk).
G-5 Ship as a single drag-and-drop .app (PyInstaller bundle, ~35 MB) that auto-launches the default browser at http://127.0.0.1:3009/ and places a tray icon via rumps.
G-6 Provide a visual, color-coded, interactive schedule view for all jobs by day/hour, with edit/delete and speaker tooltips.

Out of scope (v1)
• Cross-platform support beyond this one macOS host.
• Complex AirPlay controls (multi-room sync etc. handled by Airfoil).

⸻

2 User Stories
• U-1 – Refresh speakers: "As a staff member I click Refresh to see all zones Airfoil currently lists as connected."
• U-2 – Add schedule: "I pick Living Room → Add schedule → Mon–Fri 07:30 → Play playlist → spotify:playlist:1234… and save."
• U-3 – Edit schedule: "I click ✏️ next to a job, change time to 08:00, save, and cron is updated."
• U-4 – Delete schedule: "I click 🗑 to remove a job; it disappears and cron rewrites without that line."
• U-5 – View schedule: "I open the 'View Schedule' tab, pick a day, and see a color-coded 24h grid of all jobs, with speaker tooltips and edit/delete."

⸻

3 System Architecture

flowchart TD
subgraph Tray App (PyInstaller)
A[rumps
• menu-bar icon
• opens browser] --> B[Flask server]
end
B -->|Shell| C[aircron_run.sh]
B -->|cron writer| D[`crontab`]
B -->|osascript| E[Airfoil.app]
C -->|CLI| F[spotify-cli]

3.1 Components

Component Language Key libs Notes
Tray runner Python 3.12 rumps Starts Flask in a background thread; opens browser on first launch.
Flask/HTMX server Python 3.12 Flask, htmx, croniter Provides REST & HTML.
Cron handler Python stdlib subprocess, tempfile Replaces only the AirCron block; backs up current crontab to ~/aircron*backup*<ISO>.txt.
Shell wrapper bash Exists already; signature becomes aircron_run.sh "<speaker>" <action> [args…].

⸻

4 Directory Layout

aircron-ui/
├── main.py # rumps + browser launcher
├── app/ # Flask package
│ ├── **init**.py # creates Flask app
│ ├── views.py # HTML routes (HTMX-friendly)
│ ├── api.py # JSON endpoints
│ ├── cronblock.py # read/write cron helpers
│ ├── speakers.py # Airfoil AppleScript wrapper
│ └── jobs_store.py # JSON persistence (~~/Library/Application Support/AirCron/jobs.json)
├── static/
│ └── app.js # small Alpine.js or vanilla helpers
├── templates/
│ └── index.html # one file; HTMX swaps panes
├── requirements.txt
└── build.sh # PyInstaller one-liner

⸻

5 Backend APIs (JSON)

Verb & Path Purpose Payload Response
GET /api/speakers Current zones from Airfoil – ["Kitchen","Living Room",…]
GET /api/jobs/<zone> All jobs for zone (global allowed) – [{id,label,days,time,action,args}]
POST /api/jobs/<zone> Create job {label:str,days:[1,2,3],time:"07:30",action:"play",args:{uri:"spotify:playlist:…"}} 201 JSON job
PUT /api/jobs/<zone>/<id> Update job … 200 JSON job
DELETE /api/jobs/<zone>/<id> Delete job – 204
GET /api/jobs/all All jobs (flat list, for schedule view) – {jobs:[{id,label,zone,days,time,action,args}]}
POST /api/cron/apply Rewrite crontab – {ok:true} or {error:…}

⸻

6 Cron Line Format

# BEGIN AirCron (auto-generated; do not edit between markers)

# Kitchen – Morning Jazz 07:30

30 7 \* \* 1-5 /usr/local/bin/aircron_run.sh "Kitchen" play "spotify:playlist:1234…"

# Kitchen – Stop 09:00

0 9 \* \* 1-5 /usr/local/bin/aircron_run.sh "Kitchen" pause

# END AirCron

One cron line per job.
cronblock.py keeps markers intact; anything outside them is untouched.

⸻

7 UI Flows & Wireframes

7.1 Main Layout (HTMX)

┌────────────────────────── AirCron ──────────────────────────┐
│ [Refresh 🔄] | Kitchen ▼ │
├─────────────────────────────────────────────────────────────┤
│ ■ Speakers (left sidebar) | ▢ Schedules (right pane) │
│ ─────────────────────────── | ─────────────────────────── │
│ ▸ Kitchen | [ + Add schedule ] │
│ ▸ Living Room | 1. Weekdays 07:30 ▶ Play… │
│ ▸ Patio | ✏️ 🗑 │
│ ▾ All Speakers | 2. Sat–Sun 18:00 ▶ Resume │
└─────────────────────────────────────────────────────────────┘

7.2 Add / Edit Modal

┌────────── Schedule ──────────┐
│ Label: [ Start the day ] │
│ Speakers: [ ] All Speakers [ ] Kitchen [ ] Living Room ... (scrollable multi-select) │
│ Days: □Mon □Tue … □Sun │
│ Time: [ 07 : 30 ] │
│ Action: (play ▾) │
│ ├─ play playlist │
│ ├─ resume last │
│ ├─ pause │
│ └─ volume fade │
│ Args: URI / Volume: [ … ] │
│ │
│ [Cancel] [ Save ] │
└──────────────────────────────┘

- The modal now requires a label (display name) for each job, shown in all lists and schedule views.
- The top of the modal features a scrollable, multi-select speaker area. The speaker(s) you clicked from are preselected, but you can select/deselect any others.
- If "All Speakers" is checked, all other checkboxes are disabled and visually greyed out. If you check all individual speakers, "All Speakers" will auto-check and the rest will be disabled.
- The modal supports both adding and editing jobs for any combination of speakers in a single step.

  7.3 View Schedule Tab

┌─────────────── View Schedule ───────────────┐
│ Select Day: [Mon][Tue][Wed][Thu][Fri][Sat][Sun] │
│ ─────────────────────────────────────────────── │
│ 00:00 | — │
│ 01:00 | — │
│ ... │
│ 07:00 | 🔈 Morning Jazz 07:30 (Play) ✏️ 🗑 │
│ ... │
│ 18:00 | 🔈 Evening Wind Down 18:00 (Pause) ✏️ 🗑 │
│ ... │
└──────────────────────────────────────────────┘

- Each job is color-coded by type: play=green, pause=yellow, resume=blue, volume=purple.
- Hovering the 🔈 icon shows a tooltip with the full speaker list for the job.
- Edit (✏️) and delete (🗑) buttons are available for each job in the grid.
- Empty and error states are clearly shown.

⸻

8 Build & Run Locally

# 1 Install Python 3.12 via pyenv (if not present)

pyenv install 3.12.3 ; pyenv local 3.12.3

# 2 Install deps

python -m pip install -r requirements.txt

# 3 Run in dev mode

python main.py # tray icon appears, browser opens

# 4 Build app

./build.sh # creates dist/AirCron.app (signed-ad-hoc)

build.sh (excerpt)

#!/usr/bin/env bash
pyinstaller \
 --windowed --onefile \
 --icon=assets/icon.icns \
 --name "AirCron" main.py

Codesign & notarisation are optional for internal distribution on macOS 10.13; Gatekeeper quarantines are disabled on that machine.

⸻

9 Testing Checklist

1. Speaker refresh returns the same list Airfoil GUI shows.
2. Adding a job writes one cron line and appears in crontab -l.
3. Deleting a job removes only that line, leaves others.
4. Backup file is created in ~/aircron_backup_YYYY-MM-DDTHHMMSS.txt.
5. Tray app auto-reconnects to Flask after reboot (launch agent plist provided in dist/com.orchid.aircron.plist).
6. View Schedule tab shows all jobs for the selected day, color-coded, with tooltips and working edit/delete.

⸻

Appendix A Sample aircron_run.sh

#!/usr/bin/env bash
SPEAKER="$1"; ACTION="$2"; shift 2
case "$ACTION" in
play) /usr/local/bin/spotify play "$@" && osascript -e "tell app \"Airfoil\" to connect (every speaker whose name is \"$SPEAKER\")" ;;
pause) /usr/local/bin/spotify pause ;;
resume) /usr/local/bin/spotify play ;;
volume) /usr/local/bin/spotify volume "$1" ;;
esac
