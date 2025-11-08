# localfs/config.py

import secrets, os # Import the secrets module to generate a cryptographically secure key.

# --- General Settings ---
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True

# --- Folder and File Paths ---
MEDIA_FOLDER = "media"
DATA_FOLDER = "data"
DATA_FILE = "localfs-data.json"
THUMBNAIL_FOLDER = os.path.join("static", "thumbnails") # Path for generated video thumbnails.

# --- File Sharing Settings ---
ALLOWED_EXTENSIONS = ".mkv .mp4 .mp3"

# --- Security & API Settings ---
# A secure, random key for accessing the API endpoint AND the website.
API_KEY = secrets.token_hex(16)

# Set to True to require the API key to access the website (e.g., http://.../?key=...).
# Set to False to allow anyone on the network to view the website without a key.
WEBSITE_ACCESS_KEY_REQUIRED = True
