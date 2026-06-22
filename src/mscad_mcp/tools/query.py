"""Entity query tools — enumerate and inspect drawing entities."""

from mscad_mcp.server import mcp
from mscad_mcp import connection


def _entity_type_name(entity) -> str:
    """Get a readable type name for a CAD entity."""
    try:
        return entity.EntityName
    except Exception:
        pass
    try:
        return entity.ObjectName
    except Exception:
        pass
    return "Unknown"


def _get_color_index(entity) -> int | None:
    """Get the ACI color index from an entity or layer."""
    try:
        return entity.Color.ColorIndex
    except Exception:
        return None


def _entity_to_dict(entity) -> dict:
    """Convert an entity to a summary dict."""
    info = {}
    try:
        info["handle"] = entity.Handle
    except Exception:
        pass
    info["type"] = _entity_type_name(entity)
    try:
        info["layer"] = entity.Layer
    except Exception:
        pass
    info["color_index"] = _get_color_index(entity)
    return info


def _point_to_dict(pt) -> dict | None:
    """Convert a COM Point object to a dict."""
    try:
        return {"x": pt.x, "y": pt.y, "z": pt.z}
    except Exception:
        return None


def _entity_detail(entity) -> dict:
    """Get detailed properties for an entity."""
    info = _entity_to_dict(entity)

    for attr, key in [
        ("StartPoint", "start_point"),
        ("EndPoint", "end_point"),
        ("Center", "center"),
        ("InsertionPoint", "insertion_point"),
    ]:
        try:
            val = getattr(entity, attr)
            converted = _point_to_dict(val)
            if converted:
                info[key] = converted
        except Exception:
            pass

    for attr, key in [
        ("Radius", "radius"),
        ("Length", "length"),
        ("Area", "area"),
        ("Rotation", "rotation"),
        ("TextString", "text"),
        ("Height", "height"),
        ("Closed", "closed"),
        ("Linetype", "linetype"),
        ("Lineweight", "lineweight"),
        ("Visible", "visible"),
        ("StartAngle", "start_angle"),
        ("EndAngle", "end_angle"),
        ("Angle", "angle"),
        ("EntityType", "entity_type_id"),
        ("ObjectName", "object_name"),
    ]:
        try:
            info[key] = getattr(entity, attr)
        except Exception:
            pass

    return info


@mcp.tool()
def get_entities(
    entity_type: str | None = None,
    layer: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """List entities in the active drawing's ModelSpace.

    Args:
        entity_type: Filter by type name (e.g. 'Line', 'Circle', 'Text', 'Arc', 'LWPolyline').
                     Case-insensitive partial match. Returns all types if omitted.
        layer: Filter by layer name. Returns all layers if omitted.
        limit: Maximum number of entities to return (default 100).

    Returns:
        List of entity summary dicts with handle, type, layer, color_index.
    """
    try:
        ms = connection.get_model_space()
        results = []
        count = ms.Count

        for i in range(count):
            if len(results) >= limit:
                break
            try:
                entity = ms.Item(i)
                etype = _entity_type_name(entity)

                if entity_type and entity_type.lower() not in etype.lower():
                    continue

                if layer:
                    try:
                        if entity.Layer.lower() != layer.lower():
                            continue
                    except Exception:
                        continue

                results.append(_entity_to_dict(entity))
            except Exception:
                continue

        return results
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_entity_properties(handle: str) -> dict:
    """Get detailed properties of a specific entity by its handle.

    Args:
        handle: The entity handle string (from get_entities or draw_* tools).

    Returns:
        Dict with all available properties for the entity.
    """
    try:
        doc = connection.get_document()
        entity = doc.HandleToObject(handle)
        return _entity_detail(entity)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def count_entities(layer: str | None = None) -> dict:
    """Count entities in ModelSpace, optionally filtered by layer.

    Args:
        layer: Count only entities on this layer. Counts all if omitted.

    Returns:
        Dict with total count and per-type breakdown.
    """
    try:
        ms = connection.get_model_space()
        total = 0
        by_type: dict[str, int] = {}
        count = ms.Count

        for i in range(count):
            try:
                entity = ms.Item(i)
                if layer:
                    try:
                        if entity.Layer.lower() != layer.lower():
                            continue
                    except Exception:
                        continue
                etype = _entity_type_name(entity)
                by_type[etype] = by_type.get(etype, 0) + 1
                total += 1
            except Exception:
                continue

        return {"total": total, "by_type": by_type}
    except Exception as e:
        return {"error": str(e)}
