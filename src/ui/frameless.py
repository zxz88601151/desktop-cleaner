"""Frameless top-level window with native Windows behaviors.

``Qt.FramelessWindowHint`` alone strips away everything Windows users expect:
edge resize, drag, double-click maximize and Aero Snap. Re-adding them in
mouseMoveEvent produces laggy, snap-less fakes. Instead, this base class keeps
the *native* window path alive: ``WM_NCHITTEST`` is answered with HTCAPTION /
HT* resize codes so the OS itself drives dragging, snapping, double-click
maximize and edge sizing, while Qt still paints 100% of the surface.

``WM_GETMINMAXINFO`` constrains OS-initiated maximize (double-click on the
caption, drag-to-top snap) to the monitor's work area, because Windows
maximizes popup windows to the full monitor by default — which would bury the
taskbar.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QWidget

if sys.platform == "win32":
    WM_NCHITTEST = 0x0084
    WM_GETMINMAXINFO = 0x0024
    MONITOR_DEFAULTTONEAREST = 2

    HTCLIENT = 1
    HTCAPTION = 2
    HTLEFT = 10
    HTRIGHT = 11
    HTTOP = 12
    HTTOPLEFT = 13
    HTTOPRIGHT = 14
    HTBOTTOM = 15
    HTBOTTOMLEFT = 16
    HTBOTTOMRIGHT = 17

    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    DWMWCP_ROUND = 2

    class MINMAXINFO(ctypes.Structure):
        _fields_ = [
            ("ptReserved", wintypes.POINT),
            ("ptMaxSize", wintypes.POINT),
            ("ptMaxPosition", wintypes.POINT),
            ("ptMinTrackSize", wintypes.POINT),
            ("ptMaxTrackSize", wintypes.POINT),
        ]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    class MARGINS(ctypes.Structure):
        _fields_ = [
            ("cxLeftWidth", ctypes.c_int),
            ("cxRightWidth", ctypes.c_int),
            ("cyTopHeight", ctypes.c_int),
            ("cyBottomHeight", ctypes.c_int),
        ]


class FramelessWindow(QWidget):
    """QWidget base for frameless top-level windows with a custom titlebar.

    Call :meth:`set_caption_widget` with the bar that should act as the
    native caption (drag / double-click / snap region). Children of that bar
    that are :class:`QPushButton` stay interactive; everything else in the bar
    drags the window.
    """

    def __init__(self):
        super().__init__()
        self._caption: QWidget | None = None
        self._dwm_applied = False
        self.setWindowFlag(Qt.FramelessWindowHint, True)

    def set_caption_widget(self, widget: QWidget) -> None:
        self._caption = widget

    # ------------------------------------------------------------------ #
    def nativeEvent(self, eventType, message):  # noqa: N802 - Qt override
        if sys.platform == "win32" and eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_NCHITTEST:
                return True, self._hit_test(msg.lParam)
            if msg.message == WM_GETMINMAXINFO:
                self._constrain_maximize(msg.hwnd, msg.lParam)
                return False, 0
        return super().nativeEvent(eventType, message)

    def _physical_to_logical(self, x: int, y: int) -> QPoint:
        # WM_NCHITTEST lParam carries physical px; Qt's global space is DIPs.
        # Exact for screens anchored at the primary origin (single-monitor).
        handle = self.windowHandle()
        dpr = handle.devicePixelRatio() if handle is not None else 1.0
        if dpr != 1.0:
            x, y = round(x / dpr), round(y / dpr)
        return QPoint(x, y)

    def _hit_test(self, lParam: int) -> int:
        x = ctypes.c_short(lParam & 0xFFFF).value
        y = ctypes.c_short((lParam >> 16) & 0xFFFF).value
        pos = self.mapFromGlobal(self._physical_to_logical(x, y))
        w, h = self.width(), self.height()
        m = 0 if self.isMaximized() else 8

        left = pos.x() < m
        right = pos.x() >= w - m
        top = pos.y() < m
        bottom = pos.y() >= h - m
        if top and left:
            return HTTOPLEFT
        if top and right:
            return HTTOPRIGHT
        if bottom and left:
            return HTBOTTOMLEFT
        if bottom and right:
            return HTBOTTOMRIGHT
        if left:
            return HTLEFT
        if right:
            return HTRIGHT
        if top:
            return HTTOP
        if bottom:
            return HTBOTTOM
        if self._over_caption(pos):
            return HTCAPTION
        return HTCLIENT

    def _over_caption(self, pos: QPoint) -> bool:
        cap = self._caption
        if cap is None or not cap.isVisible():
            return False
        local = cap.mapFrom(self, pos)
        if not cap.rect().contains(local):
            return False
        from PySide6.QtWidgets import QPushButton

        child = cap.childAt(local)
        return not isinstance(child, QPushButton)

    def _constrain_maximize(self, hwnd: int, lParam: int) -> None:
        mmi = MINMAXINFO.from_address(int(lParam))
        user32 = ctypes.windll.user32
        monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return
        mmi.ptMaxPosition.x = info.rcWork.left - info.rcMonitor.left
        mmi.ptMaxPosition.y = info.rcWork.top - info.rcMonitor.top
        mmi.ptMaxSize.x = info.rcWork.right - info.rcWork.left
        mmi.ptMaxSize.y = info.rcWork.bottom - info.rcWork.top

    # ------------------------------------------------------------------ #
    def showEvent(self, event):  # noqa: N802 - Qt override
        super().showEvent(event)
        if not self._dwm_applied:
            self._dwm_applied = True
            self._apply_dwm()

    def _apply_dwm(self) -> None:
        """Dark titlebar mode, rounded corners, DWM shadow via 1px frame."""
        hwnd = int(self.winId())
        if not hwnd:
            return
        dwm = ctypes.windll.dwmapi
        one = ctypes.c_int(1)
        dwm.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(one), 4
        )
        pref = ctypes.c_int(DWMWCP_ROUND)
        dwm.DwmSetWindowAttribute(
            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(pref), 4
        )
        # Extending the frame by 1px opts the frameless (popup-style) window
        # back into the DWM drop shadow.
        margins = MARGINS(1, 1, 1, 1)
        dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
