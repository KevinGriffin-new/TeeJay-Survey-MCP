"""View control tools — zoom and pan."""

from mscad_mcp.server import mcp
from mscad_mcp import connection


@mcp.tool()
def zoom_extents() -> str:
    """Zoom to fit all entities in the drawing.

    Returns:
        Status message.
    """
    try:
        app = connection.get_app()
        app.ZoomExtents()
        return "Zoomed to extents"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def zoom_all() -> str:
    """Zoom to show the full drawing limits.

    Returns:
        Status message.
    """
    try:
        app = connection.get_app()
        app.ZoomAll()
        return "Zoomed to all"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def zoom_window(
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
) -> str:
    """Zoom to a rectangular window.

    Args:
        min_x: Lower-left X coordinate.
        min_y: Lower-left Y coordinate.
        max_x: Upper-right X coordinate.
        max_y: Upper-right Y coordinate.

    Returns:
        Status message.
    """
    try:
        app = connection.get_app()
        p1 = app.CreatePointInterface(min_x, min_y, 0.0)
        p2 = app.CreatePointInterface(max_x, max_y, 0.0)
        app.ZoomWindow(p1, p2)
        return f"Zoomed to window ({min_x},{min_y}) - ({max_x},{max_y})"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def zoom_center(
    x: float,
    y: float,
    magnification: float = 1.0,
) -> str:
    """Zoom centered on a point with a magnification factor.

    Args:
        x: Center X coordinate.
        y: Center Y coordinate.
        magnification: Magnification factor (>1 zooms in, <1 zooms out).

    Returns:
        Status message.
    """
    try:
        app = connection.get_app()
        center = app.CreatePointInterface(x, y, 0.0)
        app.ZoomCenter(center, magnification)
        return f"Zoomed to center ({x},{y}) magnification {magnification}"
    except Exception as e:
        return f"Error: {e}"
