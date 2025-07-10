# Apple Music Integration — Design & Progress Tracker

## Context

AirCron currently supports Spotify for scheduled playback, volume, and zone control via Airfoil. We want to add support for Apple Music, so users can schedule Apple Music and Spotify jobs simultaneously (to different zones), with the same UI/UX simplicity. This file tracks all design decisions, requirements, and implementation progress for this feature.

---

## Goals

- Allow users to schedule Apple Music playlist playback, volume, and zone control, just like Spotify.
- Support simultaneous jobs: Spotify and Apple Music can play at the same time (to different zones).
- UI/UX for Apple Music jobs/playlists should match existing Spotify flows.
- All changes must follow AirCron rules: clean code, strict error handling, no breakage, full test coverage.

---

## High-Level Requirements

- [x] Users can add Apple Music playlists to the system (with name/ID, like Spotify URIs)
- [x] Users can create jobs for Apple Music (play, pause, resume, volume) in any zone
- [x] Users can create jobs to connect/disconnect speaker zones from an audio source (Spotify/Apple Music)
- [x] UI clearly distinguishes between Spotify and Apple Music jobs/playlists
- [x] Backend supports both services, with correct validation and cron generation for all actions
- [x] Shell script can control Apple Music and Spotify via AppleScript and CLI
- [x] Speaker routing (connect/disconnect/source selection) works for both services via Airfoil
- [x] All endpoints and tests updated for new cases, including connect/disconnect actions

---

## Architecture Changes

### Data Model

- Add `service: "spotify" | "applemusic"` to jobs and playlists.
- Add `connect` and `disconnect` to the allowed `action` types.
- For Apple Music, `args` may be `{ "playlist": <name> }`. For volume, `{ "volume": <int> }`.
- For `connect`, `disconnect`, `pause`, `resume`, `args` is empty.

### API/Backend

- Update all job/playlist endpoints to handle `service`.
- Validation ensures correct args for each service and action.
- Cron generation creates correct shell command for all job types.
- `aircron_run.sh` is now action-centric, dispatching to helper functions.

### UI/UX

- Add service selector for all relevant actions (play, pause, resume, volume, connect).
- Update job modal to show/hide fields contextually (e.g., no playlist field for 'connect').
- Add `connect`/`disconnect` to the actions list.
- Labels and help text clarify the purpose of each action (e.g., "Application Audio Source").

### Shell/AppleScript

- AppleScript commands for Apple Music playback, volume, and source selection in Airfoil.
- Shell script refactored with helper functions for `connect_speakers`, `disconnect_speakers`, and `set_airfoil_source`.
- Main dispatcher in shell script correctly handles all actions for both services.

### Speaker Routing

- `connect` action explicitly sets the Airfoil source to "Spotify" or "Music" app.
- `connect` / `disconnect` actions manage speaker connections for any zone.
- This architecture robustly supports simultaneous playback to different zones.

### Testing

- Add/extend tests for all new Apple Music cases.
- Add/extend tests for `connect` and `disconnect` actions.
- Assert correct HTTP status codes for all new error types.

---

## Implementation Checklist

### Data Model

- [x] Add `service` field to jobs and playlists.
- [x] Add `connect`/`disconnect` actions to `jobs_service.py` validation.

### UI/UX

- [x] Update job creation modal for service selection for all relevant actions.
- [x] Update job modal with `connect`/`disconnect` actions and contextual fields/labels.
- [x] Update playlist management for Apple Music.
- [x] Update schedule and job list views to show service.

### Backend/API

- [x] Update job/playlist endpoints for `service`.
- [x] Update validation logic for all actions and services.
- [x] Update cron job generation for all actions.
- [x] Update all error handling and tests.

### Shell/AppleScript

- [x] Add AppleScript for Apple Music playback/volume/source selection.
- [x] Refactor `aircron_run.sh` to be action-centric with helper functions.
- [x] Test all actions from shell.

### Speaker Routing

- [x] Implement `connect`/`disconnect` logic in shell script.
- [x] Implement Airfoil source selection logic.
- [x] Test simultaneous playback to different zones.

### Testing

- [x] Add/extend tests for all new API cases (Apple Music, connect, disconnect).
- [x] Add integration tests for all job types.
- [x] Manual QA: UI, cron, playback, and all error cases are confirmed working.

---

## Open Questions / Decisions

- **How to uniquely identify Apple Music playlists?**
  - _Decision_: Using the playlist name is sufficient for `osascript` control and user-friendliness.
- **Any Apple Music-specific error cases to handle?**
  - _Decision_: The main error is the Music app not running or a playlist not found. `osascript` handles these gracefully; our script logs the events.
- **How to handle user confusion if both services are scheduled to the same zone at the same time?**
  - _Decision_: This was resolved by introducing the `connect` action. This action explicitly sets the audio source in Airfoil for a given zone, making the user's intent clear and preventing conflicts.

---

## Progress Log

- 2025-07-07: Design phase started.
- 2025-07-08: **Phase 1 (Model & API)**, **Phase 2 (UI)**, and **Phase 3 (Shell/Cron)** for basic Apple Music support completed.
- 2025-07-09: **Phase 4 started: Bug Fixes & Architectural Refinement.**
  - **Identified Bug**: Generic actions (`pause`, `volume`) were incorrectly hardcoded to Spotify, breaking Apple Music control.
  - **Identified Architectural Flaw**: The original model of tying all actions to speaker zones was insufficient for a multi-service environment.
- 2025-07-09: **Phase 4 completed: `Connect`/`Disconnect` Implemented.**
  - Introduced `connect` and `disconnect` actions to give users granular control over speaker zones and audio sources.
  - Refactored the entire `aircron_run.sh` script to be action-centric, improving maintainability and fixing all service-related bugs.
  - Updated the UI to be fully contextual, with clear labels and help text for the new, more powerful actions.
  - Added comprehensive tests for all new functionality.
- [x] **Project Complete:** All initial goals met, and the architecture is now robust and flexible for future enhancements.

### Shell/AppleScript

- [x] Add AppleScript for Apple Music playback/volume
- [x] Update `aircron_run.sh` to handle all actions for both services
- [x] Test all actions from shell

---

## References

- See `.cursor/rules/general-rules.mdc` and `README.md` for all project rules and architecture constraints.
