# Theme & Settings System — Implementation Plan

## Architecture

### New Files
- `theme.py` — All 17 theme definitions, load/save to `~/.config/neostore/localfs/config.toml`
- `static/css/theme.css` — CSS custom properties + utility classes for all themes
- `templates/settings.html` — Theme picker page with preview cards

### Modified Files
- `main.py` — Import theme, add `/settings` GET+POST route, pass `current_theme` to templates
- `templates/index.html` — Extend base layout, use CSS variable classes, add settings link
- `templates/player.html` — Extend base layout, use CSS variable classes
- `templates/error.html` — Extend base layout, use CSS variable classes
- `templates/base.html` — NEW base layout with theme CSS injection
- `static/js/main.js` — Add theme preview hover on settings page

### Theme Config Path
- `~/.config/neostore/localfs/config.toml` — Stores `theme_name` and `mode` (dark/light)

## Theme Data Structure
```python
THEMES = OrderedDict of:
    "theme-slug": {
        "name": "Display Name",
        "mode": "dark" | "light",
        "colors": ["#hex", ...],  # raw palette
        "css": {                  # semantic CSS vars
            "bg-primary": "#...",
            "bg-secondary": "#...",
            ...
        }
    }
```

## CSS Strategy
- Use CSS custom properties on `:root` + `[data-theme="..."]`
- Define utility classes: `.bg-primary`, `.bg-card`, `.text-primary`, `.btn-accent`, etc.
- Tailwind CDN handles layout (flex, grid, padding, margin) — no build step
- Color classes replaced with CSS variable classes

## Settings Page
- Cards grid showing all themes with color swatches
- Click to select → auto-submit POST → save config → redirect to index
- Current theme highlighted

## Routes
- `GET /settings` — Show settings page with current theme selected
- `POST /settings` — Save selected theme, redirect to index
- Both protected by access key (like index/player)

## Theme-to-CSS Variable Mapping
```css
--bg-primary:        page background (body)
--bg-secondary:      header, nav, footer
--bg-card:           cards, panels, containers
--border:            borders, dividers
--text-muted:        secondary/muted text
--text-primary:      primary text color
--accent:            buttons, links, active states
--accent-hover:      hover state for accent
--input-bg:          input field background
--shadow:            box-shadow color
```

## Implementation Order
1. theme.py — data + load/save
2. static/css/theme.css — all CSS variables
3. templates/base.html — base layout
4. Rewrite index.html, player.html, error.html
5. templates/settings.html — theme picker UI
6. main.py — inject theme, settings routes
7. Tests
8. Commit

## Testing
- Test theme loading/saving
- Test settings route (GET/POST)
- Test theme context in templates
- Test theme persistence across requests
