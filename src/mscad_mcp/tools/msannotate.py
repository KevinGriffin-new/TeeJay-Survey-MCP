"""MsAnnotate configuration tools — read and modify labeling defaults.

MicroSurvey CAD stores MsAnnotate settings in a JSON config file at:
  %APPDATA%/MicroSurvey/MSCAD/<version>/config.json

This module provides tools to read and modify those settings directly,
bypassing the GUI dialogs. Settings include bearing styles, distance
styles, curve styles, text heights (leroy), decimal places, colors,
fonts, offsets, and layer assignments.

Leroy reference (plotted text height):
  60 = ~1.5mm,  80 = ~2.0mm,  100 = ~2.5mm,  120 = ~3.0mm

Compatible with MSCAD 2024 and 2026.
"""

import json
import os
from pathlib import Path

from mscad_mcp.server import mcp


# ============================================================
# CONFIG FILE DISCOVERY
# ============================================================

def _find_config_paths() -> list[Path]:
    """Find all MsAnnotate config.json files across MSCAD versions."""
    roaming = Path(os.environ.get("APPDATA", ""))
    base = roaming / "MicroSurvey" / "MSCAD"
    configs = []
    if base.exists():
        for version_dir in sorted(base.iterdir()):
            cfg = version_dir / "config.json"
            if cfg.exists():
                configs.append(cfg)
    return configs


def _get_config_path(version: str | None = None) -> Path:
    """Get config.json path for a specific MSCAD version.

    Args:
        version: e.g. "2024", "2026". If None, uses the latest found.

    Returns:
        Path to config.json.

    Raises:
        FileNotFoundError if no config found.
    """
    roaming = Path(os.environ.get("APPDATA", ""))
    if version:
        cfg = roaming / "MicroSurvey" / "MSCAD" / version / "config.json"
        if cfg.exists():
            return cfg
        raise FileNotFoundError(f"No config.json found for MSCAD {version}")

    configs = _find_config_paths()
    if not configs:
        raise FileNotFoundError(
            "No MsAnnotate config.json found. "
            "Expected at %APPDATA%/MicroSurvey/MSCAD/<version>/config.json"
        )
    return configs[-1]  # Latest version


def _read_config(version: str | None = None) -> tuple[dict, Path]:
    """Read and parse config.json. Returns (data, path)."""
    path = _get_config_path(version)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data, path


def _write_config(data: dict, path: Path) -> None:
    """Write config.json with pretty formatting."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ============================================================
# STYLE SUMMARY HELPERS
# ============================================================

def _bearing_summary(style: dict) -> dict:
    """Extract key fields from a bearing style dict."""
    return {
        "name": style.get("name"),
        "index": style.get("index"),
        "leroy": style.get("leroy"),
        "color": style.get("color"),
        "font": style.get("fontname"),
        "layer": style.get("layername"),
        "textoffset": style.get("textoffset"),
        "rounding": style.get("rounding"),
    }


def _distance_summary(style: dict) -> dict:
    """Extract key fields from a distance style dict."""
    return {
        "name": style.get("name"),
        "index": style.get("index"),
        "leroy": style.get("leroy"),
        "decimalplaces": style.get("decimalplaces"),
        "color": style.get("color"),
        "font": style.get("fontname"),
        "layer": style.get("layername"),
        "textoffset": style.get("textoffset"),
        "scalefactor": style.get("scalefactor"),
        "prefix": style.get("distanceprefix"),
        "suffix": style.get("distancesuffix"),
    }


def _curve_summary(style: dict) -> dict:
    """Extract key fields from a curve style dict."""
    return {
        "name": style.get("name"),
        "index": style.get("index"),
        "leroy": style.get("leroy"),
        "color": style.get("color"),
        "font": style.get("fontname"),
        "layer": style.get("layername"),
        "bearingstyleindex": style.get("bearingstyleindex"),
        "distancestyleindex": style.get("distancestyleindex"),
    }


# ============================================================
# MCP TOOLS
# ============================================================

@mcp.tool()
def get_msannotate_config(version: str | None = None) -> dict:
    """Get current MsAnnotate labeling defaults from config.json.

    Returns the active bearing, distance, and curve styles with all
    their settings (leroy/text height, decimal places, colors, etc.).

    Args:
        version: MSCAD version year, e.g. "2024" or "2026".
                 If omitted, uses the latest version found.

    Returns:
        Dict with config_path, active style indices, active style
        details, and all available styles summary.
    """
    try:
        data, path = _read_config(version)

        brg_idx = data.get("bearingstyleindex", 0)
        dst_idx = data.get("distancestyleindex", 0)
        crv_idx = data.get("curvestyleindex", 0)

        brg_styles = data.get("bearingstyles", [])
        dst_styles = data.get("distancestyles", [])
        crv_styles = data.get("curvestyles", [])

        result = {
            "config_path": str(path),
            "active_bearing_index": brg_idx,
            "active_distance_index": dst_idx,
            "active_curve_index": crv_idx,
            "active_bearing": _bearing_summary(brg_styles[brg_idx]) if brg_idx < len(brg_styles) else None,
            "active_distance": _distance_summary(dst_styles[dst_idx]) if dst_idx < len(dst_styles) else None,
            "active_curve": _curve_summary(crv_styles[crv_idx]) if crv_idx < len(crv_styles) else None,
            "all_bearing_styles": [_bearing_summary(s) for s in brg_styles],
            "all_distance_styles": [_distance_summary(s) for s in dst_styles],
            "all_curve_styles": [_curve_summary(s) for s in crv_styles],
        }
        return result

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def set_msannotate_bearing(
    style_index: int | None = None,
    leroy: int | None = None,
    color: int | None = None,
    font: str | None = None,
    textoffset: float | None = None,
    rounding: int | None = None,
    layer: str | None = None,
    useleadingzero: bool | None = None,
    usereferencenorth: bool | None = None,
    version: str | None = None,
) -> dict:
    """Set MsAnnotate bearing style defaults.

    Modifies the active bearing style in config.json. Can change the
    active style index and/or modify properties of the active style.

    Args:
        style_index: Switch active bearing style (0-9 = BEARING1-10).
        leroy: Plotted text height (60=~1.5mm, 80=~2mm, 100=~2.5mm).
        color: ACI color number (1=red, 2=yellow, 3=green, etc.).
        font: Font name (e.g. "MSURVEY.SHX").
        textoffset: Offset distance from line.
        rounding: Bearing rounding (1=seconds, etc.).
        layer: Layer name for bearing text.
        useleadingzero: Show leading zeros in bearing labels.
        usereferencenorth: Use reference north for bearings.
        version: MSCAD version year. Latest if omitted.

    Returns:
        Dict with old and new values for changed settings.
    """
    try:
        data, path = _read_config(version)
        changes = {}

        if style_index is not None:
            old = data.get("bearingstyleindex", 0)
            data["bearingstyleindex"] = style_index
            changes["bearingstyleindex"] = {"old": old, "new": style_index}

        idx = data.get("bearingstyleindex", 0)
        styles = data.get("bearingstyles", [])
        if idx < len(styles):
            style = styles[idx]
            field_map = {
                "leroy": leroy,
                "color": color,
                "fontname": font,
                "textoffset": textoffset,
                "rounding": rounding,
                "layername": layer,
                "useleadingzero": useleadingzero,
                "usereferencenorth": usereferencenorth,
            }
            for field, value in field_map.items():
                if value is not None:
                    old = style.get(field)
                    style[field] = value
                    changes[field] = {"old": old, "new": value}

        _write_config(data, path)

        return {
            "status": "ok",
            "config_path": str(path),
            "active_bearing": _bearing_summary(styles[idx]) if idx < len(styles) else None,
            "changes": changes,
        }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def set_msannotate_distance(
    style_index: int | None = None,
    leroy: int | None = None,
    decimalplaces: int | None = None,
    color: int | None = None,
    font: str | None = None,
    textoffset: float | None = None,
    scalefactor: float | None = None,
    prefix: str | None = None,
    suffix: str | None = None,
    usefootsymbol: bool | None = None,
    layer: str | None = None,
    version: str | None = None,
) -> dict:
    """Set MsAnnotate distance style defaults.

    Modifies the active distance style in config.json. Can change the
    active style index and/or modify properties of the active style.

    Args:
        style_index: Switch active distance style (0-9 = DISTANCE1-10).
        leroy: Plotted text height (60=~1.5mm, 80=~2mm, 100=~2.5mm).
        decimalplaces: Number of decimal places for distance labels.
        color: ACI color number.
        font: Font name.
        textoffset: Offset distance from line.
        scalefactor: Distance scale factor (default 1.0).
        prefix: Distance label prefix text.
        suffix: Distance label suffix text.
        usefootsymbol: Show foot/meter symbol after distance labels.
        layer: Layer name for distance text.
        version: MSCAD version year. Latest if omitted.

    Returns:
        Dict with old and new values for changed settings.
    """
    try:
        data, path = _read_config(version)
        changes = {}

        if style_index is not None:
            old = data.get("distancestyleindex", 0)
            data["distancestyleindex"] = style_index
            changes["distancestyleindex"] = {"old": old, "new": style_index}

        idx = data.get("distancestyleindex", 0)
        styles = data.get("distancestyles", [])
        if idx < len(styles):
            style = styles[idx]
            field_map = {
                "leroy": leroy,
                "decimalplaces": decimalplaces,
                "color": color,
                "fontname": font,
                "textoffset": textoffset,
                "scalefactor": scalefactor,
                "distanceprefix": prefix,
                "distancesuffix": suffix,
                "usefootsymbol": usefootsymbol,
                "layername": layer,
            }
            for field, value in field_map.items():
                if value is not None:
                    old = style.get(field)
                    style[field] = value
                    changes[field] = {"old": old, "new": value}

        _write_config(data, path)

        return {
            "status": "ok",
            "config_path": str(path),
            "active_distance": _distance_summary(styles[idx]) if idx < len(styles) else None,
            "changes": changes,
        }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def set_msannotate_curve(
    style_index: int | None = None,
    leroy: int | None = None,
    color: int | None = None,
    font: str | None = None,
    bearing_style_index: int | None = None,
    distance_style_index: int | None = None,
    layer: str | None = None,
    version: str | None = None,
) -> dict:
    """Set MsAnnotate curve style defaults.

    Modifies the active curve style in config.json.

    Args:
        style_index: Switch active curve style (0-9 = CURVE1-10).
        leroy: Plotted text height (60=~1.5mm, 80=~2mm, 100=~2.5mm).
        color: ACI color number.
        font: Font name.
        bearing_style_index: Bearing style index for curves.
        distance_style_index: Distance style index for curves.
        layer: Layer name for curve text.
        version: MSCAD version year. Latest if omitted.

    Returns:
        Dict with old and new values for changed settings.
    """
    try:
        data, path = _read_config(version)
        changes = {}

        if style_index is not None:
            old = data.get("curvestyleindex", 0)
            data["curvestyleindex"] = style_index
            changes["curvestyleindex"] = {"old": old, "new": style_index}

        idx = data.get("curvestyleindex", 0)
        styles = data.get("curvestyles", [])
        if idx < len(styles):
            style = styles[idx]
            field_map = {
                "leroy": leroy,
                "color": color,
                "fontname": font,
                "bearingstyleindex": bearing_style_index,
                "distancestyleindex": distance_style_index,
                "layername": layer,
            }
            for field, value in field_map.items():
                if value is not None:
                    old = style.get(field)
                    style[field] = value
                    changes[field] = {"old": old, "new": value}

        _write_config(data, path)

        return {
            "status": "ok",
            "config_path": str(path),
            "active_curve": _curve_summary(styles[idx]) if idx < len(styles) else None,
            "changes": changes,
        }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def apply_msannotate_preset(
    preset: str,
    version: str | None = None,
) -> dict:
    """Apply a named preset to MsAnnotate config — sets multiple values at once.

    Available presets:
      "survey_bearings_2mm" — common metric survey annotation defaults:
        - BEARING4 active (leroy 80 = 2mm, color 1 = red)
        - DISTANCE3 active with 3 decimal places (leroy 80 = 2mm, color 3 = green)
        - CURVE1 with leroy 80 = 2mm
      "metric_3dec" — Metric survey, 3 decimal places, 2mm text
      "metric_2dec" — Metric survey, 2 decimal places, 2mm text
      "imperial" — Imperial survey with foot symbol, 2 decimal places

    Args:
        preset: Preset name (see above).
        version: MSCAD version year. Latest if omitted.

    Returns:
        Dict summarizing all changes made.
    """
    try:
        data, path = _read_config(version)
        changes = {}

        if preset == "survey_bearings_2mm":
            # Active style indices
            data["bearingstyleindex"] = 3   # BEARING4
            data["distancestyleindex"] = 2  # DISTANCE3
            data["curvestyleindex"] = 0     # CURVE1

            # BEARING4: leroy 80 (2mm), color red
            brg = data["bearingstyles"][3]
            brg["leroy"] = 80
            brg["color"] = 1
            brg["fontname"] = "MSURVEY.SHX"

            # DISTANCE3: 3 decimals, leroy 80 (2mm), color green
            dst = data["distancestyles"][2]
            old_dec = dst.get("decimalplaces")
            dst["decimalplaces"] = 3
            dst["leroy"] = 80
            dst["color"] = 3
            dst["fontname"] = "MSURVEY.SHX"
            changes["DISTANCE3.decimalplaces"] = {"old": old_dec, "new": 3}

            # CURVE1: leroy 80 (2mm)
            crv = data["curvestyles"][0]
            old_leroy = crv.get("leroy")
            crv["leroy"] = 80
            changes["CURVE1.leroy"] = {"old": old_leroy, "new": 80}

            changes["preset"] = "survey_bearings_2mm"

        elif preset == "metric_3dec":
            data["distancestyleindex"] = 2
            dst = data["distancestyles"][2]
            dst["decimalplaces"] = 3
            dst["leroy"] = 80
            data["bearingstyleindex"] = 3
            brg = data["bearingstyles"][3]
            brg["leroy"] = 80
            crv = data["curvestyles"][data.get("curvestyleindex", 0)]
            crv["leroy"] = 80
            changes["preset"] = "metric_3dec"

        elif preset == "metric_2dec":
            data["distancestyleindex"] = 2
            dst = data["distancestyles"][2]
            dst["decimalplaces"] = 2
            dst["leroy"] = 80
            data["bearingstyleindex"] = 3
            brg = data["bearingstyles"][3]
            brg["leroy"] = 80
            crv = data["curvestyles"][data.get("curvestyleindex", 0)]
            crv["leroy"] = 80
            changes["preset"] = "metric_2dec"

        elif preset == "imperial":
            data["distancestyleindex"] = 2
            dst = data["distancestyles"][2]
            dst["decimalplaces"] = 2
            dst["leroy"] = 80
            dst["usefootsymbol"] = True
            data["bearingstyleindex"] = 3
            brg = data["bearingstyles"][3]
            brg["leroy"] = 80
            crv = data["curvestyles"][data.get("curvestyleindex", 0)]
            crv["leroy"] = 80
            changes["preset"] = "imperial"

        else:
            return {"error": f"Unknown preset: '{preset}'. Available: survey_bearings_2mm, metric_3dec, metric_2dec, imperial"}

        _write_config(data, path)

        # Return full state after applying preset
        brg_idx = data.get("bearingstyleindex", 0)
        dst_idx = data.get("distancestyleindex", 0)
        crv_idx = data.get("curvestyleindex", 0)

        return {
            "status": "ok",
            "config_path": str(path),
            "preset_applied": preset,
            "changes": changes,
            "active_bearing": _bearing_summary(data["bearingstyles"][brg_idx]),
            "active_distance": _distance_summary(data["distancestyles"][dst_idx]),
            "active_curve": _curve_summary(data["curvestyles"][crv_idx]),
        }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def list_msannotate_configs() -> dict:
    """List all MsAnnotate config.json files found across MSCAD versions.

    Useful for seeing which versions are installed and which configs exist.

    Returns:
        Dict with list of config file paths and their version directories.
    """
    try:
        configs = _find_config_paths()
        result = {
            "configs_found": len(configs),
            "versions": [],
        }
        for cfg in configs:
            version = cfg.parent.name
            size = cfg.stat().st_size
            result["versions"].append({
                "version": version,
                "path": str(cfg),
                "size_bytes": size,
            })
        return result

    except Exception as e:
        return {"error": str(e)}
