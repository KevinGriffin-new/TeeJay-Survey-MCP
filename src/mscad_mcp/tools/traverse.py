"""Traverse tools — input, adjustment, listing, import/export."""

from mscad_mcp.server import mcp
from mscad_mcp import connection


@mcp.tool()
def traverse_manual_entry() -> str:
    """Open the Manual Traverse Entry dialog in MSCAD.

    Allows manual data entry of traverse measurements (angles, distances).

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_traverse\n")
        return "Manual Traverse Entry dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_editor() -> str:
    """Open the Active Traverse Editor in MSCAD.

    Edit raw survey data in the active traverse file.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_ms_edit_raw_data\n")
        return "Active Traverse Editor launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_list() -> str:
    """List the current traverse file contents.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_list_traverse\n")
        return "List Traverse command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_report() -> str:
    """Generate a traverse listing report.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_traverse_report\n")
        return "Traverse Report command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_show_graphically() -> str:
    """Show the current traverse graphically on the drawing.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_show_traverse\n")
        return "Show Traverse Graphically command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_compute_closure() -> str:
    """Compute traverse closure (error of closure).

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_calc_closure\n")
        return "Compute Traverse Closure command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_angle_balance() -> str:
    """Balance angles in the current traverse.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_adjust_traverse\n")
        return "Angle Balance command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_adjust_compass() -> str:
    """Adjust traverse using the Compass (Bowditch) method.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("(balance_traverse 1)\n")
        return "Compass Method Adjustment command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_adjust_transit() -> str:
    """Adjust traverse using the Transit method.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("(balance_traverse 0)\n")
        return "Transit Method Adjustment command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_adjust_crandall() -> str:
    """Adjust traverse using Crandall's method.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_crandall_adjustment\n")
        return "Crandall's Method Adjustment command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_adjust_least_squares() -> str:
    """Adjust traverse using Least Squares method.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_least_square\n")
        return "Least Squares Adjustment command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_vertical_adjustment() -> str:
    """Perform vertical traverse adjustment.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_vertical_balance\n")
        return "Vertical Traverse Adjustment command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_recoordinate() -> str:
    """Recompute coordinates for the current traverse.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_ms_coordinate\n")
        return "Recoordinate Traverse command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_set_current_file() -> str:
    """Set the current traverse file for processing.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_set_current_traverse_file\n")
        return "Set Current Traverse File command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_delete_file() -> str:
    """Delete a traverse file.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_delete_traverse\n")
        return "Delete Traverse File command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_existing_point() -> str:
    """Launch Existing Point Traverse computation.

    Computes traverse from existing coordinate database points.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_existing_pt_traverse\n")
        return "Existing Point Traverse command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def traverse_export_rw5() -> str:
    """Export the current traverse in TDS RW5 format.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_export_traverse\n")
        return "Export Traverse (RW5) command sent"
    except Exception as e:
        return f"Error: {e}"
