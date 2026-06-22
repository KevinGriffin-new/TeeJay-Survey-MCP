"""System toggles and drawing variable tools.

MicroSurvey CAD stores system toggles in an INI-format file:
  %APPDATA%/MicroSurvey/MSCAD/<version>/X99.dat

Key toggles include:
  UseLeroyNotation — YES/NO (Leroy vs mm for text sizes)
  ShowAssistantOnNewOpen — YES/NO (startup assistant dialog)
  UseProjectManagerStartup — TRUE/FALSE (project manager on launch)
  PerformScaleFactorCheck — YES/NO (scale factor warning)
  show_cogo_dlgs — YES/NO (COGO dialogs)

Drawing variables (LTSCALE, DIMSCALE, etc.) are accessed via COM.
"""

import configparser
import io
import os
from pathlib import Path

from mscad_mcp.server import mcp
from mscad_mcp import connection


# ============================================================
# X99.DAT FILE DISCOVERY
# ============================================================

def _find_x99_paths() -> list[Path]:
    """Find all X99.dat files across MSCAD versions."""
    roaming = Path(os.environ.get("APPDATA", ""))
    base = roaming / "MicroSurvey" / "MSCAD"
    paths = []
    if base.exists():
        for version_dir in sorted(base.iterdir()):
            dat = version_dir / "X99.dat"
            if dat.exists():
                paths.append(dat)
    return paths


def _get_x99_path(version: str | None = None) -> Path:
    """Get X99.dat path for a specific MSCAD version."""
    roaming = Path(os.environ.get("APPDATA", ""))
    if version:
        dat = roaming / "MicroSurvey" / "MSCAD" / version / "X99.dat"
        if dat.exists():
            return dat
        raise FileNotFoundError(f"No X99.dat found for MSCAD {version}")

    paths = _find_x99_paths()
    if not paths:
        raise FileNotFoundError(
            "No X99.dat found. Is MicroSurvey CAD installed?"
        )
    return paths[-1]  # Latest version


def _read_x99(path: Path) -> configparser.ConfigParser:
    """Read X99.dat as INI format."""
    cp = configparser.ConfigParser(interpolation=None)
    cp.optionxform = str  # Preserve case of keys
    cp.read(str(path), encoding="utf-8")
    return cp


def _write_x99(cp: configparser.ConfigParser, path: Path) -> None:
    """Write X99.dat preserving INI format."""
    with open(path, "w", encoding="utf-8") as f:
        cp.write(f)


def _x99_to_dict(cp: configparser.ConfigParser) -> dict:
    """Convert ConfigParser to nested dict."""
    result = {}
    for section in cp.sections():
        result[section] = dict(cp[section])
    return result


# ============================================================
# MCP TOOLS
# ============================================================

@mcp.tool()
def get_system_toggles(
    section: str | None = None,
    version: str | None = None,
) -> dict:
    """Read MicroSurvey system toggles from X99.dat.

    Returns toggle settings that control startup behavior, text size
    units (Leroy vs mm), scale factor checks, COGO dialogs, etc.

    Args:
        section: INI section to read (e.g. "Toggles"). If omitted,
                 returns all sections.
        version: MSCAD version year (e.g. "2024"). Latest if omitted.

    Returns:
        Dict with file path and toggle values by section.
    """
    try:
        path = _get_x99_path(version)
        cp = _read_x99(path)
        data = _x99_to_dict(cp)

        if section:
            if section in data:
                return {
                    "x99_path": str(path),
                    "section": section,
                    "toggles": data[section],
                }
            return {"error": f"Section '{section}' not found. Available: {list(data.keys())}"}

        return {
            "x99_path": str(path),
            "sections": list(data.keys()),
            "toggles": data,
        }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def set_system_toggles(
    toggles: dict,
    section: str = "Toggles",
    version: str | None = None,
) -> dict:
    """Set MicroSurvey system toggles in X99.dat.

    Common toggles (section "Toggles"):
      UseLeroyNotation: "YES"/"NO" — Leroy vs mm for text sizes
      ShowAssistantOnNewOpen: "YES"/"NO" — startup assistant
      UseProjectManagerStartup: "TRUE"/"FALSE" — project manager
      PerformScaleFactorCheck: "YES"/"NO" — scale factor warning
      show_cogo_dlgs: "YES"/"NO" — COGO dialog boxes

    Args:
        toggles: Dict of key-value pairs to set (e.g. {"UseLeroyNotation": "NO"}).
        section: INI section name (default "Toggles").
        version: MSCAD version year. Latest if omitted.

    Returns:
        Dict with old and new values for changed toggles.
    """
    try:
        path = _get_x99_path(version)
        cp = _read_x99(path)
        changes = {}

        if not cp.has_section(section):
            cp.add_section(section)

        for key, value in toggles.items():
            old = cp.get(section, key, fallback=None)
            cp.set(section, key, str(value))
            changes[key] = {"old": old, "new": str(value)}

        _write_x99(cp, path)

        return {
            "status": "ok",
            "x99_path": str(path),
            "section": section,
            "changes": changes,
        }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_drawing_variables(
    names: list[str],
) -> dict:
    """Read CAD system variables from the active drawing.

    Common variables:
      LTSCALE — Linetype scale factor
      DIMSCALE — Dimension scale factor
      TEXTSIZE — Default text height
      ANGBASE — Angle base direction (0=East)
      ANGDIR — Angle direction (0=CCW, 1=CW)
      LUNITS — Linear units (1=Scientific, 2=Decimal, etc.)

    Args:
        names: List of system variable names to read.

    Returns:
        Dict mapping variable names to their current values.
    """
    try:
        doc = connection.get_document()
        variables = {}
        for name in names:
            try:
                variables[name] = doc.GetVariable(name)
            except Exception as e:
                variables[name] = {"error": str(e)}

        return {"variables": variables}

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def set_drawing_variables(
    variables: dict,
) -> dict:
    """Set CAD system variables on the active drawing.

    Common variables:
      LTSCALE — Linetype scale (e.g. 1000 for 1:1000)
      DIMSCALE — Dimension scale (e.g. 1000)
      TEXTSIZE — Default text height in drawing units

    Args:
        variables: Dict of variable name to value (e.g. {"LTSCALE": 1000}).

    Returns:
        Dict with old and new values for each variable.
    """
    try:
        doc = connection.get_document()
        changes = {}

        for name, value in variables.items():
            try:
                old = doc.GetVariable(name)
            except Exception:
                old = None
            try:
                doc.SetVariable(name, value)
                changes[name] = {"old": old, "new": value}
            except Exception as e:
                changes[name] = {"error": str(e)}

        return {"status": "ok", "changes": changes}

    except Exception as e:
        return {"error": str(e)}
