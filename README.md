# FuselageLab

FuselageLab is a Python application for exploring simplified fuselage geometries, estimating basic aerodynamics from empirical correlations, and exporting results. It ships with a desktop GUI (Tkinter) that lets you adjust configuration via a categorized form, run the pipeline, and visualize a 3D model.

The project is intentionally compact and dependency‑light by default. Optional add‑ons enable a more modern interactive 3D viewer.

## Highlights

- Geometry synthesis: Haack nose + optional cylinder + cosine tail.
- Aerodynamics: friction correlations (laminar / transition / turbulent) and Hoerner‑style frontal drag factor; optional base drag.
- Integrals: wetted area, base area, solid volume, and simple CG locations along x.
- Mass: shell mass/weight from surface density or ρ·t.
- Outputs: CSV of the 2D profile, JSON payload with results, and dashboard plots.
- Exports: STL of the 3D fuselage surface (ASCII or binary).
- GUI: dark theme, full‑pane Matplotlib wireframe in the app; optional interactive 3D in a browser or a pywebview window.

## Requirements

- Python 3.10+
- Tk (Tkinter is part of the standard library; on Linux ensure the Tk runtime is installed via your package manager)
- Python packages (minimal):
  - `numpy`
  - `matplotlib`

Optional (for richer 3D):

- Plotly in a browser or pywebview window: `plotly`, `pywebview` (Linux requires the WebKit2GTK system library; see below)
- VTK embedded in Tk: `vtk` (system builds may or may not include the Tk module)
- Legacy HTML embed (limited): `tkinterweb`

## Install

You can install dependencies into a virtual environment or your user Python.

- Minimal (GUI + Matplotlib):
  - `pip install numpy matplotlib`

- Interactive 3D via browser/pywebview (recommended):
  - `pip install plotly`
  - `pip install pywebview`
  - Linux (WebKit2GTK runtime for pywebview):
    - Debian/Ubuntu: `sudo apt install libwebkit2gtk-4.1-0`
    - Fedora: `sudo dnf install webkit2gtk4.1`
    - Manjaro/Arch: `sudo pacman -S webkit2gtk`

- Native VTK in Tk (optional):
  - `pip install vtk`
  - Note: Many distro builds of VTK are Qt‑focused; the `libvtkRenderingTk-*.so` component may be missing. If you see a load error for that library, use the browser/pywebview path instead, or install a VTK build that includes Tk rendering.

## Run

- Start the GUI: `python main.py`
- The window loads a default `config.json` (if present) into the Configuration form.
- Adjust values and click `Run` to execute the pipeline; results appear in the Summary box and the 3D pane updates.
- Files written under `results/`:
  - `results/data/fuselaje_xy.csv` (2D profile)
  - `results/data/resultados.json` (numerical results)
  - `results/figs` (dashboard plots) when enabled

## Using The GUI

- Top bar:
  - Config path field with `Browse…`, `Load`, `Save`, `Save As…` controls.
- Right pane:
  - `Actions`: `Run`, `Open Results Folder`, `Export STL (ASCII)`, `Export STL (Binary)`, `Show Axes` (toggle), and `Open Interactive 3D`.
  - `Summary`: compact values (ReL, Cf_eff, CD_total, D_total, S_total).
  - `Configuration`: categorized tabs (Geometry, Operation, CF Model, Builder, Mass, I/O, Plots) with labeled inputs and toggles. Use the top bar `Save`/`Load` to persist/load JSON files.
- Bottom pane:
  - `Log`: status and errors.
- Left pane (3D):
  - In‑GUI wireframe (Matplotlib) with a pure black background and white lines. Use the toolbar at the bottom for basic pan/zoom.
  - The `Show Axes` checkbox toggles axes visibility (hidden by default for a clean wireframe look).
  - For fully interactive rotation/zoom (modern 3D), use the `Open Interactive 3D` button (opens a pywebview window when available, otherwise your default browser).

## Configuration Reference

The pipeline consumes a JSON configuration. When loading, defaults are merged (values you don’t supply are filled). Validation rejects obviously invalid combinations.

Top‑level keys (see defaults in `src/configio.py`):

- `geom`:
  - `l`: total length [m]
  - `d`: maximum diameter [m]
  - `base_ratio`: base‑drag ratio (d_base / d) ≥ 0
- `op` (operating point):
  - `V`: freestream speed [m/s]
  - `rho`: air density [kg/m³]
  - `nu`: kinematic viscosity [m²/s]
- `cf_model` (friction):
  - `mode`: `"laminar" | "transition" | "turbulent"`
  - `k_transition`: Hoerner transition term
  - `threeD_correction`: multiplier to account for 3D effects (> 0)
- `builder` (shape synthesis):
  - `Ln_frac`: nose length fraction of `l` (0–1)
  - `C_haack`: Haack family parameter (0=LD; ~1/3=LV)
  - `Nn`: nose sample count
  - `Lt_frac`: tail length fraction of `l` (0–1)
  - `r_tip`: tail tip radius [m]
  - `enforce_tail_angle`: boolean; if true, increases tail length to respect `alpha_max_deg`
  - `alpha_max_deg`: max tail angle [deg]
  - `Nt`: tail sample count
- `mass`:
  - `use_surface_density`: if true use `sigma_surface`; else use `rho_material * t_skin`
  - `sigma_surface`: surface density [kg/m²]
  - `rho_material`: material density [kg/m³]
  - `t_skin`: shell thickness [m]
  - `include_base_disk_area`: include base disk in wetted area calculations
  - `g`: gravity [m/s²]
- `io`:
  - `export_csv`: write the profile CSV
  - `csv_path`: relative path under `results/` or absolute
- `plots`:
  - `make_plots`: generate dashboard plots to `results/figs`
  - `dpi`: matplotlib figure DPI (≥ 50)

Notes:

- `op.base_ratio` is derived automatically from `geom.base_ratio` for convenience.
- Direct defaults and validation live in `src/configio.py`.

## What The Pipeline Does

Code lives in `src/` and is orchestrated by `src/pipeline.py`:

- Geometry (`src/build.py`): Haack nose + cylinder + cosine tail, concatenated with no duplicate point at interfaces; returns arrays `x`, `y` and basic lengths/radii.
- Aerodynamics (`src/calcs.py`): computes `Cf` and `Cf_eff`, a Hoerner‑derived factor `F`, base drag (optional), and totals (CD, D) using `q = 0.5 ρ V²` and frontal area.
- Integrals (`src/calcs.py`): wetted area, base area (optional), solid volume, and simple x‑location centroids.
- Mass (`src/calcs.py`): shell mass and weight from surface properties.
- Outputs (`src/utils.py`): saves profile CSV and JSON payload; plots dashboard via `src/plots.py` (if enabled).

## 3D Visualization

The GUI prefers a simple, robust in‑app wireframe (Matplotlib) and provides a separate interactive 3D option.

- In‑app (Matplotlib):
  - Black background (`#000`), white wireframe; axes hidden by default with a toggle.
  - Equal scaling enforced to avoid distortion; the view fills the entire left pane.

- Interactive (Plotly):
  - Click `Open Interactive 3D` in the Actions bar.
  - If `pywebview` is installed (and WebKit2GTK is present on Linux), it opens a native window.
  - Otherwise your default browser opens `results/interactive_3d.html`.

- VTK (optional):
  - If a Tk‑capable VTK build is available, the app embeds a native 3D view by default. If initialization fails (e.g., missing `libvtkRenderingTk-*.so`), it falls back automatically.

## Manjaro / Arch Notes

- Install WebKit2GTK for pywebview: `sudo pacman -S webkit2gtk`
- Install VTK: `sudo pacman -S vtk` (if Tk module is missing, use the browser/pywebview path)

## Troubleshooting

- Plotly page is blank inside the app:
  - The legacy embed (`tkinterweb`) does not include a modern JS engine; use the `Open Interactive 3D` button to open a pywebview window or your browser instead.

- VTK error: `couldn't load file libvtkRenderingTk-*.so`:
  - Your VTK build lacks the Tk rendering module. Either install a VTK build with Tk, or use the `Open Interactive 3D` button.

- Tk not found on Linux:
  - Install your distro’s Tk runtime (e.g., `sudo pacman -S tk` on Arch/Manjaro).

- Nothing happens when clicking `Open Interactive 3D`:
  - Ensure `plotly` is installed in the same environment running the app.
  - Check the log pane; the app falls back to opening `results/interactive_3d.html` in your default browser.

## Project Structure

- `main.py`: Tk GUI application.
- `src/configio.py`: defaults, validation, and config loader.
- `src/build.py`: geometry construction.
- `src/calcs.py`: aerodynamics, integrals, and mass estimates.
- `src/plots.py`: dashboard plots.
- `src/utils.py`: CSV/JSON helpers and filenames.
  - Also: mesh generation and STL writers (ASCII/binary).
- `results/`: output directory (data and figures).

## Extending

- Add shaping laws: implement a new function in `src/build.py` and call it from `build_fuselage`.
- Add a friction model: implement in `src/calcs.py` and hook into `aero_from_geometry`.
- Extra outputs: extend `src/utils.py` and add toggles under the `io` section of the config.

## License

No license has been set in this repository. If you plan to distribute or reuse, add an appropriate license file.
