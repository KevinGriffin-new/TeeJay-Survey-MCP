"""Coordinate transformation tools — Helmert, rotate, scale, shift."""

from mscad_mcp.server import mcp
from mscad_mcp import connection


@mcp.tool()
def helmert_transformation() -> str:
    """Run Helmert's Transformation (Least Squares).

    Opens the Helmert transformation dialog where you match known
    control points between two coordinate systems.  The transformation
    computes best-fit translation, rotation, and scale.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_ms_helmert\n")
        return "Helmert Transformation dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def rotate_points() -> str:
    """Rotate survey points around a base point.

    Opens the Rotate Points dialog in MSCAD.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_MS_ROTATEP\n")
        return "Rotate Points dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def scale_points() -> str:
    """Scale survey points relative to a base point.

    Opens the Scale Points dialog in MSCAD.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_MS_SCALEP\n")
        return "Scale Points dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def shift_points() -> str:
    """Shift (translate) survey points by a delta N/E/Z.

    Opens the Shift Points dialog in MSCAD.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_MS_SHIFTP\n")
        return "Shift Points dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def transform_database() -> str:
    """Transform the entire point database between coordinate systems.

    Opens the Transform Database dialog where you can apply a
    predefined coordinate system transformation to all stored points.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_transform_coordinates\n")
        return "Transform Database dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def manual_coordinate_conversion() -> str:
    """Open the Manual Coordinate Conversions dialog.

    Convert individual coordinate values between different
    coordinate systems (e.g. geographic ↔ projected).

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_ll_transform_coordinates\n")
        return "Manual Coordinate Conversions dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def coordinate_system_search() -> str:
    """Search for a coordinate system / datum / projection.

    Opens the Coordinate System Search dialog to find and select
    a coordinate reference system by name, code, or region.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_MS_CSSEARCH\n")
        return "Coordinate System Search dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_coordinate_system() -> str:
    """Set the project coordinate system.

    Opens the Coordinate System settings dialog to assign a
    coordinate reference system to the current project.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_ms_coordsys\n")
        return "Coordinate System settings dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def geoid_model_settings() -> str:
    """Open the Geoid Model settings.

    Configure the geoid undulation model used for
    ellipsoid-to-orthometric height conversions.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_ms_geoid\n")
        return "Geoid Model settings dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def combined_scale_factor() -> str:
    """Open the Combined Scale Factor settings.

    Configure grid-to-ground scale factor for distance adjustments.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_ms_csf\n")
        return "Combined Scale Factor settings launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"
