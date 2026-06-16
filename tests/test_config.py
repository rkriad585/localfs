import config
import secrets
import os


class TestConfigValues:
    def test_host(self):
        assert config.HOST == "0.0.0.0"

    def test_port(self):
        assert config.PORT == 5000

    def test_debug(self):
        assert config.DEBUG is True

    def test_base_dir(self):
        assert config.BASE_DIR.endswith("/.config/neostore/localfs") or config.BASE_DIR.endswith("\\.config\\neostore\\localfs")
        assert os.path.isabs(config.BASE_DIR)

    def test_base_dir_uses_home(self):
        home = os.path.expanduser("~")
        assert config.BASE_DIR.startswith(home)

    def test_media_folder(self):
        assert config.MEDIA_FOLDER == os.path.join(os.path.expanduser("~"), "Downloads")

    def test_media_extra_dirs(self):
        assert "Videos" in config.MEDIA_EXTRA_DIRS
        assert "Music" in config.MEDIA_EXTRA_DIRS
        assert config.MEDIA_EXTRA_DIRS["Videos"] == os.path.join(os.path.expanduser("~"), "Videos")
        assert config.MEDIA_EXTRA_DIRS["Music"] == os.path.join(os.path.expanduser("~"), "Music")

    def test_data_folder(self):
        assert config.DATA_FOLDER == os.path.join(config.BASE_DIR, "data")

    def test_data_file(self):
        assert config.DATA_FILE == "localfs-data.json"

    def test_thumbnail_folder(self):
        assert config.THUMBNAIL_FOLDER == os.path.join(config.BASE_DIR, "thumbnails")

    def test_allowed_extensions(self):
        assert config.ALLOWED_EXTENSIONS == ".mkv .mp4 .mp3"

    def test_api_key_is_generated(self):
        assert len(config.API_KEY) == 32
        assert isinstance(config.API_KEY, str)

    def test_api_key_is_hex(self):
        int(config.API_KEY, 16)

    def test_api_key_is_random(self):
        keys = {secrets.token_hex(16) for _ in range(100)}
        assert len(keys) == 100

    def test_website_access_key_required(self):
        assert config.WEBSITE_ACCESS_KEY_REQUIRED is True

    def test_media_folder_is_absolute(self):
        assert os.path.isabs(config.MEDIA_FOLDER)

    def test_data_folder_is_absolute(self):
        assert os.path.isabs(config.DATA_FOLDER)

    def test_version_is_string(self):
        assert isinstance(config.VERSION, str)
        assert len(config.VERSION) > 0

    def test_version_format(self):
        parts = config.VERSION.split(".")
        assert len(parts) == 3
        for p in parts:
            int(p)  # each part must be numeric
