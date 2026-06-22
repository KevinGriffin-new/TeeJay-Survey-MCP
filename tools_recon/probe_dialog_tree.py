"""Win32 control-tree probe for MicroSurvey modal dialogs.

Install-free (pywin32 only). Enumerates top-level windows, then recursively
dumps child controls (class / text / control-id / rect / visible / enabled) for
any window whose title matches a filter. Used to recover the exact control
identifiers for driving the New Drawing Wizard programmatically.

Usage:
  python probe_dialog_tree.py            # dump MicroSurvey + dialog tree
  python probe_dialog_tree.py "Wizard"   # filter top-levels by substring
"""
import sys
import win32gui

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _text(hwnd):
    try:
        return win32gui.GetWindowText(hwnd)
    except Exception:
        return ""


def _cls(hwnd):
    try:
        return win32gui.GetClassName(hwnd)
    except Exception:
        return ""


def dump_children(hwnd, depth=1):
    kids = []

    def cb(child, _):
        kids.append(child)
        return True

    try:
        win32gui.EnumChildWindows(hwnd, cb, None)
    except Exception:
        return
    for child in kids:
        rect = win32gui.GetWindowRect(child)
        cid = win32gui.GetDlgCtrlID(child)
        vis = win32gui.IsWindowVisible(child)
        en = win32gui.IsWindowEnabled(child)
        print("  " * depth
              + f"[{_cls(child)!r} id={cid} vis={vis} en={en} "
                f"rect={rect}] {_text(child)!r}")


def main():
    filt = sys.argv[1] if len(sys.argv) > 1 else None
    tops = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        t = _text(hwnd)
        if not t:
            return True
        tops.append(hwnd)
        return True

    win32gui.EnumWindows(cb, None)
    for hwnd in tops:
        t = _text(hwnd)
        if filt and filt.lower() not in t.lower():
            continue
        if not filt and ("microsurvey" not in t.lower()
                         and "wizard" not in t.lower()
                         and "drawing" not in t.lower()):
            continue
        print(f"== TOP hwnd={hwnd} cls={_cls(hwnd)!r} title={t!r}")
        dump_children(hwnd)
        print()


if __name__ == "__main__":
    main()
