"""Survey point management tools — store, delete, list, import, export points."""

from mscad_mcp.server import mcp
from mscad_mcp import connection


@mcp.tool()
def store_point(
    point_number: int,
    easting: float,
    northing: float,
    elevation: float = 0.0,
    description: str = "",
) -> str:
    """Store a survey point in the MicroSurvey coordinate database.

    Uses the _MS_EDITP command to add a point to the active project's
    coordinate database.

    Args:
        point_number: Point number (integer).
        easting: X coordinate (Easting).
        northing: Y coordinate (Northing).
        elevation: Z coordinate (Elevation). Default 0.
        description: Point description code.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        # Use the coordedit command with parameters
        # Format: point#, northing, easting, elevation, description
        cmd = f"_coordedit\n{point_number}\n{northing}\n{easting}\n{elevation}\n{description}\n\n"
        doc.SendCommand(cmd)
        return f"Point {point_number} stored: E={easting}, N={northing}, Z={elevation}, Desc={description}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def store_points_batch(
    points: list[dict],
) -> str:
    """Store multiple survey points at once.

    Args:
        points: List of point dicts with keys: number, easting, northing,
                and optional elevation, description.
                Example: [{"number": 1, "easting": 100, "northing": 200, "elevation": 50, "description": "IP"}]

    Returns:
        Status message with count.
    """
    try:
        doc = connection.get_document()
        count = 0
        for pt in points:
            num = pt["number"]
            e = pt["easting"]
            n = pt["northing"]
            z = pt.get("elevation", 0.0)
            desc = pt.get("description", "")
            cmd = f"_coordedit\n{num}\n{n}\n{e}\n{z}\n{desc}\n\n"
            doc.SendCommand(cmd)
            count += 1
        return f"Stored {count} points"
    except Exception as e:
        return f"Error after storing some points: {e}"


@mcp.tool()
def delete_points(point_range: str) -> str:
    """Delete survey points from the coordinate database.

    Args:
        point_range: Point range string, e.g. "1-10", "5", "1,3,5-10".

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand(f"_MS_DELETEP\n{point_range}\nY\n")
        return f"Delete command sent for points: {point_range}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def list_points(point_range: str = "1-99999") -> str:
    """List survey points from the coordinate database.

    Opens the point listing dialog in MSCAD.

    Args:
        point_range: Point range to list, e.g. "1-100". Default all.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand(f"_MS_LISTP\n{point_range}\n")
        return f"List Points command sent for range: {point_range}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def zoom_to_point(point_number: int) -> str:
    """Zoom the view to center on a survey point.

    Args:
        point_number: The point number to zoom to.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand(f"_MS_ZOOMP\n{point_number}\n")
        return f"Zoomed to point {point_number}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def edit_point() -> str:
    """Open the Single Point Editor dialog (Store and Edit Points).

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_MS_EDITP\n")
        return "Point Editor launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def multi_point_editor() -> str:
    """Open the Multiple Point List Editor in MSCAD.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_MEDITP\n")
        return "Multi Point Editor launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def import_ascii_points(file_path: str) -> str:
    """Import survey points from an ASCII file (CSV, PNEZD, etc.).

    Opens the MicroSurvey ASCII import dialog.

    Args:
        file_path: Path to the ASCII point file.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand(f'_ascii_in\n"{file_path}"\n')
        return f"ASCII Points import command sent for: {file_path}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def export_ascii_points(file_path: str) -> str:
    """Export survey points to an ASCII file.

    Opens the MicroSurvey ASCII export dialog.

    Args:
        file_path: Destination file path.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand(f'_ascii_out\n"{file_path}"\n')
        return f"ASCII Points export command sent for: {file_path}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def import_landxml(file_path: str) -> str:
    """Import data from a LandXML file.

    Args:
        file_path: Path to the LandXML (.xml) file.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand(f'_landxml_in\n"{file_path}"\n')
        return f"LandXML import command sent for: {file_path}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def export_landxml(file_path: str) -> str:
    """Export data to a LandXML file.

    Args:
        file_path: Destination LandXML (.xml) file path.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand(f'_landxml_out\n"{file_path}"\n')
        return f"LandXML export command sent for: {file_path}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def renumber_points() -> str:
    """Open the Renumber Points dialog in MSCAD.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_ms_start_renumber\n")
        return "Renumber Points dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def refresh_drawing_from_database() -> str:
    """Update the drawing display from the coordinate database.

    Refreshes all point symbols, numbers, and descriptions on screen.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_MS_REFRESH\n")
        return "Drawing refreshed from database"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def update_database_from_drawing() -> str:
    """Scan the drawing and update the coordinate database.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_ms_update_db\n")
        return "Database update from drawing command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def point_groups() -> str:
    """Open the Point Groups manager in MSCAD.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_PTGROUPS\n")
        return "Point Groups manager launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def coordinate_listing() -> str:
    """Generate a coordinate listing report.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_coord_report\n")
        return "Coordinate Listing report command sent"
    except Exception as e:
        return f"Error: {e}"
