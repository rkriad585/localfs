# localfs/main.py

import os
import sys
import json
import subprocess
import importlib.util
import shutil
import mimetypes
from datetime import datetime

import config

def check_and_install_dependencies():
    def print_fallback(msg):
        print(msg)

    console = None
    try:
        from rich.console import Console
        console = Console()
    except ImportError:
        pass

    out = console.print if console else print_fallback

    required_packages = ['flask', 'rich', 'click']
    missing_packages = [pkg for pkg in required_packages if importlib.util.find_spec(pkg) is None]

    if missing_packages:
        out(f"Warning: Missing packages: {', '.join(missing_packages)}")
        try:
            answer = input("Install them now? (Y/n): ").lower().strip()
        except (EOFError, KeyboardInterrupt):
            answer = 'n'
        if answer in ['y', 'yes', '']:
            try:
                for package in missing_packages:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                out("Dependencies installed. Please restart the script.")
                sys.exit(0)
            except subprocess.CalledProcessError as e:
                out(f"Error installing dependencies. Please install manually. {e}")
                sys.exit(1)
        else:
            out("Cannot proceed without dependencies.")
            sys.exit(1)

def check_ffmpeg():
    def print_fallback(msg):
        print(msg)

    console = None
    try:
        from rich.console import Console
        console = Console()
    except ImportError:
        pass

    out = console.print if console else print_fallback

    if not shutil.which("ffmpeg"):
        out("Error: `ffmpeg` is not installed or not in your system's PATH.")
        out("`ffmpeg` is required to generate video thumbnails.")
        out("")
        out("How to install:")
        out("  - Windows: Download from https://ffmpeg.org/download.html and add to your PATH.")
        out("  - macOS (using Homebrew): `brew install ffmpeg`")
        out("  - Linux (Debian/Ubuntu): `sudo apt update && sudo apt install ffmpeg`")
        out("  - Linux (Fedora/CentOS): `sudo dnf install ffmpeg`")
        sys.exit(1)

check_and_install_dependencies()
check_ffmpeg()

from flask import Flask, render_template, send_from_directory, request, jsonify, g, abort, redirect, url_for
from rich.console import Console
import click

import theme as theme_mod

console = Console()
app = Flask(__name__, template_folder='templates', static_folder='static')

_share_enabled = False

theme_mod.load_config()


@app.context_processor
def inject_theme():
    theme_name = theme_mod.CURRENT_THEME
    theme_data = theme_mod.THEMES.get(theme_name)
    css_vars = theme_mod.get_theme_vars()
    return {
        "current_theme": theme_name,
        "theme_name": theme_name,
        "themes": theme_mod.get_all_themes(),
        "theme_css": css_vars,
    }


def setup_directories():
    os.makedirs(config.MEDIA_FOLDER, exist_ok=True)
    os.makedirs(config.DATA_FOLDER, exist_ok=True)
    os.makedirs(config.THUMBNAIL_FOLDER, exist_ok=True)

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

def get_file_type(filename):
    image_ext = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    video_ext = ['.mp4', '.webm', '.ogg', '.mkv', '.mov', '.avi']
    audio_ext = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma']
    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()
    if ext_lower in image_ext:
        return 'image'
    if ext_lower in video_ext:
        return 'video'
    if ext_lower in audio_ext:
        return 'audio'
    return 'other'

def get_mime_type(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'

def is_media_playable(file_type):
    return file_type in ('video', 'audio')

def generate_thumbnail(filename):
    try:
        source_path = os.path.join(config.MEDIA_FOLDER, filename)
        thumbnail_filename = f"{os.path.splitext(filename)[0]}.jpg"
        dest_path = os.path.join(config.THUMBNAIL_FOLDER, thumbnail_filename)

        if os.path.exists(dest_path):
            return "thumbnails/" + thumbnail_filename

        command = [
            'ffmpeg', '-i', source_path, '-ss', '00:00:01.000',
            '-vframes', '1', '-y', dest_path, '-loglevel', 'error'
        ]

        subprocess.run(command, check=True)

        return "thumbnails/" + thumbnail_filename
    except Exception as e:
        console.print(f"[bold yellow]Warning:[/bold yellow] Could not generate thumbnail for '{filename}'. Reason: {e}")
        return None

def get_file_size(filepath):
    size_bytes = os.path.getsize(filepath)
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    else:
        return f"{size_bytes / 1024 ** 3:.1f} GB"


def get_file_icon(file_type):
    return {
        'video': 'fa-file-video',
        'audio': 'fa-file-audio',
        'image': 'fa-file-image',
        'other': 'fa-file-alt',
    }.get(file_type, 'fa-file-alt')


@app.before_request
def before_request_func():
    g.share_api = _share_enabled
    if config.WEBSITE_ACCESS_KEY_REQUIRED:
        protected_endpoints = ['index', 'player', 'settings']
        if request.endpoint in protected_endpoints:
            provided_key = request.args.get('key')
            if provided_key != config.API_KEY:
                log_activity("web_access_denied", {"reason": "Invalid or missing web access key"})
                abort(401, description="Unauthorized: A valid access key is required.")


@app.errorhandler(401)
def unauthorized_error(e):
    return render_template('error.html', code=401, message="Unauthorized: A valid access key is required."), 401


@app.errorhandler(403)
def forbidden_error(e):
    return render_template('error.html', code=403, message="Forbidden: You don't have permission to access this resource."), 403


@app.errorhandler(404)
def not_found_error(e):
    return render_template('error.html', code=404, message="Page not found."), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('error.html', code=500, message="Internal server error."), 500


@app.route('/')
def index():
    log_activity("page_view", {"page": "index"})
    files_to_share = []
    try:
        allowed_exts = [ext.strip() for ext in config.ALLOWED_EXTENSIONS.lower().split(' ') if ext]

        for filename in sorted(os.listdir(config.MEDIA_FOLDER)):
            filepath = os.path.join(config.MEDIA_FOLDER, filename)

            if not os.path.isfile(filepath):
                continue

            if allowed_exts and not any(filename.lower().endswith(ext) for ext in allowed_exts):
                continue

            file_type = get_file_type(filename)

            file_info = {
                "name": filename,
                "type": file_type,
                "size": get_file_size(filepath),
                "is_playable": is_media_playable(file_type),
                "mime_type": get_mime_type(filename),
                "icon": get_file_icon(file_type),
                "thumbnail": None,
            }

            if file_type == 'video':
                file_info["thumbnail"] = generate_thumbnail(filename)

            files_to_share.append(file_info)
    except Exception as e:
        console.print(f"[bold red]Error reading media folder:[/bold red] {e}")

    return render_template('index.html', files=files_to_share)


@app.route('/player/<filename>')
def player(filename):
    filepath = os.path.join(config.MEDIA_FOLDER, filename)

    if not os.path.isfile(filepath):
        abort(404)

    file_type = get_file_type(filename)

    if not is_media_playable(file_type):
        abort(400)

    mime_type = get_mime_type(filename)

    log_activity("media_play_request", {"filename": filename, "type": file_type})

    return render_template(
        'player.html',
        filename=filename,
        file_type=file_type,
        mime_type=mime_type,
    )


@app.route('/media/<filename>')
def serve_media(filename):
    filepath = os.path.join(config.MEDIA_FOLDER, filename)

    if not os.path.isfile(filepath):
        abort(404)

    log_activity("file_download_request", {"filename": filename})
    return send_from_directory(config.MEDIA_FOLDER, filename, as_attachment=False)


@app.route('/api')
def api_data():
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


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        selected = request.form.get('theme', 'dark')
        if selected in theme_mod.THEMES:
            theme_mod.save_config(selected)
            theme_mod.load_config()
        key = request.args.get('key')
        if key:
            return redirect(url_for('index', key=key))
        return redirect(url_for('index'))

    theme_name = theme_mod.CURRENT_THEME
    return render_template('settings.html', current_theme=theme_name, themes=theme_mod.get_all_themes())


def _self_uninstall():
    console.print("[yellow]Uninstalling localfs...[/yellow]")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "localfs"])
        console.print("[green]localfs uninstalled successfully.[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to uninstall localfs: {e}[/red]")

    if os.path.isdir(config.DATA_FOLDER):
        shutil.rmtree(config.DATA_FOLDER, ignore_errors=True)
        console.print(f"[green]Removed data directory: {config.DATA_FOLDER}[/green]")

    sys.exit(0)


@click.command()
@click.option('-s', '--share', is_flag=True, help='Enable the API endpoint to share logged data.')
@click.option('--selfuninstall', is_flag=True, help='Uninstall localfs and clean up configuration.')
def main(share, selfuninstall):
    """localfs: A simple local file sharing service."""
    if selfuninstall:
        _self_uninstall()
        return

    global _share_enabled
    _share_enabled = share
    setup_directories()

    console.print("[bold green]Starting localfs server...[/bold green]")
    console.print(f" * Media Folder: [cyan]{os.path.abspath(config.MEDIA_FOLDER)}[/cyan]")

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
