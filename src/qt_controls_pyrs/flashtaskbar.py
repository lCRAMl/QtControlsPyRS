# flashtaskbar.py
"""Lässt den Taskleisten-Eintrag eines Fensters blinken.

Nur unter Windows wirksam. Auf anderen Systemen passiert nichts und die
Funktion meldet `False` zurück, damit Aufrufer nichts abfangen müssen.
"""

from __future__ import annotations

import ctypes
import sys

FLASHW_STOP      = 0
FLASHW_CAPTION   = 0x00000001
FLASHW_TRAY      = 0x00000002
FLASHW_ALL       = FLASHW_CAPTION | FLASHW_TRAY
FLASHW_TIMERNOFG = 0x0000000C

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    from ctypes import wintypes

    class FLASHWINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize",    wintypes.UINT),
            ("hwnd",      wintypes.HWND),
            ("dwFlags",   wintypes.DWORD),
            ("uCount",    wintypes.UINT),
            ("dwTimeout", wintypes.DWORD),
        ]


def flash_taskbar(win_id: int, count: int = 3, flags: int = FLASHW_TRAY | FLASHW_TIMERNOFG) -> bool:
    """Blinkt `count` mal. `win_id` ist das Ergebnis von ``int(widget.winId())``.

    Returns:
        True, wenn das Blinken ausgelöst wurde, sonst False (z.B. nicht Windows).
    """
    if not IS_WINDOWS:
        return False

    info = FLASHWINFO(
        ctypes.sizeof(FLASHWINFO),
        int(win_id),
        flags,
        count,
        0,
    )
    ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
    return True


def stop_flashing(win_id: int) -> bool:
    """Beendet ein laufendes Blinken vorzeitig."""
    return flash_taskbar(win_id, count=0, flags=FLASHW_STOP)
