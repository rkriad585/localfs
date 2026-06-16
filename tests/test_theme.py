import os
import json
from collections import OrderedDict

import theme


class TestThemeData:
    def test_all_themes_present(self):
        assert len(theme.THEMES) == 16

    def test_dark_theme_is_default(self):
        assert "dark" in theme.THEMES

    def test_each_theme_has_required_keys(self):
        for slug, data in theme.THEMES.items():
            assert "name" in data, f"{slug} missing name"
            assert "mode" in data, f"{slug} missing mode"
            assert "colors" in data, f"{slug} missing colors"
            assert "css" in data, f"{slug} missing css"

    def test_each_theme_has_valid_mode(self):
        for slug, data in theme.THEMES.items():
            assert data["mode"] in ("dark", "light"), f"{slug} mode must be dark or light"

    def test_each_theme_has_css_vars(self):
        required_vars = {"bg-primary", "bg-secondary", "bg-card", "border", "text-muted", "text-primary"}
        for slug, data in theme.THEMES.items():
            css_keys = set(data["css"].keys())
            assert required_vars.issubset(css_keys), f"{slug} missing CSS vars: {required_vars - css_keys}"

    def test_each_theme_has_at_least_one_color(self):
        for slug, data in theme.THEMES.items():
            assert len(data["colors"]) >= 1, f"{slug} has no colors"

    def test_themes_is_ordered_dict(self):
        assert isinstance(theme.THEMES, OrderedDict)

    def test_theme_names_are_displayable(self):
        for slug, data in theme.THEMES.items():
            name = data["name"]
            assert len(name) > 0
            assert name[0].isupper() or name[0].isdigit()


class TestThemeLoading:
    def test_load_config_defaults_to_dark(self, tmp_path, monkeypatch):
        monkeypatch.setattr(theme, "CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(theme, "CONFIG_FILE", str(tmp_path / "config.toml"))
        theme.CURRENT_THEME = "dark"
        theme.CURRENT_MODE = "dark"
        theme.load_config()
        assert theme.CURRENT_THEME == "dark"

    def test_save_and_load_persists_theme(self, tmp_path, monkeypatch):
        monkeypatch.setattr(theme, "CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(theme, "CONFIG_FILE", str(tmp_path / "config.toml"))
        theme.save_config("light")
        assert theme.CURRENT_THEME == "light"

    def test_save_creates_config_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(theme, "CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(theme, "CONFIG_FILE", str(tmp_path / "config.toml"))
        theme.save_config("dark-rad")
        assert os.path.exists(tmp_path / "config.toml")

    def test_save_writes_valid_content(self, tmp_path, monkeypatch):
        monkeypatch.setattr(theme, "CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(theme, "CONFIG_FILE", str(tmp_path / "config.toml"))
        theme.save_config("dark-green")
        content = (tmp_path / "config.toml").read_text()
        assert "[theme]" in content
        assert 'name = "dark-green"' in content
        assert 'mode = "dark"' in content

    def test_load_invalid_file_falls_back_to_dark(self, tmp_path, monkeypatch):
        monkeypatch.setattr(theme, "CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(theme, "CONFIG_FILE", str(tmp_path / "config.toml"))
        (tmp_path / "config.toml").write_text("invalid toml [[[")
        theme.CURRENT_THEME = "dark"
        theme.CURRENT_MODE = "dark"
        theme.load_config()
        assert theme.CURRENT_THEME == "dark"

    def test_load_nonexistent_file_keeps_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr(theme, "CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(theme, "CONFIG_FILE", str(tmp_path / "nonexistent.toml"))
        theme.CURRENT_THEME = "dark"
        theme.CURRENT_MODE = "dark"
        theme.load_config()
        assert theme.CURRENT_THEME == "dark"

    def test_save_unknown_theme_still_writes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(theme, "CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(theme, "CONFIG_FILE", str(tmp_path / "config.toml"))
        theme.save_config("nonexistent")
        content = (tmp_path / "config.toml").read_text()
        assert 'name = "nonexistent"' in content

    def test_save_with_custom_mode(self, tmp_path, monkeypatch):
        monkeypatch.setattr(theme, "CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(theme, "CONFIG_FILE", str(tmp_path / "config.toml"))
        theme.save_config("dark", mode="light")
        assert theme.CURRENT_MODE == "light"


class TestGetThemeVars:
    def test_get_theme_vars_returns_css(self):
        vars = theme.get_theme_vars("dark")
        assert "#0f172a" in str(vars)
        assert "#e2e8f0" in str(vars)

    def test_get_theme_vars_unknown_falls_back(self):
        vars = theme.get_theme_vars("nonexistent")
        assert vars["bg-primary"] == "#0f172a"

    def test_get_theme_vars_current_theme(self):
        theme.CURRENT_THEME = "light"
        vars = theme.get_theme_vars()
        assert vars["bg-primary"] == "#ffffff"
        theme.CURRENT_THEME = "dark"

    def test_all_themes_have_all_vars(self):
        required = {"bg-primary", "bg-secondary", "bg-card", "border", "text-muted", "text-primary"}
        for slug in theme.THEMES:
            vars = theme.get_theme_vars(slug)
            for key in required:
                assert key in vars, f"{slug} missing {key}"
                assert vars[key].startswith("#") or vars[key].startswith("rgba"), \
                    f"{slug}.{key} is not a color: {vars[key]}"


class TestEnsureConfigDir:
    def test_creates_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr(theme, "CONFIG_DIR", str(tmp_path / "new" / "nested" / "dir"))
        theme.ensure_config_dir()
        assert os.path.isdir(tmp_path / "new" / "nested" / "dir")

    def test_existing_directory_does_not_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(theme, "CONFIG_DIR", str(tmp_path))
        os.makedirs(tmp_path, exist_ok=True)
        theme.ensure_config_dir()


class TestGetAllThemes:
    def test_returns_all_themes(self):
        all_themes = theme.get_all_themes()
        assert len(all_themes) == 16
        assert "dark" in all_themes
        assert "light" in all_themes
