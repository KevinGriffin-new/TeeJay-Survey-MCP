"""Surface and TIN tools — create TIN, contours, volume calculations."""

from mscad_mcp.server import mcp
from mscad_mcp import connection


@mcp.tool()
def create_tin() -> str:
    """Create a Triangulated Irregular Network (TIN) surface.

    Opens the TIN creation dialog in MSCAD. Select points or objects
    to include in the triangulation.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_TIN\n")
        return "TIN creation command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def generate_contours() -> str:
    """Generate contour lines from the current surface.

    Opens the contour generation dialog in MSCAD.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_CONT\n")
        return "Contour generation command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_contour_interval() -> str:
    """Open the contour interval settings dialog.

    Configure major and minor contour intervals, smoothing, etc.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_cont_interval\n")
        return "Contour Interval settings dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def contour_color_settings() -> str:
    """Open the contour color settings dialog.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("(contcolr_dialog)\n")
        return "Contour Color Settings dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def edit_tin_edges() -> str:
    """Edit TIN triangle edges (flip, add, remove edges).

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_TINEDGE\n")
        return "TIN Edge editing command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def surface_operations() -> str:
    """Open the Surface Operations dialog.

    Perform surface modifications, merging, and processing.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_DSOP\n")
        return "Surface Operations dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def calculate_volumes() -> str:
    """Calculate cut/fill volumes between two surfaces (SVOL).

    Opens the Surface Volumes dialog where you select existing ground
    and design surfaces to compute earthwork volumes.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_SVOL\n")
        return "Surface Volumes calculation command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def extract_to_surface() -> str:
    """Extract existing ground to create a surface from drawing entities.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_QSX\n")
        return "Extract to Surface command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def extract_break_lines() -> str:
    """Extract break lines from survey data for surface modeling.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_QSBX\n")
        return "Extract Break Lines command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def surface_region() -> str:
    """Define a surface region boundary.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_QSREGION\n")
        return "Surface Region command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def surface_area() -> str:
    """Calculate the 3D surface area of the current TIN.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_sarea\n")
        return "Surface Area calculation command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def surface_view_3d() -> str:
    """Switch to a 3D view of the surface.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_SVIEW\n")
        return "Surface 3D View command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def surface_plan_view() -> str:
    """Switch to plan (top-down) view of the surface.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_SPLAN\n")
        return "Surface Plan View command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def surface_zoom() -> str:
    """Zoom to the surface extents.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_SZOOM\n")
        return "Surface Zoom command sent"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def surface_colors() -> str:
    """Open the surface color/shading settings dialog.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_PAINT\n")
        return "Surface Colors Settings dialog launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def scale_elevations() -> str:
    """Scale Z values (elevations) of surface data.

    Opens a dialog to apply a scale factor to all elevations.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_SCALEZ\n")
        return "Scale Z command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"
