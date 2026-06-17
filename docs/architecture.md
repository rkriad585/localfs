# Architecture

## Overview

localfs is a Python Flask web application that shares files from a local directory over the local network. It uses a simple monolithic architecture with server-rendered HTML templates.

## Components

### Application Entry Point (`src/localfs/main.py`)

- Flask app initialization
- Route handlers for all endpoints
- Helper functions for file operations
- Click CLI entry point
- Module-level dependency checks

### Configuration (`src/localfs/config.py`)

Singleton configuration module imported by `main.py`. Contains all user-configurable constants.

### Theme System (`src/localfs/theme.py`)

16 theme definitions with CSS variables. Load/save theme selection to `~/.config/neostore/localfs/config.toml`.

### Templates (Jinja2)

Server-side rendered HTML with Tailwind CSS. No frontend framework.

| Template | Route | Purpose |
|---|---|---|---|
| `base.html` | — | Base layout with theme CSS injection |
| `index.html` | `/` | File grid with search, play/download buttons |
| `player.html` | `/player/<filename>` | Video/audio player |
| `settings.html` | `/settings` | Theme picker with color swatches |
| `login.html` | `/login` | Username/password login form |
| `error.html` | all errors | 401/403/404/500 pages |

### Static Files

- `css/theme.css` — CSS custom properties for 16 themes
- `js/main.js` — jQuery-based search filtering (client-side)
- `logo.svg` — Project logo

## Request Flow

```
Browser → Flask → before_request (access key check) → route handler → template render → response
```

### Middleware

`before_request` checks:
1. Sets `g.share_api` flag for API availability.
2. If `WEBSITE_ACCESS_KEY_REQUIRED` is True, validates the `key` query parameter on protected routes (`/`, `/player/`).

### Route Handlers

| Route | Method | Purpose |
|---|---|---|---|
| `/` | GET | List files from media directories |
| `/player/<filename>` | GET | Render player page for media files |
| `/media/<filename>` | GET | Stream file content (no access key check) |
| `/settings` | GET/POST | Theme picker page |
| `/upload` | POST | Upload files with auto-rename |
| `/delete` | POST | Delete files |
| `/rename` | POST | Rename files |
| `/login` | GET/POST | User authentication |
| `/logout` | GET | Clear session |
| `/api` | GET | Return JSON log data (requires `--share` flag) |
| `/favicon.ico` | GET | Serve SVG favicon |
| `/thumbnails/<path>` | GET | Serve generated thumbnails |

## Data Flow

### File Listing

1. `os.listdir(MEDIA_FOLDER)` reads directory.
2. Files are filtered by `ALLOWED_EXTENSIONS`.
3. Each file gets metadata: type, size, icon, playability.
4. Videos get thumbnail generated (via ffmpeg).
5. Template renders the file grid.

### Logging

`log_activity()` reads existing JSON from `~/.config/neostore/localfs/localfs-data.json`, appends an entry, and writes back.

## Security Model

- **Access key**: Required for web interface (configurable).
- **API key**: Same as access key, required for API endpoint.
- **Path traversal**: Flask's `send_from_directory` prevents path traversal.
- **Media streaming**: `/media/` route intentionally unprotected for direct file access.

## Dependencies

- **Flask** — Web framework
- **Click** — CLI interface
- **Rich** — Terminal output formatting
- **ffmpeg** — Video thumbnail generation (external)

## Test Architecture

Tests use pytest with:
- Flask test client (no real server needed)
- Temporary directories (conftest.py fixtures)
- Monkeypatching / mocking for side-effect functions
- Click test runner for CLI tests
