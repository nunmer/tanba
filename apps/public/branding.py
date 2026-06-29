"""Per-destination branding (icons + colors) and safe landing theme helpers.

Icons are inline white SVG glyphs shown on a brand-colored badge — self-contained
(no external requests on the hot path), recognizable, and fast. User-supplied theme
values are sanitized before they reach CSS.
"""

from __future__ import annotations

import re
from typing import Any

# --- white glyphs (simple, reliable shapes) ---
_PIN = (
    '<svg viewBox="0 0 24 24" fill="#fff" aria-hidden="true">'
    '<path d="M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7zm0 9.5'
    'A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>'
)
_INSTAGRAM = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" aria-hidden="true">'
    '<rect x="3" y="3" width="18" height="18" rx="5"/>'
    '<circle cx="12" cy="12" r="4"/>'
    '<circle cx="17.5" cy="6.5" r="1.2" fill="#fff" stroke="none"/></svg>'
)
_WHATSAPP = (
    '<svg viewBox="0 0 24 24" fill="#fff" aria-hidden="true">'
    '<path d="M12 3a9 9 0 0 0-7.7 13.7L3 21l4.5-1.2A9 9 0 1 0 12 3zm0 2a7 7 0 0 1 5.9 10.8'
    'l.4.6-.7 2.5-2.6-.7-.6.3A7 7 0 1 1 12 5z"/>'
    '<path d="M9.2 8.3c.2-.4.4-.4.6-.4h.5c.2 0 .4 0 .6.5l.7 1.6c0 .2 0 .3-.1.5l-.4.5c-.1.1-.2.3 '
    '0 .5.3.5 1.4 1.6 2.4 2 .2.1.4.1.5 0l.6-.7c.2-.2.3-.2.5-.1l1.5.7c.2.1.3.2.3.3 0 .5-.6 1.4-1 '
    '1.5-.4.2-1 .3-3.2-.8-2.6-1.3-4-3.8-4.1-4-.1-.2-.6-1-.6-1.9 0-.9.5-1.3.6-1.5z"/></svg>'
)
_TELEGRAM = (
    '<svg viewBox="0 0 24 24" fill="#fff" aria-hidden="true">'
    '<path d="M21.9 4.3 2.9 11.6c-.7.3-.7 1.3 0 1.5l4.6 1.4 1.8 5.4c.2.6 1 .7 1.4.2l2.5-2.7 '
    '4.6 3.4c.5.4 1.2.1 1.3-.5l3-13.9c.2-.8-.6-1.4-1.2-1.1zM9.6 14.2l8-5-6.5 6.1-.2 2.6z"/></svg>'
)
_GLOBE = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" aria-hidden="true">'
    '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/>'
    '<path d="M12 3c2.6 2.7 2.6 15.3 0 18M12 3c-2.6 2.7-2.6 15.3 0 18"/></svg>'
)

KIND_BRANDS: dict[str, dict[str, str]] = {
    "instagram": {
        "label": "Instagram",
        "badge": "linear-gradient(45deg,#feda75,#fa7e1e,#d62976,#962fbf,#4f5bd5)",
        "icon": _INSTAGRAM,
    },
    "whatsapp": {"label": "WhatsApp", "badge": "#25D366", "icon": _WHATSAPP},
    "telegram": {"label": "Telegram", "badge": "#2AABEE", "icon": _TELEGRAM},
    "review_2gis": {"label": "2GIS", "badge": "#19AA1E", "icon": _PIN},
    "google_maps": {"label": "Google Maps", "badge": "#1A73E8", "icon": _PIN},
    "apple_maps": {"label": "Apple Maps", "badge": "#0B84FF", "icon": _PIN},
    "yandex_maps": {"label": "Yandex Maps", "badge": "#FC3F1D", "icon": _PIN},
    "url": {"label": "Open link", "badge": "#2f6df6", "icon": _GLOBE},
}

DEFAULT_BRAND = KIND_BRANDS["url"]

_HEX = re.compile(r"^#[0-9a-fA-F]{3,8}$")


def brand_for(kind: str) -> dict[str, str]:
    return KIND_BRANDS.get(kind, DEFAULT_BRAND)


def safe_color(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) and _HEX.match(value) else fallback


def safe_url(value: Any) -> str | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")) and '"' not in value:
        return value
    return None


_SAFE_SCHEMES = ("http://", "https://", "mailto:", "tel:")


def safe_href(value: Any) -> str:
    """Allow only safe link schemes (blocks javascript:/data: XSS in destination URLs)."""
    if isinstance(value, str) and value.startswith(_SAFE_SCHEMES):
        return value
    return "#"


def background_css(theme: dict[str, Any]) -> str:
    """Build a sanitized CSS `background` value: image > gradient > solid color."""
    image = safe_url(theme.get("bgImage"))
    if image:
        return f"#0f1115 url('{image}') center / cover no-repeat fixed"

    gradient = theme.get("gradient")
    if isinstance(gradient, list) and len(gradient) >= 2:
        c1 = safe_color(gradient[0], "#1a1a2e")
        c2 = safe_color(gradient[1], "#16213e")
        return f"linear-gradient(160deg, {c1}, {c2})"

    return safe_color(theme.get("bg"), "#0f1115")
