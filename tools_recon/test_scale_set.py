"""Set Drawing Scale factor via improved set_text, OK, reopen, read back."""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from mscad_mcp import connection
from mscad_mcp import dialog_driver as dd
import win32gui


def open_gc():
    threading.Thread(
        target=connection.send_command_isolated,
        args=("_cnf_edit_general ",), daemon=True,
    ).start()
    warn = dd.wait_for_dialog("MicroSurvey", timeout=2.0)
    if warn and not dd.child_by_id(warn, 21403):
        dd.click(warn, 2)
    return dd.wait_for_dialog("General Configuration Options", timeout=8.0)


# Pass 1: set scale + OK.
gc = open_gc()
print("set scale ->", dd.set_text(gc, 21032, "500"))
time.sleep(0.3)
dd.click(gc, 1)  # OK
time.sleep(0.5)
for _ in range(3):
    extra = dd.wait_for_dialog("MicroSurvey", timeout=1.0)
    if not extra:
        break
    print("dismiss extra modal:", win32gui.GetWindowText(extra))
    dd.click(extra, 2)
    time.sleep(0.3)

time.sleep(0.5)
# Pass 2: reopen + read back.
gc2 = open_gc()
h = dd.child_by_id(gc2, 21032)
print("Drawing Scale factor after =", repr(win32gui.GetWindowText(h) if h else None))
h38 = dd.child_by_id(gc2, 21038)
print("Job Description =", repr(win32gui.GetWindowText(h38) if h38 else None))
dd.click(gc2, 2)
print("done")
