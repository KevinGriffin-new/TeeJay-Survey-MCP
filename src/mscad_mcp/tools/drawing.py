"""Drawing/project management tools."""

import os
import threading
import time

from mscad_mcp.server import mcp
from mscad_mcp import connection
from mscad_mcp import dialog_driver as dd


@mcp.tool()
def get_drawing_info() -> dict:
    """Get information about the active drawing.

    Returns:
        Dict with filename, path, layer count, entity count, etc.
    """
    try:
        doc = connection.get_document()
        info = {}

        for attr, key in [
            ("Name", "name"),
            ("FullName", "full_path"),
            ("Path", "directory"),
            ("Saved", "is_saved"),
            ("ReadOnly", "read_only"),
        ]:
            try:
                info[key] = getattr(doc, attr)
            except Exception:
                info[key] = None

        try:
            info["layer_count"] = doc.Layers.Count
        except Exception:
            info["layer_count"] = None

        try:
            info["entity_count"] = doc.ModelSpace.Count
        except Exception:
            info["entity_count"] = None

        return info
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def open_drawing(file_path: str) -> str:
    """Open a drawing file in MicroSurvey CAD.

    Args:
        file_path: Full path to .dwg, .dxf, or .msz file.

    Returns:
        Status message.
    """
    try:
        app = connection.get_app()
        doc = app.Documents.Open(file_path)
        return f"Opened: {doc.Name}"
    except Exception as e:
        # Fallback: use command
        try:
            app = connection.get_app()
            app.RunCommand(f'_OPEN\n"{file_path}"\n')
            return f"Open command sent for: {file_path}"
        except Exception as e2:
            return f"Error opening file: {e} / {e2}"


@mcp.tool()
def save_drawing(file_path: str | None = None) -> str:
    """Save the active drawing.

    Args:
        file_path: Path for Save As. Omit to save in place.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        if file_path:
            doc.SaveAs(file_path)
            return f"Saved as: {file_path}"
        else:
            doc.Save()
            return f"Saved: {doc.Name}"
    except Exception as e:
        # Fallback: command
        try:
            doc = connection.get_document()
            if file_path:
                doc.SendCommand(f'_SAVEAS\n\n"{file_path}"\n')
                return f"SaveAs command sent: {file_path}"
            else:
                doc.SendCommand("_QSAVE\n")
                return "Save command sent"
        except Exception as e2:
            return f"Error saving: {e} / {e2}"


# General Configuration Options ('_cnf_edit_general') control IDs.
_DISTANCE_IDS = {"metric": 21028, "intl_feet": 21029, "us_feet": 21403}
_DIRECTION_IDS = {
    "bearings": 21030,        # Bearings (NSEW) DMS
    "azimuth_dms": 21031,     # Azimuth DMS
    "azimuth_dd": 21546,      # Azimuth Decimal Degrees
    "azimuth_grad": 21548,    # Azimuth Gradians
}
_GC_SCALE_EDIT = 21032
_GC_JOBDESC_EDIT = 21038
_GC_CLIENT_EDIT = 21039
_GC_OK = 1
_GC_CANCEL = 2

# IntelliCAD New Drawing Wizard control IDs.
_WIZ_CREATE_NEW = 11504
_WIZ_FEET = 11533
_WIZ_METRIC = 11534
_WIZ_LINEAR_DECIMAL = 11520
_WIZ_ANG_SURVEYOR = 1041
_WIZ_ANG_DECIMAL = 1541
_WIZ_NEXT = 12324
_WIZ_FINISH = 12325


def _fire_async(cmd: str):
    """Run a (possibly blocking) MSCAD command on a daemon thread."""
    t = threading.Thread(
        target=connection.send_command_isolated, args=(cmd,), daemon=True
    )
    t.start()
    return t


def _wait_child(dlg, ctrl_id, timeout=5.0, poll=0.15):
    """Poll until a control id exists on dlg (page transitions)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if dd.child_by_id(dlg, ctrl_id):
            return True
        time.sleep(poll)
    return False


def _walk_new_drawing_wizard(metric: bool, bearings: bool, log: list) -> bool:
    """Drive the IntelliCAD New Drawing Wizard end to end. Returns success."""
    wiz = dd.wait_for_dialog("New Drawing Wizard", timeout=10.0)
    if not wiz:
        log.append("wizard did not appear")
        return False

    # P1: create entirely new drawing.
    dd.click(wiz, _WIZ_CREATE_NEW)
    dd.click(wiz, _WIZ_NEXT)

    # P3: measurement unit (wizard re-captions same hwnd; wait for the radio).
    if _wait_child(wiz, _WIZ_METRIC):
        dd.click(wiz, _WIZ_METRIC if metric else _WIZ_FEET)
        dd.click(wiz, _WIZ_NEXT)

    # P4: linear units format -> decimal.
    if _wait_child(wiz, _WIZ_LINEAR_DECIMAL):
        dd.click(wiz, _WIZ_LINEAR_DECIMAL)
        dd.click(wiz, _WIZ_NEXT)

    # P5: angular units -> Surveyor's (bearings) or decimal degrees.
    if _wait_child(wiz, _WIZ_ANG_SURVEYOR):
        dd.click(wiz, _WIZ_ANG_SURVEYOR if bearings else _WIZ_ANG_DECIMAL)
        dd.click(wiz, _WIZ_NEXT)

    # Remaining pages (print style, entity creation): accept defaults, advance
    # until Finish is available.
    for _ in range(4):
        if _wait_child(wiz, _WIZ_FINISH, timeout=1.5):
            break
        dd.click(wiz, _WIZ_NEXT)
        time.sleep(0.3)
    if not _wait_child(wiz, _WIZ_FINISH, timeout=2.0):
        log.append("Finish button never became available")
        return False
    dd.click(wiz, _WIZ_FINISH)
    # Wait for the wizard to close.
    deadline = time.time() + 5
    while dd.is_alive(wiz) and time.time() < deadline:
        time.sleep(0.2)
    log.append("wizard completed")
    return True


def _is_gc(dlg) -> bool:
    """True if a #32770 is the General Configuration Options dialog (it carries
    the distance-unit radios; warnings/gates do not)."""
    return dd.child_by_id(dlg, _DISTANCE_IDS["us_feet"]) is not None


def _dismiss_gate_warnings() -> int:
    """Dismiss every visible #32770 that is NOT the GC dialog (the config flow
    raises gate warnings whose title varies — 'MicroSurvey' for the
    save-to-a-name gate, 'MSCAD' for 'A drawing is required'. Match by
    structure, not title). Returns how many were dismissed."""
    n = 0
    for hwnd, _title in dd._visible_dialogs():
        if _is_gc(hwnd):
            continue
        if dd.child_by_id(hwnd, 2):       # OK / acknowledge
            dd.click(hwnd, 2)
            n += 1
        elif dd.child_by_id(hwnd, 1):
            dd.click(hwnd, 1)
            n += 1
    return n


def _configure_general(distance_key, direction_key, scale_factor,
                       job_description, client_name, log: list) -> bool:
    """Drive General Configuration Options ('_cnf_edit_general').

    Fires the command and waits for the dialog, retrying a few times. Right
    after a SaveAs the CAD is still writing the .msj job folder and can silently
    drop the command, so a single fire is unreliable — re-fire if GC doesn't
    show.
    """
    # Saving to a survey-job name AUTO-raises General Config; prefer that one
    # over firing a duplicate. Only fire _cnf_edit_general if none is already up.
    gc = dd.wait_for_dialog("General Configuration Options", timeout=2.5)
    if not gc:
        for attempt in range(3):
            _fire_async("_cnf_edit_general ")
            # The config flow can raise a gate warning first (save-to-a-name,
            # or 'A drawing is required') whose title differs by case —
            # dismiss any non-GC dialog by structure, not by guessing a title.
            time.sleep(0.8)
            _dismiss_gate_warnings()
            gc = dd.wait_for_dialog("General Configuration Options", timeout=6.0)
            if gc:
                break
            log.append(f"GC not up (attempt {attempt + 1}); re-firing")
            _dismiss_gate_warnings()
            time.sleep(1.0)
    if not gc:
        log.append("General Configuration Options did not appear")
        return False

    if distance_key in _DISTANCE_IDS:
        dd.click(gc, _DISTANCE_IDS[distance_key])
    if direction_key in _DIRECTION_IDS:
        dd.click(gc, _DIRECTION_IDS[direction_key])
    if scale_factor is not None:
        dd.set_text(gc, _GC_SCALE_EDIT, scale_factor)
    if job_description:
        dd.set_text(gc, _GC_JOBDESC_EDIT, job_description)
    if client_name:
        dd.set_text(gc, _GC_CLIENT_EDIT, client_name)

    dd.click(gc, _GC_OK)
    time.sleep(0.5)
    # Cancel any leftover/duplicate GC dialogs — both the auto-raised one and
    # our fired one can be open at once; they hold template defaults (Int'l
    # Feet), so OK-ing them would clobber the units we just set. Cancel, don't OK.
    for hwnd, _title in dd._visible_dialogs():
        if _is_gc(hwnd):
            dd.click(hwnd, _GC_CANCEL)
            time.sleep(0.2)
    # OK may also re-raise a scale-factor warning; dismiss any lingering modal.
    _dismiss_gate_warnings()
    log.append("general config applied")
    return True


@mcp.tool()
def create_new_drawing(
    name: str | None = None,
    distance_units: str = "us_feet",
    direction: str = "bearings",
    scale_factor: float | None = None,
    job_description: str | None = None,
    client_name: str | None = None,
    jobs_dir: str | None = None,
) -> str:
    """Create and configure a new MicroSurvey CAD survey drawing.

    Reliable from ANY app state, including the zero-document Start Page a fresh
    launch sits in. Creates the drawing via Documents.Add (the only doc-
    creation primitive that persists a usable drawing from zero docs), then
    drives the real dialog chain by Win32 control id (focus-independent):
    SaveAs (name) -> General Configuration Options (distance units / direction
    convention / drawing scale / job metadata, which set INSUNITS/AUNITS).
    Absorbs the bespoke modal-dialog ceremony so callers get a correctly
    set-up drawing with no manual interaction.

    Args:
        name: Job/drawing name. If given, the drawing is saved to
            <jobs_dir>/<name>.dwg so survey config will stick (the config flow
            refuses default/unsaved names). If None, the drawing stays unnamed.
        distance_units: 'metric', 'intl_feet', or 'us_feet'.
        direction: 'bearings', 'azimuth_dms', 'azimuth_dd', or 'azimuth_grad'.
        scale_factor: Drawing scale factor, e.g. 500 for 1"=500'. None leaves
            the default.
        job_description: Optional General-Config 'Job Description' text.
        client_name: Optional General-Config 'Client name' text.
        jobs_dir: Directory for the saved .dwg. Defaults to
            ~/Documents/MicroSurvey/Jobs (OneDrive-redirected if applicable).

    Returns:
        Status message describing each stage that ran.
    """
    log: list = []

    try:
        # 1) Create the drawing. Documents.Add reliably yields a usable, active
        #    drawing from ANY state — including the zero-document Start Page a
        #    fresh launch sits in. (The New Drawing Wizard's _NEW does NOT
        #    persist a drawing when fired with no document open: it shows,
        #    Finish-es, and leaves zero drawings, which is why the old wizard
        #    path failed cold with "wizard did not appear" / "A drawing is
        #    required". The wizard's unit pages are redundant with General
        #    Configuration below, which sets the survey INSUNITS/AUNITS.)
        # new_document_isolated does the Add and confirms the count increase
        # inside one apartment; run it on a daemon thread (keeps all COM off
        # the caller's thread) and capture its result.
        seed = {}
        t = threading.Thread(
            target=lambda: seed.__setitem__(
                "ok", connection.new_document_isolated()),
            daemon=True,
        )
        t.start()
        t.join(timeout=14)
        if not seed.get("ok"):
            log.append("could not create a new drawing (Documents.Add)")
            return "create_new_drawing FAILED: " + "; ".join(log)
        log.append("new drawing created")
        time.sleep(0.8)

        # 2) Name the drawing (required for survey config to persist).
        if name:
            if jobs_dir is None:
                docs = os.path.join(os.path.expanduser("~"), "Documents")
                jobs_dir = os.path.join(docs, "MicroSurvey", "Jobs")
            os.makedirs(jobs_dir, exist_ok=True)
            dwg = os.path.join(jobs_dir, f"{name}.dwg")
            # Fire SaveAs on an isolated daemon thread like every other command.
            # A main-thread COM connection here poisons the subsequent isolated
            # _cnf_edit_general fires (mixed COM apartments -> commands silently
            # dropped, GC never opens). Keep ALL command delivery isolated.
            _fire_async(f'_SAVEAS\n\n"{dwg}"\n')
            # Wait for the .dwg to land, then let the .msj job folder (db tables,
            # incad.cfg, etc.) finish writing before the config command.
            deadline = time.time() + 8
            while not os.path.exists(dwg) and time.time() < deadline:
                time.sleep(0.3)
            time.sleep(1.5)
            log.append(f"saved as {dwg}")

        # 3) Survey configuration.
        _configure_general(
            distance_units, direction, scale_factor,
            job_description, client_name, log,
        )

        return "create_new_drawing OK: " + "; ".join(log)
    except Exception as e:
        return f"create_new_drawing error after [{'; '.join(log)}]: {e}"


@mcp.tool()
def export_drawing(file_path: str, format: str = "dxf") -> str:
    """Export the active drawing to another format.

    Args:
        file_path: Destination file path.
        format: Export format — 'dxf' or 'pdf'.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        if format.lower() == "dxf":
            doc.SendCommand(f'_SAVEAS\nDXF\n"{file_path}"\n')
            return f"Export DXF command sent: {file_path}"
        elif format.lower() == "pdf":
            doc.SendCommand(f'-EXPORT\nPDF\n"{file_path}"\n')
            return f"Export PDF command sent: {file_path}"
        else:
            return f"Unsupported format: {format}. Use 'dxf' or 'pdf'."
    except Exception as e:
        return f"Error exporting: {e}"
