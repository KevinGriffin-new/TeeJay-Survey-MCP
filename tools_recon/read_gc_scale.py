"""Re-open General Config, read the Drawing Scale factor edit (21032), cancel."""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from mscad_mcp import connection
from mscad_mcp import dialog_driver as dd
import win32gui
import win32con


def main():
    threading.Thread(
        target=connection.send_command_isolated,
        args=("_cnf_edit_general ",), daemon=True,
    ).start()
    warn = dd.wait_for_dialog("MicroSurvey", timeout=2.0)
    if warn and not dd.child_by_id(warn, 21403):
        dd.click(warn, 2)
    gc = dd.wait_for_dialog("General Configuration Options", timeout=8.0)
    if not gc:
        print("GC did not open")
        return
    time.sleep(1.5)  # let the dialog finish populating its fields
    h = dd.child_by_id(gc, 21032)
    txt = win32gui.GetWindowText(h) if h else "<no edit>"
    print("Drawing Scale factor (21032) =", repr(txt))
    # Read which distance/direction radios are checked.
    for cid, label in [(21028, "Metric"), (21029, "Intl Feet"),
                       (21403, "US Feet"), (21030, "Bearings"),
                       (21031, "Azimuth DMS")]:
        c = dd.child_by_id(gc, cid)
        state = win32gui.SendMessage(c, win32con.BM_GETCHECK, 0, 0) if c else "?"
        print(f"  {label} ({cid}) checked={state}")
    time.sleep(0.3)
    dd.click(gc, 2)  # Cancel
    print("cancelled GC")


if __name__ == "__main__":
    main()
