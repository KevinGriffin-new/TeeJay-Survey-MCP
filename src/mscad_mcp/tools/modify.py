"""Entity modification tools — modify, delete, move entities."""

from mscad_mcp.server import mcp
from mscad_mcp import connection


@mcp.tool()
def modify_entity(
    handle: str,
    layer: str | None = None,
    color: int | None = None,
    linetype: str | None = None,
) -> str:
    """Modify properties of an existing entity.

    Args:
        handle: Entity handle string.
        layer: New layer name.
        color: New ACI color number (0=ByBlock, 1-255, 256=ByLayer).
        linetype: New linetype name.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        entity = doc.HandleToObject(handle)
        changes = []
        if layer is not None:
            entity.Layer = layer
            changes.append(f"layer={layer}")
        if color is not None:
            try:
                entity.Color.ColorIndex = color
            except Exception:
                # Fallback: use CHPROP command
                doc.SendCommand(f"(entmod (subst (cons 62 {color}) (assoc 62 (entget (handent \"{handle}\"))) (entget (handent \"{handle}\"))))\n")
            changes.append(f"color={color}")
        if linetype is not None:
            entity.Linetype = linetype
            changes.append(f"linetype={linetype}")
        try:
            entity.Update()
        except Exception:
            pass
        return f"Entity {handle} modified: {', '.join(changes)}" if changes else f"No changes to entity {handle}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def delete_entity(handle: str) -> str:
    """Delete an entity from the drawing.

    Args:
        handle: Entity handle string.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        entity = doc.HandleToObject(handle)
        entity.Delete()
        return f"Entity {handle} deleted"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def move_entity(
    handle: str,
    dx: float = 0.0,
    dy: float = 0.0,
    dz: float = 0.0,
) -> str:
    """Move (translate) an entity by a displacement vector.

    Args:
        handle: Entity handle string.
        dx: X displacement.
        dy: Y displacement.
        dz: Z displacement (default 0).

    Returns:
        Status message.
    """
    try:
        app = connection.get_app()
        doc = connection.get_document()
        entity = doc.HandleToObject(handle)
        from_pt = app.CreatePointInterface(0.0, 0.0, 0.0)
        to_pt = app.CreatePointInterface(dx, dy, dz)
        entity.Move(from_pt, to_pt)
        try:
            entity.Update()
        except Exception:
            pass
        return f"Entity {handle} moved by ({dx}, {dy}, {dz})"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def copy_entity(
    handle: str,
    dx: float = 0.0,
    dy: float = 0.0,
    dz: float = 0.0,
) -> dict:
    """Copy an entity with a displacement offset.

    Args:
        handle: Entity handle string.
        dx: X displacement for the copy.
        dy: Y displacement for the copy.
        dz: Z displacement for the copy (default 0).

    Returns:
        Dict with the new entity's handle.
    """
    try:
        app = connection.get_app()
        doc = connection.get_document()
        entity = doc.HandleToObject(handle)
        copied = entity.Copy()
        from_pt = app.CreatePointInterface(0.0, 0.0, 0.0)
        to_pt = app.CreatePointInterface(dx, dy, dz)
        copied.Move(from_pt, to_pt)
        try:
            copied.Update()
        except Exception:
            pass
        result = {"type": "copy"}
        try:
            result["handle"] = copied.Handle
        except Exception:
            pass
        return result
    except Exception as e:
        return {"error": str(e)}
