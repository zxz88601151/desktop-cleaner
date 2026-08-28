"""Self-drawn line-icon system for Desktop Cleaner (UI-1.3 Phase 1).

Zero third-party dependencies: every glyph is painted with :class:`QPainter`
onto a transparent :class:`QPixmap` at the requested size. Icons inherit their
colour from the caller (usually a theme token), so they stay consistent with
the neutral Windows-utility palette and re-colour correctly on a theme switch.

Style: outline / line, uniform ~1.7 stroke, simple and restrained. No glow,
no fill-everything, no emoji.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from ui.theme.themes import DEFAULT_THEME, THEMES
from ui.theme_manager import ThemeManager

_STROKE = 1.7
_SCALE = 2  # render at 2x for crisp HiDPI output; callers show at logical size

# --------------------------------------------------------------------------- #
# palette helpers
# --------------------------------------------------------------------------- #
def _active_theme() -> str:
    """Resolve the current theme name, degrading safely.

    ``ThemeManager`` reads the persisted preference from SQLite, but icon
    rendering can legitimately happen before ``database.init_db()`` (for
    example a dialog constructed in isolation). A missing or unready DB must
    fall back to the default palette instead of raising — an icon is decoration,
    it must never be able to crash a dialog.
    """
    try:
        return getattr(ThemeManager.instance(), "theme", DEFAULT_THEME)
    except Exception:  # noqa: BLE001 - intentional: icon rendering is non-critical
        return DEFAULT_THEME


def _palette(theme: str | None = None) -> dict:
    if theme is None:
        theme = _active_theme()
    return THEMES.get(theme, THEMES[DEFAULT_THEME])


def color(token: str, theme: str | None = None) -> str:
    """Resolve a theme token to a hex colour string (e.g. ``"text_secondary"``)."""
    return _palette(theme).get(token, "#000000")


# --------------------------------------------------------------------------- #
# drawing primitives
# --------------------------------------------------------------------------- #
def _pen(col: str, w: float = _STROKE) -> QPen:
    p = QPen(QColor(col))
    p.setWidthF(w)
    p.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return p


def _poly(p: QPainter, pts, close: bool = False) -> None:
    path = QPainterPath()
    path.moveTo(pts[0][0], pts[0][1])
    for x, y in pts[1:]:
        path.lineTo(x, y)
    if close:
        path.closeSubpath()
    p.drawPath(path)


def _pt(x: float, y: float) -> QPointF:
    """Shorthand for QPointF — glyph coordinates live in a 24x24 float box."""
    return QPointF(x, y)


def _fill_circle(p: QPainter, cx: float, cy: float, r: float) -> None:
    p.setBrush(QColor(p.pen().color()))
    p.drawEllipse(QPointF(cx, cy), r, r)
    p.setBrush(Qt.BrushStyle.NoBrush)


def _rect(p: QPainter, x: float, y: float, w: float, h: float) -> None:
    """drawRect wrapper taking x/y/w/h (QPainter has no QPointF+w+h overload)."""
    p.drawRect(QRectF(x, y, w, h))


# --------------------------------------------------------------------------- #
# glyph drawers — coordinates live in a 24x24 logical box
# --------------------------------------------------------------------------- #
_DRAWERS = {}


def _drawer(name):
    def deco(fn):
        _DRAWERS[name] = fn
        return fn

    return deco


@_drawer("folder")
def _d_folder(p, col):
    p.setPen(_pen(col))
    _poly(p, [(3, 7), (9, 7), (11, 9), (21, 9), (21, 18), (3, 18)], close=True)


@_drawer("open_folder")
def _d_open_folder(p, col):
    p.setPen(_pen(col))
    _poly(p, [(3, 7), (9, 7), (11, 9), (21, 9), (21, 16), (3, 16)], close=True)
    p.drawLine(_pt(3, 16), _pt(7, 20))
    p.drawLine(_pt(7, 20), _pt(21, 20))
    p.drawLine(_pt(21, 20), _pt(21, 16))


@_drawer("history")
def _d_history(p, col):
    p.setPen(_pen(col))
    p.drawEllipse(_pt(12, 12), 8, 8)
    p.drawLine(_pt(12, 12), _pt(12, 7))
    p.drawLine(_pt(12, 12), _pt(16, 12))


@_drawer("settings")
def _d_settings(p, col):
    p.setPen(_pen(col))
    p.drawEllipse(_pt(12, 12), 6.5, 6.5)
    p.drawEllipse(_pt(12, 12), 2, 2)
    for i in range(8):
        a = math.radians(i * 45)
        cx, cy = 12 + math.cos(a) * 9.5, 12 + math.sin(a) * 9.5
        ix, iy = 12 + math.cos(a) * 7, 12 + math.sin(a) * 7
        p.drawLine(_pt(ix, iy), _pt(cx, cy))


@_drawer("info")
def _d_info(p, col):
    p.setPen(_pen(col))
    p.drawEllipse(_pt(12, 12), 8, 8)
    p.drawLine(_pt(12, 11), _pt(12, 17))
    _fill_circle(p, 12, 8, 1.1)


@_drawer("about")
def _d_about(p, col):
    _d_info(p, col)


@_drawer("home")
def _d_home(p, col):
    p.setPen(_pen(col))
    _poly(
        p,
        [(12, 4), (3, 11), (3, 20), (9, 20), (9, 14), (15, 14), (15, 20), (21, 20), (21, 11)],
        close=True,
    )


@_drawer("scan")
def _d_scan(p, col):
    p.setPen(_pen(col))
    # four corner brackets
    p.drawLine(_pt(4, 8), _pt(4, 4))
    p.drawLine(_pt(4, 4), _pt(8, 4))
    p.drawLine(_pt(20, 8), _pt(20, 4))
    p.drawLine(_pt(20, 4), _pt(16, 4))
    p.drawLine(_pt(4, 16), _pt(4, 20))
    p.drawLine(_pt(4, 20), _pt(8, 20))
    p.drawLine(_pt(20, 16), _pt(20, 20))
    p.drawLine(_pt(20, 20), _pt(16, 20))
    p.drawLine(_pt(12, 9), _pt(12, 15))
    p.drawLine(_pt(9, 12), _pt(15, 12))


@_drawer("refresh")
def _d_refresh(p, col):
    p.setPen(_pen(col))
    p.drawArc(5, 5, 14, 14, int(30 * 16), int(280 * 16))
    p.drawLine(_pt(18, 6), _pt(19.5, 9.5))
    p.drawLine(_pt(19.5, 9.5), _pt(15.5, 9.5))


@_drawer("undo")
def _d_undo(p, col):
    p.setPen(_pen(col))
    p.drawArc(5, 7, 14, 14, int(45 * 16), int(260 * 16))
    p.drawLine(_pt(6, 12), _pt(9.5, 8.5))
    p.drawLine(_pt(6, 12), _pt(9.5, 15.5))


@_drawer("check")
def _d_check(p, col):
    p.setPen(_pen(col, 2.0))
    p.drawLine(_pt(5, 12), _pt(10, 17))
    p.drawLine(_pt(10, 17), _pt(19, 6))


@_drawer("warning")
def _d_warning(p, col):
    p.setPen(_pen(col))
    _poly(p, [(12, 4), (21, 20), (3, 20)], close=True)
    p.drawLine(_pt(12, 9), _pt(12, 15))
    _fill_circle(p, 12, 18, 1.1)


@_drawer("error")
def _d_error(p, col):
    p.setPen(_pen(col))
    p.drawEllipse(_pt(12, 12), 8, 8)
    p.drawLine(_pt(8, 8), _pt(16, 16))
    p.drawLine(_pt(16, 8), _pt(8, 16))


@_drawer("close")
def _d_close(p, col):
    p.setPen(_pen(col))
    p.drawLine(_pt(6, 6), _pt(18, 18))
    p.drawLine(_pt(18, 6), _pt(6, 18))


@_drawer("back")
def _d_back(p, col):
    p.setPen(_pen(col, 2.0))
    p.drawLine(_pt(14, 6), _pt(8, 12))
    p.drawLine(_pt(8, 12), _pt(14, 18))


@_drawer("forward")
def _d_forward(p, col):
    p.setPen(_pen(col, 2.0))
    p.drawLine(_pt(10, 6), _pt(16, 12))
    p.drawLine(_pt(16, 12), _pt(10, 18))


@_drawer("search")
def _d_search(p, col):
    p.setPen(_pen(col))
    p.drawEllipse(_pt(10, 10), 6, 6)
    p.drawLine(_pt(14.5, 14.5), _pt(20, 20))


@_drawer("document")
def _d_document(p, col):
    p.setPen(_pen(col))
    _poly(p, [(6, 3), (14, 3), (19, 8), (19, 21), (6, 21)], close=True)
    p.drawLine(_pt(6, 8), _pt(14, 8))
    p.drawLine(_pt(14, 8), _pt(14, 3))
    p.drawLine(_pt(9, 13), _pt(16, 13))
    p.drawLine(_pt(9, 17), _pt(16, 17))


@_drawer("image")
def _d_image(p, col):
    p.setPen(_pen(col))
    _poly(p, [(4, 6), (20, 6), (20, 18), (4, 18)], close=True)
    _fill_circle(p, 8.5, 10, 2)
    p.drawLine(_pt(5, 17), _pt(10, 12))
    p.drawLine(_pt(10, 12), _pt(14, 16))
    p.drawLine(_pt(14, 16), _pt(19, 11))


@_drawer("video")
def _d_video(p, col):
    p.setPen(_pen(col))
    _poly(p, [(4, 6), (20, 6), (20, 18), (4, 18)], close=True)
    _poly(p, [(10, 9), (10, 15), (16, 12)], close=True)


@_drawer("audio")
def _d_audio(p, col):
    p.setPen(_pen(col))
    p.drawLine(_pt(9, 16), _pt(9, 6))
    p.drawLine(_pt(15, 16), _pt(15, 6))
    p.drawLine(_pt(9, 6), _pt(15, 6))
    _fill_circle(p, 7, 17, 2)
    _fill_circle(p, 17, 17, 2)


@_drawer("archive")
def _d_archive(p, col):
    p.setPen(_pen(col))
    _poly(p, [(4, 8), (20, 8), (20, 19), (4, 19)], close=True)
    p.drawLine(_pt(4, 11), _pt(20, 11))
    _rect(p, 10, 4, 4, 4)


@_drawer("code")
def _d_code(p, col):
    p.setPen(_pen(col))
    p.drawLine(_pt(9, 8), _pt(5, 12))
    p.drawLine(_pt(5, 12), _pt(9, 16))
    p.drawLine(_pt(15, 8), _pt(19, 12))
    p.drawLine(_pt(19, 12), _pt(15, 16))
    p.drawLine(_pt(13, 7), _pt(11, 17))


@_drawer("other")
def _d_other(p, col):
    p.setPen(_pen(col))
    _fill_circle(p, 7, 12, 1.8)
    _fill_circle(p, 12, 12, 1.8)
    _fill_circle(p, 17, 12, 1.8)


@_drawer("play")
def _d_play(p, col):
    p.setPen(_pen(col))
    _poly(p, [(8, 6), (8, 18), (19, 12)], close=True)


@_drawer("pause")
def _d_pause(p, col):
    p.setPen(_pen(col))
    _rect(p, 7, 6, 4, 12)
    _rect(p, 13, 6, 4, 12)


@_drawer("download")
def _d_download(p, col):
    p.setPen(_pen(col))
    p.drawLine(_pt(12, 4), _pt(12, 15))
    p.drawLine(_pt(8, 11), _pt(12, 15))
    p.drawLine(_pt(12, 15), _pt(16, 11))
    p.drawLine(_pt(5, 19), _pt(19, 19))


@_drawer("update")
def _d_update(p, col):
    p.setPen(_pen(col))
    p.drawArc(5, 5, 14, 14, int(30 * 16), int(280 * 16))
    p.drawLine(_pt(12, 5), _pt(9, 8.5))
    p.drawLine(_pt(12, 5), _pt(15, 8.5))


@_drawer("external_link")
def _d_external(p, col):
    p.setPen(_pen(col))
    _poly(p, [(10, 14), (10, 20), (20, 20), (20, 10), (14, 10)], close=True)
    p.drawLine(_pt(13, 4), _pt(5, 4))
    p.drawLine(_pt(5, 4), _pt(5, 12))
    p.drawLine(_pt(5, 4), _pt(11, 10))


@_drawer("moon")
def _d_moon(p, col):
    p.setPen(_pen(col))
    p.drawArc(4, 4, 16, 16, int(20 * 16), int(220 * 16))
    p.drawLine(_pt(13, 4), _pt(13, 20))


@_drawer("sun")
def _d_sun(p, col):
    p.setPen(_pen(col))
    _fill_circle(p, 12, 12, 3.5)
    for i in range(8):
        a = math.radians(i * 45)
        cx, cy = 12 + math.cos(a) * 8, 12 + math.sin(a) * 8
        ix, iy = 12 + math.cos(a) * 5, 12 + math.sin(a) * 5
        p.drawLine(_pt(ix, iy), _pt(cx, cy))


@_drawer("calendar")
def _d_calendar(p, col):
    p.setPen(_pen(col))
    _poly(p, [(5, 6), (19, 6), (19, 20), (5, 20)], close=True)
    p.drawLine(_pt(5, 9), _pt(19, 9))
    p.drawLine(_pt(9, 3), _pt(9, 7))
    p.drawLine(_pt(15, 3), _pt(15, 7))


@_drawer("clock")
def _d_clock(p, col):
    p.setPen(_pen(col))
    p.drawEllipse(_pt(12, 12), 8, 8)
    p.drawLine(_pt(12, 12), _pt(12, 7))
    p.drawLine(_pt(12, 12), _pt(16, 12))


@_drawer("lock")
def _d_lock(p, col):
    p.setPen(_pen(col))
    _poly(p, [(6, 10), (6, 20), (18, 20), (18, 10)], close=True)
    p.drawArc(8, 4, 8, 8, int(180 * 16), int(180 * 16))
    _fill_circle(p, 12, 14, 1.6)
    p.drawLine(_pt(12, 15), _pt(12, 18))


@_drawer("eye")
def _d_eye(p, col):
    p.setPen(_pen(col))
    p.drawEllipse(_pt(12, 12), 8, 5)
    _fill_circle(p, 12, 12, 2)


@_drawer("sort")
def _d_sort(p, col):
    p.setPen(_pen(col))
    p.drawLine(_pt(6, 7), _pt(14, 7))
    p.drawLine(_pt(6, 12), _pt(11, 12))
    p.drawLine(_pt(6, 17), _pt(8, 17))
    p.drawLine(_pt(16, 9), _pt(16, 17))
    p.drawLine(_pt(16, 17), _pt(13, 14))
    p.drawLine(_pt(16, 17), _pt(19, 14))


@_drawer("executable")
def _d_executable(p, col):
    p.setPen(_pen(col))
    _poly(p, [(5, 7), (19, 7), (19, 19), (5, 19)], close=True)
    p.drawLine(_pt(12, 10), _pt(12, 16))
    p.drawLine(_pt(9, 13), _pt(12, 16))
    p.drawLine(_pt(12, 16), _pt(15, 13))


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def pixmap(name: str, col: str, size: int = 20) -> QPixmap:
    """Render ``name`` as a transparent QPixmap at ``size`` logical px.

    Drawn at 2x then flagged with devicePixelRatio=2 so it stays crisp on
    HiDPI displays when the caller shows it inside a ``size`` x ``size`` label.
    """
    target = max(1, int(size * _SCALE))
    pm = QPixmap(target, target)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(target / 24.0, target / 24.0)
    draw = _DRAWERS.get(name, _DRAWERS["other"])
    draw(painter, col)
    painter.end()
    pm.setDevicePixelRatio(_SCALE)
    return pm


def icon(name: str, col: str, size: int = 20) -> QIcon:
    """Same as :func:`pixmap` but wrapped in a :class:`QIcon`."""
    return QIcon(pixmap(name, col, size))


# --------------------------------------------------------------------------- #
# category mapping (UI-side; Core emoji data is left untouched)
# --------------------------------------------------------------------------- #
_CATEGORY_ICON = {
    "图片": "image",
    "文档": "document",
    "视频": "video",
    "音频": "audio",
    "压缩包": "archive",
    "代码": "code",
    "安装程序": "executable",
    "其他": "other",
}


def category_pixmap(label: str, col: str | None = None, size: int = 24) -> QPixmap:
    """Map a Chinese category display label to its line icon.

    Falls back to ``calendar`` for date-mode folders (``2026-08``) and
    ``folder`` for anything unknown. Never touches Core.
    """
    if col is None:
        col = color("text_secondary")
    name = _CATEGORY_ICON.get(label)
    if not name:
        try:
            from core.rules import is_date_dir

            name = "calendar" if is_date_dir(label) else "folder"
        except Exception:  # noqa: BLE001 - defensive: never break rendering
            name = "folder"
    return pixmap(name, col, size)


def category_icon(label: str, col: str | None = None, size: int = 24) -> QIcon:
    return QIcon(category_pixmap(label, col, size))
