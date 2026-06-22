"""Manages the COM connection to MicroSurvey CAD 2024.

Uses pythonnet to call IcadInteraction.ConnectToComHost(pid) which returns a
.NET COM wrapper, then converts it to a win32com late-bound IDispatch object
for full property/method access.
"""

import os
import sys
import time
import logging
import subprocess

log = logging.getLogger(__name__)

MSCAD_INSTALL_PATH = os.environ.get(
    "MSCAD_INSTALL_PATH", r"C:\Program Files\MicroSurvey\MSCAD2024"
)

# Module-level singletons
_app = None  # win32com.client.CDispatch
_connected_pid: int | None = None
_clr_loaded = False


def _ensure_clr():
    """Load the .NET CLR and add MSCAD assemblies (once)."""
    global _clr_loaded
    if _clr_loaded:
        return

    import clr

    mscad = MSCAD_INSTALL_PATH
    if mscad not in sys.path:
        sys.path.append(mscad)

    clr.AddReference(os.path.join(mscad, "IcadDotnetSdk.dll"))
    clr.AddReference(os.path.join(mscad, "IcadAuto.interop.dll"))
    _clr_loaded = True


def _dotnet_to_dispatch(dotnet_com_obj):
    """Convert a pythonnet COM wrapper to a win32com late-bound dispatch object.

    This is necessary because pythonnet's COM interop only exposes a subset
    of the interface. win32com's IDispatch late-binding gives us full access.
    """
    from System.Runtime.InteropServices import Marshal
    import pythoncom
    import win32com.client

    idisp_ptr = Marshal.GetIDispatchForObject(dotnet_com_obj)
    try:
        ptr_value = int(str(idisp_ptr))
        punk = pythoncom.ObjectFromAddress(ptr_value)
        pdisp = punk.QueryInterface(pythoncom.IID_IDispatch)
        return win32com.client.Dispatch(pdisp)
    finally:
        Marshal.Release(idisp_ptr)


def find_mscad_pid() -> int | None:
    """Find the PID of a running Icad.exe process."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Icad.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.strip().splitlines():
            parts = line.strip('"').split('","')
            if len(parts) >= 2 and parts[0].lower() == "icad.exe":
                return int(parts[1])
    except Exception as e:
        log.warning("Failed to find MSCAD process: %s", e)
    return None


def connect(process_id: int | None = None):
    """Connect to a running MSCAD instance and return the Application dispatch object.

    Args:
        process_id: PID of Icad.exe. Auto-detected if None.

    Returns:
        A win32com late-bound dispatch object for IntelliCAD.Application.

    Raises:
        RuntimeError: If MSCAD is not running or connection fails.
    """
    global _app, _connected_pid

    if process_id is None:
        process_id = find_mscad_pid()
        if process_id is None:
            raise RuntimeError(
                "MicroSurvey CAD is not running. Please start MSCAD2024 first."
            )

    _ensure_clr()

    from IntellicadDotNetSdk import IcadInteraction

    try:
        dotnet_app = IcadInteraction.ConnectToComHost(process_id)
        _app = _dotnet_to_dispatch(dotnet_app)
        _connected_pid = process_id
        log.info("Connected to MSCAD PID %d", process_id)
        return _app
    except Exception as e:
        _app = None
        _connected_pid = None
        raise RuntimeError(f"Failed to connect to MSCAD PID {process_id}: {e}") from e


def get_app():
    """Get the current Application dispatch object, connecting if needed."""
    global _app, _connected_pid

    if _app is not None:
        try:
            _ = _app.Version
            return _app
        except Exception:
            log.warning("Lost connection to MSCAD, reconnecting...")
            _app = None
            _connected_pid = None

    return connect()


def get_document():
    """Get the working document from the connected MSCAD instance.

    Prefers ActiveDocument, but falls back to Documents.Item(0) when
    ActiveDocument raises — which it does whenever the Start Page (not a
    drawing) holds focus, even though a drawing is open. Without this fallback
    the whole bridge is unusable on a fresh launch sitting on the Start Page.
    """
    app = get_app()
    try:
        doc = app.ActiveDocument
        if doc is not None:
            return doc
    except Exception as e:
        log.debug("ActiveDocument unavailable (%s); trying Documents.Item(0)", e)

    try:
        docs = app.Documents
        if docs is not None and docs.Count > 0:
            return docs.Item(0)
    except Exception as e:
        raise RuntimeError(
            f"No active document and no open documents. Open a drawing first. ({e})"
        ) from e

    raise RuntimeError("No active document in MSCAD. Open or create a drawing first.")


def get_model_space():
    """Get the ModelSpace of the active document."""
    doc = get_document()
    return doc.ModelSpace


def is_connected() -> bool:
    """Check if we have an active connection to MSCAD."""
    if _app is None:
        return False
    try:
        _ = _app.Version
        return True
    except Exception:
        return False


def disconnect():
    """Clear the connection."""
    global _app, _connected_pid
    _app = None
    _connected_pid = None


def get_connected_pid() -> int | None:
    """Return the PID we're connected to, or None."""
    return _connected_pid


def _resolve_doc(app):
    """Resolve a document to send commands to, mirroring get_document()'s
    fallback: ActiveDocument throws while the Start Page holds focus, but a
    drawing may still be open under Documents.Item(0). Returns None when no
    document exists at all (fresh launch sitting on the Start Page)."""
    try:
        doc = app.ActiveDocument
        if doc is not None:
            return doc
    except Exception:
        pass
    try:
        docs = app.Documents
        if docs is not None and docs.Count > 0:
            return docs.Item(0)
    except Exception:
        pass
    return None


def new_document_isolated(timeout: float = 10.0) -> bool:
    """Create a new blank drawing on a dedicated COM apartment; return whether
    one was created (Documents.Count increased).

    ``Documents.Add()`` reliably creates a usable, *active* drawing even from
    the zero-document Start Page, BUT raises a benign com_error while
    marshaling the returned Document object — the drawing is created
    regardless, so the fault is swallowed. This is the reliable cold-start
    seed: the New Drawing Wizard's ``_NEW`` does NOT persist a drawing when
    delivered with no document open (the wizard shows and Finish-es but leaves
    zero drawings), whereas ``Documents.Add`` does.

    Polls for the count increase WITHIN this single apartment so callers never
    have to spin up a fresh CLR/COM connection per poll (which contends with
    the Add and is slow). Does not touch the module singleton, so it won't
    poison subsequent isolated command delivery.
    """
    import pythoncom

    pythoncom.CoInitialize()
    try:
        pid = find_mscad_pid()
        if pid is None:
            raise RuntimeError("MicroSurvey CAD is not running.")
        _ensure_clr()
        from IntellicadDotNetSdk import IcadInteraction

        app = _dotnet_to_dispatch(IcadInteraction.ConnectToComHost(pid))
        try:
            before = int(app.Documents.Count)
        except Exception:
            before = 0
        try:
            app.Documents.Add()
        except Exception:
            pass  # benign return-marshaling fault; the drawing IS created
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if int(app.Documents.Count) > before:
                    return True
            except Exception:
                pass
            time.sleep(0.4)
        return False
    finally:
        pythoncom.CoUninitialize()


def document_count_isolated() -> int:
    """``Documents.Count`` read from a fresh apartment — for polling new-doc
    creation without touching the module singleton (which would poison
    isolated command delivery)."""
    import pythoncom

    pythoncom.CoInitialize()
    try:
        pid = find_mscad_pid()
        if pid is None:
            return 0
        _ensure_clr()
        from IntellicadDotNetSdk import IcadInteraction

        app = _dotnet_to_dispatch(IcadInteraction.ConnectToComHost(pid))
        try:
            return int(app.Documents.Count)
        except Exception:
            return 0
    finally:
        pythoncom.CoUninitialize()


def send_command_isolated(cmd: str) -> None:
    """Send a command on a dedicated COM apartment, without touching the
    module singleton.

    Commands that open a modal dialog (_NEW, _project_manager,
    _cnf_edit_general, ...) block inside SendCommand until the dialog closes.
    Run this on a daemon thread so the caller can drive the dialog via the
    Win32 control-ID driver (dialog_driver) while this stays blocked.

    Resolves the target document robustly: ``ActiveDocument`` raises whenever
    the Start Page (not a drawing) holds focus — which is exactly the state a
    fresh launch is in — so the old ``app.ActiveDocument.SendCommand`` raised a
    bare com_error and the caller saw "wizard did not appear". When a drawing
    is open we route through it; when none is, we fall back to the
    application-level command channel (``RunCommand``), which delivers commands
    like ``_NEW`` even with zero open documents.
    """
    import pythoncom

    pythoncom.CoInitialize()
    try:
        pid = find_mscad_pid()
        if pid is None:
            raise RuntimeError("MicroSurvey CAD is not running.")
        _ensure_clr()
        from IntellicadDotNetSdk import IcadInteraction

        dotnet_app = IcadInteraction.ConnectToComHost(pid)
        app = _dotnet_to_dispatch(dotnet_app)
        doc = _resolve_doc(app)
        if doc is not None:
            doc.SendCommand(cmd)
        else:
            # No document at all (Start Page, zero drawings). SendCommand has
            # no stream to write to; the app-level RunCommand channel works
            # without an ActiveDocument.
            app.RunCommand(cmd)
    finally:
        pythoncom.CoUninitialize()
