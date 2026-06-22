"""Entity creation tools — draw lines, arcs, circles, polylines, text, points, blocks."""

import pythoncom
import win32com.client

from mscad_mcp.server import mcp
from mscad_mcp import connection


def _make_point(app, x: float, y: float, z: float = 0.0):
    """Create an IntelliCAD Point object."""
    return app.CreatePointInterface(x, y, z)


def _set_entity_layer(entity, layer: str | None):
    """Set the layer on an entity if specified."""
    if layer is not None:
        try:
            entity.Layer = layer
        except Exception:
            pass


def _entity_result(entity, entity_type: str) -> dict:
    """Build a standard result dict for a created entity."""
    result = {"type": entity_type}
    try:
        result["handle"] = entity.Handle
    except Exception:
        pass
    try:
        result["layer"] = entity.Layer
    except Exception:
        pass
    return result


@mcp.tool()
def draw_line(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    start_z: float = 0.0,
    end_z: float = 0.0,
    layer: str | None = None,
) -> dict:
    """Draw a line between two points.

    Args:
        start_x: Start X coordinate.
        start_y: Start Y coordinate.
        end_x: End X coordinate.
        end_y: End Y coordinate.
        start_z: Start Z coordinate (default 0).
        end_z: End Z coordinate (default 0).
        layer: Layer name. Uses current layer if omitted.

    Returns:
        Dict with entity handle and type.
    """
    try:
        app = connection.get_app()
        ms = connection.get_model_space()
        p1 = _make_point(app, start_x, start_y, start_z)
        p2 = _make_point(app, end_x, end_y, end_z)
        line = ms.AddLine(p1, p2)
        _set_entity_layer(line, layer)
        return _entity_result(line, "Line")
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def draw_circle(
    center_x: float,
    center_y: float,
    radius: float,
    center_z: float = 0.0,
    layer: str | None = None,
) -> dict:
    """Draw a circle.

    Args:
        center_x: Center X coordinate.
        center_y: Center Y coordinate.
        radius: Circle radius.
        center_z: Center Z coordinate (default 0).
        layer: Layer name.

    Returns:
        Dict with entity handle and type.
    """
    try:
        app = connection.get_app()
        ms = connection.get_model_space()
        center = _make_point(app, center_x, center_y, center_z)
        circle = ms.AddCircle(center, radius)
        _set_entity_layer(circle, layer)
        return _entity_result(circle, "Circle")
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def draw_arc(
    center_x: float,
    center_y: float,
    radius: float,
    start_angle: float,
    end_angle: float,
    center_z: float = 0.0,
    layer: str | None = None,
) -> dict:
    """Draw an arc.

    Args:
        center_x: Center X coordinate.
        center_y: Center Y coordinate.
        radius: Arc radius.
        start_angle: Start angle in degrees (0 = East, counter-clockwise).
        end_angle: End angle in degrees.
        center_z: Center Z coordinate (default 0).
        layer: Layer name.

    Returns:
        Dict with entity handle and type.
    """
    import math

    try:
        app = connection.get_app()
        ms = connection.get_model_space()
        center = _make_point(app, center_x, center_y, center_z)
        arc = ms.AddArc(
            center,
            radius,
            math.radians(start_angle),
            math.radians(end_angle),
        )
        _set_entity_layer(arc, layer)
        return _entity_result(arc, "Arc")
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def draw_polyline(
    points: list[dict],
    closed: bool = False,
    layer: str | None = None,
) -> dict:
    """Draw a lightweight polyline through a list of points.

    Args:
        points: List of point dicts with 'x', 'y', and optional 'z' keys.
                Example: [{"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 10}]
        closed: Whether to close the polyline. Default False.
        layer: Layer name.

    Returns:
        Dict with entity handle and type.
    """
    try:
        if not points or len(points) < 2:
            return {"error": "draw_polyline needs at least 2 points"}

        # AddLightWeightPolyline takes a SAFEARRAY of doubles, which cannot be
        # marshaled through the bridge's late-bound IDispatch (no typelib) —
        # every win32com array form raises "Python instance can not be
        # converted to a COM object". Script the PLINE command with text
        # coordinates instead: no array marshaling, and it yields a genuine
        # AcDbPolyline whose .Area MicroSurvey computes. (LWPolyline is 2D, so
        # any 'z' on the input points is ignored, as before.)
        coord_lines = "\n".join(
            f"{float(pt['x'])},{float(pt['y'])}" for pt in points
        )
        suffix = "C\n" if closed else "\n"  # 'C' closes; bare Enter ends an open pline
        cmd = f"_PLINE\n{coord_lines}\n{suffix}"

        doc = connection.get_document()
        ms = doc.ModelSpace
        before = ms.Count
        doc.SendCommand(cmd)
        if ms.Count <= before:
            return {"error": "polyline not created (PLINE produced no entity)"}

        pline = ms.Item(ms.Count - 1)
        _set_entity_layer(pline, layer)
        return _entity_result(pline, "LWPolyline")
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def draw_text(
    text: str,
    x: float,
    y: float,
    height: float,
    rotation: float = 0.0,
    z: float = 0.0,
    layer: str | None = None,
    style: str | None = None,
) -> dict:
    """Draw single-line text.

    Args:
        text: The text string to display.
        x: Insertion point X.
        y: Insertion point Y.
        height: Text height in drawing units.
        rotation: Rotation angle in degrees (default 0).
        z: Insertion point Z (default 0).
        layer: Layer name.
        style: Text style name.

    Returns:
        Dict with entity handle and type.
    """
    try:
        app = connection.get_app()
        ms = connection.get_model_space()
        pt = _make_point(app, x, y, z)
        txt = ms.AddText(text, pt, height)
        if rotation != 0.0:
            import math
            txt.Rotation = math.radians(rotation)
        if style is not None:
            try:
                txt.StyleName = style
            except Exception:
                pass
        _set_entity_layer(txt, layer)
        return _entity_result(txt, "Text")
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def draw_point(
    x: float,
    y: float,
    z: float = 0.0,
    layer: str | None = None,
) -> dict:
    """Draw a point entity.

    Args:
        x: X coordinate.
        y: Y coordinate.
        z: Z coordinate (default 0).
        layer: Layer name.

    Returns:
        Dict with entity handle and type.
    """
    try:
        app = connection.get_app()
        ms = connection.get_model_space()
        pt = _make_point(app, x, y, z)
        point = ms.AddPointEntity(pt)
        _set_entity_layer(point, layer)
        return _entity_result(point, "Point")
    except Exception as e:
        return {"error": str(e)}


def _draw_batch_impl(entities: list, default_layer: str | None = None,
                     max_handles: int = 50) -> dict:
    """Shared implementation for draw_batch (also callable without MCP)."""
    import math

    app = connection.get_app()
    doc = connection.get_document()
    ms = doc.ModelSpace
    created = 0
    by_type: dict = {}
    errors = []
    handles = []
    # pre-create referenced layers so entity.Layer assignment never fails
    want_layers = {e.get("layer") or default_layer
                   for e in entities if (e.get("layer") or default_layer)}
    for lname in want_layers:
        try:
            doc.Layers.Add(lname)
        except Exception:
            pass
    for i, e in enumerate(entities):
        try:
            et = (e.get("type") or "").lower()
            layer = e.get("layer") or default_layer
            ent = None
            if et == "line":
                ent = ms.AddLine(
                    _make_point(app, e["x1"], e["y1"], e.get("z1", 0.0)),
                    _make_point(app, e["x2"], e["y2"], e.get("z2", 0.0)))
            elif et == "circle":
                ent = ms.AddCircle(
                    _make_point(app, e["cx"], e["cy"], e.get("cz", 0.0)),
                    e["radius"])
            elif et == "arc":
                ent = ms.AddArc(
                    _make_point(app, e["cx"], e["cy"], e.get("cz", 0.0)),
                    e["radius"],
                    math.radians(e["start_angle"]),
                    math.radians(e["end_angle"]))
            elif et == "text":
                ent = ms.AddText(
                    e["text"],
                    _make_point(app, e["x"], e["y"], e.get("z", 0.0)),
                    e["height"])
                if e.get("rotation"):
                    ent.Rotation = math.radians(e["rotation"])
            elif et == "point":
                ent = ms.AddPointEntity(
                    _make_point(app, e["x"], e["y"], e.get("z", 0.0)))
            elif et == "polyline":
                pts = e["points"]
                if len(pts) < 2:
                    raise ValueError("polyline needs >= 2 points")
                coord_lines = "\n".join(
                    f"{float(p['x'])},{float(p['y'])}" for p in pts)
                suffix = "C\n" if e.get("closed") else "\n"
                before = ms.Count
                doc.SendCommand(f"_PLINE\n{coord_lines}\n{suffix}")
                if ms.Count <= before:
                    raise RuntimeError("PLINE produced no entity")
                ent = ms.Item(ms.Count - 1)
            else:
                raise ValueError(f"unknown entity type {et!r}")
            _set_entity_layer(ent, layer)
            created += 1
            by_type[et] = by_type.get(et, 0) + 1
            if len(handles) < max_handles:
                try:
                    handles.append(ent.Handle)
                except Exception:
                    pass
        except Exception as ex:
            errors.append({"index": i, "error": str(ex)})
    return {"created": created, "by_type": by_type,
            "errors": errors[:20], "n_errors": len(errors),
            "handles": handles}


@mcp.tool()
def draw_batch(
    entities: list[dict],
    default_layer: str | None = None,
) -> dict:
    """Draw many entities in ONE call — lines, polylines, arcs, circles,
    text, points. The batch analogue of the individual draw_* tools; use it
    to emit an extracted plan (or any scripted geometry) without one MCP
    round-trip per entity. Layers named by the entities are created
    automatically.

    Args:
        entities: List of entity dicts. Each needs "type" plus:
            line:     x1, y1, x2, y2 [, z1, z2]
            circle:   cx, cy, radius [, cz]
            arc:      cx, cy, radius, start_angle, end_angle (deg, 0=E, CCW)
            text:     text, x, y, height [, rotation deg]
            point:    x, y [, z]
            polyline: points=[{x, y}, ...] [, closed]
            All accept "layer".
        default_layer: Layer for entities that don't name one.

    Returns:
        {created, by_type, errors (first 20), n_errors, handles (first 50)}.
    """
    try:
        return _draw_batch_impl(entities, default_layer)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def insert_block(
    block_name: str,
    x: float,
    y: float,
    x_scale: float = 1.0,
    y_scale: float = 1.0,
    rotation: float = 0.0,
    z: float = 0.0,
    layer: str | None = None,
) -> dict:
    """Insert a block reference.

    Args:
        block_name: Name of the block definition.
        x: Insertion point X.
        y: Insertion point Y.
        x_scale: X scale factor (default 1).
        y_scale: Y scale factor (default 1).
        rotation: Rotation in degrees (default 0).
        z: Insertion point Z (default 0).
        layer: Layer name.

    Returns:
        Dict with entity handle and type.
    """
    import math

    try:
        app = connection.get_app()
        ms = connection.get_model_space()
        pt = _make_point(app, x, y, z)
        blk = ms.InsertBlock(pt, block_name, x_scale, y_scale, 1.0, math.radians(rotation))
        _set_entity_layer(blk, layer)
        return _entity_result(blk, "BlockInsert")
    except Exception as e:
        return {"error": str(e)}
