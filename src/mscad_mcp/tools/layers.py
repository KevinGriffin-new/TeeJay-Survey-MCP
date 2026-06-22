"""Layer management tools."""

from mscad_mcp.server import mcp
from mscad_mcp import connection


def _get_color_index(color_obj) -> int | None:
    """Extract ACI color index from a COM Color object."""
    try:
        return color_obj.ColorIndex
    except Exception:
        return None


@mcp.tool()
def list_layers() -> list[dict]:
    """List all layers in the active drawing with their properties.

    Returns:
        List of dicts with name, on, frozen, locked, color_index, linetype.
    """
    try:
        doc = connection.get_document()
        layers_col = doc.Layers
        result = []
        for i in range(layers_col.Count):
            layer = layers_col.Item(i)
            info = {"name": layer.Name}
            try:
                info["on"] = layer.LayerOn
            except Exception:
                info["on"] = None
            try:
                info["frozen"] = layer.Freeze
            except Exception:
                info["frozen"] = None
            try:
                info["locked"] = layer.Lock
            except Exception:
                info["locked"] = None
            try:
                info["color_index"] = _get_color_index(layer.Color)
            except Exception:
                info["color_index"] = None
            try:
                info["linetype"] = layer.Linetype
            except Exception:
                info["linetype"] = None
            try:
                info["lineweight"] = layer.Lineweight
            except Exception:
                info["lineweight"] = None
            result.append(info)
        return result
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def create_layer(
    name: str,
    color: int = 7,
    linetype: str = "Continuous",
    on: bool = True,
    frozen: bool = False,
    locked: bool = False,
) -> str:
    """Create a new layer in the active drawing.

    Args:
        name: Layer name.
        color: ACI color number (1-255). Default 7 (white/black).
        linetype: Linetype name. Default 'Continuous'.
        on: Whether the layer is visible. Default True.
        frozen: Whether the layer is frozen. Default False.
        locked: Whether the layer is locked. Default False.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        # Create layer via Layers.Add
        layer = doc.Layers.Add(name)
        # Set color via command (direct property assignment doesn't work for Color objects)
        cmd_parts = [f"-LAYER", f"C", str(color), name]
        if not on:
            cmd_parts.extend(["OFF", name])
        if frozen:
            cmd_parts.extend(["F", name])
        if locked:
            cmd_parts.extend(["LO", name])
        cmd_parts.append("")  # terminate
        doc.SendCommand("\n".join(cmd_parts) + "\n")
        try:
            layer.Linetype = linetype
        except Exception:
            pass
        return f"Layer '{name}' created (color={color})"
    except Exception as e:
        return f"Error creating layer: {e}"


@mcp.tool()
def set_active_layer(name: str) -> str:
    """Set the active (current) layer.

    Args:
        name: Name of the layer to make current.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        doc.SendCommand(f"-LAYER\nS\n{name}\n\n")
        return f"Active layer set to '{name}'"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def modify_layer(
    name: str,
    color: int | None = None,
    on: bool | None = None,
    frozen: bool | None = None,
    locked: bool | None = None,
    linetype: str | None = None,
    new_name: str | None = None,
) -> str:
    """Modify properties of an existing layer.

    Args:
        name: Current layer name.
        color: New ACI color number (1-255).
        on: Set layer visibility.
        frozen: Set layer frozen state.
        locked: Set layer locked state.
        linetype: Set linetype name.
        new_name: Rename the layer.

    Returns:
        Status message.
    """
    try:
        doc = connection.get_document()
        changes = []
        cmd_parts = ["-LAYER"]
        if color is not None:
            cmd_parts.extend(["C", str(color), name])
            changes.append(f"color={color}")
        if on is not None:
            cmd_parts.extend(["ON" if on else "OFF", name])
            changes.append(f"on={on}")
        if frozen is not None:
            cmd_parts.extend(["F" if frozen else "T", name])
            changes.append(f"frozen={frozen}")
        if locked is not None:
            cmd_parts.extend(["LO" if locked else "U", name])
            changes.append(f"locked={locked}")
        if linetype is not None:
            cmd_parts.extend(["LT", linetype, name])
            changes.append(f"linetype={linetype}")
        if new_name is not None:
            cmd_parts.extend(["R", name, new_name])
            changes.append(f"renamed to '{new_name}'")
        cmd_parts.append("")
        if changes:
            doc.SendCommand("\n".join(cmd_parts) + "\n")
        return f"Layer '{name}' modified: {', '.join(changes)}" if changes else f"No changes to layer '{name}'"
    except Exception as e:
        return f"Error: {e}"
