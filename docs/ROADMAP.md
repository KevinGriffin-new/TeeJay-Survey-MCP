# Roadmap — required MCP functions (lab-driven)

Derived from the GEOM-2031 "Surveying CAD 2" lab set. The server already covers
Labs 1–2 (settings/styles), 4 (Helmert — validated to float precision vs the
licensed tool), 5 (surfaces/volumes), 7 (traverse, incl. compass/transit/
Crandall/least-squares adjustments), and COGO. The gaps below cluster in **LAB 3
(Zoning / House Layout / Foundation Certificate)** and the **Data Collector &
Contours** topo workflow.

## Tier 0 — infra (built)
`connection.send_command_isolated` (fire a blocking modal on an isolated COM
apartment), `dialog_driver` (Win32 control-ID driving), the survey point DB, the
`msannotate` config surface. Everything below builds on these. See
[`microsurvey-dialog-automation.md`](microsurvey-dialog-automation.md).

## Tier 1 — command-line driven, low dependency (quick wins)
| Tool | Wraps | Lab | Depends on |
|---|---|---|---|
| `offset_entity` | `_OFFSET` | LAB 3 setbacks (parallel-offset property lines) | entities / modify |
| `draw_dimension` (linear/aligned/angular) | `_DIMLINEAR` / `_DIMALIGNED` | LAB 3 Foundation Certificate callouts | entities, dimstyle settings |
| `cogo_point_to_line` (perpendicular offset) | pure COGO calc | LAB 3 setback verification | cogo |

## Tier 2 — dialog-driven (probe control IDs once, like `_ms_helmert`)
| Tool | Wraps | Lab | Depends on |
|---|---|---|---|
| `import_data_collector` | Sokkia/Fc4 `.raw` (+ FBK) import dialog | Data Collector Step 2 (raw field data → points) | dialog_driver, `survey.store_points_batch` |
| `connect_linework` | "Line Connection via XYZ-Coding" | Data Collector Step 4, Lab 6 linework | `automap` config, survey points |
| `annotate_lines_native` | **`cad_lines`** / native bearing-distance labelling | retires the `entmake` style-replica path | dialog_driver, `msannotate` |
| `label_contours` | contour-label command | Data Collector Step 11 | `surface.generate_contours` |

## Tier 3 — deliverables / composition
| Tool | Wraps | Lab | Depends on |
|---|---|---|---|
| `buildable_area` | offset-inward + area | LAB 3 buildable envelope | **`offset_entity`** + `cogo_area` |
| `plot_to_pdf` / layout | plot/print | Foundation Cert + assignment sheets | `template.create_border` |

## Plan ingestion — cross-repo (the `plat2json` path)
LAB 3 and the assignments start from a **published plan/plat**. The ingestion
producer is a sibling repo, **`plat2json`** (github.com/KevinGriffin-new/plat2json):
an LTSA vector-plat **label-OCR** pipeline that reads the authoritative labels
(bearings, distances, curve `r=`/`a=`, areas, lot/plan IDs) so geometry is
**COGO-reconstructed from the published numbers** (exact), not traced from
flattened linework (approximate).

- **Consumer to build here:** `import_plan_json` — draw `plat2json` output
  (lines / arcs / curves / labels) into MSCAD on named layers, mirroring the
  OpenCAD Land Survey plugin's existing `LS_IMPORTPLAN`. Depends on entities +
  `msannotate` (for label styles) + `cogo_*` (to reconstruct arcs/areas from
  `r=`/`a=`).
- **Gate:** `plat2json` currently reads distances/areas/arc-lengths reliably but
  **rotated DMS bearings are still the blocker** — so `import_plan_json` is only
  as good as the upstream reader. Track `plat2json/STATUS.md`. Until bearings are
  solved, the COGO reconstruction is incomplete.

## Critical path
`offset_entity` → `buildable_area` (LAB 3). `import_data_collector` →
`connect_linework` → `surface.create_tin` (exists) → `label_contours` is the full
Data Collector lab chain. `annotate_lines_native` and `import_plan_json` are
independent and high-value. Each Tier-2/plan tool needs a one-time control-ID
probe (`tools_recon/probe_dialog_tree.py`).

**Biggest single unlock:** `import_data_collector` — the entry point for the
entire topo/contours workflow and the only lab input (`.raw`) we can't yet ingest.

## Sibling repos
- `plat2json` — plan/plat label-OCR → JSON (ingestion producer).
- `opencad-landsurvey-plugin` — Rust Land Survey add-on for Open CAD Studio
  (already consumes plan JSON via `LS_IMPORTPLAN`; has the Helmert/RTS/volume
  engine validated against Civil 3D).
- `civil3d-mcp` — sibling MCP for Civil 3D (the licensed ground-truth source for
  volume/COGO goldens).
