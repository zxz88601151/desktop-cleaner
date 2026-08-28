"""Dual-theme design system for Desktop Cleaner (UI refactor, V1.2).

Two palettes (``light`` / ``dark``) plus a single tokenised QSS template.
QSS has no CSS-variable support, so we render a concrete stylesheet by
substituting ``{token}`` placeholders with the active palette.

Everything here is presentation-only; no business logic or schema changes.
"""
from __future__ import annotations

from PySide6.QtGui import QColor

# --------------------------------------------------------------------------- #
# Palettes
# --------------------------------------------------------------------------- #
LIGHT = {
    "name": "light",
    "bg": "#F4F6FB",
    "surface": "#FFFFFF",
    "surface_alt": "#F1F5F9",
    "surface_hover": "#F8FAFC",
    "border": "#E6EAF2",
    "border_strong": "#CBD5E1",
    "text": "#0F172A",
    "text_secondary": "#475569",
    "text_muted": "#94A3B8",
    "accent": "#4F46E5",
    "accent_hover": "#4338CA",
    "accent_pressed": "#3730A3",
    "accent_soft": "#EEF2FF",
    "on_accent": "#FFFFFF",
    "danger": "#E11D48",
    "danger_hover": "#BE123C",
    "danger_soft": "#FFF1F3",
    "success": "#16A34A",
    "success_soft": "#ECFDF3",
    "log_bg": "#0F172A",
    "log_text": "#CBD5E1",
    "separator": "#E6EAF2",
    "shadow": "rgba(15, 23, 42, 0.10)",
    "shadow_rgba": (15, 23, 42, 46),  # used for QGraphicsDropShadowEffect
    "radius": "14px",
    "radius_sm": "10px",
    "radius_xs": "8px",
}

DARK = {
    "name": "dark",
    "bg": "#0B1120",
    "surface": "#151C2C",
    "surface_alt": "#1B2436",
    "surface_hover": "#1F2937",
    "border": "#28324A",
    "border_strong": "#3A4760",
    "text": "#E8EDF6",
    "text_secondary": "#AEB9CC",
    "text_muted": "#7A8699",
    "accent": "#818CF8",
    "accent_hover": "#A5B4FC",
    "accent_pressed": "#6366F1",
    "accent_soft": "#272058",
    "on_accent": "#0B1120",
    "danger": "#FB7185",
    "danger_hover": "#F43F5E",
    "danger_soft": "#3A1420",
    "success": "#4ADE80",
    "success_soft": "#0F2E1C",
    "log_bg": "#05080F",
    "log_text": "#AEB9CC",
    "separator": "#28324A",
    "shadow": "rgba(0, 0, 0, 0.45)",
    "shadow_rgba": (0, 0, 0, 110),
    "radius": "14px",
    "radius_sm": "10px",
    "radius_xs": "8px",
}

THEMES = {"light": LIGHT, "dark": DARK}

DEFAULT_THEME = "light"

FONT_FAMILY = '"Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif'
MONO_FAMILY = '"Cascadia Code", "Consolas", "Courier New", monospace'


# --------------------------------------------------------------------------- #
# Tokenised QSS template
# --------------------------------------------------------------------------- #
QSS_TEMPLATE = """
QWidget {{
    font-family: {FONT_FAMILY};
    font-size: 13px;
    color: {text};
    background: {bg};
}}
QLabel {{
    color: {text_secondary};
    background: transparent;
}}
#title {{
    font-size: 22px;
    font-weight: 700;
    color: {text};
}}
#subtitle {{
    font-size: 12.5px;
    color: {text_muted};
}}
#section-title {{
    font-size: 14px;
    font-weight: 600;
    color: {text};
}}
#separator {{
    color: {separator};
    background: {separator};
}}

/* ---- generic card ---- */
#card {{
    background: {surface};
    border: 1px solid {border};
    border-radius: {radius};
}}
#panel {{
    background: {surface};
    border: 1px solid {border};
    border-radius: {radius};
}}

/* ---- buttons ---- */
QPushButton {{
    padding: 8px 18px;
    border: 1px solid {border_strong};
    border-radius: {radius_xs};
    background: {surface};
    color: {text};
    font-size: 13px;
}}
QPushButton:hover {{
    background: {surface_hover};
    border: 1px solid {accent};
}}
QPushButton:pressed {{
    background: {surface_alt};
}}
QPushButton:disabled {{
    color: {text_muted};
    background: {surface_alt};
    border: 1px solid {border};
}}
/* keyboard focus ring (restrained, token-driven, no layout shift) */
QPushButton:focus {{
    outline: 2px solid {accent};
    outline-offset: 2px;
}}
QPushButton#primary {{
    background: {accent};
    border: 1px solid {accent};
    color: {on_accent};
    font-weight: 600;
}}
QPushButton#primary:hover {{
    background: {accent_hover};
    border: 1px solid {accent_hover};
}}
QPushButton#primary:pressed {{
    background: {accent_pressed};
}}
QPushButton#danger {{
    background: {surface};
    border: 1px solid {danger};
    color: {danger};
}}
QPushButton#danger:hover {{
    background: {danger_soft};
}}
QPushButton#danger:pressed {{
    background: {danger_soft};
}}
QPushButton#secondary {{
    background: {surface_alt};
    border: 1px solid {border_strong};
    color: {text};
    font-weight: 600;
}}
QPushButton#secondary:hover {{
    background: {surface_hover};
    border: 1px solid {accent};
}}
QPushButton#secondary:pressed {{
    background: {border};
}}
QPushButton#tertiary {{
    background: transparent;
    border: 1px solid transparent;
    color: {text_secondary};
    font-weight: 600;
}}
QPushButton#tertiary:hover {{
    background: {surface_hover};
    border: 1px solid {border_strong};
    color: {text};
}}
QPushButton#tertiary:pressed {{
    background: {surface_alt};
    color: {text};
}}
QPushButton#ghost {{
    background: transparent;
    border: 1px solid transparent;
    color: {text_secondary};
}}
QPushButton#ghost:hover {{
    background: {surface_hover};
    color: {text};
}}
QPushButton#ghost:pressed {{
    background: {surface_alt};
    color: {text};
}}
QPushButton#icon {{
    background: {surface};
    border: 1px solid {border};
    border-radius: {radius_xs};
    padding: 6px 10px;
    font-size: 15px;
}}
QPushButton#icon:hover {{
    background: {surface_hover};
    border: 1px solid {accent};
}}
QPushButton#icon:pressed {{
    background: {surface_alt};
}}
/* ---- inputs ---- */
QLineEdit, QComboBox {{
    padding: 8px 10px;
    border: 1px solid {border_strong};
    border-radius: {radius_xs};
    background: {surface};
    color: {text};
}}
QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {accent};
}}
QComboBox QAbstractItemView {{
    background: {surface};
    color: {text};
    selection-background-color: {accent_soft};
}}
QCheckBox {{
    spacing: 8px;
    color: {text_secondary};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {border_strong};
    border-radius: 4px;
    background: {surface};
}}
QCheckBox::indicator:checked {{
    background: {accent};
    border: 1px solid {accent};
}}

/* ---- group (used sparingly) ---- */
QGroupBox {{
    font-weight: 600;
    border: 1px solid {border};
    border-radius: {radius_sm};
    margin-top: 8px;
    padding: 10px 12px 12px 12px;
    background: {surface};
    color: {text_secondary};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {text_muted};
}}

/* ---- tables / lists ---- */
QTableWidget {{
    gridline-color: {border};
    background: {surface};
    border: 1px solid {border};
    border-radius: {radius_xs};
    alternate-background-color: {surface_alt};
    color: {text};
}}
QHeaderView::section {{
    background: {surface_alt};
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid {border};
    font-weight: 600;
    color: {text_muted};
}}
QTableWidget::item:selected, QListWidget::item:selected {{
    background: {accent_soft};
    color: {text};
}}
QListWidget {{
    background: {surface};
    border: 1px solid {border};
    border-radius: {radius_xs};
    alternate-background-color: {surface_alt};
    color: {text};
}}
QListWidget::item {{
    padding: 8px 10px;
    border-bottom: 1px solid {border};
}}

/* ---- log / activity ---- */
QTextEdit#log {{
    background: {log_bg};
    color: {log_text};
    border: 1px solid {border};
    border-radius: {radius_xs};
    font-family: {MONO_FAMILY};
    font-size: 12px;
}}

/* ---- progress ---- */
QProgressBar {{
    border: 1px solid {border};
    border-radius: {radius_xs};
    background: {surface_alt};
    text-align: center;
    height: 8px;
    color: {text_muted};
}}
QProgressBar::chunk {{
    background: {accent};
    border-radius: {radius_xs};
}}

/* ---- dialogs ---- */
QDialog {{
    background: {bg};
}}
#welcome-title {{ font-size: 22px; font-weight: 700; color: {text}; }}
#welcome-sub {{ font-size: 13px; color: {text_muted}; }}
#welcome-check {{ font-size: 16px; font-weight: 700; color: {success}; }}
#welcome-bullet {{ font-size: 14px; color: {text_secondary}; }}
#welcome-note {{ font-size: 11.5px; color: {text_muted}; }}
#about-name {{ font-size: 20px; font-weight: 700; color: {text}; }}
#about-version {{ color: {text_muted}; font-size: 13px; }}
#about-tagline {{ font-size: 12.5px; color: {text_muted}; }}
#about-feature {{ font-size: 13px; color: {text_secondary}; }}
#about-author {{ font-size: 12px; color: {text_muted}; }}
#report-root {{ color: {text_secondary}; }}
#report-summary {{ color: {text}; font-size: 13px; }}
#report-detail {{ color: {text_secondary}; }}
#report-note {{ color: {text_muted}; font-size: 11.5px; }}
#report-warn {{ color: {danger}; font-size: 11.5px; font-weight: 600; }}

/* ---- stat cards (dashboard) ---- */
#stat-icon {{ font-size: 24px; }}
#stat-value {{ font-size: 24px; font-weight: 700; color: {text}; }}
#stat-label {{ font-size: 12px; color: {text_muted}; }}

/* ---- empty state ---- */
#empty-title {{ font-size: 14px; font-weight: 600; color: {text_secondary}; }}
#empty-sub {{ font-size: 12px; color: {text_muted}; }}

/* ---- app shell ---- */
#sidebar {{ background: {surface}; border-right: 1px solid {border}; }}
#brand-mark {{ background: {accent}; border-radius: 12px; }}
#sidebar-logo {{ font-size: 16px; font-weight: 700; color: {text}; }}
#sidebar-logo-sub {{ font-size: 11px; color: {text_muted}; font-weight: 500; }}
#nav-item {{
    padding: 11px 12px; border-radius: {radius_sm};
    color: {text_secondary}; font-size: 14px; font-weight: 500;
    background: transparent; border: none; text-align: left;
}}
#nav-item:hover {{ background: {bg}; color: {text}; }}
#nav-item[active="true"] {{
    background: {accent_soft}; color: {accent}; font-weight: 600;
}}
#safety {{
    background: {accent_soft}; border: 1px solid {border};
    border-radius: {radius}; padding: 16px;
}}
#safety-title {{ font-weight: 700; color: {text}; font-size: 14px; }}
#safety-li {{ font-size: 12.5px; color: {text_secondary}; }}

/* ---- score ring label ---- */
#score-v {{ font-size: 56px; font-weight: 780; color: {text}; }}
#score-v-sm {{ font-size: 22px; font-weight: 780; color: {text}; }}
#score-k {{ font-size: 14px; color: {text_secondary}; font-weight: 600; }}

/* ---- plan / scheme cards ---- */
#plan-card {{
    background: {surface}; border: 1px solid {border};
    border-radius: {radius}; padding: 24px;
}}
#plan-card[active="true"] {{ border: 1px solid {accent}; background: {accent_soft}; }}
#plan-card:hover {{ border: 1px solid {accent}; }}
#plan-emoji {{ font-size: 30px; }}
#plan-name {{ font-size: 18px; font-weight: 750; color: {text}; }}
#plan-desc {{ font-size: 13px; color: {text_secondary}; }}
#chip {{
    font-size: 12.5px; padding: 6px 11px; border-radius: 999px;
    background: {bg}; border: 1px solid {border}; color: {text_secondary};
}}
#badge {{
    background: {accent}; color: {on_accent}; font-size: 11px; font-weight: 700;
    padding: 5px 11px; border-radius: 999px;
}}

/* ---- timeline ---- */
#tl-day {{ font-size: 13px; font-weight: 700; color: {text_muted}; }}
#tl-ico {{ background: {accent_soft}; color: {accent}; border-radius: {radius_sm}; }}
#tl-title {{ font-weight: 650; color: {text}; }}
#tl-sub {{ font-size: 13px; color: {text_secondary}; }}
#tl-tag {{ font-size: 12px; font-weight: 700; color: {success}; background: {success_soft}; padding: 5px 11px; border-radius: 999px; }}

/* ---- settings ---- */
#set-row {{ padding: 18px 4px; border-bottom: 1px solid {border}; }}
#set-label {{ font-weight: 600; color: {text}; font-size: 15px; }}
#set-desc {{ font-size: 12.5px; color: {text_muted}; }}
#toggle {{ background: {border_strong}; border-radius: 999px; }}
#toggle[on="true"] {{ background: {accent}; }}
#seg {{ background: {bg}; border: 1px solid {border}; border-radius: {radius_sm}; }}
#seg QPushButton {{ padding: 8px 14px; color: {text_secondary}; border: none; background: transparent; font-size: 13px; font-weight: 600; }}
#seg QPushButton[on="true"] {{ background: {surface}; color: {accent}; }}

/* ---- scan steps ---- */
#scan-step {{ padding: 13px 16px; border-radius: {radius_sm}; background: {surface}; border: 1px solid {border}; color: {text_muted}; font-weight: 600; }}
#scan-step[state="active"] {{ color: {text}; border: 1px solid {accent}; }}
#scan-step[state="done"] {{ color: {text}; }}

/* ---- execute category boxes ---- */
#cat-box {{ background: {surface}; border: 1px solid {border}; border-radius: {radius}; padding: 16px; }}
#cat-emoji {{ font-size: 26px; }}
#cat-name {{ font-weight: 650; color: {text}; font-size: 14px; }}
#cat-count {{ font-size: 12px; color: {text_muted}; }}
#cat-ext {{ font-size: 11.5px; color: {text_muted}; }}

/* ---- page headings / celebrate ---- */
#page-title {{ font-size: 24px; font-weight: 700; color: {text}; }}
#page-sub {{ font-size: 13px; color: {text_muted}; }}
#hero-card {{ background: {surface}; border: 1px solid {border}; border-radius: {radius}; }}
#hero-greet {{ font-size: 14px; font-weight: 600; color: {text}; }}
#done-title {{ font-size: 32px; font-weight: 780; color: {text}; }}
#done-ico {{ font-size: 46px; }}

/* ---- organize wizard ---- */
#field-label {{ font-size: 13px; font-weight: 600; color: {text_secondary}; }}
#step-card {{ background: {surface}; border: 1px solid {border}; border-radius: {radius}; padding: 22px; }}
#cat-row {{ background: {surface}; border: 1px solid {border}; border-radius: {radius_sm}; padding: 12px 16px; }}
#cat-row:hover {{ border: 1px solid {accent}; }}
#cat-bar {{ background: {accent_soft}; border-radius: 999px; min-height: 6px; max-height: 6px; }}
#cat-bar-fill {{ background: {accent}; border-radius: 999px; }}
#summary-line {{ font-size: 14px; color: {text}; font-weight: 600; }}
#result-title {{ font-size: 26px; font-weight: 780; color: {text}; }}
#result-sub {{ font-size: 14px; color: {text_secondary}; }}
#ghost-link {{ background: transparent; border: none; color: {accent}; padding: 4px; font-size: 13px; }}
#ghost-link:hover {{ color: {accent_hover}; text-decoration: underline; }}

/* ---- history timeline ---- */
#tl-row {{ background: {surface}; border: 1px solid {border}; border-radius: {radius}; padding: 14px 16px; }}
#tl-row[selected="true"] {{ border: 1px solid {accent}; background: {accent_soft}; }}
#tl-dot {{ background: {accent}; border-radius: 999px; }}
#tl-title {{ font-weight: 650; color: {text}; font-size: 15px; }}
#tl-sub {{ font-size: 12.5px; color: {text_secondary}; }}
#tl-tag {{ font-size: 12px; font-weight: 700; padding: 4px 11px; border-radius: 999px; }}
#tl-tag[state="done"] {{ color: {success}; background: {success_soft}; }}
#tl-tag[state="undone"] {{ color: {text_muted}; background: {surface_alt}; }}
#tl-tag[state="failed"] {{ color: {danger}; background: {danger_soft}; }}
#tl-tag[state="running"] {{ color: {accent}; background: {accent_soft}; }}

/* ---- settings rows ---- */
#set-row {{ padding: 18px 4px; border-bottom: 1px solid {border}; }}
#set-label {{ font-weight: 600; color: {text}; font-size: 15px; }}
#set-desc {{ font-size: 12.5px; color: {text_muted}; }}
#toggle-hint {{ font-size: 12px; color: {text_muted}; }}

/* ---- one-click undo ---- */
#undo-cta {{ background: {accent_soft}; color: {accent}; border: 1px solid {accent}; border-radius: 14px; font-weight: 650; }}
#undo-cta:hover {{ background: {accent}; color: {on_accent}; }}
#dialog-title {{ font-size: 20px; font-weight: 760; color: {text}; }}
#dialog-body {{ font-size: 14px; color: {text_secondary}; line-height: 1.6; }}

/* ---- tools page / coming soon (UI-2.0) ---- */
#tool-card {{ background: {surface}; border: 1px solid {border}; border-radius: {radius}; }}
#tool-card:hover {{ border: 1px solid {accent}; }}
#tool-icon {{ font-size: 28px; }}
#tool-name {{ font-size: 16px; font-weight: 700; color: {text}; }}
#tool-desc {{ font-size: 13px; color: {text_secondary}; line-height: 1.5; }}
#tool-badge {{
    font-size: 11px; font-weight: 700; padding: 5px 11px; border-radius: 999px;
    color: {accent}; background: {accent_soft}; border: 1px solid {accent};
}}
#tool-badge[state="planned"] {{
    color: {text_muted}; background: {surface_alt}; border: 1px solid {border};
}}
#coming-soon {{ background: {surface}; }}
"""


def build_stylesheet(theme_name: str) -> str:
    """Render a concrete QSS string for the given theme."""
    palette = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
    return QSS_TEMPLATE.format(
        FONT_FAMILY=FONT_FAMILY,
        MONO_FAMILY=MONO_FAMILY,
        **palette,
    )


def shadow_color(theme_name: str | None = None) -> QColor:
    """Return the drop-shadow colour for a theme (defaults to current)."""
    if theme_name is None:
        theme_name = DEFAULT_THEME
    rgba = THEMES.get(theme_name, THEMES[DEFAULT_THEME])["shadow_rgba"]
    return QColor(*rgba)
