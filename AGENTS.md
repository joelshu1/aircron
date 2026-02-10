# AirCron - AI & Developer Documentation

## Overview

**AirCron** is a professional macOS audio scheduling application designed for environments like hotels, restaurants, and offices that require automated music management across multiple zones. It provides a web interface for managing Spotify and Apple Music playback across multiple AirPlay/Airfoil speaker zones.

### Key Features

- **Multi-Zone Audio Control**: Manage playback across individual speakers, custom groups, or all speakers simultaneously
- **Dual Service Support**: Full support for both Spotify and Apple Music
- **Visual Scheduling**: 24-hour grid visualization for intuitive schedule management
- **Cron Integration**: Direct integration with macOS cron for reliable scheduled execution
- **Web Interface**: Modern, responsive UI built with HTMX and modular JavaScript
- **Airfoil Integration**: Leverages Airfoil for multi-room audio distribution

## Architecture

AirCron follows a **layered service-oriented architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Interface (HTMX)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Schedule    │  │  Control     │  │   Playlists  │      │
│  │     View     │  │   Panel      │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (Flask)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  /api/jobs  │  /api/speakers  │  /api/control  │ ... │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Jobs       │  │  Speakers    │  │    Cron      │      │
│  │  Service     │  │   Service    │  │   Service    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │   Control    │  │  Playlists   │                        │
│  │   Service    │  │   Service    │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data & Integration Layer                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Jobs Store   │  │ Cron Manager │  │  Airfoil     │      │
│  │  (JSON)      │  │  (crontab)   │  │ AppleScript  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- **macOS** 10.15 or later
- **Python** 3.12+
- **Airfoil** application (for speaker management)
- **Spotify** desktop application (for Spotify integration)
- **Music** app (for Apple Music integration)
- **spotify-cli** - Install via Homebrew: `brew install spotify-cli`

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/aircron.git
cd aircron
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure `aircron_run.sh` is executable:
```bash
chmod +x aircron_run.sh
```

4. Run the application:
```bash
python main.py
```

The web interface will open at `http://127.0.0.1:3009`

### Development Setup

For development with auto-reload:
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
python -m flask run --host=127.0.0.1 --port=3009
```

## Dependencies

### Python Packages

See `requirements.txt` for the complete list. Key dependencies include:

- **Flask** - Web framework
- **croniter** - Cron expression parsing and validation
- **pytest** - Testing framework

### External Applications

- **Airfoil** - Required for multi-speaker audio distribution
- **Spotify** - Required for Spotify playback control
- **Music.app** - Required for Apple Music playback control

### System Components

- **cron** - macOS cron for job scheduling
- **osascript** - AppleScript execution for application control

## Project Structure

```
aircron/
├── main.py                 # Application entry point
├── aircron_run.sh          # Cron execution wrapper
├── build.sh                # PyInstaller build script
│
├── app/                    # Flask application package
│   ├── __init__.py        # App factory and configuration
│   ├── api.py             # REST API endpoints
│   ├── views.py           # HTML routes (HTMX)
│   ├── cronblock.py       # Cron management
│   ├── speakers.py        # Airfoil AppleScript integration
│   ├── jobs_store.py      # JSON persistence layer
│   │
│   ├── services/          # Business logic layer
│   │   ├── control_service.py
│   │   ├── cron_service.py
│   │   ├── jobs_service.py
│   │   ├── playlists_service.py
│   │   └── speakers_service.py
│   │
│   └── tests/             # Test suite
│       ├── test_api.py
│       └── test_jobs_store.py
│
├── templates/             # Jinja2 templates
│   ├── base.html
│   ├── index.html
│   └── partials/          # HTMX partials (16 files)
│
├── static/                # Frontend assets
│   ├── app.js             # Main coordinator
│   ├── app-core.js        # Core utilities
│   ├── notifications.js   # Toast system
│   ├── modal-manager.js   # Modal operations
│   ├── schedule-view.js   # Schedule grid
│   └── control-panel.js   # Control panel
│
├── docs/                  # Additional documentation
│   ├── jobs-system.md
│   ├── speaker-system.md
│   └── cron-system.md
│
└── AGENTS.md             # This file
```

## Key Concepts

### Zone Types

AirCron supports three types of speaker zones:

1. **All Speakers** - Special zone that targets all available speakers
2. **Custom Zones** - User-defined combinations of speakers (prefixed with "Custom:")
3. **Individual Speakers** - Single speaker zones

### Day Numbering

**Important**: AirCron uses a non-standard day numbering convention:
- **1 = Monday, 2 = Tuesday, ..., 7 = Sunday**

This is converted to cron's 0=Sunday format when generating cron entries (see `cronblock.py:176`).

### Actions

Supported job actions:
- **play** - Start playback (requires URI/playlist in args)
- **pause** - Pause playback
- **resume** - Resume paused playback
- **volume** - Set volume level (0-100)
- **connect** - Connect speakers for a service
- **disconnect** - Disconnect speakers

### Services

Supported music services:
- **spotify** - Spotify integration via spotify-cli
- **applemusic** - Apple Music integration via AppleScript

## Data Flow

### Job Creation Flow

```
User fills form → HTMX POST /api/jobs/{zone} → jobs_service.create_job()
    → JobsStore.add_job() → jobs.json (atomic write)
```

### Cron Apply Flow

```
User clicks "Apply" → POST /api/cron/apply → cron_service.apply_jobs_to_cron()
    → CronManager.apply_jobs_to_cron() → Backup crontab
    → Generate cron lines → Write new crontab
```

### Scheduled Execution Flow

```
Cron triggers → aircron_run.sh {zone} {action} {arg1} {service}
    → AppleScript to Airfoil/Music.app/Spotify → Audio output
```

## Development Guidelines

### Code Style

- **Python**: Follow PEP 8, use type hints where appropriate
- **JavaScript**: Modular ES6, avoid inline scripts where possible
- **Logging**: Use the logging module, include context in messages

### Testing

Run the test suite:
```bash
pytest
```

With coverage:
```bash
pytest --cov=app
```

### Adding New Features

1. Add business logic to the appropriate service in `app/services/`
2. Expose functionality via `app/api.py` (for AJAX) or `app/views.py` (for HTMX)
3. Add frontend modules to `static/` as needed
4. Update this documentation

## Troubleshooting

### Common Issues

**Jobs not executing**:
- Verify cron entries: `crontab -l`
- Check aircron_run.sh is executable
- Review logs: `~/Library/Logs/AirCron/aircron.log`

**Speakers not discovered**:
- Ensure Airfoil is running
- Check AppleScript permissions in System Settings

**Spotify control not working**:
- Verify spotify-cli is installed: `which spotify`
- Check Spotify desktop app is running

## Additional Documentation

- **Backend Architecture**: See `app/AGENTS.md`
- **Service Layer**: See `app/services/AGENTS.md`
- **Frontend Architecture**: See `static/AGENTS.md`
- **Jobs System**: See `docs/jobs-system.md`
- **Speaker System**: See `docs/speaker-system.md`
- **Cron Integration**: See `docs/cron-system.md`

## License

[Your License Here]
