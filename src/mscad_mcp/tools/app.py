"""Application connection and generic command tools."""

from mscad_mcp.server import mcp
from mscad_mcp import connection


@mcp.tool()
def connect_to_mscad(process_id: int | None = None) -> str:
    """Connect to a running MicroSurvey CAD 2024 instance.

    Args:
        process_id: PID of Icad.exe. Auto-detected if omitted.

    Returns:
        Connection status message.
    """
    try:
        app = connection.connect(process_id)
        pid = connection.get_connected_pid()
        try:
            ver = app.Version
        except Exception:
            ver = "unknown"
        return f"Connected to MicroSurvey CAD (PID {pid}, version {ver})"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_app_info() -> dict:
    """Get information about the connected MicroSurvey CAD instance.

    Returns:
        Dict with version, active document, window title, and PID.
    """
    try:
        app = connection.get_app()
        info = {"pid": connection.get_connected_pid()}

        for attr, key in [
            ("Version", "version"),
            ("Caption", "caption"),
            ("Path", "install_path"),
        ]:
            try:
                info[key] = getattr(app, attr)
            except Exception:
                info[key] = None

        try:
            doc = app.ActiveDocument
            if doc is not None:
                info["active_document"] = doc.FullName
                info["document_name"] = doc.Name
            else:
                info["active_document"] = None
        except Exception:
            info["active_document"] = None

        return info
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def run_command(command: str) -> str:
    """Execute any CAD command string in MicroSurvey CAD.

    This sends a command to the CAD command line. Use standard IntelliCAD
    or MicroSurvey command names. For commands that need input, separate
    arguments with spaces or newlines.

    Args:
        command: Command string, e.g. '_LINE', '_ZOOM E', '_MS_COGO'.

    Returns:
        Status message. Note: most commands do not return output.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand(command + "\n")
        return f"Command sent: {command}"
    except Exception as e:
        return f"Error executing command: {e}"


@mcp.tool()
def get_system_variable(name: str) -> str:
    """Get a CAD system variable value.

    Args:
        name: System variable name, e.g. UNITS, DIMSCALE, LTSCALE, CLAYER.

    Returns:
        The variable value as a string.
    """
    try:
        doc = connection.get_document()
        val = doc.GetVariable(name)
        return str(val)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_system_variable(name: str, value: str) -> str:
    """Set a CAD system variable.

    Args:
        name: System variable name.
        value: New value (will be converted to appropriate type).

    Returns:
        Confirmation message.
    """
    try:
        doc = connection.get_document()
        # Try numeric conversion first
        try:
            num = float(value)
            if num == int(num):
                num = int(num)
            doc.SetVariable(name, num)
        except ValueError:
            doc.SetVariable(name, value)
        return f"Set {name} = {value}"
    except Exception as e:
        return f"Error: {e}"
