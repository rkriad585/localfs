# API Reference

The API endpoint is only available when the server is started with the `--share` flag.

## Endpoint

```
GET /api?key=YOUR_API_KEY
```

## Authentication

The API key is the same as the website access key, set in `src/localfs/config.py`:

```python
API_KEY = secrets.token_hex(16)
```

Or auto-generated on each startup.

## Response

**Success (200):**

Returns an array of logged events:

```json
[
    {
        "timestamp": "2025-01-15T10:30:00.123456",
        "event": "page_view",
        "ip_address": "192.168.1.5",
        "details": {
            "page": "index"
        }
    },
    {
        "timestamp": "2025-01-15T10:31:00.654321",
        "event": "media_play_request",
        "ip_address": "192.168.1.5",
        "details": {
            "filename": "video.mp4",
            "type": "video"
        }
    }
]
```

**Empty log (200):**

```json
{
    "message": "No data logged yet."
}
```

**Missing or invalid key (401):**

```json
{
    "error": "Invalid or missing API key"
}
```

**API not enabled (403):**

```json
{
    "error": "API is not enabled."
}
```

## Example Usage

```bash
curl "http://127.0.0.1:5000/api?key=abc123def456..."
```

Or filter with `jq`:

```bash
curl -s "http://127.0.0.1:5000/api?key=abc123..." | jq '.[] | select(.event == "page_view")'
```

## Logged Events

| Event | Trigger |
|---|---|
| `page_view` | Homepage visit |
| `media_play_request` | Player page opened |
| `file_download_request` | File download initiated |
| `web_access_denied` | Failed web access attempt |
| `api_access_granted` | Successful API access |
| `api_access_denied` | Failed API access attempt |
