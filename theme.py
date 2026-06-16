import os
import tomllib
import config
from collections import OrderedDict

CONFIG_DIR = config.BASE_DIR
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.toml")
CURRENT_THEME = "dark"
CURRENT_MODE = "dark"

THEMES = OrderedDict()

_NAMES = {
    "dark": "Dark Theme",
    "light": "Light Theme",
    "dark-rad": "Dark & Rad",
    "light-rad": "Light & Rad",
    "dark-green": "Dark & Green",
    "sunny-beach-day": "Sunny Beach Day",
    "olive-garden-feast": "Olive Garden Feast",
    "summer-ocean-breeze": "Summer Ocean Breeze",
    "refreshing-summer-fun": "Refreshing Summer Fun",
    "black-gold-elegance": "Black & Gold Elegance",
    "vibrant-color-fiesta": "Vibrant Color Fiesta",
    "light-steel": "Light Steel",
    "golden-twilight": "Golden Twilight",
    "deep-sea": "Deep Sea",
    "bright-green": "Bright Green",
    "vivid-nightfall": "Vivid Nightfall",
}


def _t(name, mode, colors, **overrides):
    css = {
        "bg-primary": colors[0],
        "bg-secondary": colors[1],
        "bg-card": colors[2],
        "border": colors[3] if len(colors) > 3 else "#334155",
        "text-muted": colors[4] if len(colors) > 4 else "#64748b",
        "text-primary": colors[5] if len(colors) > 5 else "#e2e8f0",
    }
    css.update(overrides)
    display = _NAMES.get(name, name.replace("-", " ").title())
    THEMES[name] = {"name": display, "mode": mode, "colors": colors, "css": css}

_t("dark", "dark", ["#0f172a", "#111827", "#1e293b", "#334155", "#64748b", "#e2e8f0"],
  accent="#3b82f6", accent_hover="#2563eb", input_bg="#1e293b", shadow="rgba(0,0,0,0.3)")

_t("light", "light", ["#ffffff", "#f8fafc", "#e2e8f0", "#cbd5e1", "#475569", "#0f172a"],
  accent="#3b82f6", accent_hover="#2563eb", input_bg="#ffffff", shadow="rgba(0,0,0,0.1)")

_t("dark-rad", "dark", ["#000000", "#0a0a0a", "#1a1a1a", "#ff0000", "#cc0000", "#ffffff", "#8e8e93"],
  bg_primary="#000000", bg_secondary="#0a0a0a", bg_card="#1a1a1a", border="#333333",
  text_muted="#8e8e93", text_primary="#ffffff",
  accent="#ff0000", accent_hover="#cc0000", input_bg="#1a1a1a", shadow="rgba(0,0,0,0.5)")

_t("light-rad", "light", ["#ffffff", "#ffffff", "#eed937", "#ff0000", "#cc0000", "#000000", "#6c6000"],
  bg_primary="#ffffff", bg_secondary="#ffffff", bg_card="#eed937", border="#cccccc",
  text_muted="#6c6000", text_primary="#000000",
  accent="#ff0000", accent_hover="#cc0000", input_bg="#ffffff", shadow="rgba(0,0,0,0.1)")

_t("dark-green", "dark", ["#000000", "#0a0a0a", "#1a1a1a", "#0dff00", "#22cc00", "#ffffff", "#a09829"],
  bg_primary="#000000", bg_secondary="#0a0a0a", bg_card="#1a1a1a", border="#333333",
  text_muted="#a09829", text_primary="#ffffff",
  accent="#0dff00", accent_hover="#22cc00", input_bg="#1a1a1a", shadow="rgba(0,0,0,0.5)")

_t("sunny-beach-day", "light", ["#264653", "#2a9d8f", "#e9c46a", "#f4a261", "#e76f51"],
  bg_primary="#264653", bg_secondary="#2a9d8f", bg_card="#e9c46a", border="#f4a261",
  text_muted="#2a9d8f", text_primary="#264653",
  accent="#e76f51", accent_hover="#d45a40", input_bg="#e9c46a", shadow="rgba(0,0,0,0.15)")

_t("olive-garden-feast", "light", ["#606c38", "#283618", "#fefae0", "#dda15e", "#bc6c25"],
  bg_primary="#606c38", bg_secondary="#283618", bg_card="#fefae0", border="#dda15e",
  text_muted="#283618", text_primary="#283618",
  accent="#bc6c25", accent_hover="#a85c15", input_bg="#fefae0", shadow="rgba(0,0,0,0.15)")

_t("summer-ocean-breeze", "light", ["#e63946", "#f1faee", "#a8dadc", "#457b9d", "#1d3557"],
  bg_primary="#e63946", bg_secondary="#f1faee", bg_card="#a8dadc", border="#457b9d",
  text_muted="#457b9d", text_primary="#1d3557",
  accent="#e63946", accent_hover="#c62a38", input_bg="#f1faee", shadow="rgba(0,0,0,0.1)")

_t("refreshing-summer-fun", "dark", ["#8ecae6", "#219ebc", "#023047", "#ffb703", "#fb8500"],
  bg_primary="#8ecae6", bg_secondary="#219ebc", bg_card="#023047", border="#219ebc",
  text_muted="#8ecae6", text_primary="#ffffff",
  accent="#ffb703", accent_hover="#fb8500", input_bg="#023047", shadow="rgba(0,0,0,0.3)")

_t("black-gold-elegance", "dark", ["#000000", "#14213d", "#fca311", "#e5e5e5", "#ffffff"],
  bg_primary="#000000", bg_secondary="#14213d", bg_card="#14213d", border="#fca311",
  text_muted="#e5e5e5", text_primary="#ffffff",
  accent="#fca311", accent_hover="#e09c10", input_bg="#14213d", shadow="rgba(0,0,0,0.4)")

_t("vibrant-color-fiesta", "dark", ["#ffbe0b", "#fb5607", "#ff006e", "#8338ec", "#3a86ff"],
  bg_primary="#ffbe0b", bg_secondary="#fb5607", bg_card="#ff006e", border="#8338ec",
  text_muted="#e0aaff", text_primary="#ffffff",
  accent="#3a86ff", accent_hover="#2d6dcc", input_bg="#ff006e", shadow="rgba(0,0,0,0.3)")

_t("light-steel", "light", ["#f8f9fa", "#e9ecef", "#dee2e6", "#ced4da", "#adb5bd", "#6c757d", "#495057", "#343a40", "#212529"],
  bg_primary="#f8f9fa", bg_secondary="#e9ecef", bg_card="#dee2e6", border="#ced4da",
  text_muted="#6c757d", text_primary="#212529",
  accent="#495057", accent_hover="#343a40", input_bg="#ffffff", shadow="rgba(0,0,0,0.08)")

_t("golden-twilight", "dark", ["#000814", "#001d3d", "#003566", "#ffc300", "#ffd60a"],
  bg_primary="#000814", bg_secondary="#001d3d", bg_card="#003566", border="#ffc300",
  text_muted="#ffd60a", text_primary="#ffffff",
  accent="#ffc300", accent_hover="#e6af00", input_bg="#003566", shadow="rgba(0,0,0,0.4)")

_t("deep-sea", "dark", ["#0d1b2a", "#1b263b", "#415a77", "#778da9", "#e0e1dd"],
  bg_primary="#0d1b2a", bg_secondary="#1b263b", bg_card="#415a77", border="#778da9",
  text_muted="#778da9", text_primary="#e0e1dd",
  accent="#778da9", accent_hover="#5c7a99", input_bg="#415a77", shadow="rgba(0,0,0,0.3)")

_t("bright-green", "dark", ["#004b23", "#006400", "#007200", "#008000", "#38b000", "#70e000", "#9ef01a", "#ccff33"],
  bg_primary="#004b23", bg_secondary="#006400", bg_card="#007200", border="#008000",
  text_muted="#9ef01a", text_primary="#ccff33",
  accent="#70e000", accent_hover="#5cc000", input_bg="#007200", shadow="rgba(0,0,0,0.3)")

_t("vivid-nightfall", "dark", ["#10002b", "#240046", "#3c096c", "#5a189a", "#7b2cbf", "#9d4edd", "#c77dff", "#e0aaff"],
  bg_primary="#10002b", bg_secondary="#240046", bg_card="#3c096c", border="#5a189a",
  text_muted="#c77dff", text_primary="#e0aaff",
  accent="#9d4edd", accent_hover="#7b2cbf", input_bg="#3c096c", shadow="rgba(0,0,0,0.4)")


def ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config():
    global CURRENT_THEME, CURRENT_MODE
    ensure_config_dir()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "rb") as f:
                data = tomllib.load(f)
            theme_settings = data.get("theme", {})
            name = theme_settings.get("name", "dark")
            mode = theme_settings.get("mode", THEMES.get(name, {}).get("mode", "dark"))
            if name in THEMES:
                CURRENT_THEME = name
                CURRENT_MODE = mode
                return
        except Exception:
            pass
    CURRENT_THEME = "dark"
    CURRENT_MODE = "dark"


def save_config(name, mode=None):
    ensure_config_dir()
    if mode is None:
        mode = THEMES.get(name, {}).get("mode", "dark")
    try:
        import tomli_w
    except ImportError:
        pass
    lines = ["[theme]", f'name = "{name}"', f'mode = "{mode}"', ""]
    try:
        with open(CONFIG_FILE, "w") as f:
            f.write("\n".join(lines))
    except Exception:
        pass
    load_config()


def get_theme_vars(theme_name=None):
    if theme_name is None:
        theme_name = CURRENT_THEME
    theme = THEMES.get(theme_name)
    if not theme:
        theme = THEMES["dark"]
    return theme["css"]


def get_all_themes():
    return THEMES
