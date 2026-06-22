"""Deterministic Win32 driver for MicroSurvey's bespoke modal dialogs.

MicroSurvey's survey-job setup lives behind standard `#32770` dialogs (the
IntelliCAD New Drawing Wizard, the Project Manager, and General Configuration
Options). Those dialogs are driven here by Win32 control ID via
`SendMessage(child, BM_CLICK)` / `WM_SETTEXT` — focus- and coordinate-
independent, so it works regardless of which window has focus.

This is the foundation the `create_new_drawing` MCP tool uses to absorb the
new-drawing dialog ceremony instead of routing around it. Control IDs were
recovered by probing the live dialogs (see tools_recon/).
"""

import time

import win32con
import win32gui

# Common nav / button control IDs.
BM_CLICK = win32con.BM_CLICK
WM_SETTEXT = win32con.WM_SETTEXT
WM_GETTEXT = win32con.WM_GETTEXT
WM_GETTEXTLENGTH = win32con.WM_GETTEXTLENGTH

DIALOG_CLASS = "#32770"


def _visible_dialogs():
    """Return (hwnd, title) for every visible top-level #32770 dialog."""
    out = []

    def cb(hwnd, _):
        if (win32gui.IsWindowVisible(hwnd)
                and win32gui.GetClassName(hwnd) == DIALOG_CLASS):
            out.append((hwnd, win32gui.GetWindowText(hwnd)))
        return True

    win32gui.EnumWindows(cb, None)
    return out


def wait_for_dialog(title_substr=None, timeout=10.0, poll=0.25,
                    exclude_hwnds=None):
    """Block until a visible #32770 dialog matching title_substr appears.

    Args:
        title_substr: case-insensitive substring the title must contain.
            None matches any #32770 dialog.
        timeout: seconds to wait before giving up.
        poll: seconds between polls.
        exclude_hwnds: iterable of hwnds to ignore (e.g. a dialog you already
            have, so you can detect a *new* one).

    Returns:
        The matching dialog hwnd, or None on timeout.
    """
    exclude = set(exclude_hwnds or ())
    needle = title_substr.lower() if title_substr else None
    deadline = time.time() + timeout
    while time.time() < deadline:
        for hwnd, title in _visible_dialogs():
            if hwnd in exclude:
                continue
            if needle is None or needle in title.lower():
                return hwnd
        time.sleep(poll)
    return None


def child_by_id(dlg, ctrl_id):
    """Return the child control hwnd with the given dialog control id."""
    hit = []

    def cb(child, _):
        if win32gui.GetDlgCtrlID(child) == ctrl_id:
            hit.append(child)
        return True

    win32gui.EnumChildWindows(dlg, cb, None)
    return hit[0] if hit else None


def click(dlg, ctrl_id):
    """BM_CLICK the control with the given id. Returns True if found."""
    h = child_by_id(dlg, ctrl_id)
    if not h:
        return False
    win32gui.SendMessage(h, BM_CLICK, 0, 0)
    return True


WM_COMMAND = win32con.WM_COMMAND
EN_CHANGE = 0x0300
EN_KILLFOCUS = 0x0200


def set_text(dlg, ctrl_id, text):
    """Set an edit/combo control's text and notify the parent so the value
    commits.

    WM_SETTEXT alone changes the displayed text but doesn't fire the
    EN_CHANGE / EN_KILLFOCUS notifications that MFC dialogs rely on to read a
    field back on OK (DDX). Without them the value silently reverts. We send
    both notifications to the parent as if the user had typed and left the
    field. Returns True if the control was found.
    """
    h = child_by_id(dlg, ctrl_id)
    if not h:
        return False
    win32gui.SendMessage(h, WM_SETTEXT, 0, str(text))
    parent = win32gui.GetParent(h)
    wparam_change = (EN_CHANGE << 16) | (ctrl_id & 0xFFFF)
    wparam_kill = (EN_KILLFOCUS << 16) | (ctrl_id & 0xFFFF)
    win32gui.SendMessage(parent, WM_COMMAND, wparam_change, h)
    win32gui.SendMessage(parent, WM_COMMAND, wparam_kill, h)
    return True


def get_title(dlg):
    """Window title of a dialog hwnd ('' if gone)."""
    try:
        return win32gui.GetWindowText(dlg)
    except Exception:
        return ""


def is_alive(dlg):
    """True if the dialog hwnd is still a visible window."""
    try:
        return bool(win32gui.IsWindow(dlg) and win32gui.IsWindowVisible(dlg))
    except Exception:
        return False


def dump(dlg):
    """Return a list of (class, id, enabled, text) for visible children.

    Useful for diagnostics when a control id isn't found.
    """
    rows = []

    def cb(child, _):
        if not win32gui.IsWindowVisible(child):
            return True
        rows.append((
            win32gui.GetClassName(child),
            win32gui.GetDlgCtrlID(child),
            win32gui.IsWindowEnabled(child),
            win32gui.GetWindowText(child),
        ))
        return True

    win32gui.EnumChildWindows(dlg, cb, None)
    return rows
