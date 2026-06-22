"""Open GC, set fields, click OK, dump any modal that appears."""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from mscad_mcp import connection
from mscad_mcp import dialog_driver as dd
import win32gui


threading.Thread(
    target=connection.send_command_isolated,
    args=("_cnf_edit_general ",), daemon=True,
).start()
warn = dd.wait_for_dialog("MicroSurvey", timeout=2.0)
if warn and not dd.child_by_id(warn, 21403):
    dd.click(warn, 2)
gc = dd.wait_for_dialog("General Configuration Options", timeout=8.0)
print("GC hwnd", gc)
dd.set_text(gc, 21032, "500")
dd.set_text(gc, 21038, "MCP smoke test")
time.sleep(0.3)
dd.click(gc, 1)  # OK
time.sleep(0.8)
# Dump every visible #32770 now.
for hwnd, title in dd._visible_dialogs():
    print(f"--- dialog hwnd={hwnd} title={title!r}")
    for cls, cid, en, txt in dd.dump(hwnd):
        if cls in ("Button", "Static", "Edit") and (txt or cls == "Edit"):
            print(f"     [{cls} id={cid} en={en}] {txt!r}")
