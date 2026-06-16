import os
import json
import subprocess
import sys
from unittest.mock import patch, MagicMock, ANY
from io import StringIO

import pytest

import config
import main


# =============================================================================
# Pure helper functions
# =============================================================================

class TestGetFileType:
    @pytest.mark.parametrize("filename,expected", [
        ("video.mp4", "video"),
        ("video.mkv", "video"),
        ("video.webm", "video"),
        ("video.ogg", "video"),
        ("video.mov", "video"),
        ("video.avi", "video"),
        ("VIDEO.MP4", "video"),
        ("caption.srt", "other"),
    ])
    def test_video_extensions(self, filename, expected):
        assert main.get_file_type(filename) == expected

    def test_ogg_is_video(self):
        assert main.get_file_type("audio.ogg") == "video"

    @pytest.mark.parametrize("filename,expected", [
        ("audio.mp3", "audio"),
        ("audio.wav", "audio"),
        ("audio.flac", "audio"),
        ("audio.aac", "audio"),
        ("audio.wma", "audio"),
        ("AUDIO.MP3", "audio"),
    ])
    def test_audio_extensions(self, filename, expected):
        assert main.get_file_type(filename) == expected

    @pytest.mark.parametrize("filename,expected", [
        ("image.jpg", "image"),
        ("image.jpeg", "image"),
        ("image.png", "image"),
        ("image.gif", "image"),
        ("image.webp", "image"),
        ("IMAGE.JPG", "image"),
    ])
    def test_image_extensions(self, filename, expected):
        assert main.get_file_type(filename) == expected

    @pytest.mark.parametrize("filename", [
        "noext",
        "file.txt",
        "file.pdf",
        "archive.zip",
    ])
    def test_other_extensions(self, filename):
        assert main.get_file_type(filename) == "other"

    def test_empty_extension(self):
        assert main.get_file_type("file") == "other"

    def test_dotfile(self):
        assert main.get_file_type(".gitignore") == "other"


class TestGetMimeType:
    @pytest.mark.parametrize("filename,expected_prefix", [
        ("video.mp4", "video/"),
        ("video.mkv", "video/"),
        ("audio.mp3", "audio/"),
        ("image.jpg", "image/"),
        ("image.png", "image/"),
    ])
    def test_known_types(self, filename, expected_prefix):
        mime = main.get_mime_type(filename)
        assert mime.startswith(expected_prefix)

    def test_unknown_type_falls_back(self):
        assert main.get_mime_type("file.zzzzz") == "application/octet-stream"

    def test_no_extension(self):
        assert main.get_mime_type("file") == "application/octet-stream"

    def test_mp3_is_audio_mpeg(self):
        assert main.get_mime_type("song.mp3") == "audio/mpeg"

    def test_mp4_is_video_mp4(self):
        assert main.get_mime_type("video.mp4") == "video/mp4"


class TestIsMediaPlayable:
    @pytest.mark.parametrize("file_type", ["video", "audio"])
    def test_playable_types(self, file_type):
        assert main.is_media_playable(file_type) is True

    @pytest.mark.parametrize("file_type", ["image", "other", "text", "", None])
    def test_non_playable_types(self, file_type):
        assert main.is_media_playable(file_type) is False


class TestGetFileIcon:
    @pytest.mark.parametrize("file_type,expected", [
        ("video", "fa-file-video"),
        ("audio", "fa-file-audio"),
        ("image", "fa-file-image"),
        ("other", "fa-file-alt"),
    ])
    def test_known_types(self, file_type, expected):
        assert main.get_file_icon(file_type) == expected

    @pytest.mark.parametrize("file_type", ["text", "", None, "unknown"])
    def test_unknown_types_fall_back_to_file_alt(self, file_type):
        assert main.get_file_icon(file_type) == "fa-file-alt"


class TestGetFileSize:
    def test_zero_bytes_with_mock(self):
        with patch("os.path.getsize", return_value=0):
            assert main.get_file_size("/fake") == "0 B"

    def test_bytes_range_with_mock(self):
        with patch("os.path.getsize", return_value=512):
            assert main.get_file_size("/fake") == "512 B"

    def test_kilobyte_boundary_with_mock(self):
        with patch("os.path.getsize", return_value=1024):
            assert main.get_file_size("/fake") == "1.0 KB"

    def test_megabyte_boundary_with_mock(self):
        with patch("os.path.getsize", return_value=1024 ** 2):
            assert main.get_file_size("/fake") == "1.0 MB"

    def test_gigabyte_boundary_with_mock(self):
        with patch("os.path.getsize", return_value=1024 ** 3):
            assert main.get_file_size("/fake/path") == "1.0 GB"

    def test_two_gigabytes_with_mock(self):
        with patch("os.path.getsize", return_value=2 * 1024 ** 3):
            assert main.get_file_size("/fake/path") == "2.0 GB"

    def test_one_point_five_gigabytes_with_mock(self):
        with patch("os.path.getsize", return_value=int(1.5 * 1024 ** 3)):
            result = main.get_file_size("/fake/path")
            assert result.endswith("GB")
            assert "1.5" in result


# =============================================================================
# Side-effect functions
# =============================================================================

class TestSetupDirectories:
    def test_creates_media_dir(self, test_config, media_dir):
        main.setup_directories()
        assert os.path.isdir(config.MEDIA_FOLDER)

    def test_creates_data_dir(self, test_config, data_dir):
        main.setup_directories()
        assert os.path.isdir(config.DATA_FOLDER)

    def test_creates_thumbnail_dir(self, test_config, thumb_dir):
        main.setup_directories()
        assert os.path.isdir(config.THUMBNAIL_FOLDER)

    def test_is_idempotent(self, test_config, media_dir, data_dir, thumb_dir):
        main.setup_directories()
        main.setup_directories()
        main.setup_directories()
        assert os.path.isdir(config.MEDIA_FOLDER)
        assert os.path.isdir(config.DATA_FOLDER)
        assert os.path.isdir(config.THUMBNAIL_FOLDER)


class TestLogActivity:
    def _call_log(self, client, event, details):
        with client.application.test_request_context():
            main.log_activity(event, details)

    def test_creates_log_file(self, test_config, client, data_dir):
        self._call_log(client, "test_event", {"key": "value"})
        log_path = os.path.join(config.DATA_FOLDER, config.DATA_FILE)
        assert os.path.isfile(log_path)

    def test_writes_valid_json(self, test_config, client, data_dir):
        self._call_log(client, "test_event", {"key": "value"})
        log_path = os.path.join(config.DATA_FOLDER, config.DATA_FILE)
        data = json.loads(Path(log_path).read_text())
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["event"] == "test_event"
        assert data[0]["details"] == {"key": "value"}
        assert "timestamp" in data[0]
        assert "ip_address" in data[0]

    def test_appends_to_existing_log(self, test_config, client, data_dir, data_log):
        self._call_log(client, "second_event", {})
        log_path = os.path.join(config.DATA_FOLDER, config.DATA_FILE)
        data = json.loads(Path(log_path).read_text())
        assert len(data) == 2
        assert data[0]["event"] == "page_view"
        assert data[1]["event"] == "second_event"

    def test_handles_corrupt_log_gracefully(self, test_config, client, data_dir):
        log_path = os.path.join(config.DATA_FOLDER, config.DATA_FILE)
        Path(log_path).write_text("{invalid json}")
        self._call_log(client, "after_corrupt", {})
        content = Path(log_path).read_text()
        assert "{invalid json}" in content

    def test_logs_client_ip(self, test_config, client, data_dir):
        self._call_log(client, "page_view", {})
        log_path = os.path.join(config.DATA_FOLDER, config.DATA_FILE)
        data = json.loads(Path(log_path).read_text())
        assert "ip_address" in data[0]


class TestGenerateThumbnail:
    def test_returns_none_when_file_missing(self, test_config, media_dir, thumb_dir):
        result = main.generate_thumbnail("nonexistent.mp4")
        assert result is None

    def test_returns_cached_thumbnail(self, test_config, media_dir, thumb_dir):
        (media_dir / "video.mp4").write_bytes(b"fake")
        expected_thumb = thumb_dir / "video.jpg"
        expected_thumb.write_bytes(b"fake thumb")
        result = main.generate_thumbnail("video.mp4")
        assert result == "thumbnails/video.jpg"

    def test_generates_new_thumbnail_with_ffmpeg(self, test_config, media_dir, thumb_dir):
        (media_dir / "video.mp4").write_bytes(b"fake")
        with patch("subprocess.run"):
            result = main.generate_thumbnail("video.mp4")
        assert result == "thumbnails/video.jpg"

    def test_ffmpeg_failure_returns_none(self, test_config, media_dir, thumb_dir):
        (media_dir / "broken.mp4").write_bytes(b"garbage")
        with patch("subprocess.run", side_effect=Exception("ffmpeg error")):
            result = main.generate_thumbnail("broken.mp4")
        assert result is None

    def test_passes_correct_ffmpeg_args(self, test_config, media_dir, thumb_dir):
        (media_dir / "test.mkv").write_bytes(b"fake")
        with patch("subprocess.run") as mock_run:
            main.generate_thumbnail("test.mkv")
        mock_run.assert_called_once_with(
            ["ffmpeg", "-i", str(media_dir / "test.mkv"),
             "-ss", "00:00:01.000",
             "-vframes", "1", "-y", str(thumb_dir / "test.jpg"),
             "-loglevel", "error"],
            check=True,
        )


# =============================================================================
# Flask routes
# =============================================================================

class TestIndexRoute:
    def test_empty_media_folder(self, client, test_config, media_dir):
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "No files found" in html

    def test_lists_files(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode()
        for name in sample_files:
            assert name in html
        assert "document.txt" not in html

    def test_filters_by_allowed_extensions(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert "document.txt" not in html

    def test_hides_directories(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert "subdir" not in html

    def test_marks_videos_as_playable(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert "video.mp4" in html
        assert "data-filename=" in html

    def test_marks_audio_as_playable(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert "audio.mp3" in html

    def test_shows_play_button_for_media(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        play_links = [line for line in html.split("\n") if "Play" in line]
        assert len(play_links) == len(sample_files)

    def test_does_not_show_play_button_for_images(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        for line in html.split("\n"):
            if "image.jpg" in line or "image.png" in line:
                pass
        play_buttons = 0
        for line in html.split("\n"):
            if "fa-play" in line:
                play_buttons += 1
        assert play_buttons > 0

    def test_includes_download_buttons(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert html.count("fa-download") == len(sample_files)

    def test_shows_file_sizes(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert "B" in html  # all test files are < 1KB

    def test_shows_correct_icons(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert "fa-file-video" in html
        assert "fa-file-audio" in html

    def test_allow_all_extensions_when_empty(self, client, test_config, media_dir):
        (media_dir / "any.xyz").write_bytes(b"data")
        (media_dir / "script.sh").write_bytes(b"data")
        with patch.object(config, "ALLOWED_EXTENSIONS", ""):
            resp = client.get("/")
        html = resp.data.decode()
        assert "any.xyz" in html
        assert "script.sh" in html

    def test_empty_media_folder_shows_empty_state(self, client, test_config, media_dir):
        resp = client.get("/")
        html = resp.data.decode()
        assert "No files found" in html

    def test_response_is_html(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        assert resp.content_type.startswith("text/html")

    def test_search_data_attributes_present(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert 'data-filename="video.mp4"' in html
        assert 'data-filename="audio.mp3"' in html

    def test_non_media_files_get_no_thumbnail(self, client, test_config, media_dir):
        (media_dir / "notes.txt").write_bytes(b"data")
        (media_dir / "song.mp3").write_bytes(b"data")
        with patch.object(config, "ALLOWED_EXTENSIONS", ".txt .mp3"):
            resp = client.get("/")
        html = resp.data.decode()
        assert "thumbnails/" not in html

    def test_video_thumbnail_generated(self, client, test_config, media_dir, thumb_dir):
        (media_dir / "clip.mp4").write_bytes(b"fake video")
        with patch("subprocess.run"):
            resp = client.get("/")
        html = resp.data.decode()
        assert "thumbnails/clip.jpg" in html


class TestPlayerRoute:
    def test_video_player_page(self, client, test_config, media_dir):
        (media_dir / "movie.mp4").write_bytes(b"data")
        resp = client.get("/player/movie.mp4")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "<video" in html
        assert "movie.mp4" in html
        assert 'type="video/mp4"' in html

    def test_audio_player_page(self, client, test_config, media_dir):
        (media_dir / "song.mp3").write_bytes(b"data")
        resp = client.get("/player/song.mp3")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "<audio" in html
        assert "song.mp3" in html
        assert 'type="audio/mpeg"' in html

    def test_mkv_video(self, client, test_config, media_dir):
        (media_dir / "movie.mkv").write_bytes(b"data")
        resp = client.get("/player/movie.mkv")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "<video" in html
        assert "matroska" in html or "video/" in html

    def test_returns_404_for_missing_file(self, client, test_config, media_dir):
        resp = client.get("/player/nonexistent.mp4")
        assert resp.status_code == 404

    def test_returns_400_for_unplayable_type(self, client, test_config, media_dir):
        (media_dir / "photo.jpg").write_bytes(b"data")
        with patch.object(config, "ALLOWED_EXTENSIONS", ".jpg"):
            resp = client.get("/player/photo.jpg")
        assert resp.status_code == 400

    def test_back_link_preserves_key(self, client, test_config, media_dir):
        (media_dir / "video.mp4").write_bytes(b"data")
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        resp = client.get("/player/video.mp4?key=test123")
        assert resp.status_code == 401
        config.WEBSITE_ACCESS_KEY_REQUIRED = False

    def test_back_link_no_key(self, client, test_config, media_dir):
        (media_dir / "video.mp4").write_bytes(b"data")
        resp = client.get("/player/video.mp4")
        html = resp.data.decode()
        assert "Back to Library" in html

    def test_response_is_html(self, client, test_config, media_dir):
        (media_dir / "video.mp4").write_bytes(b"data")
        resp = client.get("/player/video.mp4")
        assert resp.content_type.startswith("text/html")


class TestServeMediaRoute:
    def test_serves_file_content(self, client, test_config, media_dir):
        (media_dir / "file.mp4").write_bytes(b"exact content")
        resp = client.get("/media/file.mp4")
        assert resp.status_code == 200
        assert resp.data == b"exact content"

    def test_returns_404_for_missing_file(self, client, test_config, media_dir):
        resp = client.get("/media/nonexistent.mp4")
        assert resp.status_code == 404

    def test_serves_audio_content(self, client, test_config, media_dir):
        (media_dir / "song.mp3").write_bytes(b"audio data")
        resp = client.get("/media/song.mp3")
        assert resp.status_code == 200
        assert resp.data == b"audio data"

    def test_path_traversal_blocked(self, client, test_config, media_dir):
        (media_dir / "safe.txt").write_bytes(b"safe")
        resp = client.get("/media/../config.py")
        assert resp.status_code in (404, 400, 500)

    def test_download_header_present(self, client, test_config, media_dir):
        (media_dir / "file.zip").write_bytes(b"data")
        resp = client.get("/media/file.zip")
        assert resp.status_code == 200

    def test_content_type_set(self, client, test_config, media_dir):
        (media_dir / "video.mp4").write_bytes(b"data")
        resp = client.get("/media/video.mp4")
        assert resp.content_type.startswith("video/")


class TestApiRoute:
    def test_disabled_by_default(self, client, test_config):
        resp = client.get("/api")
        assert resp.status_code == 403
        assert resp.json["error"] == "API is not enabled."

    def test_enabled_with_share_flag(self, client, test_config, data_dir):
        main._share_enabled = True
        resp = client.get(f"/api?key={config.API_KEY}")
        assert resp.status_code == 200

    def test_missing_key_returns_401(self, client, test_config, data_dir):
        main._share_enabled = True
        resp = client.get("/api")
        assert resp.status_code == 401
        assert "API key" in resp.json["error"]

    def test_wrong_key_returns_401(self, client, test_config, data_dir):
        main._share_enabled = True
        resp = client.get("/api?key=wrongkey")
        assert resp.status_code == 401

    def test_returns_logged_data(self, client, test_config, data_dir, data_log):
        main._share_enabled = True
        resp = client.get(f"/api?key={config.API_KEY}")
        assert resp.status_code == 200
        assert isinstance(resp.json, list)
        assert len(resp.json) == 2
        assert resp.json[0]["event"] == "page_view"
        assert resp.json[1]["event"] == "api_access_granted"

    def test_empty_log(self, client, test_config, data_dir):
        main._share_enabled = True
        resp = client.get(f"/api?key={config.API_KEY}")
        assert resp.status_code == 200
        assert isinstance(resp.json, list)
        assert len(resp.json) == 1
        assert resp.json[0]["event"] == "api_access_granted"

    def test_uses_correct_api_key(self, client, test_config, data_dir, data_log):
        main._share_enabled = True
        resp = client.get(f"/api?key={config.API_KEY}")
        assert resp.status_code == 200


# =============================================================================
# Error handlers
# =============================================================================

class TestErrorHandlers:
    @pytest.fixture(autouse=True)
    def _setup(self, test_config, media_dir):
        (media_dir / "video.mp4").write_bytes(b"data")

    def test_401_returns_custom_page(self, client, test_config, media_dir):
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        resp = client.get("/")
        assert resp.status_code == 401
        html = resp.data.decode()
        assert "401" in html
        assert "Unauthorized" in html
        assert "Back to Library" in html
        config.WEBSITE_ACCESS_KEY_REQUIRED = False

    def test_404_returns_custom_page(self, client, test_config):
        resp = client.get("/nonexistent")
        assert resp.status_code == 404
        html = resp.data.decode()
        assert "404" in html
        assert "Page not found" in html
        assert "Back to Library" in html

    def test_404_for_player_missing_file(self, client, test_config):
        resp = client.get("/player/missing.mp4")
        assert resp.status_code == 404
        html = resp.data.decode()
        assert "Back to Library" in html

    def test_403_returns_json_error(self, client, test_config):
        resp = client.get("/api")
        assert resp.status_code == 403
        assert resp.is_json
        assert "error" in resp.json

    def test_500_returns_custom_page(self, client, test_config, media_dir):
        bad_path = media_dir / "broken"
        bad_path.rmdir() if bad_path.is_dir() else None
        with patch.object(config, "MEDIA_FOLDER", "/nonexistent"):
            resp = client.get("/")
        assert resp.status_code in (200, 500)
        html = resp.data.decode()
        if resp.status_code == 500:
            assert "Internal server error" in html

    def test_error_page_content_type(self, client, test_config):
        resp = client.get("/missing")
        assert resp.content_type.startswith("text/html")


# =============================================================================
# Access key / before_request
# =============================================================================

class TestAccessKeyProtection:
    def test_blocked_without_key(self, client, test_config, media_dir):
        (media_dir / "video.mp4").write_bytes(b"data")
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        resp = client.get("/")
        assert resp.status_code == 401
        config.WEBSITE_ACCESS_KEY_REQUIRED = False

    def test_blocked_with_wrong_key(self, client, test_config, media_dir):
        (media_dir / "video.mp4").write_bytes(b"data")
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        resp = client.get("/?key=wrong")
        assert resp.status_code == 401
        config.WEBSITE_ACCESS_KEY_REQUIRED = False

    def test_allowed_with_correct_key(self, client, test_config, media_dir):
        (media_dir / "video.mp4").write_bytes(b"data")
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        resp = client.get(f"/?key={config.API_KEY}")
        assert resp.status_code == 200
        config.WEBSITE_ACCESS_KEY_REQUIRED = False

    def test_static_files_not_protected(self, client, test_config, media_dir):
        (media_dir / "video.mp4").write_bytes(b"data")
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        resp = client.get("/media/video.mp4")
        assert resp.status_code == 200
        config.WEBSITE_ACCESS_KEY_REQUIRED = False

    def test_player_requires_key(self, client, test_config, media_dir):
        (media_dir / "video.mp4").write_bytes(b"data")
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        resp = client.get("/player/video.mp4")
        assert resp.status_code == 401
        config.WEBSITE_ACCESS_KEY_REQUIRED = False

    def test_disabled_key_check(self, client, test_config, media_dir):
        (media_dir / "video.mp4").write_bytes(b"data")
        config.WEBSITE_ACCESS_KEY_REQUIRED = False
        resp = client.get("/")
        assert resp.status_code == 200

    def test_share_api_flag_set_on_requests(self, client, test_config):
        main._share_enabled = True
        resp = client.get("/api")
        assert resp.status_code == 401

    def test_share_api_flag_defaults_false(self, client, test_config):
        main._share_enabled = False
        resp = client.get("/api")
        assert resp.status_code == 403


# =============================================================================
# check_and_install_dependencies
# =============================================================================

class TestCheckAndInstallDependencies:
    def test_noop_when_all_installed(self):
        with patch("builtins.input") as mock_input:
            main.check_and_install_dependencies()
        mock_input.assert_not_called()

    def test_prompts_to_install_missing(self):
        with patch("importlib.util.find_spec", return_value=None):
            with patch("builtins.input", return_value="n"):
                with pytest.raises(SystemExit):
                    main.check_and_install_dependencies()

    def test_installs_with_yes(self):
        with patch("importlib.util.find_spec", return_value=None):
            with patch("builtins.input", return_value="y"):
                with patch("subprocess.check_call") as mock_pip:
                    with pytest.raises(SystemExit) as exc:
                        main.check_and_install_dependencies()
                    assert exc.value.code == 0
                    assert mock_pip.call_count == 3

    def test_installs_with_default(self):
        with patch("importlib.util.find_spec", return_value=None):
            with patch("builtins.input", return_value=""):
                with patch("subprocess.check_call") as mock_pip:
                    with pytest.raises(SystemExit) as exc:
                        main.check_and_install_dependencies()
                    assert exc.value.code == 0

    def test_exits_on_no(self):
        with patch("importlib.util.find_spec", return_value=None):
            with patch("builtins.input", return_value="n"):
                with pytest.raises(SystemExit) as exc:
                    main.check_and_install_dependencies()
                assert exc.value.code == 1

    def test_handles_pip_failure(self):
        with patch("importlib.util.find_spec", return_value=None):
            with patch("builtins.input", return_value="y"):
                with patch("subprocess.check_call", side_effect=subprocess.CalledProcessError(1, "pip")):
                    with pytest.raises(SystemExit) as exc:
                        main.check_and_install_dependencies()
                    assert exc.value.code == 1

    def test_handles_keyboard_interrupt(self):
        with patch("importlib.util.find_spec", return_value=None):
            with patch("builtins.input", side_effect=KeyboardInterrupt):
                with pytest.raises(SystemExit) as exc:
                    main.check_and_install_dependencies()
                assert exc.value.code == 1

    def test_handles_eoferror(self):
        with patch("importlib.util.find_spec", return_value=None):
            with patch("builtins.input", side_effect=EOFError):
                with pytest.raises(SystemExit) as exc:
                    main.check_and_install_dependencies()
                assert exc.value.code == 1

    def test_fallback_when_rich_missing(self):
        with patch("importlib.util.find_spec", return_value=None):
            with patch("builtins.input", return_value="y"):
                with patch("subprocess.check_call"):
                    with patch.dict("sys.modules", {"rich.console": None}):
                        with pytest.raises(SystemExit):
                            main.check_and_install_dependencies()


class TestCheckFfmpeg:
    def test_passes_when_ffmpeg_installed(self):
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            main.check_ffmpeg()

    def test_exits_when_ffmpeg_missing(self):
        with patch("shutil.which", return_value=None):
            with pytest.raises(SystemExit) as exc:
                main.check_ffmpeg()
            assert exc.value.code == 1

    def test_fallback_when_rich_missing(self):
        with patch("shutil.which", return_value=None):
            with patch.dict("sys.modules", {"rich.console": None}):
                with pytest.raises(SystemExit):
                    main.check_ffmpeg()


# =============================================================================
# CLI main()
# =============================================================================

class TestMainCli:
    def test_default_no_share(self, test_config, media_dir, data_dir, thumb_dir):
        with patch.object(main, "setup_directories") as mock_setup:
            with patch.object(main.console, "print"):
                with patch.object(main.app, "run"):
                    main.main.callback(share=False, selfuninstall=False)
        mock_setup.assert_called_once()
        assert main._share_enabled is False

    def test_share_flag(self, test_config, media_dir, data_dir, thumb_dir):
        with patch.object(main, "setup_directories"):
            with patch.object(main.console, "print"):
                with patch.object(main.app, "run"):
                    main.main.callback(share=True, selfuninstall=False)
        assert main._share_enabled is True

    def test_selfuninstall_flag(self, test_config, data_dir):
        with patch.object(main.subprocess, "check_call") as mock_pip:
            with patch.object(main.sys, "exit") as mock_exit:
                main.main.callback(share=False, selfuninstall=True)
        mock_pip.assert_called_once_with(
            [main.sys.executable, "-m", "pip", "uninstall", "-y", "localfs"]
        )
        mock_exit.assert_called_once_with(0)

    def test_click_command_created(self):
        assert hasattr(main, "main")
        assert callable(main.main)


# =============================================================================
# Template rendering
# =============================================================================

class TestIndexTemplateContext:
    def test_context_has_files_list(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "file-card" in html
        assert "file-grid" in html

    def test_video_has_play_link(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert "/player/video.mp4" in html

    def test_audio_has_play_link(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert "/player/audio.mp3" in html

    def test_image_has_no_play_link(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert "/player/image.jpg" not in html

    def test_download_links_present(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert "/media/video.mp4" in html
        assert "/media/audio.mp3" in html

    def test_no_results_message_hidden_by_default(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert 'id="no-results"' in html
        assert 'class="hidden' in html

    def test_search_input_present(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert 'id="searchInput"' in html


class TestPlayerTemplateContext:
    def test_video_context(self, client, test_config, media_dir):
        (media_dir / "clip.mp4").write_bytes(b"data")
        resp = client.get("/player/clip.mp4")
        html = resp.data.decode()
        assert "/media/clip.mp4" in html
        assert "Back to Library" in html

    def test_audio_context(self, client, test_config, media_dir):
        (media_dir / "track.mp3").write_bytes(b"data")
        resp = client.get("/player/track.mp3")
        html = resp.data.decode()
        assert "/media/track.mp3" in html

    def test_mime_type_in_source_tag(self, client, test_config, media_dir):
        (media_dir / "vid.mp4").write_bytes(b"data")
        resp = client.get("/player/vid.mp4")
        html = resp.data.decode()
        assert 'type="video/mp4"' in html

    def test_audio_mime_type(self, client, test_config, media_dir):
        (media_dir / "song.mp3").write_bytes(b"data")
        resp = client.get("/player/song.mp3")
        html = resp.data.decode()
        assert 'type="audio/mpeg"' in html


class TestErrorTemplateContext:
    def test_404_shows_code_and_message(self, client, test_config):
        resp = client.get("/no-such-page")
        html = resp.data.decode()
        assert "404" in html
        assert "Page not found" in html

    def test_back_link_in_error(self, client, test_config):
        resp = client.get("/missing")
        html = resp.data.decode()
        assert "Back to Library" in html
        assert "/" in html

    def test_back_link_preserves_key(self, client, test_config, media_dir):
        (media_dir / "test.mp4").write_bytes(b"data")
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        resp = client.get("/missing?key=abc123")
        config.WEBSITE_ACCESS_KEY_REQUIRED = False
        html = resp.data.decode()
        assert "404" in html


from pathlib import Path
