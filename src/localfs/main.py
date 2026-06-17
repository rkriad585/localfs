# localfs/main.py

import os
import sys
import json
import zipfile
import subprocess
import importlib.util
import shutil
import mimetypes
from io import BytesIO
from datetime import datetime

from . import config

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

def _detect_platform():
    import platform as _platform
    system = _platform.system().lower()

    if system == "linux":
        if shutil.which("apt-get"):
            sudo = ["sudo"] if shutil.which("sudo") else []
            return "linux", "apt-get", sudo + ["apt-get", "install", "-y"], "ffmpeg"
        if shutil.which("dnf"):
            sudo = ["sudo"] if shutil.which("sudo") else []
            return "linux", "dnf", sudo + ["dnf", "install", "-y"], "ffmpeg"
        if shutil.which("yum"):
            sudo = ["sudo"] if shutil.which("sudo") else []
            return "linux", "yum", sudo + ["yum", "install", "-y"], "ffmpeg"
        if shutil.which("pacman"):
            sudo = ["sudo"] if shutil.which("sudo") else []
            return "linux", "pacman", sudo + ["pacman", "-S", "--noconfirm"], "ffmpeg"
        if shutil.which("zypper"):
            sudo = ["sudo"] if shutil.which("sudo") else []
            return "linux", "zypper", sudo + ["zypper", "install", "-y"], "ffmpeg"
        if shutil.which("apk"):
            sudo = ["sudo"] if shutil.which("sudo") else []
            return "linux", "apk", sudo + ["apk", "add"], "ffmpeg"
    elif system == "darwin":
        if shutil.which("brew"):
            return "macos", "brew", ["brew", "install"], "ffmpeg"
    elif system == "windows":
        if shutil.which("winget"):
            return "windows", "winget", ["winget", "install", "--exact"], "FFmpeg"
        if shutil.which("choco"):
            return "windows", "choco", ["choco", "install", "-y"], "ffmpeg"

    return system, None, None, "ffmpeg"


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

    if shutil.which("ffmpeg"):
        return

    out("Warning: ffmpeg is not installed — video thumbnails will not be generated.")
    os_name, pkg_manager, install_cmd, pkg_name = _detect_platform()

    if pkg_manager is None:
        out(f"Auto-install not supported on {os_name}.")
        out("Install ffmpeg manually:")
        out("  - Windows: Download from https://ffmpeg.org/download.html and add to PATH.")
        out("  - macOS: `brew install ffmpeg`")
        out("  - Linux: `sudo apt-get install ffmpeg` or equivalent")
        sys.exit(1)

    try:
        answer = input(f"Install ffmpeg via {pkg_manager}? (Y/n): ").lower().strip()
    except (EOFError, KeyboardInterrupt):
        answer = 'n'

    if answer in ['y', 'yes', '']:
        out(f"Installing ffmpeg via {pkg_manager}...")
        try:
            subprocess.check_call(install_cmd + [pkg_name])
            if shutil.which("ffmpeg"):
                out("ffmpeg installed successfully!")
                return
            out("Installation completed but ffmpeg not found in PATH.")
        except subprocess.CalledProcessError as e:
            out(f"Failed to install ffmpeg: {e}")
        except FileNotFoundError:
            out(f"Could not run '{install_cmd[0]}'. Install ffmpeg manually.")

    out("Continuing without ffmpeg — thumbnails will not be generated.")

check_and_install_dependencies()
check_ffmpeg()

from flask import Flask, render_template, send_from_directory, send_file, request, jsonify, g, abort, redirect, url_for, session
from concurrent.futures import ThreadPoolExecutor
import threading
from werkzeug.security import generate_password_hash, check_password_hash
from rich.console import Console
import click

from . import theme as theme_mod

console = Console()
_pkg_dir = os.path.dirname(__file__)
app = Flask(__name__,
    template_folder=os.path.join(_pkg_dir, 'templates'),
    static_folder=os.path.join(_pkg_dir, 'static'))
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
    os.makedirs(config.TRASH_FOLDER, exist_ok=True)

def log_activity(event_type, details):
    log_file_path = os.path.join(config.DATA_FOLDER, config.DATA_FILE)
    try:
        os.makedirs(config.DATA_FOLDER, exist_ok=True)
    except Exception:
        pass
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


# ─── Trash / Recycle Bin ──────────────────────────────────────────────────────

def _load_trash_metadata():
    path = os.path.join(config.TRASH_FOLDER, config.TRASH_METADATA_FILE)
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_trash_metadata(meta):
    os.makedirs(config.TRASH_FOLDER, exist_ok=True)
    path = os.path.join(config.TRASH_FOLDER, config.TRASH_METADATA_FILE)
    try:
        with open(path, 'w') as f:
            json.dump(meta, f, indent=4)
    except Exception as e:
        console.print(f"[bold red]Error saving trash metadata:[/bold red] {e}")


def _trash_file(filepath, relative_path=""):
    if not os.path.isfile(filepath):
        return False
    os.makedirs(config.TRASH_FOLDER, exist_ok=True)
    filename = os.path.basename(filepath)
    trash_name = f"{int(datetime.now().timestamp())}_{filename}"
    trash_path = os.path.join(config.TRASH_FOLDER, trash_name)
    try:
        shutil.move(filepath, trash_path)
    except Exception as e:
        console.print(f"[bold red]Error moving file to trash:[/bold red] {e}")
        return False
    meta = _load_trash_metadata()
    meta[trash_name] = {
        "original_name": filename,
        "original_path": relative_path,
        "trash_name": trash_name,
        "deleted_at": datetime.now().isoformat(),
        "expires_at": (datetime.now().isoformat()),
    }
    _save_trash_metadata(meta)
    _purge_old_trash()
    return trash_name


def _restore_file(trash_name):
    meta = _load_trash_metadata()
    entry = meta.pop(trash_name, None)
    if entry is None:
        return False
    _save_trash_metadata(meta)
    trash_path = os.path.join(config.TRASH_FOLDER, trash_name)
    if not os.path.isfile(trash_path):
        return False
    orig_dir = resolve_media_path(entry["original_path"]) if entry["original_path"] else config.MEDIA_FOLDER
    if orig_dir is None:
        orig_dir = config.MEDIA_FOLDER
    os.makedirs(orig_dir, exist_ok=True)
    dest = os.path.join(orig_dir, entry["original_name"])
    counter = 1
    while os.path.exists(dest):
        base, ext = os.path.splitext(entry["original_name"])
        dest = os.path.join(orig_dir, f"{base}_{counter}{ext}")
        counter += 1
    try:
        shutil.move(trash_path, dest)
    except Exception as e:
        console.print(f"[bold red]Error restoring file:[/bold red] {e}")
        return False
    return True


def _purge_old_trash():
    meta = _load_trash_metadata()
    now = datetime.now()
    changed = False
    expired = []
    for trash_name, entry in list(meta.items()):
        try:
            deleted = datetime.fromisoformat(entry["deleted_at"])
            delta = (now - deleted).days
            if delta > config.TRASH_TTL_DAYS:
                expired.append(trash_name)
        except (ValueError, KeyError):
            expired.append(trash_name)
    for trash_name in expired:
        meta.pop(trash_name, None)
        trash_path = os.path.join(config.TRASH_FOLDER, trash_name)
        if os.path.isfile(trash_path):
            try:
                os.remove(trash_path)
            except OSError:
                pass
        changed = True
    if changed:
        _save_trash_metadata(meta)


def _list_trash():
    _purge_old_trash()
    meta = _load_trash_metadata()
    items = []
    for trash_name, entry in meta.items():
        filepath = os.path.join(config.TRASH_FOLDER, trash_name)
        size = get_file_size(filepath) if os.path.isfile(filepath) else "?"
        items.append({
            "trash_name": trash_name,
            "original_name": entry.get("original_name", trash_name),
            "original_path": entry.get("original_path", ""),
            "deleted_at": entry.get("deleted_at", ""),
            "size": size,
            "file_type": get_file_type(entry.get("original_name", trash_name)),
        })
    items.sort(key=lambda x: x.get("deleted_at", ""), reverse=True)
    return items


def _empty_trash():
    meta = _load_trash_metadata()
    for trash_name in list(meta.keys()):
        trash_path = os.path.join(config.TRASH_FOLDER, trash_name)
        if os.path.isfile(trash_path):
            try:
                os.remove(trash_path)
            except OSError:
                pass
    _save_trash_metadata({})


PREVIEWABLE_EXTENSIONS = {
    '.txt': 'text', '.py': 'code', '.js': 'code', '.ts': 'code',
    '.jsx': 'code', '.tsx': 'code', '.html': 'code', '.htm': 'code',
    '.css': 'code', '.scss': 'code', '.json': 'code', '.xml': 'code',
    '.yaml': 'code', '.yml': 'code', '.toml': 'code', '.ini': 'code',
    '.cfg': 'code', '.conf': 'code', '.sh': 'code', '.bash': 'code',
    '.zsh': 'code', '.fish': 'code', '.log': 'text', '.csv': 'text',
    '.md': 'markdown', '.mdx': 'markdown', '.rst': 'markdown',
    '.sql': 'code', '.rb': 'code', '.go': 'code', '.rs': 'code',
    '.java': 'code', '.c': 'code', '.cpp': 'code', '.h': 'code',
    '.hpp': 'code', '.php': 'code', '.r': 'code', '.lua': 'code',
    '.pl': 'code', '.pm': 'code', '.swift': 'code', '.kt': 'code',
    '.scala': 'code', '.groovy': 'code', '.gradle': 'code',
    '.bat': 'code', '.ps1': 'code', '.env': 'text', '.gitignore': 'text',
    '.dockerignore': 'text', '.editorconfig': 'text',
    '.vue': 'code', '.svelte': 'code', '.astro': 'code',
    '.tex': 'text', '.pdf': 'pdf',
}

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

def is_previewable(filename):
    _, ext = os.path.splitext(filename)
    return ext.lower() in PREVIEWABLE_EXTENSIONS

def get_preview_type(filename):
    _, ext = os.path.splitext(filename)
    return PREVIEWABLE_EXTENSIONS.get(ext.lower(), 'text')

def get_language_class(filename):
    _, ext = os.path.splitext(filename)
    lang_map = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.jsx': 'javascript', '.tsx': 'typescript',
        '.html': 'html', '.htm': 'html', '.css': 'css',
        '.json': 'json', '.xml': 'xml', '.yaml': 'yaml', '.yml': 'yaml',
        '.toml': 'toml', '.sh': 'bash', '.bash': 'bash', '.zsh': 'bash',
        '.fish': 'bash', '.sql': 'sql', '.rb': 'ruby', '.go': 'go',
        '.rs': 'rust', '.java': 'java', '.c': 'c', '.cpp': 'cpp',
        '.h': 'c', '.hpp': 'cpp', '.php': 'php', '.r': 'r',
        '.lua': 'lua', '.swift': 'swift', '.kt': 'kotlin',
        '.scala': 'scala', '.groovy': 'groovy', '.gradle': 'groovy',
        '.bat': 'bat', '.ps1': 'powershell',
        '.vue': 'html', '.svelte': 'html', '.astro': 'html',
        '.tex': 'latex', '.md': 'markdown', '.mdx': 'markdown',
        '.rst': 'markdown', '.csv': 'csv',
    }
    return lang_map.get(ext.lower(), '')

# ─── Media Metadata ───────────────────────────────────────────────────────────

_METADATA_CACHE = {}
_METADATA_CACHE_MAX = 200

def get_media_metadata(filename):
    abs_path = resolve_media_path(filename)
    if abs_path is None or not os.path.isfile(abs_path):
        return None

    key = os.path.abspath(abs_path)
    cached = _METADATA_CACHE.get(key)
    if cached:
        return cached

    meta = {"filename": os.path.basename(abs_path)}
    ext = os.path.splitext(abs_path)[1].lower()
    img_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.avif'}
    video_exts = {'.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v', '.ts', '.mts'}

    stat = os.stat(abs_path)
    meta["size"] = stat.st_size
    meta["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()

    if ext in img_exts:
        try:
            from PIL import Image
            with Image.open(abs_path) as img:
                meta["width"] = img.width
                meta["height"] = img.height
                meta["format"] = img.format
                meta["mode"] = img.mode
        except Exception:
            pass
    elif ext in video_exts or ext == '.mp3':
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json',
                 '-show_format', '-show_streams', abs_path],
                capture_output=True, text=True, timeout=15
            )
            data = json.loads(result.stdout)
            fmt = data.get("format", {})
            streams = data.get("streams", [])
            meta["duration"] = float(fmt.get("duration", 0))
            meta["bitrate"] = int(fmt.get("bit_rate", 0))
            for s in streams:
                codec_type = s.get("codec_type")
                if codec_type == "video" and "width" not in meta:
                    meta["width"] = s.get("width")
                    meta["height"] = s.get("height")
                    meta["video_codec"] = s.get("codec_name")
                    meta["video_codec_long"] = s.get("codec_long_name")
                elif codec_type == "audio" and "audio_codec" not in meta:
                    meta["audio_codec"] = s.get("codec_name")
                    meta["audio_channels"] = s.get("channels")
                    meta["sample_rate"] = s.get("sample_rate")
        except Exception:
            pass

    if len(_METADATA_CACHE) >= _METADATA_CACHE_MAX:
        _METADATA_CACHE.clear()
    _METADATA_CACHE[key] = meta
    return meta


_thumbnail_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="thumb")
_thumbnail_pending = set()
_thumbnail_failed = set()
_thumbnail_lock = threading.Lock()


def _generate_thumbnail_task(filename, source_path, thumb_rel, dest_path, thumb_dir):
    try:
        os.makedirs(thumb_dir, exist_ok=True)
        command = [
            'ffmpeg', '-i', source_path, '-ss', '00:00:01.000',
            '-vframes', '1', '-y', dest_path, '-loglevel', 'error'
        ]
        subprocess.run(command, check=True)
        with _thumbnail_lock:
            _thumbnail_pending.discard(filename)
        return True
    except Exception as e:
        with _thumbnail_lock:
            _thumbnail_pending.discard(filename)
            _thumbnail_failed.add(filename)
        console.print(f"[bold yellow]Warning:[/bold yellow] Could not generate thumbnail for '{filename}'. Reason: {e}")
        return False


def generate_thumbnail(filename):
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

    with _thumbnail_lock:
        if filename in _thumbnail_pending or filename in _thumbnail_failed:
            return None
        _thumbnail_pending.add(filename)

    _thumbnail_executor.submit(
        _generate_thumbnail_task, filename, source_path,
        thumb_rel, dest_path, thumb_dir
    )
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
    previewable = is_previewable(entry) if file_type == 'other' else False
    has_meta = file_type in ("video", "audio", "image")
    info = {
        "name": entry,
        "path": rel_path,
        "type": file_type,
        "size": get_file_size(filepath),
        "is_playable": is_media_playable(file_type),
        "is_previewable": previewable,
        "has_metadata": has_meta,
        "preview_type": get_preview_type(entry) if previewable else None,
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
    exemptions = ['login', 'static', 'serve_media', 'serve_thumbnail', 'preview_file', 'trash_list', 'trash_restore', 'trash_empty']
    if request.endpoint in exemptions:
        return
    if config.WEBSITE_ACCESS_KEY_REQUIRED:
        protected_endpoints = ['index', 'player', 'settings', 'upload_file', 'delete_file', 'rename_file', 'batch_delete', 'batch_download', 'create_dir', 'move_file', 'copy_file', 'dir_tree', 'api_metadata', 'gallery_images', 'poll_changes']
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


def _try_render_markdown(text):
    try:
        import markdown
        return markdown.markdown(text, extensions=['fenced_code', 'codehilite', 'tables'])
    except ImportError:
        return None


@app.route('/preview/<path:filename>')
def preview_file(filename):
    filepath = resolve_media_path(filename)

    if filepath is None or not os.path.isfile(filepath):
        abort(404)

    preview_type = get_preview_type(filename)
    file_size = get_file_size(filepath)

    if preview_type == 'pdf':
        return render_template('preview.html', filename=filename, preview_type='pdf',
                               content=None, language='', filepath=filename,
                               raw_content=None, file_size=file_size)

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
    except Exception:
        abort(500)

    content = raw
    raw_content = raw
    language = get_language_class(filename)

    if preview_type == 'markdown':
        rendered = _try_render_markdown(raw)
        if rendered:
            content = rendered
            preview_type = 'rendered_markdown'

    log_activity("file_preview", {"filename": filename, "preview_type": preview_type})

    return render_template('preview.html', filename=filename, preview_type=preview_type,
                           content=content, raw_content=raw_content,
                           language=language, filepath=filename, file_size=file_size)


@app.route('/media/<path:filename>')
def serve_media(filename):
    filepath = resolve_media_path(filename)

    if filepath is None or not os.path.isfile(filepath):
        abort(404)

    log_activity("file_download_request", {"filename": filename})
    return send_file(filepath)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, "logo.svg", mimetype="image/svg+xml")


@app.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    filepath = safe_join(config.THUMBNAIL_FOLDER, filename)

    if filepath is None or not os.path.isfile(filepath):
        abort(404)

    return send_file(filepath)


@app.route('/api/metadata', methods=['POST'])
def api_metadata():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename", "")
    rel_dir = data.get("dir", "")

    if not filename:
        return jsonify({"error": "Filename required"}), 400

    full_path = os.path.join(rel_dir, filename) if rel_dir else filename
    meta = get_media_metadata(full_path)
    if meta is None:
        return jsonify({"error": "File not found"}), 404

    log_activity("metadata_requested", {"filename": full_path})
    return jsonify(meta)


@app.route('/gallery-images')
def gallery_images():
    rel_dir = request.args.get("dir", "")
    directory = safe_join(config.MEDIA_FOLDER, rel_dir) if rel_dir else config.MEDIA_FOLDER
    if directory is None or not os.path.isdir(directory):
        return jsonify([])

    img_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.avif', '.svg'}
    images = []
    try:
        for entry in sorted(os.listdir(directory)):
            ext = os.path.splitext(entry)[1].lower()
            if ext in img_exts:
                rel = os.path.join(rel_dir, entry) if rel_dir else entry
                images.append({
                    "name": entry,
                    "path": rel,
                    "url": url_for('serve_media', filename=rel),
                    "thumbnail": url_for('serve_media', filename=rel),
                })
    except OSError:
        pass
    return jsonify(images)


@app.route('/poll-changes')
def poll_changes():
    rel_dir = request.args.get("dir", "")
    directory = safe_join(config.MEDIA_FOLDER, rel_dir) if rel_dir else config.MEDIA_FOLDER
    if directory is None or not os.path.isdir(directory):
        return jsonify({"hash": ""})

    parts = []
    try:
        for entry in sorted(os.listdir(directory)):
            fp = os.path.join(directory, entry)
            try:
                mtime = os.path.getmtime(fp)
            except OSError:
                mtime = 0
            parts.append(f"{entry}:{mtime}")
    except OSError:
        pass

    import hashlib
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return jsonify({"hash": h})


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

    trash_name = _trash_file(filepath, relative_dir)
    if not trash_name:
        return jsonify({"error": "Failed to move file to trash"}), 500

    log_activity("file_deleted", {"filename": filename, "dir": relative_dir, "trash_name": trash_name})
    return jsonify({"success": True, "trash_name": trash_name})


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


# ─── Trash routes ─────────────────────────────────────────────────────────────

@app.route('/trash', methods=['GET'])
def trash_list():
    items = _list_trash()
    return render_template('trash.html', items=items)


@app.route('/trash/restore', methods=['POST'])
def trash_restore():
    trash_name = request.form.get("trash_name", "")
    if not trash_name:
        return jsonify({"error": "Missing trash_name"}), 400
    if _restore_file(trash_name):
        log_activity("file_restored", {"trash_name": trash_name})
        return jsonify({"success": True})
    return jsonify({"error": "Failed to restore file"}), 404


@app.route('/trash/empty', methods=['POST'])
def trash_empty():
    _empty_trash()
    log_activity("trash_emptied", {})
    return jsonify({"success": True})


# ─── Batch operations ─────────────────────────────────────────────────────────

@app.route('/batch-delete', methods=['POST'])
def batch_delete():
    data = request.get_json(silent=True)
    if not data or "files" not in data:
        return jsonify({"error": "No files provided"}), 400
    results = []
    for entry in data["files"]:
        filename = entry.get("filename", "")
        relative_dir = entry.get("dir", "")
        filepath = safe_join(config.MEDIA_FOLDER, relative_dir, filename) if relative_dir else safe_join(config.MEDIA_FOLDER, filename)
        if filepath and os.path.isfile(filepath):
            trash_name = _trash_file(filepath, relative_dir)
            results.append({"filename": filename, "success": bool(trash_name), "trash_name": trash_name})
        else:
            results.append({"filename": filename, "success": False, "error": "not_found"})
    log_activity("batch_delete", {"count": len(results)})
    return jsonify({"results": results, "total": len(results), "succeeded": sum(1 for r in results if r["success"])})


@app.route('/batch-download', methods=['POST'])
def batch_download():
    data = request.get_json(silent=True)
    if not data or "files" not in data:
        return jsonify({"error": "No files provided"}), 400
    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for entry in data["files"]:
            filename = entry.get("filename", "")
            relative_dir = entry.get("dir", "")
            filepath = safe_join(config.MEDIA_FOLDER, relative_dir, filename) if relative_dir else safe_join(config.MEDIA_FOLDER, filename)
            if filepath and os.path.isfile(filepath):
                arcname = os.path.join(relative_dir, filename) if relative_dir else filename
                zf.write(filepath, arcname)
    buf.seek(0)
    log_activity("batch_download", {"count": len(data["files"])})
    return send_file(buf, mimetype='application/zip', as_attachment=True, download_name='localfs-batch.zip')


# ─── Directory and file management ────────────────────────────────────────────

@app.route('/create-dir', methods=['POST'])
def create_dir():
    dirname = request.form.get("dirname", "").strip()
    relative_dir = request.form.get("dir", "")

    if not dirname:
        return jsonify({"error": "Directory name required"}), 400

    if not _is_valid_filename(dirname):
        return jsonify({"error": "Invalid directory name"}), 400

    parent = safe_join(config.MEDIA_FOLDER, relative_dir) if relative_dir else config.MEDIA_FOLDER
    if parent is None:
        return jsonify({"error": "Invalid path"}), 400

    new_dir = os.path.join(parent, dirname)
    if os.path.exists(new_dir):
        return jsonify({"error": "Directory already exists"}), 409

    try:
        os.makedirs(new_dir, exist_ok=True)
        log_activity("dir_created", {"dirname": dirname, "parent": relative_dir})
        return jsonify({"success": True, "path": os.path.join(relative_dir, dirname) if relative_dir else dirname})
    except OSError as e:
        return jsonify({"error": str(e)}), 500


def _is_valid_filename(name):
    if not name or len(name) > 255:
        return False
    forbidden = set('/\\\0')
    return not any(c in forbidden for c in name)


def _list_available_dirs(base_dir):
    dirs = []
    try:
        for entry in sorted(os.listdir(base_dir)):
            full = os.path.join(base_dir, entry)
            if os.path.isdir(full) and not entry.startswith('.'):
                dirs.append(entry)
    except OSError:
        pass
    return dirs


@app.route('/dir-tree', methods=['GET'])
def dir_tree():
    current = request.args.get("dir", "")
    base = safe_join(config.MEDIA_FOLDER, current) if current else config.MEDIA_FOLDER
    if base is None or not os.path.isdir(base):
        return jsonify([])
    subdirs = _list_available_dirs(base)
    return jsonify([{"name": d, "path": os.path.join(current, d) if current else d} for d in subdirs])


@app.route('/move-file', methods=['POST'])
def move_file():
    filename = request.form.get("filename", "")
    source_dir = request.form.get("source_dir", "")
    target_dir = request.form.get("target_dir", "")

    if not filename:
        return jsonify({"error": "Filename required"}), 400

    src = safe_join(config.MEDIA_FOLDER, source_dir, filename) if source_dir else safe_join(config.MEDIA_FOLDER, filename)
    dst_dir = safe_join(config.MEDIA_FOLDER, target_dir) if target_dir else config.MEDIA_FOLDER

    if src is None or dst_dir is None:
        return jsonify({"error": "Invalid path"}), 400
    if not os.path.isfile(src):
        return jsonify({"error": "File not found"}), 404
    if not os.path.isdir(dst_dir):
        return jsonify({"error": "Target directory not found"}), 404

    dst = os.path.join(dst_dir, filename)
    if os.path.exists(dst):
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(dst_dir, f"{base}_{counter}{ext}")):
            counter += 1
        dst = os.path.join(dst_dir, f"{base}_{counter}{ext}")

    try:
        shutil.move(src, dst)
        log_activity("file_moved", {"filename": filename, "from": source_dir, "to": target_dir})
        return jsonify({"success": True})
    except OSError as e:
        return jsonify({"error": str(e)}), 500


@app.route('/copy-file', methods=['POST'])
def copy_file():
    filename = request.form.get("filename", "")
    source_dir = request.form.get("source_dir", "")
    target_dir = request.form.get("target_dir", "")

    if not filename:
        return jsonify({"error": "Filename required"}), 400

    src = safe_join(config.MEDIA_FOLDER, source_dir, filename) if source_dir else safe_join(config.MEDIA_FOLDER, filename)
    dst_dir = safe_join(config.MEDIA_FOLDER, target_dir) if target_dir else config.MEDIA_FOLDER

    if src is None or dst_dir is None:
        return jsonify({"error": "Invalid path"}), 400
    if not os.path.isfile(src):
        return jsonify({"error": "File not found"}), 404
    if not os.path.isdir(dst_dir):
        return jsonify({"error": "Target directory not found"}), 404

    dst = os.path.join(dst_dir, filename)
    if os.path.exists(dst):
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(dst_dir, f"{base}_{counter}{ext}")):
            counter += 1
        dst = os.path.join(dst_dir, f"{base}_{counter}{ext}")

    try:
        shutil.copy2(src, dst)
        log_activity("file_copied", {"filename": filename, "from": source_dir, "to": target_dir})
        return jsonify({"success": True})
    except OSError as e:
        return jsonify({"error": str(e)}), 500


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
@click.option('-s', '--share', is_flag=False, flag_value='key', default=None,
              help='Enable API sharing. Use "--share free" to run without any key/auth.')
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
    if share == 'free':
        _share_enabled = True
        config.WEBSITE_ACCESS_KEY_REQUIRED = False
    elif share == 'key':
        _share_enabled = True
    else:
        _share_enabled = False

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

    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    access_url_local = f"http://127.0.0.1:{config.PORT}"
    access_url_net = f"http://{local_ip}:{config.PORT}"

    if share == 'free':
        console.print(f" * Mode: [bold green]Free[/bold green] — no key required, open access")
        console.print(f" * Local:    [link={access_url_local}]{access_url_local}[/link]")
        console.print(f" * Network:  [link={access_url_net}]{access_url_net}[/link]")
    elif config.WEBSITE_ACCESS_KEY_REQUIRED:
        console.print(f" * Website Access Key: [bold magenta]{config.API_KEY}[/bold magenta]")
        console.print(f" * Local:    [link={access_url_local}/?key={config.API_KEY}]{access_url_local}/?key={config.API_KEY}[/link]")
        console.print(f" * Network:  [link={access_url_net}/?key={config.API_KEY}]{access_url_net}/?key={config.API_KEY}[/link]")
    else:
        console.print(f" * Local:    [link={access_url_local}]{access_url_local}[/link]")
        console.print(f" * Network:  [link={access_url_net}]{access_url_net}[/link]")

    if share == 'key':
        console.print(f" * API Sharing: [bold green]Enabled[/bold green] (endpoint: /api)")

    console.print("[yellow]Press CTRL+C to stop the server.[/yellow]")

    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, threaded=True)


if __name__ == '__main__':
    main()
