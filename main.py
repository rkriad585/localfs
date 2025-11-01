# localfs/main.py

# --- Standard Library Imports ---
import os
import sys
import json
import subprocess
import importlib.util
import shutil  # For checking for external programs like ffmpeg
from datetime import datetime

# --- Third-Party Library Imports ---
try:
    from flask import Flask, render_template, send_from_directory, request, jsonify, g, abort
    from rich.console import Console
    import click
except ImportError:
    pass

# --- Local Application Imports ---
import config

# --- Dependency Management & Initialization ---
def check_and_install_dependencies():
    console = Console()
    required_packages = ['flask', 'rich', 'click']
    missing_packages = [pkg for pkg in required_packages if importlib.util.find_spec(pkg) is None]

    if missing_packages:
        console.print(f"[bold yellow]Warning:[/bold yellow] Missing packages: [bold red]{', '.join(missing_packages)}[/bold red]")
        if input("Install them now? (Y/n): ").lower().strip() in ['y', 'yes', '']:
            try:
                for package in missing_packages:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                console.print("[bold green]Dependencies installed. Please restart the script.[/bold green]")
                sys.exit(0)
            except subprocess.CalledProcessError as e:
                console.print(f"[bold red]Error installing dependencies.[/bold red] Please install manually.", e)
                sys.exit(1)
        else:
            console.print("[bold red]Cannot proceed without dependencies.[/bold red]")
            sys.exit(1)

# NEW: Function to check for the ffmpeg external dependency
def check_ffmpeg():
    """Checks if ffmpeg is installed and available in the system's PATH."""
    console = Console()
    if not shutil.which("ffmpeg"):
        console.print("[bold red]Error: `ffmpeg` is not installed or not in your system's PATH.[/bold red]")
        console.print("`ffmpeg` is required to generate video thumbnails.")
        console.print("\n[bold yellow]How to install:[/bold yellow]")
        console.print("  - [bold]Windows:[/bold] Download from https://ffmpeg.org/download.html and add to your PATH.")
        console.print("  - [bold]macOS (using Homebrew):[/bold] `brew install ffmpeg`")
        console.print("  - [bold]Linux (Debian/Ubuntu):[/bold] `sudo apt update && sudo apt install ffmpeg`")
        console.print("  - [bold]Linux (Fedora/CentOS):[/bold] `sudo dnf install ffmpeg`")
        sys.exit(1)

# Run dependency checks
check_and_install_dependencies()
check_ffmpeg()  # Check for ffmpeg after Python packages are confirmed

# --- Application Setup ---
from flask import Flask, render_template, send_from_directory, request, jsonify, g, abort
from rich.console import Console
import click

console = Console()
app = Flask(__name__, template_folder='templates', static_folder='static')

def setup_directories():
    """Creates media, data, and thumbnails directories if they don't exist."""
    os.makedirs(config.MEDIA_FOLDER, exist_ok=True)
    os.makedirs(config.DATA_FOLDER, exist_ok=True)
    os.makedirs(config.THUMBNAIL_FOLDER, exist_ok=True) # Ensure thumbnail folder exists

# --- Helper and Logging Functions ---
def log_activity(event_type, details):
    log_file_path = os.path.join(config.DATA_FOLDER, config.DATA_FILE)
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "ip_address": request.remote_addr,
        "details": details
    }
    try:
        data = []
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r') as f:
                data = json.load(f)
        data.append(log_entry)
        with open(log_file_path, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        console.print(f"[bold red]Error logging activity:[/bold red] {e}")

# UPDATED: File type checker now recognizes more video formats
def get_file_type(filename):
    image_ext = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    video_ext = ['.mp4', '.webm', '.ogg', '.mkv', '.mov', '.avi'] # Added more common video types
    _, ext = os.path.splitext(filename)
    if ext.lower() in image_ext:
        return 'image'
    if ext.lower() in video_ext:
        return 'video'
    return 'other'

# NEW: Function to generate a thumbnail for a video file
def generate_thumbnail(filename):
    """Generates a 1-frame thumbnail for a video file using ffmpeg."""
    try:
        # Define the source video path and the destination thumbnail path.
        source_path = os.path.join(config.MEDIA_FOLDER, filename)
        # The thumbnail will have the same name as the video but with a .jpg extension.
        thumbnail_filename = f"{os.path.splitext(filename)[0]}.jpg"
        dest_path = os.path.join(config.THUMBNAIL_FOLDER, thumbnail_filename)

        # If the thumbnail already exists, don't regenerate it.
        if os.path.exists(dest_path):
            return os.path.join("thumbnails", thumbnail_filename).replace("\\", "/")

        # The ffmpeg command:
        # -i: input file
        # -ss: seek to the 1-second mark
        # -vframes 1: extract only 1 frame
        # -y: overwrite output file if it exists
        # -loglevel error: only show errors, not the full verbose output
        command = [
            'ffmpeg', '-i', source_path, '-ss', '00:00:01.000', 
            '-vframes', '1', '-y', dest_path, '-loglevel', 'error'
        ]
        
        # Execute the command.
        subprocess.run(command, check=True)
        
        # Return the web-accessible path to the thumbnail.
        return os.path.join("thumbnails", thumbnail_filename).replace("\\", "/")
    except Exception as e:
        # If ffmpeg fails (e.g., corrupt video), log the error and return None.
        console.print(f"[bold yellow]Warning:[/bold yellow] Could not generate thumbnail for '{filename}'. Reason: {e}")
        return None

def get_file_size(filepath):
    """Returns a human-readable file size string."""
    size_bytes = os.path.getsize(filepath)
    if size_bytes < 1024: return f"{size_bytes} B"
    elif size_bytes < 1024**2: return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3: return f"{size_bytes/1024**2:.1f} MB"
    else: return f"{size_bytes/1024**3:.1f} GB"

# --- Flask Routes ---

# NEW: This function runs before every request to check the API key for web access
@app.before_request
def check_access_key():
    """If enabled in config, validates the API key for web pages."""
    # Only run this check if the feature is enabled in the config.
    if config.WEBSITE_ACCESS_KEY_REQUIRED:
        # Define which endpoints are protected. We don't want to protect static files or media downloads.
        protected_endpoints = ['index', 'player']
        if request.endpoint in protected_endpoints:
            # Get the key from the URL query parameter (?key=...)
            provided_key = request.args.get('key')
            # If the key doesn't match, block access with a 401 Unauthorized error.
            if provided_key != config.API_KEY:
                log_activity("web_access_denied", {"reason": "Invalid or missing web access key"})
                abort(401, description="Unauthorized: A valid access key is required.")

@app.route('/')
def index():
    """The main route that renders the homepage."""
    log_activity("page_view", {"page": "index"})
    files_to_share = []
    try:
        allowed_exts = [ext.strip() for ext in config.ALLOWED_EXTENSIONS.lower().split(' ') if ext]
        
        for filename in sorted(os.listdir(config.MEDIA_FOLDER)):
            if not allowed_exts or any(filename.lower().endswith(ext) for ext in allowed_exts):
                filepath = os.path.join(config.MEDIA_FOLDER, filename)
                file_type = get_file_type(filename)
                
                # Prepare file information dictionary
                file_info = {
                    "name": filename,
                    "type": file_type,
                    "size": get_file_size(filepath),
                    "is_video": file_type == 'video',
                    "thumbnail": None # Default thumbnail to None
                }

                # If the file is a video, attempt to generate a thumbnail for it.
                if file_info["is_video"]:
                    file_info["thumbnail"] = generate_thumbnail(filename)
                
                files_to_share.append(file_info)
    except Exception as e:
        console.print(f"[bold red]Error reading media folder:[/bold red] {e}")

    return render_template('index.html', files=files_to_share)

# NEW: Route for the dedicated video player page
@app.route('/player/<filename>')
def player(filename):
    """Renders the video player page for a specific file."""
    log_activity("video_play_request", {"filename": filename})
    return render_template('player.html', filename=filename)

@app.route('/media/<filename>')
def serve_media(filename):
    """Serves the actual files from the media folder."""
    log_activity("file_download_request", {"filename": filename})
    return send_from_directory(config.MEDIA_FOLDER, filename, as_attachment=False)

@app.route('/api')
def api_data():
    """API endpoint to share all logged data."""
    if not g.get('share_api'):
        return jsonify({"error": "API is not enabled."}), 403
    
    provided_key = request.args.get('key')
    if provided_key != config.API_KEY:
        log_activity("api_access_denied", {"reason": "Invalid or missing API key"})
        return jsonify({"error": "Invalid or missing API key"}), 401

    log_activity("api_access_granted", {})
    log_file_path = os.path.join(config.DATA_FOLDER, config.DATA_FILE)
    try:
        with open(log_file_path, 'r') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"message": "No data logged yet."})
    except Exception as e:
        return jsonify({"error": f"Could not retrieve data: {e}"}), 500

# --- Command-Line Interface (CLI) ---
@click.command()
@click.option('-s', '--share', is_flag=True, help='Enable the API endpoint to share logged data.')
def main(share):
    """localfs: A simple local file sharing service."""
    setup_directories()

    @app.before_request
    def before_request_func():
        g.share_api = share

    console.print("[bold green]Starting localfs server...[/bold green]")
    console.print(f" * Media Folder: [cyan]{os.path.abspath(config.MEDIA_FOLDER)}[/cyan]")
    
    # UPDATED: Display the correct access URL based on security settings
    access_url = f"http://127.0.0.1:{config.PORT}"
    if config.WEBSITE_ACCESS_KEY_REQUIRED:
        console.print(f" * Website Access Key: [bold magenta]{config.API_KEY}[/bold magenta]")
        access_url_with_key = f"{access_url}/?key={config.API_KEY}"
        console.print(f" * Access URL: [link={access_url_with_key}]{access_url_with_key}[/link]")
    else:
        console.print(f" * Access URL: [link={access_url}]{access_url}[/link]")

    if share:
        console.print(f" * API Key: [bold magenta]{config.API_KEY}[/bold magenta]")
    else:
        console.print(f" * API Enabled: [bold red]No[/bold red]")
        
    console.print("[yellow]Press CTRL+C to stop the server.[/yellow]")

    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, threaded=True)

if __name__ == '__main__':
    main()
