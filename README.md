# TeeJay Survey MCP

An MCP server that drives **MicroSurvey CAD 2024** (and compatible IntelliCAD /
inCAD / embeddedCAD builds) from an AI agent or any MCP client — survey points,
COGO, traverse, surfaces/volumes, coordinate transforms (RTS / Helmert),
annotation styles, and the full new-drawing / survey-job setup ceremony.

> Named in memory of **TeeJay**.

## Why this exists

MicroSurvey's automation surface is COM (pythonnet + win32com) plus a lot of
**bespoke modal dialogs**. The design principle here is to *absorb* that dialog
ceremony — drive the real `#32770` dialogs by Win32 control ID — rather than
route around it, so an automated caller gets a correctly set-up survey job with
no manual clicking. The hard-won dialog maps and the rules that make this
reliable are written up in [`docs/microsurvey-dialog-automation.md`](docs/microsurvey-dialog-automation.md);
read that before extending the dialog-driven tools.

## Architecture

```
MCP client ──stdio/MCP──> server.py ──pythonnet/win32com COM──> MicroSurvey CAD
```

- `src/mscad_mcp/connection.py` — COM attach. pythonnet's
  `IcadInteraction.ConnectToComHost(pid)` gets a .NET COM wrapper, converted to a
  late-bound win32com IDispatch — this bypasses CloudPaging's COM-registry
  limitation. Also exposes `send_command_isolated` (fire a *blocking* modal
  command on a fresh COM apartment / daemon thread).
- `src/mscad_mcp/dialog_driver.py` — deterministic Win32 driver for the modal
  dialogs (find by class/id, `BM_CLICK`, `WM_SETTEXT`, dump). Focus- and
  coordinate-independent.
- `src/mscad_mcp/tools/` — the MCP tools, grouped by domain: `app`, `drawing`,
  `layers`, `entities`, `query`, `modify`, `view`, `cogo`, `survey`, `traverse`,
  `surface`, `transform`, `msannotate`, `settings`, `automap`, `template`.
- `tools_recon/` — standalone probes used to recover dialog control IDs
  (`probe_dialog_tree.py`, `wizard_driver.py`, `fire_command.py`, …). Handy when
  mapping a new dialog.

## Key COM facts

- Layer props: `LayerOn` (not `On`), `Freeze`, `Lock`, `Color.ColorIndex`.
- `entity.EntityName` → "Line"/"Circle"/"Text"; `entity.ObjectName` → "AcDbLine"…
- Setting a layer colour: direct assignment fails (type mismatch) — use
  `-LAYER` via `SendCommand`.
- `CreatePointInterface(x,y,z)` returns a COM point with `.x/.y/.z`.
- `Documents.Add()` is the only doc-creation primitive that reliably persists a
  usable drawing from the zero-document Start Page (it throws a benign marshaling
  `com_error` but the drawing IS created — confirm via `Documents.Count`).

## Running

```sh
# deps: mcp[cli] >= 1.0, pythonnet >= 3.0, pywin32 (from pythonnet/mcp)
python -m venv .venv && .venv\Scripts\pip install -e .
# point your MCP client at:  python -m mscad_mcp.server   (stdio)
```

MicroSurvey CAD 2024 must be running. The bridge attaches to the live process
over COM.

## License

See [`LICENSE`](LICENSE).
