# localfs

A simple, fast, and beautiful local file sharing service built with Python and Flask. Share your media library (videos, audio, images) across your local network through a clean, modern web interface.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## Features

- Instant web access — view and download files from any device on your network
- Built-in video & audio player with auto-generated thumbnails
- Live search filtering
- Clean, modern UI styled with Tailwind CSS
- Configurable file-type filtering
- Optional access key for web interface security
- JSON API endpoint for sharing activity logs

## Quick Start

### Install from source

```bash
git clone https://github.com/rkriad585/localfs.git
cd localfs
pip install -e .
python main.py
```

### Install via script (Linux / macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/rkriad585/localfs/main/installer.sh | sh
```

### Install via script (Windows PowerShell)

```powershell
irm https://raw.githubusercontent.com/rkriad585/localfs/main/installer.ps1 | iex
```

Open the URL printed in the terminal to access the web interface.

## Docker

```bash
docker build -t localfs .
docker run -p 5000:5000 -v ./media:/app/media localfs
```

Or with docker compose:

```bash
docker compose up
```

## Documentation

Full documentation is in the [docs/](docs/) directory:

| Guide | Description |
|---|---|
| [Setup Guide](docs/setup.md) | Installation and first run |
| [Usage Guide](docs/usage.md) | How to use localfs |
| [Configuration](docs/configuration.md) | All config options explained |
| [API Reference](docs/api.md) | JSON API documentation |
| [Development](docs/development.md) | Setting up a dev environment |
| [Deployment](docs/deployment.md) | Production deployment options |
| [Troubleshooting](docs/troubleshooting.md) | Common issues and fixes |
| [Architecture](docs/architecture.md) | Project architecture overview |

## Build Commands

```bash
make build      # Build wheel and sdist
make install    # Install in editable mode
make test       # Run tests
make lint       # Run linter
make format     # Format code
make run        # Start server
make clean      # Remove build artifacts
make docker     # Build Docker image
```

## Project Structure

```
localfs/
├── main.py              # Application entry point and Flask routes
├── config.py            # Configuration constants
├── pyproject.toml       # Project metadata and dependencies
├── Dockerfile           # Multi-stage Docker build
├── docker-compose.yml   # Docker Compose configuration
├── Makefile             # Build automation
├── build.sh / .ps1      # Cross-platform build scripts
├── installer.sh / .ps1  # System installer / uninstaller
│
├── data/                # Runtime data (logs, auto-created)
├── media/               # Place your shared files here
├── static/
│   ├── js/main.js       # Search filtering logic
│   ├── logo.svg         # Project logo
│   └── thumbnails/      # Auto-generated video thumbnails
├── templates/
│   ├── index.html       # File grid homepage
│   ├── player.html      # Video/audio player page
│   └── error.html       # Error pages (401/403/404/500)
├── tests/
│   ├── conftest.py      # Pytest fixtures
│   ├── test_config.py   # Config tests
│   └── test_main.py     # Main application tests
└── docs/                # Documentation
```

## Uninstalling

```bash
localfs --selfuninstall
```

### Uninstall via script (Linux / macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/rkriad585/localfs/main/installer.sh | sh -s -- --selfuninstall
```

### Uninstall via script (Windows PowerShell)

```powershell
Invoke-RestMethod -Uri "https://raw.githubusercontent.com/rkriad585/localfs/main/installer.ps1" | Invoke-Expression -ArgumentList "--selfuninstall"
```

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
