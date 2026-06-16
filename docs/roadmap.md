# Roadmap — localfs

## Completed

- [x] Core Flask app with file listing, video/audio player, download
- [x] Access key authentication for web interface
- [x] JSON API endpoint for activity logs
- [x] CLI flags: `--share`, `--selfuninstall`
- [x] Auto-dependency installation on startup
- [x] ffmpeg thumbnail generation for videos
- [x] Search filtering (client-side jQuery)
- [x] Error pages (401/403/404/500)
- [x] MIME type detection and dynamic player
- [x] File type icons and size formatting
- [x] 200+ test suite covering all functions and routes
- [x] Cross-platform installer/uninstaller scripts
- [x] Build system: Makefile, build.sh, build.ps1, CMakeLists.txt
- [x] Docker: multi-stage Dockerfile, docker-compose.yml
- [x] Documentation: setup, usage, config, API, dev, deployment, troubleshooting
- [x] Repository standards: LICENSE, CODE_OF_CONDUCT, CONTRIBUTING, SECURITY, .gitattributes
- [x] Theme system: 16 themes with CSS custom properties
- [x] Settings page with theme picker
- [x] All runtime data stored in `~/.config/neostore/localfs/`

---

## Short-term (Next)

### 1. CLI improvements

| Feature | Description |
|---|---|
| `--port PORT` | Override the port at runtime |
| `--host HOST` | Override the bind address |
| `--key KEY` | Set a specific access key for this session |
| `--media PATH` | Point to a different media directory |
| `--no-auth` | Disable access key for this session |
| `--version` | Print version from `.version` |
| `--theme THEME` | Start with a specific theme |
| `--mode MODE` | Start in dark/light mode |

### 2. User management

- Add user accounts with passwords (not just a shared access key)
- Per-user access levels: admin, viewer, downloader
- Login page with session cookies

### 3. Directory browsing

- Navigate subdirectories inside `media/`
- Breadcrumb navigation
- Per-directory views

### 4. File operations

- Upload files through the web UI (drag & drop)
- Delete files from the web UI (with confirmation)
- Rename files
- Create directories
- Multi-file select and batch operations

### 5. Search improvements

- Server-side search (instead of client-side only)
- Search by file type (video/audio/image)
- Search by date, size
- Full-text search in filenames with fuzzy matching

---

## Medium-term

### 6. Media enhancements

- Subtitle support in video player (SRT, VTT)
- Playlist support (auto-play next video in directory)
- Streaming quality selection (if ffmpeg can transcode)
- Audio-only mode for music streaming
- Picture-in-picture for videos

### 7. UI/UX improvements

- Mobile-responsive layout enhancements
- Dark/light mode toggle in the header (not just settings)
- Grid/list view toggle
- Sort by name, date, size, type
- Pagination for large libraries (1000+ files)
- Keyboard shortcuts (n: next, p: previous, f: fullscreen)

### 8. Thumbnail improvements

- Generate thumbnails in background thread (non-blocking)
- Cache with LRU eviction
- Custom thumbnail size configuration
- Audio waveform thumbnails

### 9. Config migration

- Move all config to `config.toml` (not just theme settings)
- Support runtime config reload without restart
- Config validation on startup
- Environment variable overrides for Docker

### 10. Internationalization (i18n)

- Chinese, Spanish, Arabic, Hindi, French, German
- Auto-detect browser language
- RTL layout support for Arabic/Hebrew

---

## Long-term

### 11. Plugin system

- Plugin API with hooks for: file listing, rendering, auth, media processing
- Plugin directory `~/.config/neostore/localfs/plugins/`
- Example plugins: metadata reader, subtitle downloader, virus scanner

### 12. Advanced media features

- Transcoding on-the-fly via ffmpeg (e.g. MKV→MP4 for browser compatibility)
- Hardware acceleration (VAAPI, NVENC) for transcoding
- HLS/DASH streaming for large files
- Audio transcoding (FLAC→MP3 for bandwidth saving)

### 13. Sync & sharing

- Watch folder: auto-import files from a directory
- Share links with expiry (temporary URLs)
- Upload tokens (one-time upload links for others)
- Folder sharing (share a subdirectory with a different key)

### 14. Database backend

- Replace JSON file log with SQLite
- Store file metadata in database for fast search
- Usage statistics and analytics
- Migration tool from JSON to SQLite

### 15. REST API v2

- Full CRUD API for files and metadata
- API tokens (separate from web access key)
- Rate limiting
- API documentation with Swagger/OpenAPI
- Pagination, filtering, sorting for API responses

### 16. Security

- HTTPS support (built-in, with Let's Encrypt auto-cert)
- Rate limiting for auth attempts
- IP allow/deny lists
- Audit log (who accessed what, when)
- Content Security Policy headers
- Two-factor authentication

### 17. Mobile app

- React Native or Flutter companion app
- Auto-discover localfs servers on the network (mDNS/Bonjour)
- Download for offline viewing
- Cast to Chromecast/Apple TV

### 18. Monitoring & observability

- Prometheus metrics endpoint
- Structured logging (JSON format)
- Health check endpoint
- Grafana dashboard template

---

## CLI Flag Reference (planned)

```
Usage: localfs [OPTIONS]

Options:
  -s, --share        Enable the API endpoint to share logged data
  --selfuninstall    Uninstall localfs and clean up configuration
  --port PORT        Server port (default: 5000)
  --host HOST        Server bind address (default: 0.0.0.0)
  --key KEY          Access key for this session
  --media PATH       Path to media directory
  --no-auth          Disable access key
  --theme THEME      Theme name (default: dark)
  --mode MODE        Color mode: dark | light
  --version          Show version and exit
  --help             Show this help and exit
```

---

## Theme System Extensions (planned)

- Per-user theme selection (not just global)
- Custom theme creator in the settings UI (pick your own colors)
- Auto theme based on time of day (dark at night, light during day)
- System theme detection (follow OS dark/light preference)
- Theme import/export (share themes as JSON)
- Seasonal/holiday themes (auto-activate on dates)
