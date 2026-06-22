"""COGO (Coordinate Geometry) tools — inverse, bearing-distance, intersection, area.

Pure computation tools return results directly. MSCAD command tools
send commands to the CAD for operations that require the drawing engine.

Interactive COGO tools (cogo_ms_bearing_distance, cogo_ms_bearing_distance_batch)
drive MicroSurvey's native _MS_COGO command via SendCommand, which stores computed
points in the coordinate database and auto-draws bearing/distance labels.

Entmake LISP tools generate AutoLISP entmake calls for direct entity creation.
This is the most reliable method for programmatic drawing — no dialogs, no prompts,
fully deterministic. Generated LISP can be reviewed, edited, saved to .lsp files,
or executed from Emacs.
"""

import math
import logging
import os
import threading

from mscad_mcp.server import mcp
from mscad_mcp import connection

log = logging.getLogger(__name__)


def _dms_from_decimal(decimal_degrees: float) -> str:
    """Convert decimal degrees to D°MM'SS.ss\" format."""
    d = int(decimal_degrees)
    m_full = (decimal_degrees - d) * 60
    m = int(m_full)
    s = (m_full - m) * 60
    return f"{d}°{m:02d}'{s:05.2f}\""


def _bearing_str(azimuth_deg: float) -> str:
    """Convert azimuth (0-360) to quadrant bearing string (e.g. N45°30'00\"E)."""
    az = azimuth_deg % 360
    if az <= 90:
        return f"N{_dms_from_decimal(az)}E"
    elif az <= 180:
        return f"S{_dms_from_decimal(180 - az)}E"
    elif az <= 270:
        return f"S{_dms_from_decimal(az - 180)}W"
    else:
        return f"N{_dms_from_decimal(360 - az)}W"


def _dddmmss_to_decimal(dddmmss: float) -> float:
    """Convert MicroSurvey DDD.MMSS bearing format to decimal degrees.

    Example: 180.0711 → 180 + 07/60 + 11/3600 = 180.11972...
    """
    sign = 1 if dddmmss >= 0 else -1
    val = abs(dddmmss)
    d = int(val)
    remainder = round((val - d) * 100, 6)
    mm = int(remainder)
    ss = round((remainder - mm) * 100, 4)
    return sign * (d + mm / 60.0 + ss / 3600.0)


def _compute_label_pick(
    from_e: float,
    from_n: float,
    azimuth_dddmmss: float,
    distance: float,
    side: str = "left",
) -> tuple[float, float]:
    """Compute a coordinate for the COGO label side pick.

    Returns a point offset perpendicular to the line midpoint, on the
    specified side of the direction of travel. The exact position doesn't
    matter — MicroSurvey just uses it to decide which side to place the
    bearing/distance label.

    Args:
        from_e: Easting of the from-point.
        from_n: Northing of the from-point.
        azimuth_dddmmss: Azimuth in DDD.MMSS format.
        distance: Horizontal distance.
        side: "left" or "right" of the direction of travel.

    Returns:
        (easting, northing) tuple for the label pick coordinate.
    """
    az_dec = _dddmmss_to_decimal(azimuth_dddmmss)
    az_rad = math.radians(az_dec)

    # Compute to-point
    to_e = from_e + distance * math.sin(az_rad)
    to_n = from_n + distance * math.cos(az_rad)

    # Midpoint of the line
    mid_e = (from_e + to_e) / 2.0
    mid_n = (from_n + to_n) / 2.0

    # Perpendicular offset (5 units) — left = counterclockwise from azimuth
    if side == "left":
        perp_rad = az_rad - math.pi / 2
    else:
        perp_rad = az_rad + math.pi / 2

    pick_e = mid_e + 5.0 * math.sin(perp_rad)
    pick_n = mid_n + 5.0 * math.cos(perp_rad)
    return (round(pick_e, 3), round(pick_n, 3))


def _run_sendcommand_with_timeout(doc, cmd_str: str, timeout_s: float = 30) -> dict:
    """Execute doc.SendCommand() in a thread with timeout detection.

    SendCommand is synchronous and blocks until the command finishes.
    If a dialog pops up or the command hangs, this avoids freezing the
    MCP server.

    Returns:
        {"ok": True/False, "blocked": True/False, "error": str|None}
    """
    result = {"ok": False, "blocked": False, "error": None}

    def _run():
        try:
            doc.SendCommand(cmd_str)
            result["ok"] = True
        except Exception as e:
            result["error"] = str(e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout_s)

    if t.is_alive():
        result["blocked"] = True
        log.warning("SendCommand blocked after %.1fs: %s...", timeout_s, cmd_str[:80])
    return result


# ---------------------------------------------------------------------------
# Pure computation tools (return results, no MSCAD dependency)
# ---------------------------------------------------------------------------

@mcp.tool()
def cogo_inverse(
    from_x: float,
    from_y: float,
    to_x: float,
    to_y: float,
    from_z: float | None = None,
    to_z: float | None = None,
) -> dict:
    """Compute the bearing and distance between two points (2-point inverse).

    This is a pure computation — does not require MSCAD.

    Args:
        from_x: Easting of the from-point.
        from_y: Northing of the from-point.
        to_x: Easting of the to-point.
        to_y: Northing of the to-point.
        from_z: Elevation of from-point (for slope distance).
        to_z: Elevation of to-point (for slope distance).

    Returns:
        Dict with azimuth, bearing, horizontal_distance, delta_x, delta_y,
        and optionally slope_distance, delta_z, vertical_angle.
    """
    dx = to_x - from_x
    dy = to_y - from_y
    horiz_dist = math.hypot(dx, dy)

    # Azimuth from north, clockwise
    if horiz_dist < 1e-10:
        azimuth = 0.0
    else:
        azimuth = math.degrees(math.atan2(dx, dy)) % 360

    result = {
        "azimuth_degrees": round(azimuth, 6),
        "bearing": _bearing_str(azimuth),
        "horizontal_distance": round(horiz_dist, 4),
        "delta_x": round(dx, 4),
        "delta_y": round(dy, 4),
    }

    if from_z is not None and to_z is not None:
        dz = to_z - from_z
        slope_dist = math.sqrt(dx**2 + dy**2 + dz**2)
        vert_angle = math.degrees(math.atan2(dz, horiz_dist)) if horiz_dist > 1e-10 else (90.0 if dz > 0 else -90.0)
        result["delta_z"] = round(dz, 4)
        result["slope_distance"] = round(slope_dist, 4)
        result["vertical_angle_degrees"] = round(vert_angle, 6)

    return result


@mcp.tool()
def cogo_bearing_distance(
    from_x: float,
    from_y: float,
    azimuth_degrees: float,
    distance: float,
    from_z: float | None = None,
    vertical_angle: float | None = None,
) -> dict:
    """Compute a new point from a starting point, bearing, and distance.

    Args:
        from_x: Easting of the starting point.
        from_y: Northing of the starting point.
        azimuth_degrees: Azimuth from north, clockwise (0-360).
        distance: Horizontal distance.
        from_z: Starting elevation (optional).
        vertical_angle: Vertical angle in degrees (optional, for 3D).

    Returns:
        Dict with computed x, y, and optionally z coordinates.
    """
    az_rad = math.radians(azimuth_degrees)
    dx = distance * math.sin(az_rad)
    dy = distance * math.cos(az_rad)
    result = {
        "x": round(from_x + dx, 4),
        "y": round(from_y + dy, 4),
    }
    if from_z is not None and vertical_angle is not None:
        dz = distance * math.tan(math.radians(vertical_angle))
        result["z"] = round(from_z + dz, 4)
    elif from_z is not None:
        result["z"] = from_z
    return result


@mcp.tool()
def cogo_intersection(
    pt1_x: float,
    pt1_y: float,
    azimuth1: float,
    pt2_x: float,
    pt2_y: float,
    azimuth2: float,
) -> dict:
    """Compute the intersection of two bearing lines (bearing-bearing intersection).

    Args:
        pt1_x: Easting of first point.
        pt1_y: Northing of first point.
        azimuth1: Azimuth from first point (degrees, from north clockwise).
        pt2_x: Easting of second point.
        pt2_y: Northing of second point.
        azimuth2: Azimuth from second point (degrees, from north clockwise).

    Returns:
        Dict with intersection x, y and distances from each point.
    """
    az1 = math.radians(azimuth1)
    az2 = math.radians(azimuth2)

    sin1, cos1 = math.sin(az1), math.cos(az1)
    sin2, cos2 = math.sin(az2), math.cos(az2)

    denom = sin1 * cos2 - sin2 * cos1
    if abs(denom) < 1e-10:
        return {"error": "Lines are parallel or nearly parallel — no intersection."}

    dx = pt2_x - pt1_x
    dy = pt2_y - pt1_y

    t = (dx * cos2 - dy * sin2) / denom

    ix = pt1_x + t * sin1
    iy = pt1_y + t * cos1

    dist1 = math.hypot(ix - pt1_x, iy - pt1_y)
    dist2 = math.hypot(ix - pt2_x, iy - pt2_y)

    return {
        "x": round(ix, 4),
        "y": round(iy, 4),
        "distance_from_pt1": round(dist1, 4),
        "distance_from_pt2": round(dist2, 4),
    }


@mcp.tool()
def cogo_distance_distance_intersection(
    pt1_x: float,
    pt1_y: float,
    distance1: float,
    pt2_x: float,
    pt2_y: float,
    distance2: float,
) -> dict:
    """Compute the intersection of two circles (distance-distance intersection).

    Returns both solutions (left and right of the line from pt1 to pt2).

    Args:
        pt1_x: Easting of first point.
        pt1_y: Northing of first point.
        distance1: Distance (radius) from first point.
        pt2_x: Easting of second point.
        pt2_y: Northing of second point.
        distance2: Distance (radius) from second point.

    Returns:
        Dict with two intersection points (solution_1 and solution_2).
    """
    dx = pt2_x - pt1_x
    dy = pt2_y - pt1_y
    d = math.hypot(dx, dy)

    if d > distance1 + distance2:
        return {"error": "Circles do not intersect — points too far apart."}
    if d < abs(distance1 - distance2):
        return {"error": "One circle contains the other — no intersection."}
    if d < 1e-10:
        return {"error": "Points are coincident."}

    a = (distance1**2 - distance2**2 + d**2) / (2 * d)
    h = math.sqrt(max(0, distance1**2 - a**2))

    mx = pt1_x + a * dx / d
    my = pt1_y + a * dy / d

    ix1 = mx + h * dy / d
    iy1 = my - h * dx / d
    ix2 = mx - h * dy / d
    iy2 = my + h * dx / d

    return {
        "solution_1": {"x": round(ix1, 4), "y": round(iy1, 4)},
        "solution_2": {"x": round(ix2, 4), "y": round(iy2, 4)},
    }


@mcp.tool()
def cogo_area(
    points: list[dict],
) -> dict:
    """Compute the area and perimeter of a polygon defined by coordinate points.

    Uses the Shoelace formula. Points should be in order (CW or CCW).

    Args:
        points: List of point dicts with 'x' and 'y' keys, in polygon order.
                Example: [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 80}, {"x": 0, "y": 80}]

    Returns:
        Dict with area (always positive), perimeter, and point count.
    """
    n = len(points)
    if n < 3:
        return {"error": "Need at least 3 points to compute area."}

    # Shoelace formula
    area = 0.0
    perimeter = 0.0
    for i in range(n):
        x1, y1 = points[i]["x"], points[i]["y"]
        x2, y2 = points[(i + 1) % n]["x"], points[(i + 1) % n]["y"]
        area += x1 * y2 - x2 * y1
        perimeter += math.hypot(x2 - x1, y2 - y1)

    area = abs(area) / 2.0

    return {
        "area_sq_units": round(area, 4),
        "area_acres": round(area / 43560, 6),
        "area_hectares": round(area / 107639.104, 6),
        "perimeter": round(perimeter, 4),
        "point_count": n,
    }


@mcp.tool()
def cogo_three_point_angle(
    backsight_x: float,
    backsight_y: float,
    occupied_x: float,
    occupied_y: float,
    foresight_x: float,
    foresight_y: float,
) -> dict:
    """Compute the angle at the occupied point between backsight and foresight (3-point inverse).

    Args:
        backsight_x: Easting of backsight point.
        backsight_y: Northing of backsight point.
        occupied_x: Easting of occupied (vertex) point.
        occupied_y: Northing of occupied (vertex) point.
        foresight_x: Easting of foresight point.
        foresight_y: Northing of foresight point.

    Returns:
        Dict with turned angle (clockwise from backsight to foresight),
        interior angle, azimuths to backsight and foresight.
    """
    # Azimuth to backsight
    dx_bs = backsight_x - occupied_x
    dy_bs = backsight_y - occupied_y
    az_bs = math.degrees(math.atan2(dx_bs, dy_bs)) % 360

    # Azimuth to foresight
    dx_fs = foresight_x - occupied_x
    dy_fs = foresight_y - occupied_y
    az_fs = math.degrees(math.atan2(dx_fs, dy_fs)) % 360

    # Turned angle (clockwise from backsight to foresight)
    turned = (az_fs - az_bs) % 360

    return {
        "turned_angle_degrees": round(turned, 6),
        "turned_angle_dms": _dms_from_decimal(turned),
        "azimuth_to_backsight": round(az_bs, 6),
        "azimuth_to_foresight": round(az_fs, 6),
        "bearing_to_backsight": _bearing_str(az_bs),
        "bearing_to_foresight": _bearing_str(az_fs),
        "distance_to_backsight": round(math.hypot(dx_bs, dy_bs), 4),
        "distance_to_foresight": round(math.hypot(dx_fs, dy_fs), 4),
    }


# ---------------------------------------------------------------------------
# MSCAD COGO command wrappers (send commands to the running CAD)
# ---------------------------------------------------------------------------

@mcp.tool()
def cogo_ms_inverse() -> str:
    """Launch the MicroSurvey 2-Point Inverse dialog in MSCAD.

    This opens the interactive inverse command which reads from the
    coordinate database.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_inverse\n")
        return "2-Point Inverse command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def cogo_ms_radial_inverse() -> str:
    """Launch the MicroSurvey Radial Inverse dialog in MSCAD.

    Computes inverse from one point to multiple points.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_radial_inverse\n")
        return "Radial Inverse command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def cogo_ms_curve() -> str:
    """Launch the MicroSurvey COGO Curve Calculations dialog.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_MS_CURVE\n")
        return "COGO Curve Calculations command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def cogo_ms_area_by_points() -> str:
    """Launch the MicroSurvey area calculation by point numbers.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_areas\n")
        return "Area by Point Numbers command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def cogo_ms_fast_area() -> str:
    """Launch the MicroSurvey Fast Area command (select objects to compute area).

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_fastarea\n")
        return "Fast Area command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def cogo_ms_lines_by_inversing() -> str:
    """Launch Lines by Inversing (dot-to-dot connect points).

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand("_connect_points\n")
        return "Lines by Inversing command launched in MSCAD"
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Interactive COGO tools — drive _MS_COGO via SendCommand
# ---------------------------------------------------------------------------

@mcp.tool()
def cogo_ms_bearing_distance(
    from_point: int,
    azimuth_dddmmss: float,
    distance: float,
    solve_point: int,
    from_easting: float,
    from_northing: float,
    description: str = "",
    label_side: str = "left",
) -> dict:
    """Compute a new survey point using MicroSurvey's native COGO bearing-distance.

    Drives the _MS_COGO interactive command via SendCommand. This:
    - Stores the computed point in the MicroSurvey coordinate database
    - Draws the line, point marker, and bearing/distance labels automatically
    - Uses the project's configured label styles

    The from_point must already exist in the coordinate database (stored via
    store_point or a previous COGO computation). The tool returns the computed
    coordinates of the new point so subsequent calls can chain.

    Args:
        from_point: Point number to start from (must exist in database).
        azimuth_dddmmss: Azimuth in DDD.MMSS format (e.g. 180.0711 = 180 deg 07' 11").
        distance: Horizontal distance.
        solve_point: Point number to assign to the computed point.
        from_easting: Easting (X) of the from-point (needed to compute label placement).
        from_northing: Northing (Y) of the from-point (needed to compute label placement).
        description: Optional point description (default: blank).
        label_side: Side for bearing/distance label placement relative to direction
                    of travel: "left" or "right" (default: "left").

    Returns:
        Dict with status, computed coordinates, and entity count.
        The computed_easting and computed_northing can be used as from_easting
        and from_northing in the next call to chain COGO legs.
    """
    try:
        doc = connection.get_document()
        ms = doc.ModelSpace
        count_before = ms.Count

        # Pre-compute the to-point coordinates (for return value and label pick)
        az_dec = _dddmmss_to_decimal(azimuth_dddmmss)
        az_rad = math.radians(az_dec)
        to_e = round(from_easting + distance * math.sin(az_rad), 4)
        to_n = round(from_northing + distance * math.cos(az_rad), 4)

        # Compute label placement coordinate
        pick_e, pick_n = _compute_label_pick(
            from_easting, from_northing,
            azimuth_dddmmss, distance, label_side
        )

        # Build the COGO SendCommand string
        # Sequence: _MS_COGO → from_pt → azimuth → distance → solve_pt →
        #           description → label_pick → blank (exit)
        cmd = (
            f"_MS_COGO\n"
            f"{from_point}\n"
            f"{azimuth_dddmmss}\n"
            f"{distance}\n"
            f"{solve_point}\n"
            f"{description}\n"
            f"{pick_e},{pick_n}\n"
            f"\n"
        )

        log.info(
            "COGO BD: pt%d → pt%d  Az=%s  D=%.4f  pick=(%s,%s)",
            from_point, solve_point, azimuth_dddmmss, distance, pick_e, pick_n
        )

        result = _run_sendcommand_with_timeout(doc, cmd, timeout_s=30)

        count_after = ms.Count
        new_entities = count_after - count_before

        return {
            "status": "ok" if new_entities > 0 else ("blocked" if result["blocked"] else "no_entities"),
            "solve_point": solve_point,
            "computed_easting": to_e,
            "computed_northing": to_n,
            "azimuth_dddmmss": azimuth_dddmmss,
            "distance": distance,
            "bearing": _bearing_str(az_dec),
            "new_entity_count": new_entities,
            "from_point": from_point,
            "note": "Use computed_easting/computed_northing as from_easting/from_northing for the next leg.",
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def cogo_ms_bearing_distance_batch(
    legs: list[dict],
    seed_easting: float,
    seed_northing: float,
    label_side: str = "left",
) -> dict:
    """Execute multiple COGO bearing-distance legs in a single _MS_COGO session.

    Much more efficient than calling cogo_ms_bearing_distance() per leg, because
    all legs run in one COGO session without restarting the command.

    The seed_easting/seed_northing are the coordinates of the first from-point.
    For chained legs (where each leg's from_point is the previous leg's solve_point),
    coordinates are tracked automatically. For non-chained legs, provide
    from_easting/from_northing in the leg dict.

    Each leg dict requires:
        from_point (int): Point number to start from.
        azimuth (float): Azimuth in DDD.MMSS format.
        distance (float): Horizontal distance.
        solve_point (int): Point number for the computed point.

    Optional leg dict keys:
        description (str): Point description (default: blank).
        label_side (str): Override label side for this leg.
        from_easting (float): Override from-point easting (for non-chained legs).
        from_northing (float): Override from-point northing (for non-chained legs).

    Args:
        legs: List of leg dicts defining the COGO operations.
        seed_easting: Easting (X) of the first from-point.
        seed_northing: Northing (Y) of the first from-point.
        label_side: Default label side for all legs ("left" or "right").

    Returns:
        Dict with list of computed points, total entities created, and status.
    """
    try:
        doc = connection.get_document()
        ms = doc.ModelSpace
        count_before = ms.Count

        # Track coordinates for chaining: point_number → (easting, northing)
        known_coords = {}

        # The first from-point's coordinates come from seed
        if legs:
            known_coords[legs[0]["from_point"]] = (seed_easting, seed_northing)

        # Build the full SendCommand string for all legs
        cmd_parts = ["_MS_COGO\n"]
        computed_points = []

        for i, leg in enumerate(legs):
            from_pt = leg["from_point"]
            azimuth = leg["azimuth"]
            dist = leg["distance"]
            solve_pt = leg["solve_point"]
            desc = leg.get("description", "")
            side = leg.get("label_side", label_side)

            # Get from-point coordinates (explicit override or tracked)
            from_e = leg.get("from_easting", known_coords.get(from_pt, (None, None))[0])
            from_n = leg.get("from_northing", known_coords.get(from_pt, (None, None))[1])

            if from_e is None or from_n is None:
                return {
                    "status": "error",
                    "error": f"Leg {i}: No coordinates for from_point {from_pt}. "
                             f"Provide from_easting/from_northing in the leg dict, or ensure "
                             f"a previous leg computed this point.",
                    "computed_points": computed_points,
                }

            # Pre-compute the to-point
            az_dec = _dddmmss_to_decimal(azimuth)
            az_rad = math.radians(az_dec)
            to_e = round(from_e + dist * math.sin(az_rad), 4)
            to_n = round(from_n + dist * math.cos(az_rad), 4)

            # Store for future legs that might chain from this point
            known_coords[solve_pt] = (to_e, to_n)

            # Compute label placement
            pick_e, pick_n = _compute_label_pick(from_e, from_n, azimuth, dist, side)

            # Append to command string
            cmd_parts.append(
                f"{from_pt}\n"
                f"{azimuth}\n"
                f"{dist}\n"
                f"{solve_pt}\n"
                f"{desc}\n"
                f"{pick_e},{pick_n}\n"
            )

            computed_points.append({
                "point_number": solve_pt,
                "easting": to_e,
                "northing": to_n,
                "from_point": from_pt,
                "azimuth_dddmmss": azimuth,
                "bearing": _bearing_str(az_dec),
                "distance": dist,
                "description": desc,
            })

        # Blank from-point to exit COGO
        cmd_parts.append("\n")

        full_cmd = "".join(cmd_parts)
        log.info("COGO batch: %d legs, cmd length=%d", len(legs), len(full_cmd))

        # Execute with generous timeout (more legs = more time)
        timeout = max(30, len(legs) * 10)
        result = _run_sendcommand_with_timeout(doc, full_cmd, timeout_s=timeout)

        count_after = ms.Count
        new_entities = count_after - count_before

        return {
            "status": "ok" if new_entities > 0 else ("blocked" if result["blocked"] else "no_entities"),
            "legs_submitted": len(legs),
            "computed_points": computed_points,
            "new_entity_count": new_entities,
            "note": "Points are stored in the MicroSurvey coordinate database with labels drawn.",
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Entmake LISP helpers and tools — direct entity creation via AutoLISP
# ---------------------------------------------------------------------------

def _survey_to_math_angle(bearing_deg: float) -> float:
    """Convert a surveying azimuth (from North, clockwise) to a math angle (from +X, CCW).

    Surveying:  0=North, 90=East, 180=South, 270=West (clockwise)
    Math/DXF:   0=East, 90=North, 180=West, 270=South (counter-clockwise)

    Returns angle in radians.
    """
    math_deg = (90.0 - bearing_deg) % 360.0
    return math.radians(math_deg)


def _entmake_line_lisp(
    x1: float, y1: float, x2: float, y2: float, layer: str, color: int | None = None
) -> str:
    """Generate LISP entmake expression for a LINE entity."""
    parts = [
        f"'(0 . \"LINE\")",
        f"'(8 . \"{layer}\")",
    ]
    if color is not None:
        parts.append(f"'(62 . {color})")
    parts.append(f"(cons 10 '({x1:.4f} {y1:.4f} 0.0))")
    parts.append(f"(cons 11 '({x2:.4f} {y2:.4f} 0.0))")
    return f"(entmake (list {' '.join(parts)}))"


def _entmake_arc_lisp(
    cx: float, cy: float, radius: float,
    start_rad: float, end_rad: float, layer: str, color: int | None = None
) -> str:
    """Generate LISP entmake expression for an ARC entity.

    Angles are in radians, math convention (from +X axis, counter-clockwise).
    """
    parts = [
        f"'(0 . \"ARC\")",
        f"'(8 . \"{layer}\")",
    ]
    if color is not None:
        parts.append(f"'(62 . {color})")
    parts.append(f"(cons 10 '({cx:.4f} {cy:.4f} 0.0))")
    parts.append(f"(cons 40 {radius:.4f})")
    parts.append(f"(cons 50 {start_rad:.6f})")
    parts.append(f"(cons 51 {end_rad:.6f})")
    return f"(entmake (list {' '.join(parts)}))"


def _entmake_circle_lisp(
    cx: float, cy: float, radius: float, layer: str, color: int | None = None
) -> str:
    """Generate LISP entmake expression for a CIRCLE entity."""
    parts = [
        f"'(0 . \"CIRCLE\")",
        f"'(8 . \"{layer}\")",
    ]
    if color is not None:
        parts.append(f"'(62 . {color})")
    parts.append(f"(cons 10 '({cx:.4f} {cy:.4f} 0.0))")
    parts.append(f"(cons 40 {radius:.4f})")
    return f"(entmake (list {' '.join(parts)}))"


def _entmake_point_lisp(
    x: float, y: float, layer: str, color: int | None = None
) -> str:
    """Generate LISP entmake expression for a POINT entity."""
    parts = [
        f"'(0 . \"POINT\")",
        f"'(8 . \"{layer}\")",
    ]
    if color is not None:
        parts.append(f"'(62 . {color})")
    parts.append(f"(cons 10 '({x:.4f} {y:.4f} 0.0))")
    return f"(entmake (list {' '.join(parts)}))"


def _dms_for_lisp(decimal_degrees: float) -> str:
    """Convert decimal degrees to D%%dMM'SS\" format for LISP text strings.

    Uses %%d instead of the degree symbol to avoid encoding issues in AutoLISP.
    """
    d = int(decimal_degrees)
    m_full = (decimal_degrees - d) * 60
    m = int(m_full)
    s = (m_full - m) * 60
    return f"{d}%%d{m:02d}'{s:05.2f}\""


def _bearing_str_lisp(azimuth_deg: float) -> str:
    """Convert azimuth (0-360) to quadrant bearing string for LISP text.

    Uses %%d for the degree symbol. E.g. N45%%d30'00.00\"E
    """
    az = azimuth_deg % 360
    if az <= 90:
        return f"N{_dms_for_lisp(az)}E"
    elif az <= 180:
        return f"S{_dms_for_lisp(180 - az)}E"
    elif az <= 270:
        return f"S{_dms_for_lisp(az - 180)}W"
    else:
        return f"N{_dms_for_lisp(360 - az)}W"


def _entmake_text_lisp(
    x: float, y: float, height: float, text: str,
    rotation_rad: float = 0.0, layer: str = "0",
    color: int | None = None, justify: str = "MC",
    style: str = "",
) -> str:
    """Generate LISP entmake expression for a TEXT entity.

    Args:
        x, y: Insertion/alignment point.
        height: Text height in drawing units.
        text: Text content string.
        rotation_rad: Text rotation in radians (0 = horizontal/east).
        layer: Layer name.
        color: ACI color index (optional).
        justify: Justification code. Common values:
            "L"  = Left (baseline), "C" = Center (baseline),
            "R"  = Right (baseline), "ML" = Middle-Left,
            "MC" = Middle-Center, "MR" = Middle-Right,
            "TL" = Top-Left, "TC" = Top-Center, "TR" = Top-Right.
            Default "MC" (middle-center) is best for annotations.
        style: Text style name (DXF group 7). E.g. "BEARING4", "DISTANCE3",
               "POINTNUMBER". If empty, uses the drawing's current text style.
               Set this to match MsAnnotate conventions from GEOM2031.cfg.
    """
    # Map justification to DXF group 72 (horizontal) and 73 (vertical)
    hjust_map = {"L": 0, "C": 1, "R": 2}
    vjust_map = {"": 0, "B": 1, "M": 2, "T": 3}  # baseline, bottom, middle, top

    if len(justify) == 1:
        h_code = hjust_map.get(justify, 0)
        v_code = 0  # baseline
    elif len(justify) == 2:
        v_code = vjust_map.get(justify[0], 0)
        h_code = hjust_map.get(justify[1], 0)
    else:
        h_code, v_code = 1, 2  # default MC

    # Escape any backslashes and quotes in text for LISP
    safe_text = text.replace("\\", "\\\\").replace('"', '\\"')

    parts = [
        f"'(0 . \"TEXT\")",
        f"'(8 . \"{layer}\")",
    ]
    if style:
        parts.append(f"'(7 . \"{style}\")")
    if color is not None:
        parts.append(f"'(62 . {color})")

    # For justified text (anything but left-baseline), use group 11 as alignment point
    if h_code == 0 and v_code == 0:
        # Left-baseline: use group 10 as insertion point
        parts.append(f"(cons 10 '({x:.4f} {y:.4f} 0.0))")
    else:
        # Justified: group 10 is required but ignored; group 11 is alignment point
        parts.append(f"(cons 10 '(0.0 0.0 0.0))")
        parts.append(f"(cons 11 '({x:.4f} {y:.4f} 0.0))")
        parts.append(f"'(72 . {h_code})")
        parts.append(f"'(73 . {v_code})")

    parts.append(f"(cons 40 {height:.4f})")
    parts.append(f"(cons 1 \"{safe_text}\")")

    if abs(rotation_rad) > 1e-6:
        parts.append(f"(cons 50 {rotation_rad:.6f})")

    return f"(entmake (list {' '.join(parts)}))"


@mcp.tool()
def cogo_line_annotation(
    x1: float, y1: float, x2: float, y2: float,
    offset: float = 3.0,
    side: str = "left",
    bearing_style: str = "BEARING4",
    bearing_height: float = 2.0,
    bearing_layer: str = "BEARING4",
    distance_style: str = "DISTANCE3",
    distance_height: float = 2.0,
    distance_layer: str = "DISTANCE3",
    distance_decimals: int = 3,
) -> dict:
    """Compute bearing, distance, and annotation placement for a survey line.

    Given two endpoints, computes the survey bearing, horizontal distance,
    label text, and optimal placement position for annotation text.

    The annotation is placed at the midpoint of the line, offset to one side,
    and rotated to align with the line. Text is always oriented to be readable
    (not upside-down).

    Default styles, heights, and layers match the MsAnnotate settings from
    GEOM2031.cfg (BEARING4 at height 2.0, DISTANCE3 at height 2.0, using
    MSURVEY.SHX font on their respective layers).

    Args:
        x1, y1: Start point (easting, northing).
        x2, y2: End point (easting, northing).
        offset: Perpendicular offset from line to text center (drawing units).
                Default 3.0 works well with height-2.0 text.
        side: "left" or "right" of travel direction for text placement.
        bearing_style: Text style for bearing label (from .cfg). Default "BEARING4".
        bearing_height: Text height for bearing. Default 2.0 (from GEOM2031.cfg).
        bearing_layer: Layer for bearing text. Default "BEARING4".
        distance_style: Text style for distance label. Default "DISTANCE3".
        distance_height: Text height for distance. Default 2.0 (from GEOM2031.cfg).
        distance_layer: Layer for distance text. Default "DISTANCE3".
        distance_decimals: Decimal places for distance. Default 3 (e.g. "36.000").

    Returns:
        Dict with bearing_text, distance_text, annotation placement data
        including style, layer, height for direct use with cogo_entmake_draw().
    """
    dx = x2 - x1
    dy = y2 - y1
    distance = math.sqrt(dx * dx + dy * dy)

    # Compute azimuth (from North, clockwise)
    azimuth_rad = math.atan2(dx, dy)  # atan2(dE, dN) = azimuth from North
    azimuth_deg = math.degrees(azimuth_rad) % 360

    # Bearing string for LISP text (uses %%d for degree symbol)
    bearing_text = _bearing_str_lisp(azimuth_deg)
    distance_text = f"{distance:.{distance_decimals}f}"

    # Midpoint
    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2

    # Text rotation: align with line, but keep readable (not upside-down)
    # Math angle of the line direction
    line_angle_rad = math.atan2(dy, dx)  # standard math angle
    line_angle_deg = math.degrees(line_angle_rad) % 360

    # Keep text readable: if angle would make text upside-down, flip 180
    text_angle_deg = line_angle_deg
    if 90 < text_angle_deg <= 270:
        text_angle_deg = (text_angle_deg + 180) % 360
    text_angle_rad = math.radians(text_angle_deg)

    # Offset perpendicular to line for text placement
    # Perpendicular direction (left = CCW from travel direction)
    if side == "left":
        perp_rad = line_angle_rad + math.pi / 2
    else:
        perp_rad = line_angle_rad - math.pi / 2

    # Bearing text position (offset to side)
    brg_x = mid_x + offset * math.cos(perp_rad)
    brg_y = mid_y + offset * math.sin(perp_rad)

    # Distance text position (offset to opposite side)
    dist_x = mid_x - offset * math.cos(perp_rad)
    dist_y = mid_y - offset * math.sin(perp_rad)

    return {
        "azimuth_deg": round(azimuth_deg, 6),
        "bearing_text": bearing_text,
        "bearing_text_unicode": _bearing_str(azimuth_deg),
        "distance": round(distance, 4),
        "distance_text": distance_text,
        "bearing_annotation": {
            "x": round(brg_x, 4),
            "y": round(brg_y, 4),
            "rotation_rad": round(text_angle_rad, 6),
            "text": bearing_text,
            "height": bearing_height,
            "style": bearing_style,
            "layer": bearing_layer,
        },
        "distance_annotation": {
            "x": round(dist_x, 4),
            "y": round(dist_y, 4),
            "rotation_rad": round(text_angle_rad, 6),
            "text": distance_text,
            "height": distance_height,
            "style": distance_style,
            "layer": distance_layer,
        },
    }


@mcp.tool()
def cogo_point_marker(
    x: float, y: float,
    point_number: int | None = None,
    description: str = "",
    marker_size: float = 0.3,
    number_height: float = 1.5,
    number_style: str = "POINTNUMBER",
    desc_height: float = 1.5,
    desc_style: str = "DESCRIPTION",
    text_offset: float = 1.0,
    layer: str = "MSPOINT",
    number_layer: str = "POINTNUMBER",
    desc_layer: str = "DESCRIPTION",
) -> list[dict]:
    """Generate entity dicts for a survey point marker with label.

    Creates a small circle marker, optional crosshair lines, point number text,
    and optional description text. Returns a list of entity dicts suitable for
    passing directly to cogo_entmake_draw().

    Default styles, heights, and layers match MsAnnotate conventions from
    GEOM2031.cfg (POINTNUMBER at 1.5, DESCRIPTION at 1.5, MSURVEY.SHX font).

    Args:
        x, y: Point coordinates (easting, northing).
        point_number: Point number to display. If None, no number label.
        description: Point description text. If empty, no description label.
        marker_size: Radius of the marker circle (drawing units).
        number_height: Text height for point number. Default 1.5 (from .cfg).
        number_style: Text style for point number. Default "POINTNUMBER".
        desc_height: Text height for description. Default 1.5 (from .cfg).
        desc_style: Text style for description. Default "DESCRIPTION".
        text_offset: Offset from marker center to text.
        layer: Layer for the marker symbol. Default "MSPOINT" (MicroSurvey standard).
        number_layer: Layer for point number text. Default "POINTNUMBER".
        desc_layer: Layer for description text. Default "DESCRIPTION".

    Returns:
        List of entity dicts (CIRCLE, LINE, TEXT) for use with cogo_entmake_draw().
    """
    entities = []

    # Marker circle
    entities.append({
        "type": "CIRCLE", "layer": layer,
        "center": [x, y], "radius": marker_size,
    })

    # Crosshair lines (small + inside the circle)
    cr = marker_size * 0.7
    entities.append({
        "type": "LINE", "layer": layer,
        "start": [x - cr, y], "end": [x + cr, y],
    })
    entities.append({
        "type": "LINE", "layer": layer,
        "start": [x, y - cr], "end": [x, y + cr],
    })

    # Point number label (upper-right of marker)
    if point_number is not None:
        entities.append({
            "type": "TEXT", "layer": number_layer,
            "position": [x + text_offset, y + text_offset],
            "height": number_height,
            "text": str(point_number),
            "style": number_style,
            "justify": "L",  # left-baseline, standard for point numbers
        })

    # Description label (below point number)
    if description:
        entities.append({
            "type": "TEXT", "layer": desc_layer,
            "position": [x + text_offset, y - text_offset],
            "height": desc_height,
            "text": description,
            "style": desc_style,
            "justify": "L",
        })

    return entities


@mcp.tool()
def cogo_arc_from_survey(
    center_x: float,
    center_y: float,
    radius: float,
    start_x: float,
    start_y: float,
    arc_length: float,
    direction: str = "ccw",
) -> dict:
    """Compute arc parameters for entmake from survey-style inputs.

    Given the center, radius, a known start point on the arc, and an arc length,
    computes the start/end angles in math convention (radians, CCW from +X)
    and the end point coordinates.

    This bridges between survey plan data (which gives arc lengths) and the
    DXF/entmake format (which needs angles in radians).

    Args:
        center_x: Easting of arc center.
        center_y: Northing of arc center.
        radius: Arc radius.
        start_x: Easting of the start point on the arc.
        start_y: Northing of the start point on the arc.
        arc_length: Arc length along the curve.
        direction: "ccw" (counter-clockwise) or "cw" (clockwise) sweep direction.

    Returns:
        Dict with start_angle_rad, end_angle_rad (math convention),
        end_x, end_y, and included_angle_deg.
    """
    # Start angle: math convention (from +X, CCW)
    dx = start_x - center_x
    dy = start_y - center_y
    start_angle = math.atan2(dy, dx)  # Already in math convention

    # Included angle from arc length: theta = arc_length / radius
    theta = arc_length / radius

    if direction == "ccw":
        end_angle = start_angle + theta
    else:
        end_angle = start_angle - theta

    # Normalize to [0, 2*pi)
    start_norm = start_angle % (2 * math.pi)
    end_norm = end_angle % (2 * math.pi)

    # Compute end point
    end_x = center_x + radius * math.cos(end_angle)
    end_y = center_y + radius * math.sin(end_angle)

    return {
        "start_angle_rad": round(start_norm, 6),
        "end_angle_rad": round(end_norm, 6),
        "start_angle_deg": round(math.degrees(start_norm), 6),
        "end_angle_deg": round(math.degrees(end_norm), 6),
        "included_angle_deg": round(math.degrees(theta), 6),
        "end_x": round(end_x, 4),
        "end_y": round(end_y, 4),
        "direction": direction,
    }


@mcp.tool()
def cogo_entmake_draw(
    entities: list[dict],
    save_lisp_path: str = "",
    execute: bool = True,
) -> dict:
    """Draw survey geometry using LISP entmake -- the most reliable method.

    Creates lines and arcs directly via AutoLISP entmake calls. No dialogs,
    no prompts, fully deterministic. Supports mixed layers in one call.

    Each entity dict must have a "type" key ("LINE", "ARC", "TEXT", "CIRCLE", or "POINT") plus:

    LINE entity:
        {"type": "LINE", "layer": "Boundary",
         "start": [x, y], "end": [x, y]}

    ARC entity:
        {"type": "ARC", "layer": "Boundary",
         "center": [x, y], "radius": r,
         "start_angle": angle_rad, "end_angle": angle_rad}

    TEXT entity:
        {"type": "TEXT", "layer": "BEARING4",
         "position": [x, y], "height": 2.0, "text": "N45%%d30'00\"E",
         "rotation": angle_rad, "justify": "MC", "style": "BEARING4"}

    Angles are in radians, math convention (from +X axis, counter-clockwise).
    Use cogo_arc_from_survey() to convert from survey-style arc length inputs.
    Use cogo_line_annotation() to compute bearing/distance annotation placement.

    Optional per-entity: "color" (int, ACI color index).

    Args:
        entities: List of entity dicts to create.
        save_lisp_path: If provided, save the generated LISP to this file path.
                        The file can be loaded in MSCAD, Emacs, or any LISP editor.
        execute: If True (default), execute the LISP in MSCAD immediately.
                 If False, only generate and optionally save -- useful for review.

    Returns:
        Dict with generated LISP code, entity count, file path if saved,
        and execution status.
    """
    lisp_lines = ["; Generated survey geometry -- entmake"]
    lisp_lines.append(f"; {len(entities)} entities")
    lisp_lines.append("")

    errors = []

    for i, ent in enumerate(entities):
        etype = ent.get("type", "").upper()
        layer = ent.get("layer", "0")
        color = ent.get("color", None)

        if etype == "LINE":
            start = ent.get("start")
            end = ent.get("end")
            if not start or not end:
                errors.append(f"Entity {i}: LINE missing start or end")
                continue
            lisp_lines.append(
                _entmake_line_lisp(start[0], start[1], end[0], end[1], layer, color)
            )

        elif etype == "ARC":
            center = ent.get("center")
            radius = ent.get("radius")
            start_a = ent.get("start_angle")
            end_a = ent.get("end_angle")
            if not center or radius is None or start_a is None or end_a is None:
                errors.append(f"Entity {i}: ARC missing center, radius, start_angle, or end_angle")
                continue
            lisp_lines.append(
                _entmake_arc_lisp(
                    center[0], center[1], radius,
                    start_a, end_a, layer, color
                )
            )

        elif etype == "TEXT":
            pos = ent.get("position")
            height = ent.get("height", 2.0)
            text = ent.get("text", "")
            rotation = ent.get("rotation", 0.0)
            justify = ent.get("justify", "MC")
            style = ent.get("style", "")
            if not pos or not text:
                errors.append(f"Entity {i}: TEXT missing position or text")
                continue
            lisp_lines.append(
                _entmake_text_lisp(
                    pos[0], pos[1], height, text,
                    rotation, layer, color, justify, style
                )
            )

        elif etype == "CIRCLE":
            center = ent.get("center")
            radius = ent.get("radius")
            if not center or radius is None:
                errors.append(f"Entity {i}: CIRCLE missing center or radius")
                continue
            lisp_lines.append(
                _entmake_circle_lisp(center[0], center[1], radius, layer, color)
            )

        elif etype == "POINT":
            pos = ent.get("position")
            if not pos:
                errors.append(f"Entity {i}: POINT missing position")
                continue
            lisp_lines.append(
                _entmake_point_lisp(pos[0], pos[1], layer, color)
            )

        else:
            errors.append(f"Entity {i}: Unknown type '{etype}' (use LINE, ARC, TEXT, CIRCLE, POINT)")

    lisp_lines.append("")
    lisp_lines.append("(princ)")

    lisp_code = "\n".join(lisp_lines)

    result = {
        "entities_requested": len(entities),
        "lisp_lines_generated": len([l for l in lisp_lines if l.startswith("(entmake")]),
        "lisp_code": lisp_code,
    }

    if errors:
        result["errors"] = errors

    # Save to file if requested
    if save_lisp_path:
        try:
            with open(save_lisp_path, "w") as f:
                f.write(lisp_code)
            result["saved_to"] = save_lisp_path
        except Exception as e:
            result["save_error"] = str(e)

    # Execute in MSCAD if requested
    if execute:
        try:
            doc = connection.get_document()
            ms = doc.ModelSpace
            count_before = ms.Count

            # Always write to temp file and load — progn is unreliable
            # for multiple entmake calls, but (load ...) works perfectly.
            temp_path = os.path.join(
                os.environ.get("TEMP", "C:\\Temp"),
                "_mscad_mcp_entmake.lsp"
            )
            with open(temp_path, "w") as f:
                f.write(lisp_code)
            load_cmd = f'(load "{temp_path.replace(chr(92), "/")}")\n'
            exec_result = _run_sendcommand_with_timeout(doc, load_cmd, timeout_s=30)

            count_after = ms.Count
            new_ents = count_after - count_before

            result["execution"] = {
                "status": "ok" if new_ents > 0 else "no_entities",
                "new_entity_count": new_ents,
                "blocked": exec_result.get("blocked", False),
            }
            if exec_result.get("error"):
                result["execution"]["error"] = exec_result["error"]

        except Exception as e:
            result["execution"] = {"status": "error", "error": str(e)}
    else:
        result["execution"] = {"status": "skipped", "note": "execute=False, LISP not sent to MSCAD"}

    return result


@mcp.tool()
def cogo_execute_lisp(
    lisp_code: str = "",
    lisp_file: str = "",
) -> dict:
    """Execute AutoLISP code or load a .lsp file in MSCAD.

    Provide either lisp_code (inline LISP string) or lisp_file (path to .lsp file).
    If both are provided, lisp_file takes precedence.

    This is a general-purpose LISP execution tool -- use it for entmake calls,
    custom scripts, or loading files generated by external tools (Emacs, Python, etc.).

    Args:
        lisp_code: Inline LISP code to execute.
        lisp_file: Path to a .lsp file to load and execute.

    Returns:
        Dict with execution status and new entity count.
    """
    if not lisp_code and not lisp_file:
        return {"status": "error", "error": "Provide either lisp_code or lisp_file."}

    try:
        doc = connection.get_document()
        ms = doc.ModelSpace
        count_before = ms.Count

        if lisp_file:
            # Load .lsp file
            load_path = lisp_file.replace("\\", "/")
            cmd = f'(load "{load_path}")\n'
        elif len(lisp_code) > 500:
            # Write to temp file and load
            temp_path = os.path.join(
                os.environ.get("TEMP", "C:\\Temp"),
                "_mscad_mcp_exec.lsp"
            )
            with open(temp_path, "w") as f:
                f.write(lisp_code)
            cmd = f'(load "{temp_path.replace(chr(92), "/")}")\n'
        else:
            cmd = lisp_code if lisp_code.endswith("\n") else lisp_code + "\n"

        exec_result = _run_sendcommand_with_timeout(doc, cmd, timeout_s=30)

        count_after = ms.Count
        new_ents = count_after - count_before

        return {
            "status": "ok" if exec_result["ok"] else ("blocked" if exec_result["blocked"] else "error"),
            "new_entity_count": new_ents,
            "blocked": exec_result.get("blocked", False),
            "error": exec_result.get("error"),
            "source": lisp_file or "inline",
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}
