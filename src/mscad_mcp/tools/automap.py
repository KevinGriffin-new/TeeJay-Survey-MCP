"""AutoMap library management tools.

MicroSurvey's AutoMap library maps field codes (descriptions) to
symbols, layers, line styles, and connectivity settings. Libraries
are stored as CSV files at:
  C:/ProgramData/MicroSurvey/MSCAD/<version>/mscad/

Default library: mscad.csv
Custom libraries: e.g. MSCAD_2031.CSV

CSV header (20 columns):
  KEY, DESC TEXT, DESC LAYER, SYMBOL, SYM SCALE, SYM LAYER,
  SYM TRIM, MOVE DESC, MOVE NUM, MOVE ELEV, MOVE NODE, CONNECT,
  LINE LAYER, LINE TYPE, COLOR, 2D, LINES, PLINE WIDTH,
  LEGAL DESC, NO SCALE SYMBOL
"""

import csv
import os
import shutil
from pathlib import Path

from mscad_mcp.server import mcp


# ============================================================
# HELPERS
# ============================================================

_HEADER = [
    "KEY", "DESC TEXT", "DESC LAYER", "SYMBOL", "SYM SCALE",
    "SYM LAYER", "SYM TRIM", "MOVE DESC", "MOVE NUM", "MOVE ELEV",
    "MOVE NODE", "CONNECT", "LINE LAYER", "LINE TYPE", "COLOR",
    "2D", "LINES", "PLINE WIDTH", "LEGAL DESC", "NO SCALE SYMBOL",
]


def _default_automap_dir() -> Path:
    """Default AutoMap library directory."""
    return Path(r"C:\ProgramData\MicroSurvey\MSCAD\2024\mscad")


def _resolve_path(library_path: str | None) -> Path:
    """Resolve a library path, defaulting to mscad.csv."""
    if library_path:
        p = Path(library_path)
        if p.exists():
            return p
        # Try as filename in default dir
        p2 = _default_automap_dir() / library_path
        if p2.exists():
            return p2
        raise FileNotFoundError(f"Library not found: {library_path}")
    return _default_automap_dir() / "mscad.csv"


def _read_csv(path: Path) -> list[dict]:
    """Read AutoMap CSV, return list of row dicts."""
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _write_csv(rows: list[dict], path: Path) -> None:
    """Write AutoMap CSV preserving header order."""
    # Determine header from first row or use default
    if rows:
        header = list(rows[0].keys())
    else:
        header = _HEADER

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# MCP TOOLS
# ============================================================

@mcp.tool()
def automap_list(
    library_path: str | None = None,
) -> dict:
    """List all entries in an AutoMap library CSV.

    Returns all field codes (KEYs) with their symbol, layer, and
    connectivity settings.

    Args:
        library_path: Path to CSV file, or filename in default dir.
                      Defaults to "mscad.csv".

    Returns:
        Dict with file path, entry count, and list of entries.
    """
    try:
        path = _resolve_path(library_path)
        rows = _read_csv(path)

        # Return summary for each entry
        entries = []
        for row in rows:
            entries.append({
                "key": row.get("KEY", ""),
                "desc_text": row.get("DESC TEXT", ""),
                "symbol": row.get("SYMBOL", ""),
                "sym_layer": row.get("SYM LAYER", ""),
                "connect": row.get("CONNECT", ""),
                "line_layer": row.get("LINE LAYER", ""),
            })

        return {
            "library_path": str(path),
            "count": len(entries),
            "entries": entries,
        }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def automap_get(
    key: str,
    library_path: str | None = None,
) -> dict:
    """Get a single AutoMap entry by KEY.

    Args:
        key: The field code KEY to look up (case-sensitive).
        library_path: Path to CSV. Defaults to "mscad.csv".

    Returns:
        Dict with all columns for the matching entry.
    """
    try:
        path = _resolve_path(library_path)
        rows = _read_csv(path)

        for row in rows:
            if row.get("KEY", "") == key:
                return {"library_path": str(path), "entry": row}

        return {"error": f"Key '{key}' not found in {path.name}"}

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def automap_rename(
    old_key: str,
    new_key: str,
    library_path: str | None = None,
) -> dict:
    """Rename a KEY in the AutoMap library.

    Args:
        old_key: Current KEY value to find.
        new_key: New KEY value to replace it with.
        library_path: Path to CSV. Defaults to "mscad.csv".

    Returns:
        Dict confirming the rename with old and new values.
    """
    try:
        path = _resolve_path(library_path)
        rows = _read_csv(path)
        found = False

        for row in rows:
            if row.get("KEY", "") == old_key:
                row["KEY"] = new_key
                found = True
                break

        if not found:
            return {"error": f"Key '{old_key}' not found in {path.name}"}

        _write_csv(rows, path)

        return {
            "status": "ok",
            "library_path": str(path),
            "renamed": {"old": old_key, "new": new_key},
        }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def automap_delete(
    keys: list[str],
    library_path: str | None = None,
) -> dict:
    """Delete entries from the AutoMap library by KEY.

    Args:
        keys: List of KEY values to delete.
        library_path: Path to CSV. Defaults to "mscad.csv".

    Returns:
        Dict with list of deleted keys and remaining count.
    """
    try:
        path = _resolve_path(library_path)
        rows = _read_csv(path)

        keys_set = set(keys)
        deleted = []
        remaining = []

        for row in rows:
            k = row.get("KEY", "")
            if k in keys_set:
                deleted.append(k)
            else:
                remaining.append(row)

        _write_csv(remaining, path)

        return {
            "status": "ok",
            "library_path": str(path),
            "deleted": deleted,
            "remaining_count": len(remaining),
        }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def automap_save_as(
    dest_path: str,
    source_path: str | None = None,
) -> dict:
    """Copy an AutoMap library to a new location.

    Args:
        dest_path: Destination file path for the copy.
        source_path: Source CSV path. Defaults to "mscad.csv".

    Returns:
        Dict with source and destination paths.
    """
    try:
        src = _resolve_path(source_path)
        dst = Path(dest_path)

        # Create parent directory if needed
        dst.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(str(src), str(dst))

        return {
            "status": "ok",
            "source": str(src),
            "destination": str(dst),
            "size_bytes": dst.stat().st_size,
        }

    except Exception as e:
        return {"error": str(e)}
