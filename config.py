# localfs/config.py

import secrets, os

BASE_DIR = os.path.join(os.path.expanduser("~"), ".config", "neostore", "localfs")

# --- Version ---
_VERSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".version")
try:
    with open(_VERSION_FILE) as _f:
        VERSION = _f.read().strip()
except (FileNotFoundError, IOError):
    try:
        from importlib.metadata import version as _meta_version
        VERSION = _meta_version("localfs")
    except (ImportError, Exception):
        VERSION = "0.0.0"

# --- General Settings ---
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True

# --- Folder and File Paths ---
MEDIA_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
MEDIA_EXTRA_DIRS = {
    "Videos": os.path.join(os.path.expanduser("~"), "Videos"),
    "Music": os.path.join(os.path.expanduser("~"), "Music"),
}
DATA_FOLDER = os.path.join(BASE_DIR, "data")
DATA_FILE = "localfs-data.json"
THUMBNAIL_FOLDER = os.path.join(BASE_DIR, "thumbnails")

# --- File Sharing Settings ---
ALLOWED_EXTENSIONS = ".mkv .mp4 .mp3"

# --- Security & API Settings ---
# A secure, random key for accessing the API endpoint AND the website.
API_KEY = secrets.token_hex(16)

# Set to True to require the API key to access the website (e.g., http://.../?key=...).
# Set to False to allow anyone on the network to view the website without a key.
WEBSITE_ACCESS_KEY_REQUIRED = True

# Flask session secret key
SECRET_KEY = secrets.token_hex(32)

# User management
USERS_FILE = os.path.join(BASE_DIR, "users.json")
