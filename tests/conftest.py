import pytest
import os
import shutil
import json
import sys
import tempfile
from pathlib import Path

_src = Path(__file__).parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

import localfs.config as config
import localfs.main as main


@pytest.fixture(scope="session")
def test_root():
    root = Path(__file__).parent.parent / ".pytest_tmp"
    root.mkdir(parents=True, exist_ok=True)
    yield root
    shutil.rmtree(str(root), ignore_errors=True)


@pytest.fixture
def media_dir(test_root):
    d = test_root / "media"
    d.mkdir(parents=True, exist_ok=True)
    yield d
    shutil.rmtree(str(d), ignore_errors=True)


@pytest.fixture
def data_dir(test_root):
    d = test_root / "data"
    d.mkdir(parents=True, exist_ok=True)
    yield d
    shutil.rmtree(str(d), ignore_errors=True)


@pytest.fixture
def thumb_dir(test_root):
    d = test_root / "static" / "thumbnails"
    d.mkdir(parents=True, exist_ok=True)
    yield d
    shutil.rmtree(str(d), ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_theme(monkeypatch, tmp_path):
    import localfs.theme as theme
    theme.CURRENT_THEME = "dark"
    theme.CURRENT_MODE = "dark"
    monkeypatch.setattr(theme, "CONFIG_DIR", str(tmp_path / ".config" / "neostore" / "localfs"))
    monkeypatch.setattr(theme, "CONFIG_FILE", str(tmp_path / ".config" / "neostore" / "localfs" / "config.toml"))


@pytest.fixture(autouse=True)
def reset_share_enabled():
    main._share_enabled = False
    yield


@pytest.fixture(autouse=True)
def mute_console(monkeypatch):
    monkeypatch.setattr(main.console, "print", lambda *a, **kw: None)


@pytest.fixture(autouse=True)
def clean_thumbnail_state():
    with main._thumbnail_lock:
        main._thumbnail_pending.clear()
        main._thumbnail_failed.clear()
    yield


@pytest.fixture
def test_config(monkeypatch, media_dir, data_dir, thumb_dir):
    monkeypatch.setattr(config, "MEDIA_FOLDER", str(media_dir))
    monkeypatch.setattr(config, "DATA_FOLDER", str(data_dir))
    monkeypatch.setattr(config, "THUMBNAIL_FOLDER", str(thumb_dir))
    monkeypatch.setattr(config, "WEBSITE_ACCESS_KEY_REQUIRED", False)
    monkeypatch.setattr(config, "DEBUG", False)
    return config


@pytest.fixture
def client(test_config):
    with main.app.test_client() as c:
        yield c


@pytest.fixture
def sample_files(media_dir):
    files = {
        "video.mp4": b"fake mp4",
        "video.mkv": b"fake mkv",
        "audio.mp3": b"fake mp3",
    }
    for name, content in files.items():
        (media_dir / name).write_bytes(content)

    subdir = media_dir / "subdir"
    subdir.mkdir()
    (subdir / "hidden.mp4").write_bytes(b"hidden")
    return files


@pytest.fixture
def data_log(data_dir):
    path = data_dir / config.DATA_FILE
    entries = [
        {"timestamp": "2025-01-01T00:00:00", "event": "page_view", "ip_address": "127.0.0.1", "details": {"page": "index"}},
    ]
    path.write_text(json.dumps(entries, indent=4))
    return path
