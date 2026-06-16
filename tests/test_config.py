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

    def test_media_folder(self):
        assert config.MEDIA_FOLDER == "media"

    def test_data_folder(self):
        assert config.DATA_FOLDER == "data"

    def test_data_file(self):
        assert config.DATA_FILE == "localfs-data.json"

    def test_thumbnail_folder(self):
        assert config.THUMBNAIL_FOLDER == os.path.join("static", "thumbnails")

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

    def test_media_folder_is_relative(self):
        assert not os.path.isabs(config.MEDIA_FOLDER)

    def test_data_folder_is_relative(self):
        assert not os.path.isabs(config.DATA_FOLDER)
