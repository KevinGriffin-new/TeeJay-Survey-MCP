"""Deterministic Win32 driver for the MicroSurvey 'New Drawing Wizard'.

Targets the standard #32770 dialog by title and clicks controls by their
Win32 control ID (focus- and coordinate-independent). This is the basis for
the create_new_drawing MCP tool's dialog automation.

Commands:
  dump                 dump visible+enabled controls of the wizard
  click <ctrl_id>      BM_CLICK the control with that dialog id
  next                 click '&Next >' (id 12324)
  back                 click '< &Back' (id 12323)
  finish               click 'Finish' (id 12325)  [CREATES the drawing]
  cancel               click 'Cancel' (id 2)
  settext <id> <text>  set an edit/combo control's text
"""
import sys
import time
import win32gui
import win32con

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PAGE_TITLES = {
    "New Drawing Wizard", "Template Drawings", "Set Up New Drawing",
    "Measurement unit", "Linear Units",
}
NEXT, BACK, FINISH, CANCEL = 12324, 12323, 12325, 2


def find_dialog():
    found = []

    def cb(hwnd, _):
        if (win32gui.IsWindowVisible(hwnd)
                and win32gui.GetClassName(hwnd) == "#32770"):
            found.append(hwnd)
        return True

    win32gui.EnumWindows(cb, None)
    return found[0] if found else None


def child_by_id(dlg, ctrl_id):
    hit = []

    def cb(child, _):
        if win32gui.GetDlgCtrlID(child) == ctrl_id:
            hit.append(child)
        return True

    win32gui.EnumChildWindows(dlg, cb, None)
    return hit[0] if hit else None


def dump(dlg):
    rows = []

    def cb(child, _):
        if not win32gui.IsWindowVisible(child):
            return True
        cls = win32gui.GetClassName(child)
        cid = win32gui.GetDlgCtrlID(child)
        en = win32gui.IsWindowEnabled(child)
        txt = win32gui.GetWindowText(child)
        rows.append(f"  [{cls!r} id={cid} en={en}] {txt!r}")
        return True

    win32gui.EnumChildWindows(dlg, cb, None)
    print(f"== {win32gui.GetWindowText(dlg)!r} hwnd={dlg}")
    print("\n".join(rows))


def click(dlg, ctrl_id):
    h = child_by_id(dlg, ctrl_id)
    if not h:
        print(f"control id={ctrl_id} not found")
        return
    win32gui.SendMessage(h, win32con.BM_CLICK, 0, 0)
    print(f"clicked id={ctrl_id}")


def settext(dlg, ctrl_id, text):
    h = child_by_id(dlg, ctrl_id)
    if not h:
        print(f"control id={ctrl_id} not found")
        return
    win32gui.SendMessage(h, win32con.WM_SETTEXT, 0, text)
    print(f"set id={ctrl_id} -> {text!r}")


def main():
    dlg = find_dialog()
    if not dlg:
        print("New Drawing Wizard dialog NOT found (is it open?)")
        sys.exit(2)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dump"
    if cmd == "dump":
        dump(dlg)
    elif cmd == "click":
        click(dlg, int(sys.argv[2]))
    elif cmd == "next":
        click(dlg, NEXT)
    elif cmd == "back":
        click(dlg, BACK)
    elif cmd == "finish":
        click(dlg, FINISH)
    elif cmd == "cancel":
        click(dlg, CANCEL)
    elif cmd == "settext":
        settext(dlg, int(sys.argv[2]), sys.argv[3])
    else:
        print(f"unknown command {cmd!r}")
        sys.exit(2)
    if cmd in ("next", "back", "click"):
        time.sleep(0.6)
        dlg2 = find_dialog()
        if dlg2:
            dump(dlg2)


if __name__ == "__main__":
    main()
