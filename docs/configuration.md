# Configuration

All configuration is in `config.py` at the project root.

## General Settings

| Setting | Default | Description |
|---|---|---|
| `HOST` | `"0.0.0.0"` | Network interface to bind to. Use `"127.0.0.1"` for local-only. |
| `PORT` | `5000` | Port for the web server. |
| `DEBUG` | `True` | Enable Flask debug mode. Set `False` in production. |

## File Paths

| Setting | Default | Description |
|---|---|---|
| `MEDIA_FOLDER` | `"media"` | Directory containing files to share. |
| `DATA_FOLDER` | `"data"` | Directory for logs and runtime data. |
| `DATA_FILE` | `"localfs-data.json"` | Log filename inside `DATA_FOLDER`. |
| `THUMBNAIL_FOLDER` | `"static/thumbnails"` | Directory for auto-generated video thumbnails. |

## File Sharing

| Setting | Default | Description |
|---|---|---|
| `ALLOWED_EXTENSIONS` | `".mkv .mp4 .mp3"` | Space-separated list of allowed file extensions. Empty string allows all files. |

## Security

| Setting | Default | Description |
|---|---|---|
| `API_KEY` | Auto-generated | Random 32-character hex key. Used for both web access and API. |
| `WEBSITE_ACCESS_KEY_REQUIRED` | `True` | Require the API key to view the web interface. |

## Example Config

```python
# Allow only video files
ALLOWED_EXTENSIONS = ".mp4 .mkv .webm .mov .avi"

# Disable web access key (anyone on network can view)
WEBSITE_ACCESS_KEY_REQUIRED = False

# Set a specific key (instead of auto-generated)
API_KEY = "my-secret-key-123"
```

## Environment Variables

When running via Docker, you can override any config by binding your own `config.py` as a volume, or by setting environment variables in the docker-compose file.
