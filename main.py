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

from flask import Flask, render_template, send_from_directory, send_file, request, jsonify, g, abort, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from rich.console import Console
import click

import theme as theme_mod

console = Console()
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = config.SECRET_KEY

_share_enabled = False

theme_mod.load_config()


# --- User management ---

def load_users():
    if not os.path.exists(config.USERS_FILE):
        return {}
    try:
        with open(config.USERS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(users):
    os.makedirs(config.BASE_DIR, exist_ok=True)
    with open(config.USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


def user_exists(username):
    users = load_users()
    return username in users


def add_user(username, password):
    users = load_users()
    users[username] = generate_password_hash(password)
    save_users(users)


def remove_user(username):
    users = load_users()
    users.pop(username, None)
    save_users(users)


def authenticate_user(username, password):
    users = load_users()
    hashed = users.get(username)
    if hashed and check_password_hash(hashed, password):
        return True
    return False


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
        source_path = resolve_media_path(filename)
        if source_path is None:
            return None

        basename = os.path.basename(filename)
        thumbnail_filename = f"{os.path.splitext(basename)[0]}.jpg"

        rel_dir = os.path.dirname(filename)
        if rel_dir:
            thumb_dir = os.path.join(config.THUMBNAIL_FOLDER, rel_dir)
            thumb_rel = os.path.join(rel_dir, thumbnail_filename)
        else:
            thumb_dir = config.THUMBNAIL_FOLDER
            thumb_rel = thumbnail_filename

        dest_path = os.path.join(config.THUMBNAIL_FOLDER, thumb_rel)

        if os.path.exists(dest_path):
            return thumb_rel

        os.makedirs(thumb_dir, exist_ok=True)

        command = [
            'ffmpeg', '-i', source_path, '-ss', '00:00:01.000',
            '-vframes', '1', '-y', dest_path, '-loglevel', 'error'
        ]

        subprocess.run(command, check=True)

        return thumb_rel
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


def resolve_media_path(relative_path):
    if not relative_path:
        return config.MEDIA_FOLDER
    parts = relative_path.replace("\\", "/").split("/")
    if len(parts) > 1 and parts[0] in config.MEDIA_EXTRA_DIRS:
        virtual_dir = parts[0]
        real_base = config.MEDIA_EXTRA_DIRS[virtual_dir]
        inner = "/".join(parts[1:])
        return safe_join(real_base, inner) if inner else real_base
    return safe_join(config.MEDIA_FOLDER, relative_path)


def list_media_files(directory, relative_dir=""):
    files = []
    dirs = []
    try:
        allowed_exts = [e.strip() for e in config.ALLOWED_EXTENSIONS.lower().split(" ") if e]
        for entry in sorted(os.listdir(directory)):
            filepath = os.path.join(directory, entry)
            rel_path = f"{relative_dir}/{entry}" if relative_dir else entry
            if os.path.isdir(filepath):
                dirs.append({"name": entry, "path": rel_path})
                continue
            if allowed_exts and not any(entry.lower().endswith(e) for e in allowed_exts):
                continue
            files.append(entry)
    except OSError:
        pass
    return files, dirs


def generate_file_info(entry, filepath, rel_path):
    file_type = get_file_type(entry)
    info = {
        "name": entry,
        "path": rel_path,
        "type": file_type,
        "size": get_file_size(filepath),
        "is_playable": is_media_playable(file_type),
        "mime_type": get_mime_type(entry),
        "icon": get_file_icon(file_type),
        "thumbnail": None,
    }
    if file_type == "video":
        info["thumbnail"] = generate_thumbnail(rel_path)
    return info


def safe_join(directory, *path_parts):
    joined = os.path.normpath(os.path.join(directory, *path_parts))
    if not joined.startswith(os.path.normpath(directory)):
        return None
    return joined


def build_breadcrumbs(relative_dir):
    if not relative_dir:
        return []
    parts = relative_dir.replace("\\", "/").strip("/").split("/")
    crumbs = [{"name": "~", "path": ""}]
    acc = ""
    for p in parts:
        acc = f"{acc}/{p}" if acc else p
        crumbs.append({"name": p, "path": acc})
    return crumbs


def parent_dir(relative_dir):
    if not relative_dir:
        return None
    parts = relative_dir.replace("\\", "/").strip("/").split("/")
    if len(parts) <= 1:
        return ""
    return "/".join(parts[:-1])


@app.before_request
def before_request_func():
    g.share_api = _share_enabled
    exemptions = ['login', 'static', 'serve_media', 'serve_thumbnail']
    if request.endpoint in exemptions:
        return
    if config.WEBSITE_ACCESS_KEY_REQUIRED:
        protected_endpoints = ['index', 'player', 'settings', 'upload_file', 'delete_file', 'rename_file']
        if request.endpoint in protected_endpoints:
            if session.get('authenticated'):
                return
            provided_key = request.args.get('key')
            if provided_key != config.API_KEY:
                log_activity("web_access_denied", {"reason": "Invalid or missing web access key"})
                if request.endpoint == 'login':
                    return
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
    dirs = []
    relative_dir = request.args.get("dir", "")
    search_q = request.args.get("q", "").lower()
    search_type = request.args.get("type", "").lower()
    search_size = request.args.get("size", "").lower()
    sort_by = request.args.get("sort", "name")
    sort_order = request.args.get("order", "asc")

    if not relative_dir:
        for virt_name in sorted(config.MEDIA_EXTRA_DIRS):
            if os.path.isdir(config.MEDIA_EXTRA_DIRS[virt_name]):
                if not search_q or search_q in virt_name.lower():
                    dirs.append({"name": virt_name, "path": virt_name})
        base = config.MEDIA_FOLDER
    elif relative_dir in config.MEDIA_EXTRA_DIRS:
        base = config.MEDIA_EXTRA_DIRS[relative_dir]
    else:
        base = safe_join(config.MEDIA_FOLDER, relative_dir)
        if base is None or not os.path.isdir(base):
            abort(404)

    try:
        allowed_exts = [e.strip() for e in config.ALLOWED_EXTENSIONS.lower().split(" ") if e]
        for entry in sorted(os.listdir(base)):
            filepath = os.path.join(base, entry)
            rel_path = f"{relative_dir}/{entry}" if relative_dir else entry

            if os.path.isdir(filepath):
                if relative_dir in config.MEDIA_EXTRA_DIRS:
                    continue
                if search_q and search_q not in entry.lower():
                    continue
                dirs.append({"name": entry, "path": rel_path})
                continue

            if allowed_exts and not any(entry.lower().endswith(e) for e in allowed_exts):
                continue

            file_type = get_file_type(entry)

            if search_q and search_q not in entry.lower():
                continue
            if search_type and file_type != search_type:
                continue
            if search_size:
                sz = os.path.getsize(filepath)
                if search_size == "small" and sz >= 1024 * 1024:
                    continue
                if search_size == "medium" and not (1024 * 1024 <= sz < 100 * 1024 * 1024):
                    continue
                if search_size == "large" and sz < 100 * 1024 * 1024:
                    continue

            info = generate_file_info(entry, filepath, rel_path)
            files_to_share.append(info)

        if sort_by == "size":
            def _sort_key(f):
                try:
                    return os.path.getsize(os.path.join(base, f["name"]))
                except OSError:
                    return 0
            files_to_share.sort(key=_sort_key, reverse=(sort_order == "desc"))
        elif sort_by == "type":
            files_to_share.sort(key=lambda f: (f["type"], f["name"]), reverse=(sort_order == "desc"))
        elif sort_by == "date":
            def _sort_key(f):
                try:
                    return os.path.getmtime(os.path.join(base, f["name"]))
                except OSError:
                    return 0
            files_to_share.sort(key=_sort_key, reverse=(sort_order == "desc"))
        else:
            files_to_share.sort(key=lambda f: f["name"].lower(), reverse=(sort_order == "desc"))
    except Exception as e:
        console.print(f"[bold red]Error reading media folder:[/bold red] {e}")

    crumbs = build_breadcrumbs(relative_dir)
    parent = parent_dir(relative_dir)

    return render_template("index.html", files=files_to_share, dirs=dirs,
                           breadcrumbs=crumbs, parent_dir=parent, current_dir=relative_dir,
                           search_q=search_q, search_type=search_type, search_size=search_size,
                           sort_by=sort_by, sort_order=sort_order)


@app.route('/player/<path:filename>')
def player(filename):
    filepath = resolve_media_path(filename)

    if filepath is None or not os.path.isfile(filepath):
        abort(404)

    file_type = get_file_type(filename)
    if not is_media_playable(file_type):
        abort(400)

    mime_type = get_mime_type(filename)

    base_dir = os.path.dirname(filepath)
    dir_files = []
    try:
        allowed_exts = [e.strip() for e in config.ALLOWED_EXTENSIONS.lower().split(" ") if e]
        for entry in sorted(os.listdir(base_dir)):
            if not os.path.isfile(os.path.join(base_dir, entry)):
                continue
            if allowed_exts and not any(entry.lower().endswith(e) for e in allowed_exts):
                continue
            if get_file_type(entry) != file_type:
                continue
            dir_files.append(entry)
    except OSError:
        pass

    current_i = dir_files.index(os.path.basename(filename)) if os.path.basename(filename) in dir_files else -1
    prev_file = dir_files[current_i - 1] if current_i > 0 else None
    next_file = dir_files[current_i + 1] if current_i != -1 and current_i < len(dir_files) - 1 else None

    dir_prefix = os.path.dirname(filename)
    if prev_file:
        prev_file = f"{dir_prefix}/{prev_file}" if dir_prefix else prev_file
    if next_file:
        next_file = f"{dir_prefix}/{next_file}" if dir_prefix else next_file

    subtitle = _find_subtitle(filepath)

    log_activity("media_play_request", {"filename": filename, "type": file_type})

    return render_template(
        "player.html",
        filename=filename,
        file_type=file_type,
        mime_type=mime_type,
        prev_file=prev_file,
        next_file=next_file,
        subtitle=subtitle,
    )


def _find_subtitle(filepath):
    base = os.path.splitext(filepath)[0]
    for ext in (".srt", ".vtt", ".ass", ".ssa"):
        sub_path = base + ext
        if os.path.isfile(sub_path):
            return os.path.basename(sub_path)
    return None


@app.route('/media/<path:filename>')
def serve_media(filename):
    filepath = resolve_media_path(filename)

    if filepath is None or not os.path.isfile(filepath):
        abort(404)

    log_activity("file_download_request", {"filename": filename})
    return send_file(filepath)


@app.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    filepath = safe_join(config.THUMBNAIL_FOLDER, filename)

    if filepath is None or not os.path.isfile(filepath):
        abort(404)

    return send_file(filepath)


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


@app.route('/upload', methods=['POST'])
def upload_file():
    relative_dir = request.form.get("dir", "")
    dest_dir = safe_join(config.MEDIA_FOLDER, relative_dir) if relative_dir else config.MEDIA_FOLDER

    if dest_dir is None:
        abort(400)

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    uploaded = request.files['file']
    if uploaded.filename == '':
        return jsonify({"error": "No file selected"}), 400

    filename = os.path.basename(uploaded.filename)
    dest_path = os.path.join(dest_dir, filename)

    if os.path.exists(dest_path):
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(dest_dir, f"{base}_{counter}{ext}")):
            counter += 1
        filename = f"{base}_{counter}{ext}"
        dest_path = os.path.join(dest_dir, filename)

    uploaded.save(dest_path)
    log_activity("file_uploaded", {"filename": filename, "dir": relative_dir})
    key = request.args.get('key')

    if relative_dir:
        return redirect(url_for('index', key=key, dir=relative_dir))
    return redirect(url_for('index', key=key))


@app.route('/delete', methods=['POST'])
def delete_file():
    filename = request.form.get("filename", "")
    relative_dir = request.form.get("dir", "")

    filepath = safe_join(config.MEDIA_FOLDER, relative_dir, filename) if relative_dir else safe_join(config.MEDIA_FOLDER, filename)

    if filepath is None or not os.path.isfile(filepath):
        return jsonify({"error": "File not found"}), 404

    os.remove(filepath)
    log_activity("file_deleted", {"filename": filename, "dir": relative_dir})
    return jsonify({"success": True})


@app.route('/rename', methods=['POST'])
def rename_file():
    filename = request.form.get("filename", "")
    new_name = request.form.get("new_name", "")
    relative_dir = request.form.get("dir", "")

    if not new_name or not filename:
        return jsonify({"error": "Both filename and new_name required"}), 400

    filepath = safe_join(config.MEDIA_FOLDER, relative_dir, filename) if relative_dir else safe_join(config.MEDIA_FOLDER, filename)
    new_filepath = safe_join(config.MEDIA_FOLDER, relative_dir, new_name) if relative_dir else safe_join(config.MEDIA_FOLDER, new_name)

    if filepath is None or new_filepath is None:
        return jsonify({"error": "Invalid path"}), 400

    if not os.path.isfile(filepath):
        return jsonify({"error": "File not found"}), 404

    if os.path.exists(new_filepath):
        return jsonify({"error": "Target filename already exists"}), 409

    os.rename(filepath, new_filepath)
    log_activity("file_renamed", {"from": filename, "to": new_name, "dir": relative_dir})
    return jsonify({"success": True})


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if authenticate_user(username, password):
            session['authenticated'] = True
            session['username'] = username
            log_activity("user_login", {"username": username})
            key = request.args.get('key')
            if key:
                return redirect(url_for('index', key=key))
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid username or password"), 401
    return render_template('login.html', error=None)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


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

    if os.path.isdir(config.BASE_DIR):
        shutil.rmtree(config.BASE_DIR, ignore_errors=True)
        console.print(f"[green]Removed localfs data: {config.BASE_DIR}[/green]")

    sys.exit(0)


@click.command()
@click.version_option(version=config.VERSION, prog_name="localfs")
@click.option('-s', '--share', is_flag=True, help='Enable the API endpoint to share logged data.')
@click.option('--selfuninstall', is_flag=True, help='Uninstall localfs and clean up configuration.')
@click.option('--port', type=int, default=None, help='Server port (default: 5000).')
@click.option('--host', default=None, help='Server bind address (default: 0.0.0.0).')
@click.option('--key', default=None, help='Access key for this session.')
@click.option('--media', default=None, help='Path to media directory.')
@click.option('--no-auth', is_flag=True, help='Disable access key requirement.')
@click.option('--theme', default=None, help='Theme name (default: dark).')
@click.option('--mode', default=None, type=click.Choice(['dark', 'light']), help='Color mode: dark or light.')
@click.option('--add-user', default=None, help='Create a user account (prompts for password).')
@click.option('--remove-user', default=None, help='Remove a user account.')
def main(share, selfuninstall, port, host, key, media, no_auth, theme, mode, add_user, remove_user):
    """localfs: A simple local file sharing service."""
    if selfuninstall:
        _self_uninstall()
        return

    global _share_enabled
    _share_enabled = share

    if port is not None:
        config.PORT = port
    if host is not None:
        config.HOST = host
    if key is not None:
        config.API_KEY = key
    if media is not None:
        config.MEDIA_FOLDER = os.path.abspath(media)
    if no_auth:
        config.WEBSITE_ACCESS_KEY_REQUIRED = False
    if theme is not None:
        theme_mod.save_config(theme, mode)
        theme_mod.load_config()
    elif mode is not None:
        theme_mod.save_config(theme_mod.CURRENT_THEME, mode)
        theme_mod.load_config()

    if add_user:
        import getpass
        password = getpass.getpass(f"Password for '{add_user}': ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            console.print("[red]Passwords do not match.[/red]")
            sys.exit(1)
        if len(password) < 4:
            console.print("[red]Password must be at least 4 characters.[/red]")
            sys.exit(1)
        add_user(add_user, password)
        console.print(f"[green]User '{add_user}' created.[/green]")
        sys.exit(0)

    if remove_user:
        if not user_exists(remove_user):
            console.print(f"[red]User '{remove_user}' not found.[/red]")
            sys.exit(1)
        remove_user(remove_user)
        console.print(f"[green]User '{remove_user}' removed.[/green]")
        sys.exit(0)

    setup_directories()

    console.print("[bold green]Starting localfs server...[/bold green]")
    console.print(f" * Media Folder: [cyan]{os.path.abspath(config.MEDIA_FOLDER)}[/cyan]")

    access_url = f"http://{config.HOST}:{config.PORT}"
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
