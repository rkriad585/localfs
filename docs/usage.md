# Usage Guide

## Starting the Server

**Standard mode (no API):**
```bash
python -m localfs
```

**With API enabled:**
```bash
python -m localfs --share
# or
python -m localfs -s
```

## Accessing the Web Interface

Once the server is running, open the **Access URL** printed in the terminal:

```
http://127.0.0.1:5000/?key=YOUR_ACCESS_KEY
```

### From Another Device on Your Network

Replace `127.0.0.1` with your computer's local IP address:

```
http://192.168.1.10:5000/?key=YOUR_ACCESS_KEY
```

Find your IP with `ip a` (Linux), `ifconfig` (macOS), or `ipconfig` (Windows).

## Web Interface

### File Grid

The main page shows all shareable files as cards with:

- File name and type icon
- File size
- Play button (video/audio files)
- Download button
- Video thumbnail (video files)

### Search

Type in the search bar to filter files in real time by name.

### Playing Media

Click the **Play** button on any video or audio file card to open the player page. The player page includes a **Back to Library** link.

### Downloading Files

Click the **Download** button on any file card to download it.

## API Endpoint

If the `--share` flag is used, the `/api` endpoint is available:

```bash
curl "http://127.0.0.1:5000/api?key=YOUR_API_KEY"
```

Returns logged activity data as JSON.

## Uninstalling

```bash
localfs --selfuninstall
```

Or manually:

```bash
pip uninstall localfs
rm -rf ~/.config/localfs ~/.localfs
```
