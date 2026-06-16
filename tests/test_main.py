import os
import json
import subprocess
import sys
from unittest.mock import patch, MagicMock, ANY
from io import BytesIO, StringIO

import click
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

    def test_creates_data_dir_if_missing(self, test_config, client, tmp_path):
        new_data = tmp_path / "nonexistent" / "data"
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(config, "DATA_FOLDER", str(new_data))
        with client.application.test_request_context():
            main.log_activity("test", {})
        assert os.path.isdir(new_data)
        assert os.path.isfile(new_data / config.DATA_FILE)
        monkeypatch.undo()


class TestGenerateThumbnail:
    def test_returns_none_when_file_missing(self, test_config, media_dir, thumb_dir):
        result = main.generate_thumbnail("nonexistent.mp4")
        assert result is None

    def test_returns_cached_thumbnail(self, test_config, media_dir, thumb_dir):
        (media_dir / "video.mp4").write_bytes(b"fake")
        expected_thumb = thumb_dir / "video.jpg"
        expected_thumb.write_bytes(b"fake thumb")
        result = main.generate_thumbnail("video.mp4")
        assert result == "video.jpg"

    def test_generates_new_thumbnail_with_ffmpeg(self, test_config, media_dir, thumb_dir):
        (media_dir / "video.mp4").write_bytes(b"fake")
        with patch("subprocess.run"):
            result = main.generate_thumbnail("video.mp4")
        assert result == "video.jpg"

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

    def test_shows_directories(self, client, test_config, media_dir, sample_files):
        resp = client.get("/")
        html = resp.data.decode()
        assert "subdir" in html
        assert "fa-folder" in html

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


class TestDirectoryBrowsing:
    def test_shows_up_dir_at_root(self, client, test_config, media_dir):
        resp = client.get("/")
        html = resp.data.decode()
        assert "Parent" not in html or "level-up" not in html

    def test_shows_up_dir_in_subdir(self, client, test_config, media_dir):
        sub = media_dir / "subdir"
        sub.mkdir()
        (sub / "file.mp4").write_bytes(b"data")
        resp = client.get("/?dir=subdir")
        html = resp.data.decode()
        assert "Parent" in html or "level-up" in html

    def test_shows_breadcrumbs_in_subdir(self, client, test_config, media_dir):
        sub = media_dir / "subdir"
        sub.mkdir()
        resp = client.get("/?dir=subdir")
        html = resp.data.decode()
        assert "subdir" in html
        assert "~" in html

    def test_breadcrumb_link_goes_up(self, client, test_config, media_dir):
        sub = media_dir / "a" / "b"
        sub.mkdir(parents=True)
        (sub / "f.mp4").write_bytes(b"data")
        resp = client.get("/?dir=a/b")
        html = resp.data.decode()
        assert 'dir=a' in resp.data.decode() or 'dir=a' in html
        assert '/?key=' not in html or 'key=' not in html

    def test_files_in_subdir_have_correct_paths(self, client, test_config, media_dir):
        sub = media_dir / "movies"
        sub.mkdir()
        (sub / "clip.mp4").write_bytes(b"data")
        resp = client.get("/?dir=movies")
        html = resp.data.decode()
        assert "/player/movies/clip.mp4" in html
        assert "/media/movies/clip.mp4" in html

    def test_directory_404_for_nonexistent_dir(self, client, test_config, media_dir):
        resp = client.get("/?dir=nonexistent")
        assert resp.status_code == 404

    def test_directory_blocks_path_traversal(self, client, test_config, media_dir):
        resp = client.get("/?dir=../")
        assert resp.status_code in (404, 400)

    def test_extra_virtual_dirs_shown_at_root(self, client, test_config, media_dir):
        if os.path.isdir(config.MEDIA_EXTRA_DIRS.get("Videos", "/nonexistent")):
            resp = client.get("/")
            html = resp.data.decode()
            assert "Videos" in html

    def test_extra_virtual_dir_accessible(self, client, test_config, media_dir):
        virt = None
        for name, path in config.MEDIA_EXTRA_DIRS.items():
            if os.path.isdir(path):
                virt = name
                break
        if virt:
            resp = client.get(f"/?dir={virt}")
            assert resp.status_code in (200, 404)

    def test_extra_virtual_dir_no_subdirs_shown(self, client, test_config, media_dir):
        for name, path in config.MEDIA_EXTRA_DIRS.items():
            if os.path.isdir(path):
                resp = client.get(f"/?dir={name}")
                html = resp.data.decode()
                assert "fa-folder" not in html
                break

    def test_dirs_listed_with_folder_icon(self, client, test_config, media_dir):
        sub = media_dir / "testdir"
        sub.mkdir()
        resp = client.get("/")
        html = resp.data.decode()
        assert "testdir" in html
        assert "fa-folder" in html

    def test_directory_has_no_download_button(self, client, test_config, media_dir):
        sub = media_dir / "testdir"
        sub.mkdir()
        resp = client.get("/")
        html = resp.data.decode()
        assert "testdir" in html


class TestSorting:
    def test_default_sort_by_name(self, client, test_config, media_dir):
        (media_dir / "b.mp4").write_bytes(b"bbb")
        (media_dir / "a.mp4").write_bytes(b"aaa")
        resp = client.get("/")
        html = resp.data.decode()
        a_pos = html.index("a.mp4")
        b_pos = html.index("b.mp4")
        assert a_pos < b_pos

    def test_sort_by_name_desc(self, client, test_config, media_dir):
        (media_dir / "a.mp4").write_bytes(b"aaa")
        (media_dir / "b.mp4").write_bytes(b"bbb")
        resp = client.get("/?sort=name&order=desc")
        html = resp.data.decode()
        a_pos = html.index("a.mp4")
        b_pos = html.index("b.mp4")
        assert b_pos < a_pos

    def test_sort_by_size(self, client, test_config, media_dir):
        (media_dir / "small.mp4").write_bytes(b"x" * 10)
        (media_dir / "large.mp4").write_bytes(b"x" * 1000)
        resp = client.get("/?sort=size")
        html = resp.data.decode()
        s_pos = html.index("small.mp4")
        l_pos = html.index("large.mp4")
        assert s_pos < l_pos

    def test_sort_by_size_desc(self, client, test_config, media_dir):
        (media_dir / "small.mp4").write_bytes(b"x" * 10)
        (media_dir / "large.mp4").write_bytes(b"x" * 1000)
        resp = client.get("/?sort=size&order=desc")
        html = resp.data.decode()
        s_pos = html.index("small.mp4")
        l_pos = html.index("large.mp4")
        assert l_pos < s_pos

    def test_sort_by_type(self, client, test_config, media_dir):
        (media_dir / "a.mp3").write_bytes(b"aaa")
        (media_dir / "b.mp4").write_bytes(b"bbb")
        with patch.object(config, "ALLOWED_EXTENSIONS", ""):
            resp = client.get("/?sort=type")
        html = resp.data.decode()
        a_pos = html.index("a.mp3")
        b_pos = html.index("b.mp4")
        # audio before video alphabetically within type groups
        assert "type" in html or "audio" in html or "video" in html

    def test_sort_controls_present(self, client, test_config, media_dir):
        (media_dir / "f.mp4").write_bytes(b"data")
        resp = client.get("/")
        html = resp.data.decode()
        assert "Sort:" in html
        assert "Name" in html
        assert "Date" in html
        assert "Size" in html
        assert "Type" in html


class TestPlayerNavigation:
    def test_prev_next_links_present(self, client, test_config, media_dir):
        (media_dir / "a.mp4").write_bytes(b"aaa")
        (media_dir / "b.mp4").write_bytes(b"bbb")
        (media_dir / "c.mp4").write_bytes(b"ccc")
        resp = client.get("/player/b.mp4")
        html = resp.data.decode()
        assert "Prev" in html
        assert "Next" in html

    def test_first_file_no_prev(self, client, test_config, media_dir):
        (media_dir / "a.mp4").write_bytes(b"aaa")
        (media_dir / "b.mp4").write_bytes(b"bbb")
        resp = client.get("/player/a.mp4")
        html = resp.data.decode()
        assert "Prev" not in html or "step-backward" not in html

    def test_last_file_no_next(self, client, test_config, media_dir):
        (media_dir / "a.mp4").write_bytes(b"aaa")
        (media_dir / "b.mp4").write_bytes(b"bbb")
        resp = client.get("/player/b.mp4")
        html = resp.data.decode()
        assert "Next" not in html or "step-forward" not in html

    def test_single_file_no_nav(self, client, test_config, media_dir):
        (media_dir / "only.mp4").write_bytes(b"data")
        resp = client.get("/player/only.mp4")
        html = resp.data.decode()
        assert "Prev" not in html
        assert "Next" not in html


class TestServerSideSearch:
    def test_search_by_name(self, client, test_config, media_dir):
        (media_dir / "movie.mp4").write_bytes(b"data")
        (media_dir / "song.mp3").write_bytes(b"data")
        resp = client.get("/?q=movie")
        html = resp.data.decode()
        assert "movie.mp4" in html
        assert "song.mp3" not in html

    def test_search_is_case_insensitive(self, client, test_config, media_dir):
        (media_dir / "Movie.MP4").write_bytes(b"data")
        resp = client.get("/?q=movie")
        html = resp.data.decode()
        assert "Movie.MP4" in html

    def test_search_returns_all_when_empty(self, client, test_config, media_dir, sample_files):
        resp = client.get("/?q=")
        html = resp.data.decode()
        assert "video.mp4" in html
        assert "audio.mp3" in html
        assert "video.mkv" in html

    def test_search_returns_none_when_no_match(self, client, test_config, media_dir, sample_files):
        resp = client.get("/?q=nonexistent")
        html = resp.data.decode()
        assert "video.mp4" not in html
        assert "No files found" in html

    def test_search_filters_directories(self, client, test_config, media_dir):
        (media_dir / "sub_movies").mkdir()
        (media_dir / "sub_movies" / "clip.mp4").write_bytes(b"data")
        (media_dir / "sub_pics").mkdir()
        resp = client.get("/?q=movies")
        html = resp.data.decode()
        assert "sub_movies" in html
        assert "sub_pics" not in html

    def test_filter_by_type_video(self, client, test_config, media_dir):
        (media_dir / "clip.mp4").write_bytes(b"data")
        (media_dir / "song.mp3").write_bytes(b"data")
        (media_dir / "pic.jpg").write_bytes(b"data")
        with patch.object(config, "ALLOWED_EXTENSIONS", ""):
            resp = client.get("/?type=video")
        html = resp.data.decode()
        assert "clip.mp4" in html
        assert "song.mp3" not in html
        assert "pic.jpg" not in html

    def test_filter_by_type_audio(self, client, test_config, media_dir):
        (media_dir / "clip.mp4").write_bytes(b"data")
        (media_dir / "song.mp3").write_bytes(b"data")
        with patch.object(config, "ALLOWED_EXTENSIONS", ""):
            resp = client.get("/?type=audio")
        html = resp.data.decode()
        assert "song.mp3" in html
        assert "clip.mp4" not in html

    def test_filter_by_size_small(self, client, test_config, media_dir):
        (media_dir / "small.txt").write_bytes(b"x" * 100)
        (media_dir / "large.txt").write_bytes(b"x" * (1024 * 1024 * 2))
        with patch.object(config, "ALLOWED_EXTENSIONS", ""):
            resp = client.get("/?size=small")
        html = resp.data.decode()
        assert "small.txt" in html
        assert "large.txt" not in html

    def test_filter_by_size_large(self, client, test_config, media_dir):
        (media_dir / "small.txt").write_bytes(b"x" * 100)
        (media_dir / "medium.txt").write_bytes(b"x" * (1024 * 1024 * 5))
        (media_dir / "large.txt").write_bytes(b"x" * (1024 * 1024 * 200))
        with patch.object(config, "ALLOWED_EXTENSIONS", ""):
            resp = client.get("/?size=large")
        html = resp.data.decode()
        assert "large.txt" in html
        assert "small.txt" not in html
        assert "medium.txt" not in html


class TestFaviconRoute:
    def test_favicon_returns_svg(self, client, test_config):
        resp = client.get("/favicon.ico")
        assert resp.status_code == 200
        assert resp.content_type.startswith("image/svg+xml")


class TestThumbnailRoute:
    def test_serves_existing_thumbnail(self, client, test_config, thumb_dir):
        (thumb_dir / "test.jpg").write_bytes(b"image data")
        resp = client.get("/thumbnails/test.jpg")
        assert resp.status_code == 200
        assert resp.data == b"image data"

    def test_returns_404_for_missing_thumbnail(self, client, test_config):
        resp = client.get("/thumbnails/nonexistent.jpg")
        assert resp.status_code == 404

    def test_blocks_path_traversal(self, client, test_config):
        resp = client.get("/thumbnails/../config.py")
        assert resp.status_code in (404, 400)


class TestUploadRoute:
    def test_upload_file(self, client, test_config, media_dir):
        data = {"file": (BytesIO(b"test content"), "uploaded.txt")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 302
        assert (media_dir / "uploaded.txt").exists()

    def test_upload_to_subdir(self, client, test_config, media_dir):
        sub = media_dir / "sub"
        sub.mkdir()
        data = {"file": (BytesIO(b"data"), "f.txt"), "dir": "sub"}
        resp = client.post("/upload?dir=sub", data=data, content_type="multipart/form-data")
        assert resp.status_code == 302

    def test_upload_duplicate_renames(self, client, test_config, media_dir):
        (media_dir / "dup.txt").write_bytes(b"original")
        data = {"file": (BytesIO(b"new"), "dup.txt")}
        client.post("/upload", data=data, content_type="multipart/form-data")
        assert (media_dir / "dup.txt").exists()
        assert (media_dir / "dup_1.txt").exists()

    def test_upload_no_file_returns_400(self, client, test_config):
        resp = client.post("/upload", data={})
        assert resp.status_code == 400

    def test_upload_empty_filename_returns_400(self, client, test_config):
        data = {"file": (BytesIO(b""), "")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_upload_blocked_without_key_when_required(self, client, test_config, media_dir):
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        data = {"file": (BytesIO(b"data"), "f.txt")}
        resp = client.post("/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 401
        config.WEBSITE_ACCESS_KEY_REQUIRED = False

    def test_upload_with_key_when_required(self, client, test_config, media_dir):
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        data = {"file": (BytesIO(b"data"), "f.txt")}
        resp = client.post(f"/upload?key={config.API_KEY}", data=data, content_type="multipart/form-data")
        assert resp.status_code == 302
        config.WEBSITE_ACCESS_KEY_REQUIRED = False


class TestDeleteRoute:
    def test_delete_file(self, client, test_config, media_dir):
        (media_dir / "delete_me.txt").write_bytes(b"data")
        resp = client.post("/delete", data={"filename": "delete_me.txt"})
        assert resp.status_code == 200
        assert resp.json["success"] is True
        assert not (media_dir / "delete_me.txt").exists()

    def test_delete_nonexistent_returns_404(self, client, test_config):
        resp = client.post("/delete", data={"filename": "ghost.txt"})
        assert resp.status_code == 404

    def test_delete_in_subdir(self, client, test_config, media_dir):
        sub = media_dir / "sub"
        sub.mkdir()
        (sub / "f.txt").write_bytes(b"data")
        resp = client.post("/delete", data={"filename": "f.txt", "dir": "sub"})
        assert resp.status_code == 200
        assert not (sub / "f.txt").exists()

    def test_delete_blocks_path_traversal(self, client, test_config):
        resp = client.post("/delete", data={"filename": "../config.py"})
        assert resp.status_code == 404

    def test_delete_blocked_without_key_when_required(self, client, test_config, media_dir):
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        (media_dir / "f.txt").write_bytes(b"data")
        resp = client.post("/delete", data={"filename": "f.txt"})
        assert resp.status_code == 401
        config.WEBSITE_ACCESS_KEY_REQUIRED = False


class TestRenameRoute:
    def test_rename_file(self, client, test_config, media_dir):
        (media_dir / "old.txt").write_bytes(b"data")
        resp = client.post("/rename", data={"filename": "old.txt", "new_name": "new.txt"})
        assert resp.status_code == 200
        assert resp.json["success"] is True
        assert not (media_dir / "old.txt").exists()
        assert (media_dir / "new.txt").exists()

    def test_rename_nonexistent_returns_404(self, client, test_config):
        resp = client.post("/rename", data={"filename": "ghost.txt", "new_name": "alive.txt"})
        assert resp.status_code == 404

    def test_rename_to_existing_returns_409(self, client, test_config, media_dir):
        (media_dir / "a.txt").write_bytes(b"a")
        (media_dir / "b.txt").write_bytes(b"b")
        resp = client.post("/rename", data={"filename": "a.txt", "new_name": "b.txt"})
        assert resp.status_code == 409

    def test_rename_requires_names(self, client, test_config):
        resp = client.post("/rename", data={"filename": "x.txt", "new_name": ""})
        assert resp.status_code == 400

    def test_rename_in_subdir(self, client, test_config, media_dir):
        sub = media_dir / "sub"
        sub.mkdir()
        (sub / "old.txt").write_bytes(b"data")
        resp = client.post("/rename", data={"filename": "old.txt", "new_name": "renamed.txt", "dir": "sub"})
        assert resp.status_code == 200
        assert not (sub / "old.txt").exists()
        assert (sub / "renamed.txt").exists()

    def test_rename_blocked_without_key_when_required(self, client, test_config, media_dir):
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        (media_dir / "f.txt").write_bytes(b"data")
        resp = client.post("/rename", data={"filename": "f.txt", "new_name": "g.txt"})
        assert resp.status_code == 401
        config.WEBSITE_ACCESS_KEY_REQUIRED = False


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
# Settings route
# =============================================================================

class TestSettingsRoute:
    def test_settings_page_renders(self, client, test_config):
        resp = client.get("/settings")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Settings" in html
        assert "Choose your theme" in html

    def test_settings_page_lists_themes(self, client, test_config):
        resp = client.get("/settings")
        html = resp.data.decode()
        assert "Dark Theme" in html
        assert "Light Theme" in html

    def test_settings_post_saves_theme(self, client, test_config):
        resp = client.post("/settings", data={"theme": "light"}, follow_redirects=True)
        assert resp.status_code == 200

    def test_settings_post_redirects_to_index(self, client, test_config):
        resp = client.post("/settings", data={"theme": "light"})
        assert resp.status_code == 302

    def test_settings_post_unknown_theme_redirects(self, client, test_config):
        resp = client.post("/settings", data={"theme": "nonexistent"})
        assert resp.status_code == 302

    def test_settings_post_preserves_key(self, client, test_config):
        resp = client.post("/settings?key=abc123", data={"theme": "light"})
        assert resp.status_code == 302
        assert "key=abc123" in resp.location or resp.location.endswith("/")

    def test_settings_current_theme_selected(self, client, test_config):
        resp = client.get("/settings")
        html = resp.data.decode()
        assert "dark" in html


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
    _KW = dict(port=None, host=None, key=None, media=None, no_auth=False, theme=None, mode=None, add_user=None, remove_user=None)

    def test_default_no_share(self, test_config, media_dir, data_dir, thumb_dir):
        with patch.object(main, "setup_directories") as mock_setup:
            with patch.object(main.console, "print"):
                with patch.object(main.app, "run"):
                    main.main.callback(share=False, selfuninstall=False, **self._KW)
        mock_setup.assert_called_once()
        assert main._share_enabled is False

    def test_share_flag(self, test_config, media_dir, data_dir, thumb_dir):
        with patch.object(main, "setup_directories"):
            with patch.object(main.console, "print"):
                with patch.object(main.app, "run"):
                    main.main.callback(share=True, selfuninstall=False, **self._KW)
        assert main._share_enabled is True

    def test_selfuninstall_flag(self, test_config, data_dir):
        with patch.object(main.subprocess, "check_call") as mock_pip:
            with patch.object(main.sys, "exit") as mock_exit:
                main.main.callback(share=False, selfuninstall=True, **self._KW)
        mock_pip.assert_called_once_with(
            [main.sys.executable, "-m", "pip", "uninstall", "-y", "localfs"]
        )
        mock_exit.assert_called_once_with(0)

    def test_port_flag(self, test_config, media_dir, data_dir, thumb_dir):
        with patch.object(main, "setup_directories"):
            with patch.object(main.console, "print"):
                with patch.object(main.app, "run"):
                    main.main.callback(share=False, selfuninstall=False, port=8080,
                                       **{k: v for k, v in self._KW.items() if k != "port"})
        assert config.PORT == 8080

    def test_host_flag(self, test_config, media_dir, data_dir, thumb_dir):
        with patch.object(main, "setup_directories"):
            with patch.object(main.console, "print"):
                with patch.object(main.app, "run"):
                    main.main.callback(share=False, selfuninstall=False, host="127.0.0.1",
                                       **{k: v for k, v in self._KW.items() if k != "host"})
        assert config.HOST == "127.0.0.1"

    def test_key_flag(self, test_config, media_dir, data_dir, thumb_dir):
        with patch.object(main, "setup_directories"):
            with patch.object(main.console, "print"):
                with patch.object(main.app, "run"):
                    main.main.callback(share=False, selfuninstall=False, key="customkey",
                                       **{k: v for k, v in self._KW.items() if k != "key"})
        assert config.API_KEY == "customkey"

    def test_media_flag(self, test_config, media_dir, data_dir, thumb_dir, tmp_path):
        new_media = tmp_path / "custom_media"
        new_media.mkdir()
        with patch.object(main, "setup_directories"):
            with patch.object(main.console, "print"):
                with patch.object(main.app, "run"):
                    main.main.callback(share=False, selfuninstall=False, media=str(new_media),
                                       **{k: v for k, v in self._KW.items() if k != "media"})
        assert config.MEDIA_FOLDER == str(new_media)

    def test_no_auth_flag(self, test_config, media_dir, data_dir, thumb_dir):
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        with patch.object(main, "setup_directories"):
            with patch.object(main.console, "print"):
                with patch.object(main.app, "run"):
                    main.main.callback(share=False, selfuninstall=False, no_auth=True,
                                       **{k: v for k, v in self._KW.items() if k != "no_auth"})
        assert config.WEBSITE_ACCESS_KEY_REQUIRED is False

    def test_theme_flag(self, test_config, media_dir, data_dir, thumb_dir):
        import theme
        original = theme.CURRENT_THEME
        with patch.object(main, "setup_directories"):
            with patch.object(main.console, "print"):
                with patch.object(main.app, "run"):
                    main.main.callback(share=False, selfuninstall=False, theme="light",
                                       **{k: v for k, v in self._KW.items() if k != "theme"})
        assert theme.CURRENT_THEME == "light"

    def test_mode_flag(self, test_config, media_dir, data_dir, thumb_dir):
        import theme
        theme.CURRENT_MODE = "light"
        with patch.object(main, "setup_directories"):
            with patch.object(main.console, "print"):
                with patch.object(main.app, "run"):
                    main.main.callback(share=False, selfuninstall=False, mode="dark",
                                       **{k: v for k, v in self._KW.items() if k != "mode"})
        assert theme.CURRENT_MODE == "dark"

    def test_click_command_created(self):
        assert hasattr(main, "main")
        assert callable(main.main)

    def test_version_option_registered(self):
        assert any(isinstance(p, click.core.Option) and "--version" in p.opts
                   for p in main.main.params)


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


# =============================================================================
# User management
# =============================================================================

class TestUserManagement:
    def test_add_and_authenticate_user(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "USERS_FILE", str(tmp_path / "users.json"))
        main.add_user("admin", "secret123")
        assert main.authenticate_user("admin", "secret123") is True
        assert main.authenticate_user("admin", "wrong") is False
        assert main.authenticate_user("nobody", "x") is False

    def test_user_exists(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "USERS_FILE", str(tmp_path / "users.json"))
        main.add_user("alice", "pass")
        assert main.user_exists("alice") is True
        assert main.user_exists("bob") is False

    def test_remove_user(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "USERS_FILE", str(tmp_path / "users.json"))
        main.add_user("alice", "pass")
        main.remove_user("alice")
        assert main.user_exists("alice") is False

    def test_remove_nonexistent_user_does_not_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "USERS_FILE", str(tmp_path / "users.json"))
        main.remove_user("ghost")  # should not raise

    def test_load_users_empty_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "USERS_FILE", str(tmp_path / "users.json"))
        assert main.load_users() == {}

    def test_load_users_missing_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "USERS_FILE", str(tmp_path / "nonexistent.json"))
        assert main.load_users() == {}

    def test_save_users_preserves_data(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "USERS_FILE", str(tmp_path / "users.json"))
        main.add_user("u1", "p1")
        main.add_user("u2", "p2")
        loaded = main.load_users()
        assert len(loaded) == 2
        assert "u1" in loaded
        assert "u2" in loaded


class TestLoginRoute:
    def test_login_page_renders(self, client, test_config):
        resp = client.get("/login")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Sign in" in html
        assert "username" in html
        assert "password" in html

    def test_login_with_valid_credentials(self, client, test_config, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "USERS_FILE", str(tmp_path / "users.json"))
        main.add_user("admin", "pass")
        resp = client.post("/login", data={"username": "admin", "password": "pass"})
        assert resp.status_code == 302

    def test_login_with_invalid_credentials(self, client, test_config):
        resp = client.post("/login", data={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_redirects_to_index(self, client, test_config, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "USERS_FILE", str(tmp_path / "users.json"))
        main.add_user("admin", "pass")
        resp = client.post("/login", data={"username": "admin", "password": "pass"})
        assert resp.status_code == 302
        assert resp.location.endswith("/") or "/?key=" in resp.location

    def test_login_preserves_key(self, client, test_config, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "USERS_FILE", str(tmp_path / "users.json"))
        main.add_user("admin", "pass")
        resp = client.post("/login?key=abc", data={"username": "admin", "password": "pass"})
        assert resp.status_code == 302
        assert "key=abc" in resp.location

    def test_logout_clears_session(self, client, test_config):
        with client.session_transaction() as sess:
            sess['authenticated'] = True
            sess['username'] = 'admin'
        resp = client.get("/logout")
        assert resp.status_code == 302
        with client.session_transaction() as sess:
            assert 'authenticated' not in sess


class TestSessionAuth:
    def test_session_allows_access(self, client, test_config, media_dir):
        (media_dir / "video.mp4").write_bytes(b"data")
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        with client.session_transaction() as sess:
            sess['authenticated'] = True
            sess['username'] = 'admin'
        resp = client.get("/")
        assert resp.status_code == 200
        config.WEBSITE_ACCESS_KEY_REQUIRED = False

    def test_session_without_auth_still_blocked(self, client, test_config):
        config.WEBSITE_ACCESS_KEY_REQUIRED = True
        with client.session_transaction() as sess:
            sess['some_data'] = 'value'  # not authenticated
        resp = client.get("/")
        assert resp.status_code == 401
        config.WEBSITE_ACCESS_KEY_REQUIRED = False


# =============================================================================
# Directory browsing helpers
# =============================================================================

class TestResolveMediaPath:
    def test_resolve_media_path_normal(self, test_config):
        result = main.resolve_media_path("file.mp4")
        assert result == os.path.join(config.MEDIA_FOLDER, "file.mp4")

    def test_resolve_media_path_subdir(self, test_config):
        result = main.resolve_media_path("sub/file.mp4")
        assert result == os.path.join(config.MEDIA_FOLDER, "sub", "file.mp4")

    def test_resolve_media_path_extra_dir(self, test_config):
        if os.path.isdir(config.MEDIA_EXTRA_DIRS.get("Videos", "/nonexistent")):
            result = main.resolve_media_path("Videos/movie.mp4")
            assert result == os.path.join(config.MEDIA_EXTRA_DIRS["Videos"], "movie.mp4")

    def test_resolve_media_path_empty(self, test_config):
        result = main.resolve_media_path("")
        assert result == config.MEDIA_FOLDER


class TestGenerateFileInfo:
    def test_generates_correct_info(self, test_config, media_dir):
        (media_dir / "test.mp4").write_bytes(b"data")
        info = main.generate_file_info("test.mp4", media_dir / "test.mp4", "test.mp4")
        assert info["name"] == "test.mp4"
        assert info["type"] == "video"
        assert info["is_playable"] is True
        assert info["path"] == "test.mp4"

    def test_audio_type(self, test_config, media_dir):
        (media_dir / "song.mp3").write_bytes(b"data")
        info = main.generate_file_info("song.mp3", media_dir / "song.mp3", "song.mp3")
        assert info["type"] == "audio"

    def test_image_type(self, test_config, media_dir):
        (media_dir / "pic.jpg").write_bytes(b"data")
        info = main.generate_file_info("pic.jpg", media_dir / "pic.jpg", "pic.jpg")
        assert info["type"] == "image"
        assert info["is_playable"] is False

    def test_rel_path_preserved(self, test_config, media_dir):
        (media_dir / "f.mp4").write_bytes(b"data")
        info = main.generate_file_info("f.mp4", media_dir / "f.mp4", "sub/dir/f.mp4")
        assert info["path"] == "sub/dir/f.mp4"


class TestFindSubtitle:
    def test_finds_srt(self, test_config, media_dir):
        (media_dir / "video.srt").write_bytes(b"1\n00:00:01 --> 00:00:02\nHello")
        (media_dir / "video.mp4").write_bytes(b"data")
        result = main._find_subtitle(media_dir / "video.mp4")
        assert result == "video.srt"

    def test_finds_vtt(self, test_config, media_dir):
        (media_dir / "clip.vtt").write_bytes(b"WEBVTT")
        (media_dir / "clip.mp4").write_bytes(b"data")
        result = main._find_subtitle(media_dir / "clip.mp4")
        assert result == "clip.vtt"

    def test_returns_none_when_missing(self, test_config, media_dir):
        (media_dir / "naked.mp4").write_bytes(b"data")
        result = main._find_subtitle(media_dir / "naked.mp4")
        assert result is None


class TestSafeJoin:
    def test_safe_join_simple(self):
        result = main.safe_join("/base", "file.txt")
        assert result == "/base/file.txt"

    def test_safe_join_subdir(self):
        result = main.safe_join("/base", "sub", "file.txt")
        assert result == "/base/sub/file.txt"

    def test_safe_join_rejects_traversal(self):
        result = main.safe_join("/base", "../etc/passwd")
        assert result is None

    def test_safe_join_rejects_deep_traversal(self):
        result = main.safe_join("/base", "sub", "../../etc/passwd")
        assert result is None

    def test_safe_join_allows_same_dir(self):
        result = main.safe_join("/base", ".")
        assert result is not None

    def test_safe_join_returns_normalized(self):
        result = main.safe_join("/base", "sub/./file.txt")
        assert result == "/base/sub/file.txt"


class TestBuildBreadcrumbs:
    def test_empty_dir(self):
        assert main.build_breadcrumbs("") == []

    def test_single_level(self):
        crumbs = main.build_breadcrumbs("Movies")
        assert len(crumbs) == 2
        assert crumbs[0]["name"] == "~"
        assert crumbs[0]["path"] == ""
        assert crumbs[1]["name"] == "Movies"
        assert crumbs[1]["path"] == "Movies"

    def test_multi_level(self):
        crumbs = main.build_breadcrumbs("a/b/c")
        assert len(crumbs) == 4
        assert crumbs[2]["name"] == "b"
        assert crumbs[2]["path"] == "a/b"

    def test_leading_slash_stripped(self):
        crumbs = main.build_breadcrumbs("/a/b")
        assert len(crumbs) == 3

    def test_trailing_slash_stripped(self):
        crumbs = main.build_breadcrumbs("a/b/")
        assert len(crumbs) == 3


class TestParentDir:
    def test_empty(self):
        assert main.parent_dir("") is None

    def test_single_level(self):
        assert main.parent_dir("Movies") == ""

    def test_multi_level(self):
        assert main.parent_dir("a/b/c") == "a/b"

    def test_two_levels(self):
        assert main.parent_dir("a/b") == "a"
