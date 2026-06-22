# Driving MicroSurvey's modal dialogs (the hard-won notes)

MicroSurvey's survey-job setup, point import, and computations live behind
bespoke modal `#32770` dialogs. This file is the recovered control-ID map and
the rules that make driving them reliable, so you don't have to re-discover it.

## Driving technique (reliable, focus-independent)

- Standard `#32770` dialogs are driven by **Win32 control ID**, not coordinates
  or focus: `SendMessage(child, BM_CLICK)` to click, `WM_SETTEXT` to set text.
  Find a child by `EnumChildWindows` + `GetDlgCtrlID`; find a dialog by
  `EnumWindows` matching `GetClassName == "#32770"` (titles are reused per page,
  so match the class, not a fixed title). See `src/mscad_mcp/dialog_driver.py`.
- **`WM_SETTEXT` alone often silently reverts** on MFC dialogs (they read fields
  back via DDX on OK). `dialog_driver.set_text` also posts `EN_CHANGE` /
  `EN_KILLFOCUS` to the parent so the value commits.
- **Standard Windows file pickers:** `WM_SETTEXT` the actual `Edit`-class child
  (not the ComboBoxEx32 wrapper that shares its id), then **commit with
  `WM_COMMAND`/IDOK to the dialog** — a plain `BM_CLICK` on the Open/Save button
  frequently does NOT commit.

## ⚠️ THE COM-apartment rule (read this first)

In a process that drives MicroSurvey modal dialogs via win32, **NEVER also open
a main-thread COM connection.** Establishing a main-thread COM apartment poisons
subsequent isolated-thread command fires — the commands are silently dropped (no
error, no dialog). Route **every** `SendCommand` through
`connection.send_command_isolated` on a daemon thread (it `CoInitialize`s a fresh
`ConnectToComHost`), and drive the resulting modal from the main thread via pure
win32 (`dialog_driver`, which uses no COM). Mixed apartments cannot coexist for
command delivery to the single-threaded CAD.

## New drawing / survey job (`create_new_drawing`)

Command surface (each opens a `#32770`; all `SendCommand`-able):
`_project_manager`, `_cnf_edit_general` (General Configuration Options),
`_cnf_edit_bearings/distances/curves/...`, `_cnf_edit_toggles`, `_NEW` (the
IntelliCAD New Drawing Wizard — units/print prefs only, NO job name/scale).

**Verified flow** (`tools/drawing.py::create_new_drawing`): `Documents.Add` seed
→ `SaveAs <name>.dwg` → configure the auto-raised **General Config** (Metric
21028 / Int'l-Feet 21029 / US-Feet 21403; Bearings 21030 → sets `AUNITS=4`;
`INSUNITS` per units; OK 1). The save-to-a-real-name step is required *first* —
General Config refuses to stick survey defaults on a default/unsaved name.

### ⚠️ DEFAULTS-BORKING failure modes & guardrails

1. **Clobber-on-OK.** A *reopened/duplicate* General Config shows the **template
   defaults** (Int'l Feet, blank scale/desc), not the job's values. Clicking OK
   writes those over your correct units. → Configure only the GC that
   auto-raises on SaveAs; **CANCEL (id 2) any duplicate** — never OK a GC showing
   template defaults.
2. **"Set these defaults as Permanent" (control 21044) → GLOBAL corruption.**
   It writes the current values to the global/template baseline, so **every
   future new project is born with them**. → In automation, **never click
   21044**; configure per-job only.
3. **Perishable verification trap.** Reopening GC to "check" shows template
   defaults, not the job's saved values → verify via the job's `incad.cfg` /
   drawing vars (`AUNITS=4` bearings, `INSUNITS=6` metric / `2` feet), **never**
   by reopening the dialog. The scale-factor edit (21032) also does not persist
   via `WM_SETTEXT` — treat it as cosmetic; units + direction are what matter.

## ASCII point import (`_ascii_in`) — seeds numbered COGO points

1. **ASCII File Import Types:** "Coordinates Delimited" = **26001**.
2. **ASCII File Import Format Options:** pick the layout (e.g. "Pt#,North,East,
   Elev" = **26007**), delimiter Comma = **26015**, force-check **"Store
   coordinates in COGO database" = 26020** (`BM_SETCHECK`), OK = **1**.
3. **Import Toggle Check:** OK = **1** (display toggles; defaults fine).
4. **ASCII Import File** (std picker): set the `Edit` child, commit via
   `WM_COMMAND`/IDOK (see file-picker note above).

Verify the import via the `.MSJ` job's `db_coord.dbf` record count (bytes 4–7,
uint32 LE) — one record per point.

## `_ms_helmert` — 2-D Helmert / best-fit transform

Drive `_ms_helmert` (via `send_command_isolated`). All `#32770`:

- **Inputs** (title "MicroSurvey"; has ListBox 21193): Insert **21195**, OK **1**,
  Cancel 2.
- **Insert a Record:** Coordinate 24010, Coordinate **Range 24011**,
  Local→**Plan 24012**, Cancel/Finish **2** (finish = return).
- **Enter a Range of Local Coordinate Points:** From **24000**, To **24001**,
  Next 1, **Finish 24018**.
- **Local → Plan:** Local# **24014**, Plan# **24015** (disambiguate by matching
  each edit to its label's Y), Next 1 between pairs, **Finish 24018** on the last.
- **Scale question** (title "MicroSurvey"): static **65535** = "Transformation
  Scale is: <S>. Do you wish to scale…", **Yes 6 / No 7**. (Read the scale here.)
- **Helmert's Transformation Summary:** parameter Edits — Scale **24024**,
  Rotation dms **24025**, Translation N **24026**, Translation E **24027**
  (`WM_GETTEXT`); residual ListBox 24021; **Transform 1**, **Cancel 2** (Cancel =
  don't modify points).

### Validation vs. the clone engine

On a **noise-free synthetic** set (known transform applied to local points →
exact plan points), MicroSurvey, an independent least-squares implementation, and
the known transform all agree to floating-point precision — e.g. known scale
1.0025 / +12.5° → MS `1.00250000236` / `347°30'00"`, translation recovered to
~1e-8. **Rotation convention:** MS reports **clockwise** (survey azimuth):
`MS_rot = (360 − CCW_math_rot) mod 360` (so +12.5° CCW ⇒ 347°30'00"). On
*genuinely noisy* real control, a free-scale least-squares rotation and MS's
scale-locked solution diverge at the ~10–20″ level — that's estimator
sensitivity on imperfect ties, not an error; scale still agrees to ~7 figures.

## Line / curve labels — use the NATIVE tooling

Prefer MicroSurvey's native annotation (the **`cad_lines`** "CAD Lines" tool and
the configured BEARING/DISTANCE/CURVE styles) over hand-rolling label TEXT
entities (`entmake`/style-replica). The native styles live in the job
`config.json` (`bearingstyles` / `distancestyles` / `curvestyles`, active
`*styleindex`); `tools/msannotate.py` reads/sets them. `cad_lines` is a dialog
command — drive its command-line/no-dialog variant via the same control-ID
approach rather than reconstructing the labels by hand.
