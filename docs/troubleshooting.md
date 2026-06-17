# Troubleshooting

## Port 5000 Already in Use

```text
OSError: [Errno 98] Address already in use
```

**Solution:** Change the port with `--port` flag or edit `src/localfs/config.py`:

```bash
lsof -i :5000   # Find the PID
kill -9 <PID>   # Replace <PID> with the process ID
```

## ffmpeg Not Found

```text
Error: `ffmpeg` is not installed or not in your system's PATH.
```

**Solution:** Install ffmpeg (see [Setup Guide](setup.md#installing-ffmpeg)).

## "No space left on device"

If `/tmp` is full (common on small systems), localfs may crash during thumbnail generation or console output. Free up space:

```bash
sudo rm -rf /tmp/*
```

Or point `TMPDIR` to a directory with space:

```bash
export TMPDIR=/home/user/mytmp
```

## Dependencies Not Installing

If automatic dependency installation fails, install manually:

```bash
pip install flask>=3.0 rich>=13.0 click>=8.0
```

## Website Shows "Unauthorized"

The web access key is required. Make sure your URL includes the `key` parameter:

```
http://127.0.0.1:5000/?key=YOUR_KEY_HERE
```

To disable the key requirement, use `--no-auth` flag or set in `src/localfs/config.py`:

```python
WEBSITE_ACCESS_KEY_REQUIRED = False
```

## Files Not Showing

1. Make sure files are in the media directory (default: `~/Downloads`).
2. Check `ALLOWED_EXTENSIONS` in `src/localfs/config.py` — only matching extensions are displayed.
3. Set `ALLOWED_EXTENSIONS = ""` to show all files.
4. The application hides directories; only files are shown.

## Video Thumbnails Not Generating

1. Ensure ffmpeg is installed and in your PATH.
2. Check the thumbnail directory is writable.
3. Some corrupted video files may fail to generate a thumbnail.
