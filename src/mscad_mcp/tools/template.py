"""Template, configuration, and border tools.

Handles saving DWT templates, CFG configuration files, creating
new drawings from templates, and drawing standard paper borders.

DWT files are standard DWG files with a .dwt extension.
CFG files are binary (incad.cfg) — we copy them as-is.

Paper sizes (ANSI):
  A = 216 x 279 mm  (8.5 x 11")
  B = 279 x 432 mm  (11 x 17")
  C = 432 x 559 mm  (17 x 22")
"""

import os
import shutil
from pathlib import Path

from mscad_mcp.server import mcp
from mscad_mcp import connection


# ============================================================
# CONSTANTS
# ============================================================

_PAPER_SIZES = {
    "A": (216, 279),
    "B": (279, 432),
    "C": (432, 559),
}

_CONFIG_DIR_PATTERN = Path(os.environ.get("APPDATA", "")) / "MicroSurvey" / "MSCAD"


def _get_config_dir(version: str | None = None) -> Path:
    """Get MicroSurvey config directory for a version."""
    if version:
        d = _CONFIG_DIR_PATTERN / version
        if d.exists():
            return d
        raise FileNotFoundError(f"Config dir not found for MSCAD {version}")
    # Find latest
    if _CONFIG_DIR_PATTERN.exists():
        dirs = sorted(d for d in _CONFIG_DIR_PATTERN.iterdir() if d.is_dir())
        if dirs:
            return dirs[-1]
    raise FileNotFoundError("No MicroSurvey config directory found")


# ============================================================
# MCP TOOLS
# ============================================================

@mcp.tool()
def save_as_template(
    file_path: str,
) -> dict:
    """Save the active drawing as a DWT template file.

    DWT files are standard DWG files with a .dwt extension. The
    template will include all layers, styles, blocks, and settings
    from the current drawing.

    Args:
        file_path: Full path for the .dwt file to save.

    Returns:
        Dict with save status and file path.
    """
    try:
        doc = connection.get_document()
        path = Path(file_path)

        # Ensure .dwt extension
        if path.suffix.lower() != ".dwt":
            path = path.with_suffix(".dwt")

        # Try direct SaveAs
        try:
            doc.SaveAs(str(path))
            return {
                "status": "ok",
                "file_path": str(path),
                "size_bytes": path.stat().st_size if path.exists() else None,
            }
        except Exception as save_err:
            # Fallback: save as DWG then copy to DWT
            dwg_path = path.with_suffix(".dwg")
            doc.SaveAs(str(dwg_path))
            shutil.copy2(str(dwg_path), str(path))
            return {
                "status": "ok",
                "file_path": str(path),
                "method": "dwg_copy_fallback",
                "size_bytes": path.stat().st_size if path.exists() else None,
            }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def create_from_template(
    template_path: str,
    new_path: str | None = None,
) -> dict:
    """Create a new drawing from a DWT template.

    Opens the template file and optionally saves it as a new DWG.

    Args:
        template_path: Path to the .dwt template file.
        new_path: Path for the new .dwg file. If omitted, just opens
                  the template as the active document.

    Returns:
        Dict with the new drawing name and path.
    """
    try:
        app = connection.get_app()
        doc = app.Documents.Open(template_path)

        result = {
            "status": "ok",
            "template": template_path,
            "drawing_name": doc.Name,
        }

        if new_path:
            doc.SaveAs(new_path)
            result["saved_as"] = new_path

        return result

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def save_configuration(
    dest_path: str,
    version: str | None = None,
) -> dict:
    """Save MicroSurvey configuration files to a target directory.

    Copies the current config files (incad.cfg, config.json, X99.dat)
    to the specified directory. The incad.cfg is the binary CFG file
    that the lab assignment requires saving as GEOM2031.CFG.

    Args:
        dest_path: Directory to copy configuration files into.
        version: MSCAD version year. Latest if omitted.

    Returns:
        Dict listing all copied files with sizes.
    """
    try:
        config_dir = _get_config_dir(version)
        dest = Path(dest_path)
        dest.mkdir(parents=True, exist_ok=True)

        copied = []
        for filename in ["incad.cfg", "config.json", "X99.dat"]:
            src = config_dir / filename
            if src.exists():
                dst = dest / filename
                shutil.copy2(str(src), str(dst))
                copied.append({
                    "file": filename,
                    "source": str(src),
                    "destination": str(dst),
                    "size_bytes": dst.stat().st_size,
                })

        return {
            "status": "ok",
            "config_dir": str(config_dir),
            "dest_dir": str(dest),
            "files_copied": copied,
        }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def create_border(
    paper_size: str,
    orientation: str = "portrait",
    x: float = 0.0,
    y: float = 0.0,
    scale: int = 1000,
    layer: str = "BORDER",
) -> dict:
    """Draw a standard paper size border rectangle.

    Creates a border rectangle on the specified layer at the given
    position. Border dimensions are computed from the paper size and
    scale (at 1:1000, A-portrait = 216m x 279m in model space).

    Args:
        paper_size: "A" (8.5x11"), "B" (11x17"), or "C" (17x22").
        orientation: "portrait" or "landscape".
        x: X coordinate of bottom-left corner.
        y: Y coordinate of bottom-left corner.
        scale: Drawing scale denominator (e.g. 1000 for 1:1000).
        layer: Layer name for the border lines (default "BORDER").

    Returns:
        Dict with border dimensions and corner coordinates.
    """
    try:
        size = paper_size.upper()
        if size not in _PAPER_SIZES:
            return {"error": f"Unknown paper size '{paper_size}'. Use A, B, or C."}

        w_mm, h_mm = _PAPER_SIZES[size]

        if orientation.lower() == "landscape":
            w_mm, h_mm = h_mm, w_mm

        # At 1:scale, model units = mm * (scale / 1000)
        # For 1:1000 metric (1 unit = 1m), model = mm
        w = w_mm * scale / 1000
        h = h_mm * scale / 1000

        app = connection.get_app()
        ms = connection.get_model_space()

        # Draw 4 border lines
        corners = [
            (x, y),
            (x + w, y),
            (x + w, y + h),
            (x, y + h),
        ]

        for i in range(4):
            p1 = corners[i]
            p2 = corners[(i + 1) % 4]
            pt1 = app.CreatePointInterface(p1[0], p1[1], 0.0)
            pt2 = app.CreatePointInterface(p2[0], p2[1], 0.0)
            line = ms.AddLine(pt1, pt2)
            line.Layer = layer

        return {
            "status": "ok",
            "paper_size": size,
            "orientation": orientation.lower(),
            "scale": f"1:{scale}",
            "width": w,
            "height": h,
            "position": {"x": x, "y": y},
            "corners": {
                "bl": corners[0],
                "br": corners[1],
                "tr": corners[2],
                "tl": corners[3],
            },
        }

    except Exception as e:
        return {"error": str(e)}
