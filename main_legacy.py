import json
import os
import platform
import subprocess
import threading
import tkinter as tk
import traceback
from tkinter import font as tkfont
from tkinter import ttk, filedialog, messagebox

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
# Matplotlib for 3D rendering embedded in Tkinter
from matplotlib.figure import Figure

from src.configio import load_config
from src.pipeline import run_case
from src.utils import export_fuselage_stl, stamp_name

#interactive 3D via Plotly inside Tk HTML frame
try:
    from tkinterweb import HtmlFrame  # pip install tkinterweb
    import plotly.graph_objects as go  # pip install plotly
    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False

#show Plotly in a separate pywebview window (recommended on Manjaro)
try:
    import webview as pywebview  # pip install pywebview (needs webkit2gtk on Linux)
    HAS_PYWEBVIEW = True
except Exception:
    HAS_PYWEBVIEW = False

#native interactive 3D via VTK embedded in Tk
try:
    from vtkmodules.vtkRenderingCore import vtkRenderer, vtkActor, vtkPolyDataMapper
    from vtkmodules.vtkCommonDataModel import vtkPolyData, vtkCellArray
    from vtkmodules.vtkCommonCore import vtkPoints
    from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
    from vtkmodules.vtkRenderingOpenGL2 import *  # noqa: F401
    from vtkmodules.tk.vtkTkRenderWindowInteractor import vtkTkRenderWindowInteractor
    HAS_VTK = True
except Exception:
    HAS_VTK = False


class FuselageLabApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FuselageLab")
        self.geometry("1960x1360")

        # State
        self.config_path = os.path.abspath("config.json")
        self.running = False
        self.worker = None
        self._log_buffer = []  # holds early logs before log widget exists

        # Fonts (larger for readability in Summary and Config)
        try:
            self._summary_label_font = tkfont.Font(size=18)
            self._summary_value_font = tkfont.Font(size=14, weight="bold")
            self._config_font = tkfont.Font(size=12)
        except Exception:
            # Fallbacks in case fonts can't be created
            self._summary_label_font = None
            self._summary_value_font = None
            self._config_font = None

        # UI
        self._build_ui()
        # Apply dark theme and modern styling after widgets exist
        self._apply_dark_theme()
        self._load_config_to_form(self.config_path)

    # ---------- UI construction ----------
    def _build_ui(self):
        # Top toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)

        self.path_var = tk.StringVar(value=self.config_path)
        ttk.Label(toolbar, text="Config:").pack(side=tk.LEFT)
        self.path_entry = ttk.Entry(toolbar, textvariable=self.path_var, width=60)
        self.path_entry.pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Browse…", command=self._browse_config).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Load", command=self._on_load_clicked).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(toolbar, text="Save", command=self._on_save_clicked).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Save As…", command=self._on_save_as_clicked).pack(side=tk.LEFT)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(4, 6))

        # Paned layout: top (3D + right controls) and bottom (log)
        root_paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        root_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self._paned_root = root_paned

        # Top: split horizontally: left 3D (large), right config (smaller)
        top_paned = ttk.PanedWindow(root_paned, orient=tk.HORIZONTAL)
        self._paned_top = top_paned
        root_paned.add(top_paned, weight=1)

        # Left: 3D view panel (dominant)
        view3d_frame = ttk.LabelFrame(top_paned, text="3D View", padding=0)
        try:
            view3d_frame.configure(borderwidth=0)
        except Exception:
            pass
        top_paned.add(view3d_frame, weight=3)
        self.view_frame = view3d_frame

        # Choose rendering backend: prefer VTK, else Plotly, else Matplotlib
        self._use_vtk = bool(HAS_VTK)
        self._use_plotly = bool(HAS_PLOTLY) and not self._use_vtk
        self._plotly_uirev = 1
        self._last_plotly_html = None
        self._last_plotly_html_path = None
        self.toolbar3d = None
        if self._use_vtk:
            try:
                # VTK renderer embedded in Tk
                container = ttk.Frame(view3d_frame)
                container.pack(fill=tk.BOTH, expand=True)
                self.vtk_widget = vtkTkRenderWindowInteractor(container, width=600, height=400)
                self.vtk_widget.pack(fill=tk.BOTH, expand=True)
                self.vtk_renderer = vtkRenderer()
                self.vtk_widget.GetRenderWindow().AddRenderer(self.vtk_renderer)
                # Interactor style for smooth mouse controls
                style = vtkInteractorStyleTrackballCamera()
                self.vtk_widget.GetRenderWindow().GetInteractor().SetInteractorStyle(style)
                self.vtk_widget.Initialize()
                self.vtk_widget.Start()
                # No Matplotlib or Plotly widgets in this mode
                self.view3d_html = None
                self.fig3d = None
                self.ax3d = None
                self.canvas3d = None
            except Exception as e:
                # VTK not usable (e.g., missing libvtkRenderingTk). Fallback.
                self._use_vtk = False
                try:
                    if 'container' in locals() and container.winfo_exists():
                        container.destroy()
                except Exception:
                    pass
                self._log(f"VTK initialization failed; falling back. {e}\n")
        if (not self._use_vtk) and self._use_plotly:
            try:
                # HTML frame for interactive Plotly scene
                self.view3d_html = HtmlFrame(view3d_frame, messages_enabled=False)
                self.view3d_html.pack(fill=tk.BOTH, expand=True)
                # Add a tiny control bar
                btnbar = ttk.Frame(view3d_frame)
                btnbar.pack(side=tk.BOTTOM, fill=tk.X)
                ttk.Button(btnbar, text="Open in Browser", command=self._open_plotly_in_browser).pack(side=tk.RIGHT, padx=6, pady=4)
                # No Matplotlib figure in this mode
                self.fig3d = None
                self.ax3d = None
                self.canvas3d = None
            except Exception:
                # Fall back if HtmlFrame fails to init
                self._use_plotly = False
                try:
                    if hasattr(self, 'view3d_html') and self.view3d_html and self.view3d_html.winfo_exists():
                        self.view3d_html.destroy()
                except Exception:
                    pass
        if not self._use_plotly and not self._use_vtk:
            # Initialize Matplotlib figure as fallback
            self.fig3d = Figure(figsize=(5, 4), dpi=100)
            self.ax3d = self.fig3d.add_subplot(111, projection="3d")
            self.ax3d.set_xlabel("x [m]")
            self.ax3d.set_ylabel("y [m]")
            self.ax3d.set_zlabel("z [m]")
            self.ax3d.set_title("Fuselage (revolved)", pad=4)
            # Tighten inner margins and label paddings
            self._tighten_mpl_margins()
            self._maximize_mpl_axes()
            # Apply pure black background for wireframe look
            try:
                self.fig3d.patch.set_facecolor("#000000")
                self.ax3d.set_facecolor("#000000")
                # Hide axes on startup for a clean empty canvas
                self.ax3d.set_axis_off()
            except Exception:
                pass
            mpl_container = ttk.Frame(view3d_frame, padding=0)
            try:
                mpl_container.configure(borderwidth=0)
            except Exception:
                pass
            mpl_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            self.canvas3d = FigureCanvasTkAgg(self.fig3d, master=mpl_container)
            self.canvas3d.draw()
            ctk = self.canvas3d.get_tk_widget()
            try:
                ctk.configure(highlightthickness=0, bd=0)
            except Exception:
                pass
            ctk.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=0, pady=0)
            # Optional toolbar for interaction (limited)
            self.toolbar3d = NavigationToolbar2Tk(self.canvas3d, mpl_container, pack_toolbar=False)
            self.toolbar3d.update()
            self.toolbar3d.pack(side=tk.BOTTOM, fill=tk.X)

        # Prepare 2D Matplotlib canvas (lazy: created on first use)
        self.fig2d = None
        self.ax2d = None
        self.canvas2d = None

        # Right: controls + summary + Config form (smaller)
        right = ttk.Frame(top_paned)
        top_paned.add(right, weight=1)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(3, weight=1)

        actions = ttk.LabelFrame(right, text="Actions")
        actions.grid(row=0, column=0, sticky="ew"); actions.grid_columnconfigure(99, weight=1)

        self.run_btn = ttk.Button(actions, text="Run", command=self._on_run_clicked)
        self.run_btn.pack(side=tk.LEFT, padx=6, pady=6)

        self.open_results_btn = ttk.Button(actions, text="Open Results Folder", command=self._open_results)
        self.open_results_btn.pack(side=tk.LEFT, padx=6, pady=6)

        # STL export (ASCII and Binary)
        ttk.Button(actions, text="Export STL (ASCII)", command=lambda: self._export_stl(True)).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(actions, text="Export STL (Binary)", command=lambda: self._export_stl(False)).pack(side=tk.LEFT, padx=6, pady=6)

        # Wireframe/axes controls
        self.show_axes_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(actions, text="Show Axes", variable=self.show_axes_var, command=lambda: self._toggle_axes()).pack(side=tk.LEFT, padx=6, pady=6)

        # Always-available interactive viewer button (pywebview/browser)
        ttk.Button(actions, text="Open Interactive 3D", command=self._open_interactive_3d).pack(side=tk.LEFT, padx=6, pady=6)

        ttk.Separator(right, orient=tk.HORIZONTAL).grid(row=1, column=0, sticky="ew", pady=(6, 6))

        # Results summary (compact)
        self.results_frame = ttk.LabelFrame(right, text="Summary")
        self.results_frame.grid(row=2, column=0, sticky="ew", padx=(0, 0))

        self.summary_vars = {
            "ReL": tk.StringVar(value="-"),
            "Cf_eff": tk.StringVar(value="-"),
            "CD_total": tk.StringVar(value="-"),
            "D_total": tk.StringVar(value="-"),
            "S_total": tk.StringVar(value="-"),
        }

        self._add_summary_row("ReL", 0)
        self._add_summary_row("Cf_eff", 1)
        self._add_summary_row("CD_total", 2)
        self._add_summary_row("D_total [N]", 3, key="D_total")
        self._add_summary_row("S_total [m²]", 4, key="S_total")

        # Configuration form on the right
        config_frame = ttk.LabelFrame(right, text="Configuration")
        config_frame.grid(row=3, column=0, sticky="nsew")
        config_frame.grid_rowconfigure(0, weight=1)
        config_frame.grid_columnconfigure(0, weight=1)
        self._build_config_form(config_frame)

        # Plot selector below configuration
        viewer_frame = ttk.LabelFrame(right, text="Viewer")
        viewer_frame.grid(row=4, column=0, sticky="ew", pady=(6,0))
        viewer_frame.grid_columnconfigure(1, weight=1)
        ttk.Label(viewer_frame, text="Show:", style="Config.TLabel").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.plot_choice_var = tk.StringVar(value="3D View")
        choices = [
            "3D View",
            "Re_x vs x",
            "Cf_local vs x",
            "tau_w vs x",
            "Cumulative friction drag",
            "Sweep: CD_total vs l/d",
            "Sweep: CD_total vs base_ratio",
            "Sweep: CD_total vs V",
            "Sweep: CD_total vs 3D correction",
            "Overlay: CD_total vs l/d (modes)",
        ]
        self.plot_choice = ttk.Combobox(viewer_frame, textvariable=self.plot_choice_var, values=choices, state="readonly", style="Config.TCombobox")
        self.plot_choice.grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(viewer_frame, text="Show", command=self._on_plot_choice, style="Config.TButton").grid(row=0, column=2, sticky="w", padx=(0,8), pady=6)

        # Bottom: Log panel across full width
        log_frame = ttk.LabelFrame(root_paned, text="Log")
        root_paned.add(log_frame, weight=0)
        self.log = tk.Text(log_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.log.pack(fill=tk.BOTH, expand=True)
        # Flush any buffered logs captured during early init
        try:
            if self._log_buffer:
                for _m in self._log_buffer:
                    self._log(_m)
                self._log_buffer.clear()
        except Exception:
            pass

        # Set initial sash positions after window is drawn
        self.after(200, self._set_initial_sashes)

    def _set_initial_sashes(self):
        try:
            # Prefer percentages for robustness
            w = max(1, self._paned_top.winfo_width())
            h = max(1, self._paned_root.winfo_height())
            # Allocate ~70% to 3D view (left), ~30% to right panel
            left_px = int(0.70 * w)
            # Allocate ~22% to log at bottom (thin but roomy)
            log_px = int(0.78 * h)
            # Apply positions
            try:
                self._paned_top.sashpos(0, left_px)
            except Exception:
                pass
            try:
                self._paned_root.sashpos(0, log_px)
            except Exception:
                pass
        except Exception:
            pass

    def _add_summary_row(self, label: str, row: int, key: str | None = None):
        if key is None:
            key = label
        frame = self.results_frame
        frame.grid_columnconfigure(1, weight=1)
        ttk.Label(frame, text=label + ":", style="SummaryLabel.TLabel").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ttk.Label(frame, textvariable=self.summary_vars[key], style="SummaryValue.TLabel").grid(row=row, column=1, sticky="e", padx=8, pady=4)

    # ---------- Config form ----------
    def _build_config_form(self, parent: ttk.Frame):
        # Variables store
        self.cfg_vars: dict[str, dict[str, tk.Variable]] = {
            "geom": {
                "l": tk.StringVar(),
                "d": tk.StringVar(),
                "base_ratio": tk.StringVar(),
            },
            "op": {
                "V": tk.StringVar(),
                "rho": tk.StringVar(),
                "nu": tk.StringVar(),
            },
            "cf_model": {
                "mode": tk.StringVar(),
                "k_transition": tk.StringVar(),
                "threeD_correction": tk.StringVar(),
            },
            "builder": {
                "Ln_frac": tk.StringVar(),
                "C_haack": tk.StringVar(),
                "Nn": tk.StringVar(),
                "Lt_frac": tk.StringVar(),
                "r_tip": tk.StringVar(),
                "enforce_tail_angle": tk.BooleanVar(),
                "alpha_max_deg": tk.StringVar(),
                "Nt": tk.StringVar(),
            },
            "mass": {
                "use_surface_density": tk.BooleanVar(),
                "sigma_surface": tk.StringVar(),
                "rho_material": tk.StringVar(),
                "t_skin": tk.StringVar(),
                "include_base_disk_area": tk.BooleanVar(),
                "g": tk.StringVar(),
            },
            "io": {
                "export_csv": tk.BooleanVar(),
                "csv_path": tk.StringVar(),
            },
            "plots": {
                "make_plots": tk.BooleanVar(),
                "dpi": tk.StringVar(),
            },
        }

        # Notebook with custom tab style (font set in theme method)
        try:
            nb = ttk.Notebook(parent, style="Config.TNotebook")
        except Exception:
            nb = ttk.Notebook(parent)
        nb.grid(row=0, column=0, sticky="nsew")

        # Geometry
        tab_geom = ttk.Frame(nb)
        nb.add(tab_geom, text="Geometry")
        self._form_grid(tab_geom, [
            ("Length [m]", self.cfg_vars["geom"]["l"]),
            ("Diameter [m]", self.cfg_vars["geom"]["d"]),
            ("Base ratio", self.cfg_vars["geom"]["base_ratio"]),
        ])

        # Operation
        tab_op = ttk.Frame(nb)
        nb.add(tab_op, text="Operation")
        self._form_grid(tab_op, [
            ("Velocity V [m/s]", self.cfg_vars["op"]["V"]),
            ("Density rho [kg/m³]", self.cfg_vars["op"]["rho"]),
            ("Kinematic viscosity nu [m²/s]", self.cfg_vars["op"]["nu"]),
        ])

        # Cf Model
        tab_cf = ttk.Frame(nb)
        nb.add(tab_cf, text="CF Model")
        # First row: Combobox for mode
        ttk.Label(tab_cf, text="Mode", style="Config.TLabel").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        mode_cb = ttk.Combobox(tab_cf, textvariable=self.cfg_vars["cf_model"]["mode"], values=["laminar", "transition", "turbulent"], state="readonly", style="Config.TCombobox")
        mode_cb.grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        tab_cf.grid_columnconfigure(1, weight=1)
        # Rest rows
        self._form_row(tab_cf, 1, "Transition k", self.cfg_vars["cf_model"]["k_transition"])
        self._form_row(tab_cf, 2, "3D correction", self.cfg_vars["cf_model"]["threeD_correction"])

        # Builder
        tab_bld = ttk.Frame(nb)
        nb.add(tab_bld, text="Builder")
        # Checkbutton for enforce_tail_angle inline
        rows = [
            ("Nose length fraction", self.cfg_vars["builder"]["Ln_frac"]),
            ("Haack C", self.cfg_vars["builder"]["C_haack"]),
            ("Nose points Nn", self.cfg_vars["builder"]["Nn"]),
            ("Tail length fraction", self.cfg_vars["builder"]["Lt_frac"]),
            ("Tip radius r_tip [m]", self.cfg_vars["builder"]["r_tip"]),
            ("Max tail angle [deg]", self.cfg_vars["builder"]["alpha_max_deg"]),
            ("Tail points Nt", self.cfg_vars["builder"]["Nt"]),
        ]
        self._form_grid(tab_bld, rows)
        cb = ttk.Checkbutton(tab_bld, text="Limit tail angle", variable=self.cfg_vars["builder"]["enforce_tail_angle"], style="Config.TCheckbutton")
        cb.grid(row=len(rows), column=0, columnspan=2, sticky="w", padx=8, pady=4)

        # Mass
        tab_mass = ttk.Frame(nb)
        nb.add(tab_mass, text="Mass")
        tab_mass.grid_columnconfigure(1, weight=1)
        self.mass_sigma_entry = None
        self.mass_rho_entry = None
        self.mass_tskin_entry = None
        cb_usd = ttk.Checkbutton(tab_mass, text="Use surface density", variable=self.cfg_vars["mass"]["use_surface_density"], command=self._toggle_mass_mode, style="Config.TCheckbutton")
        cb_usd.grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 2))
        self._form_row(tab_mass, 1, "Surface density sigma [kg/m²]", self.cfg_vars["mass"]["sigma_surface"], entry_ref_attr="mass_sigma_entry")
        self._form_row(tab_mass, 2, "Material density rho [kg/m³]", self.cfg_vars["mass"]["rho_material"], entry_ref_attr="mass_rho_entry")
        self._form_row(tab_mass, 3, "Skin thickness t_skin [m]", self.cfg_vars["mass"]["t_skin"], entry_ref_attr="mass_tskin_entry")
        cb_base = ttk.Checkbutton(tab_mass, text="Include base disk area", variable=self.cfg_vars["mass"]["include_base_disk_area"], style="Config.TCheckbutton")
        cb_base.grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        self._form_row(tab_mass, 5, "Gravity g [m/s²]", self.cfg_vars["mass"]["g"])

        # I/O
        tab_io = ttk.Frame(nb)
        nb.add(tab_io, text="I/O")
        tab_io.grid_columnconfigure(1, weight=1)
        cb_csv = ttk.Checkbutton(tab_io, text="Export CSV", variable=self.cfg_vars["io"]["export_csv"], style="Config.TCheckbutton")
        cb_csv.grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 2))
        ttk.Label(tab_io, text="CSV path", style="Config.TLabel").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        e_csv = ttk.Entry(tab_io, textvariable=self.cfg_vars["io"]["csv_path"], style="Config.TEntry")
        e_csv.grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(tab_io, text="Browse…", command=self._browse_csv_path, style="Config.TButton").grid(row=1, column=2, sticky="w", padx=(0,8), pady=4)

        # Plots
        tab_plots = ttk.Frame(nb)
        nb.add(tab_plots, text="Plots")
        tab_plots.grid_columnconfigure(1, weight=1)
        cb_plots = ttk.Checkbutton(tab_plots, text="Make plots", variable=self.cfg_vars["plots"]["make_plots"], style="Config.TCheckbutton")
        cb_plots.grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 2))
        self._form_row(tab_plots, 1, "DPI", self.cfg_vars["plots"]["dpi"])

    def _form_grid(self, parent: ttk.Frame, rows: list[tuple[str, tk.Variable]]):
        parent.grid_columnconfigure(1, weight=1)
        for i, (label, var) in enumerate(rows):
            ttk.Label(parent, text=label, style="Config.TLabel").grid(row=i, column=0, sticky="w", padx=8, pady=4)
            e = ttk.Entry(parent, textvariable=var, style="Config.TEntry")
            e.grid(row=i, column=1, sticky="ew", padx=8, pady=4)

    def _form_row(self, parent: ttk.Frame, row: int, label: str, var: tk.Variable, entry_ref_attr: str | None = None):
        ttk.Label(parent, text=label, style="Config.TLabel").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        e = ttk.Entry(parent, textvariable=var, style="Config.TEntry")
        e.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        parent.grid_columnconfigure(1, weight=1)
        if entry_ref_attr:
            setattr(self, entry_ref_attr, e)

    def _toggle_mass_mode(self):
        try:
            use_sigma = bool(self.cfg_vars["mass"]["use_surface_density"].get())
            # Enable/disable fields accordingly
            if self.mass_sigma_entry is not None:
                self.mass_sigma_entry.configure(state=(tk.NORMAL if use_sigma else tk.DISABLED))
            if self.mass_rho_entry is not None:
                self.mass_rho_entry.configure(state=(tk.DISABLED if use_sigma else tk.NORMAL))
            if self.mass_tskin_entry is not None:
                self.mass_tskin_entry.configure(state=(tk.DISABLED if use_sigma else tk.NORMAL))
        except Exception:
            pass

    def _browse_csv_path(self):
        try:
            initialfile = os.path.basename(self.cfg_vars["io"]["csv_path"].get() or "fuselaje_xy.csv")
            path = filedialog.asksaveasfilename(
                title="Select CSV path",
                defaultextension=".csv",
                initialfile=initialfile,
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            )
            if path:
                self.cfg_vars["io"]["csv_path"].set(path)
        except Exception:
            pass

    def _populate_form_from_cfg(self, cfg: dict):
        # Fill vars safely (stringify numerics for entries)
        def s(v):
            return "" if v is None else (str(v))
        try:
            g = cfg.get("geom", {})
            self.cfg_vars["geom"]["l"].set(s(g.get("l", "")))
            self.cfg_vars["geom"]["d"].set(s(g.get("d", "")))
            self.cfg_vars["geom"]["base_ratio"].set(s(g.get("base_ratio", 0)))

            op = cfg.get("op", {})
            self.cfg_vars["op"]["V"].set(s(op.get("V", "")))
            self.cfg_vars["op"]["rho"].set(s(op.get("rho", "")))
            self.cfg_vars["op"]["nu"].set(s(op.get("nu", "")))

            cf = cfg.get("cf_model", {})
            self.cfg_vars["cf_model"]["mode"].set(cf.get("mode", "turbulent"))
            self.cfg_vars["cf_model"]["k_transition"].set(s(cf.get("k_transition", "")))
            self.cfg_vars["cf_model"]["threeD_correction"].set(s(cf.get("threeD_correction", "")))

            b = cfg.get("builder", {})
            self.cfg_vars["builder"]["Ln_frac"].set(s(b.get("Ln_frac", "")))
            self.cfg_vars["builder"]["C_haack"].set(s(b.get("C_haack", "")))
            self.cfg_vars["builder"]["Nn"].set(s(b.get("Nn", "")))
            self.cfg_vars["builder"]["Lt_frac"].set(s(b.get("Lt_frac", "")))
            self.cfg_vars["builder"]["r_tip"].set(s(b.get("r_tip", "")))
            self.cfg_vars["builder"]["enforce_tail_angle"].set(bool(b.get("enforce_tail_angle", True)))
            self.cfg_vars["builder"]["alpha_max_deg"].set(s(b.get("alpha_max_deg", "")))
            self.cfg_vars["builder"]["Nt"].set(s(b.get("Nt", "")))

            m = cfg.get("mass", {})
            self.cfg_vars["mass"]["use_surface_density"].set(bool(m.get("use_surface_density", False)))
            self.cfg_vars["mass"]["sigma_surface"].set(s(m.get("sigma_surface", "")))
            self.cfg_vars["mass"]["rho_material"].set(s(m.get("rho_material", "")))
            self.cfg_vars["mass"]["t_skin"].set(s(m.get("t_skin", "")))
            self.cfg_vars["mass"]["include_base_disk_area"].set(bool(m.get("include_base_disk_area", False)))
            self.cfg_vars["mass"]["g"].set(s(m.get("g", "")))

            io = cfg.get("io", {})
            self.cfg_vars["io"]["export_csv"].set(bool(io.get("export_csv", True)))
            self.cfg_vars["io"]["csv_path"].set(io.get("csv_path", "results/data/fuselaje_xy.csv"))

            pl = cfg.get("plots", {})
            self.cfg_vars["plots"]["make_plots"].set(bool(pl.get("make_plots", True)))
            self.cfg_vars["plots"]["dpi"].set(s(pl.get("dpi", 140)))
        finally:
            # Update enabled/disabled fields in Mass tab
            self._toggle_mass_mode()

    def _collect_cfg_from_form(self) -> dict:
        # Helpers to parse numbers safely
        def to_float(name, v):
            try:
                return float(str(v).strip())
            except Exception:
                raise ValueError(f"'{name}' must be a number")

        def to_int(name, v):
            try:
                return int(float(str(v).strip()))
            except Exception:
                raise ValueError(f"'{name}' must be an integer")

        cfg = {
            "geom": {
                "l": to_float("Length", self.cfg_vars["geom"]["l"].get()),
                "d": to_float("Diameter", self.cfg_vars["geom"]["d"].get()),
                "base_ratio": to_float("Base ratio", self.cfg_vars["geom"]["base_ratio"].get() or 0.0),
            },
            "op": {
                "V": to_float("Velocity", self.cfg_vars["op"]["V"].get()),
                "rho": to_float("Density", self.cfg_vars["op"]["rho"].get()),
                "nu": to_float("Kinematic viscosity", self.cfg_vars["op"]["nu"].get()),
            },
            "cf_model": {
                "mode": (self.cfg_vars["cf_model"]["mode"].get() or "turbulent"),
                "k_transition": to_float("Transition k", self.cfg_vars["cf_model"]["k_transition"].get()),
                "threeD_correction": to_float("3D correction", self.cfg_vars["cf_model"]["threeD_correction"].get()),
            },
            "builder": {
                "Ln_frac": to_float("Nose length fraction", self.cfg_vars["builder"]["Ln_frac"].get()),
                "C_haack": to_float("Haack C", self.cfg_vars["builder"]["C_haack"].get()),
                "Nn": to_int("Nose points Nn", self.cfg_vars["builder"]["Nn"].get()),
                "Lt_frac": to_float("Tail length fraction", self.cfg_vars["builder"]["Lt_frac"].get()),
                "r_tip": to_float("Tip radius r_tip", self.cfg_vars["builder"]["r_tip"].get() or 0.0),
                "enforce_tail_angle": bool(self.cfg_vars["builder"]["enforce_tail_angle"].get()),
                "alpha_max_deg": to_float("Max tail angle", self.cfg_vars["builder"]["alpha_max_deg"].get()),
                "Nt": to_int("Tail points Nt", self.cfg_vars["builder"]["Nt"].get()),
            },
            "mass": {
                "use_surface_density": bool(self.cfg_vars["mass"]["use_surface_density"].get()),
                "sigma_surface": to_float("Surface density sigma", self.cfg_vars["mass"]["sigma_surface"].get() or 0.0),
                "rho_material": to_float("Material density rho", self.cfg_vars["mass"]["rho_material"].get() or 0.0),
                "t_skin": to_float("Skin thickness t_skin", self.cfg_vars["mass"]["t_skin"].get() or 0.0),
                "include_base_disk_area": bool(self.cfg_vars["mass"]["include_base_disk_area"].get()),
                "g": to_float("Gravity g", self.cfg_vars["mass"]["g"].get()),
            },
            "io": {
                "export_csv": bool(self.cfg_vars["io"]["export_csv"].get()),
                "csv_path": self.cfg_vars["io"]["csv_path"].get() or "results/data/fuselaje_xy.csv",
            },
            "plots": {
                "make_plots": bool(self.cfg_vars["plots"]["make_plots"].get()),
                "dpi": to_int("DPI", self.cfg_vars["plots"]["dpi"].get()),
            },
        }

        # Sanity for mass entries according to toggle
        if cfg["mass"]["use_surface_density"]:
            # sigma must be >0; rho_material and t_skin can remain (ignored by pipeline)
            pass
        else:
            # rho_material and t_skin should be >0; sigma can be present but unused
            pass
        return cfg

    # ---------- Actions ----------
    def _browse_config(self):
        initialdir = os.path.dirname(self.config_path) if os.path.exists(self.config_path) else os.getcwd()
        path = filedialog.askopenfilename(
            title="Select config JSON",
            initialdir=initialdir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.path_var.set(path)
            self._load_config_to_form(path)

    def _on_load_clicked(self):
        self._load_config_to_form(self.path_var.get())

    def _on_save_clicked(self):
        try:
            self._save_form_to_file(self.path_var.get())
        except Exception as e:
            messagebox.showerror("Save error", f"Could not save config.\n\n{e}")

    def _on_save_as_clicked(self):
        path = filedialog.asksaveasfilename(
            title="Save config as",
            initialfile=os.path.basename(self.path_var.get() or "config.json"),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.path_var.set(path)
            try:
                self._save_form_to_file(path)
            except Exception as e:
                messagebox.showerror("Save error", f"Could not save config.\n\n{e}")

    def _on_run_clicked(self):
        if self.running:
            return
        # Save current form content to file, then run pipeline using load_config
        path = self.path_var.get().strip() or self.config_path
        if not path.lower().endswith(".json"):
            messagebox.showerror("Invalid path", "Config path must end with .json")
            return
        try:
            self._save_form_to_file(path)
        except Exception as e:
            messagebox.showerror("Save error", f"Could not save config file.\n\n{e}")
            return

        self._set_running(True)
        self._log(f"Starting run with: {path}\n")

        def worker():
            try:
                cfg = load_config(path)
                payload = run_case(cfg)
                # Schedule UI updates in main thread
                self.after(0, lambda: self._set_last(cfg, payload))
                self.after(0, lambda: self._update_summary(payload))
                self.after(0, lambda: self._render_view_current())
                self.after(0, lambda: self._log("Run completed successfully.\n"))
            except Exception:
                err = traceback.format_exc()
                # Log and show error in main thread
                self.after(0, lambda: self._log(err))
                self.after(0, lambda: messagebox.showerror("Run failed", err))
            finally:
                self.after(0, lambda: self._set_running(False))

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()

    def _open_results(self):
        # Open the results folder in the system file browser
        results_dir = os.path.abspath("results")
        os.makedirs(results_dir, exist_ok=True)
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(results_dir)  # type: ignore[attr-defined]
            elif system == "Darwin":
                subprocess.Popen(["open", results_dir])
            else:
                subprocess.Popen(["xdg-open", results_dir])
        except Exception as e:
            self._log(f"Could not open results folder: {e}\n")

    def _export_stl(self, ascii: bool = True):
        try:
            payload = getattr(self, "_last_payload", None)
            if not payload or not payload.get("geom"):
                messagebox.showinfo("Export STL", "Run a case first to generate geometry.")
                return
            geom = payload["geom"]
            # Choose save location
            default_dir = os.path.abspath(os.path.join("results", "meshes"))
            os.makedirs(default_dir, exist_ok=True)
            suffix = "ascii" if ascii else "bin"
            default_name = stamp_name("fuselage", suffix=suffix, ext="stl")
            title = f"Export STL ({'ASCII' if ascii else 'Binary'})"
            path = filedialog.asksaveasfilename(
                title=title,
                defaultextension=".stl",
                filetypes=[("STL files", "*.stl"), ("All files", "*.*")],
                initialdir=default_dir,
                initialfile=default_name,
            )
            if not path:
                return
            export_fuselage_stl(geom, path, ascii=ascii, n_theta=128, name="fuselage")
            self._log(f"[OK] Exported STL to: {path}\n")
            try:
                messagebox.showinfo("Export STL", f"Saved: {path}")
            except Exception:
                pass
        except Exception as e:
            self._log(f"Could not export STL: {e}\n")

    # ---------- Helpers ----------
    def _load_config_to_form(self, path: str):
        path = os.path.abspath(path)
        self.config_path = path
        self.path_var.set(path)
        try:
            data = load_config(path)
        except FileNotFoundError:
            data = {}
        except Exception as e:
            messagebox.showerror("Load error", f"Could not load config.\n\n{e}")
            return
        try:
            self._populate_form_from_cfg(data)
            self._log(f"Loaded config: {path}\n")
        except Exception as e:
            self._log(f"Could not populate form: {e}\n")

    def _save_form_to_file(self, path: str):
        cfg = self._collect_cfg_from_form()
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        self._log(f"Saved config: {path}\n")

    def _set_running(self, running: bool):
        self.running = running
        state = tk.DISABLED if running else tk.NORMAL
        self.run_btn.configure(state=state)
        self.path_entry.configure(state=state)

    def _update_summary(self, payload: dict):
        try:
            aero = payload.get("aero", {})
            integrals = payload.get("integrals", {})
            self.summary_vars["ReL"].set(f"{aero.get('ReL', float('nan')):.3g}")
            self.summary_vars["Cf_eff"].set(f"{aero.get('Cf_eff', float('nan')):.5f}")
            self.summary_vars["CD_total"].set(f"{aero.get('CD_total', float('nan')):.5f}")
            self.summary_vars["D_total"].set(f"{aero.get('D_total', float('nan')):.4g}")
            self.summary_vars["S_total"].set(f"{integrals.get('S_total', float('nan')):.4g}")
        except Exception as e:
            self._log(f"Could not update summary: {e}\n")

    def _log(self, msg: str):
        if hasattr(self, "log") and self.log is not None:
            try:
                self.log.configure(state=tk.NORMAL)
                self.log.insert(tk.END, msg)
                self.log.see(tk.END)
                self.log.configure(state=tk.DISABLED)
            except Exception:
                # As a last resort, print to stdout
                try:
                    print(msg, end="")
                except Exception:
                    pass
        else:
            # Buffer until log widget exists; also print to stdout for visibility
            try:
                self._log_buffer.append(msg)
                print(msg, end="")
            except Exception:
                pass

    # ---------- Viewer routing ----------
    def _set_last(self, cfg: dict, payload: dict):
        self._last_cfg = cfg
        self._last_payload = payload

    def _on_plot_choice(self):
        try:
            self._render_view_current()
        except Exception as e:
            self._log(f"Viewer update failed: {e}\n")

    def _render_view_current(self):
        choice = (self.plot_choice_var.get() if hasattr(self, 'plot_choice_var') else '3D View')
        if choice == "3D View":
            self._render_3d_current()
            return
        # 2D plots require payload and cfg
        payload = getattr(self, "_last_payload", None)
        cfg = getattr(self, "_last_cfg", None)
        if not payload or not cfg:
            messagebox.showinfo("Viewer", "Run a case first to view plots.")
            return
        try:
            if choice == "Re_x vs x":
                self._render_plot_rex(payload, cfg)
            elif choice == "Cf_local vs x":
                self._render_plot_cflocal(payload, cfg)
            elif choice == "tau_w vs x":
                self._render_plot_tau(payload, cfg)
            elif choice == "Cumulative friction drag":
                self._render_plot_df_cum(payload, cfg)
            elif choice == "Sweep: CD_total vs l/d":
                self._render_sweep_ld(cfg)
            elif choice == "Sweep: CD_total vs base_ratio":
                self._render_sweep_base_ratio(cfg)
            elif choice == "Sweep: CD_total vs V":
                self._render_sweep_V(cfg)
            elif choice == "Sweep: CD_total vs 3D correction":
                self._render_sweep_k3d(cfg)
            elif choice == "Overlay: CD_total vs l/d (modes)":
                self._render_overlay_modes(cfg)
        except Exception as e:
            self._log(f"Render plot failed: {e}\n")

    def _render_3d_current(self):
        payload = getattr(self, "_last_payload", None)
        if not payload:
            # Ensure 3D widget is visible even if empty
            self._ensure_3d_visible()
            try:
                self.view_frame.configure(text="3D View")
            except Exception:
                pass
            return
        self.view_frame.configure(text="3D View")
        self._render_3d_from_payload(payload)

    def _ensure_2d_canvas(self):
        if self.fig2d is None:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            self.fig2d = Figure(figsize=(5, 4), dpi=100)
            self.ax2d = self.fig2d.add_subplot(111)
            container = ttk.Frame(self.view_frame, padding=0)
            try:
                container.configure(borderwidth=0)
            except Exception:
                pass
            container.pack(fill=tk.BOTH, expand=True)
            self.canvas2d = FigureCanvasTkAgg(self.fig2d, master=container)
            self.canvas2d.draw()
            self.canvas2d.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            self._mpl2d_container = container
            # Hide 3D widgets if present
        # Hide 3D widgets
        try:
            if getattr(self, 'vtk_widget', None):
                self.vtk_widget.pack_forget()
        except Exception:
            pass
        try:
            if getattr(self, 'view3d_html', None):
                self.view3d_html.pack_forget()
        except Exception:
            pass
        try:
            if getattr(self, 'canvas3d', None):
                self.canvas3d.get_tk_widget().pack_forget()
                if getattr(self, 'toolbar3d', None):
                    self.toolbar3d.pack_forget()
        except Exception:
            pass
        # Show 2D container
        try:
            if hasattr(self, '_mpl2d_container') and self._mpl2d_container.winfo_ismapped() is False:
                self._mpl2d_container.pack(fill=tk.BOTH, expand=True)
        except Exception:
            pass

    def _ensure_3d_visible(self):
        # Hide 2D
        try:
            if getattr(self, '_mpl2d_container', None):
                self._mpl2d_container.pack_forget()
        except Exception:
            pass
        # Show appropriate 3D widget
        try:
            if getattr(self, 'vtk_widget', None):
                self.vtk_widget.pack(fill=tk.BOTH, expand=True)
        except Exception:
            pass
        try:
            if getattr(self, 'view3d_html', None):
                self.view3d_html.pack(fill=tk.BOTH, expand=True)
        except Exception:
            pass
        try:
            if getattr(self, 'canvas3d', None):
                self.canvas3d.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
                if getattr(self, 'toolbar3d', None):
                    self.toolbar3d.pack(side=tk.BOTTOM, fill=tk.X)
        except Exception:
            pass

    # ---------- 3D rendering ----------
    def _render_3d_from_payload(self, payload: dict):
        try:
            geom = payload.get("geom", {})
            x = np.asarray(geom.get("x"))
            y = np.asarray(geom.get("y"))
            if x is None or y is None or x.size == 0:
                self._log("No geometry to render.\n")
                return
            # Build revolution surface: revolve y around x-axis
            n_theta = 64
            theta = np.linspace(0.0, 2*np.pi, n_theta)
            X = np.repeat(x[:, None], n_theta, axis=1)
            R = np.repeat(y[:, None], n_theta, axis=1)
            Y = R * np.cos(theta)
            Z = R * np.sin(theta)
            # Cache surface for potential re-render (e.g., toggle axes)
            self._last_surface = (X, Y, Z)

            # Ensure 3D container visible
            self._ensure_3d_visible()
            if self._use_vtk:
                # Build/update VTK surface actor
                actor = self._build_vtk_surface(X, Y, Z)
                # Clear previous actors
                self.vtk_renderer.RemoveAllViewProps()
                self.vtk_renderer.AddActor(actor)
                self._apply_vtk_dark(self.vtk_renderer)
                self.vtk_renderer.ResetCamera()
                self.vtk_widget.GetRenderWindow().Render()
                self._log("Rendered interactive 3D surface (VTK).\n")
            elif self._use_plotly:
                # Interactive shaded surface via Plotly
                fig = go.Figure(
                    data=[
                        go.Surface(
                            x=X, y=Y, z=Z,
                            colorscale="Blues",
                            showscale=False,
                            opacity=1.0,
                        )
                    ]
                )
                fig.update_layout(
                    title="Fuselage (revolved)",
                    margin=dict(l=0, r=0, t=30, b=0),
                    scene=dict(
                        xaxis_title="x [m]",
                        yaxis_title="y [m]",
                        zaxis_title="z [m]",
                        aspectmode="data",
                    ),
                    uirevision=str(self._plotly_uirev),
                )
                # Apply dark theme if in use
                self._apply_plotly_dark(fig)
                # Smooth zoom/rotate with scroll
                config = dict(scrollZoom=True, displaylogo=False)
                # Embed Plotly JS inline to avoid network dependency
                html = fig.to_html(include_plotlyjs=True, full_html=False, config=config)
                try:
                    if hasattr(self.view3d_html, "load_html"):
                        self.view3d_html.load_html(html)
                    elif hasattr(self.view3d_html, "set_html"):
                        self.view3d_html.set_html(html)
                except Exception as e:
                    self._log(f"Could not update Plotly view: {e}\n")
                # Save html to file for browser fallback
                try:
                    os.makedirs("results", exist_ok=True)
                    path = os.path.join("results", "interactive_3d.html")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write("<meta charset='utf-8'>\n" + html)
                    self._last_plotly_html = html
                    self._last_plotly_html_path = os.path.abspath(path)
                except Exception as e:
                    self._log(f"Could not save interactive 3D HTML: {e}\n")
                self._log("Rendered interactive 3D surface (Plotly).\n")
            else:
                # Fallback to Matplotlib wireframe
                self.ax3d.clear()
                self.ax3d.plot_wireframe(
                    X, Y, Z,
                    rstride=max(1, X.shape[0] // 60),
                    cstride=max(1, X.shape[1] // 32),
                    color="#ffffff", linewidth=0.6, alpha=1.0,
                )
                self.ax3d.set_xlabel("x [m]")
                self.ax3d.set_ylabel("y [m]")
                self.ax3d.set_zlabel("z [m]")
                self.ax3d.set_title("Fuselage (revolved)", pad=4)
                self._set_axes_equal(self.ax3d, X, Y, Z)
                # Force equal aspect if supported (Matplotlib >=3.3)
                try:
                    self.ax3d.set_box_aspect([1, 1, 1])
                except Exception:
                    pass
                # Tighten margins after limits set and maximize axes area
                self._tighten_mpl_margins()
                self._maximize_mpl_axes()
                # Pure black background
                try:
                    self.fig3d.patch.set_facecolor("#000000")
                    self.ax3d.set_facecolor("#000000")
                except Exception:
                    pass
                # Apply axis visibility preference
                try:
                    show = bool(self.show_axes_var.get())
                    if not show:
                        # Hide axes
                        self.ax3d.set_axis_off()
                    else:
                        self.ax3d.set_axis_on()
                except Exception:
                    pass
                self.canvas3d.draw()
                self._log("Rendered 3D wireframe (Matplotlib fallback).\n")
        except Exception as e:
            self._log(f"3D render failed: {e}\n")

    @staticmethod
    def _set_axes_equal(ax, X, Y, Z):
        # Equalize axes for 3D
        x_min, x_max = np.nanmin(X), np.nanmax(X)
        y_min, y_max = np.nanmin(Y), np.nanmax(Y)
        z_min, z_max = np.nanmin(Z), np.nanmax(Z)
        x_range = x_max - x_min
        y_range = y_max - y_min
        z_range = z_max - z_min
        max_range = max(x_range, y_range, z_range)
        x_mid = 0.5 * (x_max - x_min) + x_min
        y_mid = 0.5 * (y_max - y_min) + y_min
        z_mid = 0.5 * (z_max - z_min) + z_min
        half = 0.5 * max_range
        ax.set_xlim(x_mid - half, x_mid + half)
        ax.set_ylim(y_mid - half, y_mid + half)
        ax.set_zlim(z_mid - half, z_mid + half)

    # ---------- Theming ----------
    def _apply_dark_theme(self):
        # Palette
        bg = "#121212"            # window background
        surface = "#1e1e1e"       # frames, panels
        surface_alt = "#252525"   # entries, editor
        border = "#2a2a2a"
        fg = "#e5e5e5"
        fg_muted = "#bdbdbd"
        accent = "#3b82f6"        # blue
        accent_active = "#2563eb"
        select_bg = "#2b4ea2"

        # Root window
        try:
            self.configure(bg=bg)
        except Exception:
            pass

        # Fonts (clean, modern sizing)
        try:
            default_font = tkfont.nametofont("TkDefaultFont")
            text_font = tkfont.nametofont("TkTextFont")
            heading_font = tkfont.nametofont("TkHeadingFont")
            default_font.configure(size=10)
            text_font.configure(size=10)
            heading_font.configure(size=11, weight="bold")
        except Exception:
            pass

        style = ttk.Style(self)
        # Use a theme that respects custom colors
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Global defaults
        style.configure(
            ".",
            background=surface,
            foreground=fg,
            fieldbackground=surface_alt,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            troughcolor=surface_alt,
            focusthickness=2,
            focuscolor=accent,
        )

        # Frames and labels
        for cls in ("TFrame", "TLabelFrame"):
            style.configure(cls, background=surface, foreground=fg, bordercolor=border)
        style.configure("TLabel", background=surface, foreground=fg)

        # Paned windows and separators
        style.configure("TPanedwindow", background=surface, sashrelief="flat", sashthickness=6)
        style.configure("TSeparator", background=border)

        # Buttons
        style.configure(
            "TButton",
            background=surface_alt,
            foreground=fg,
            borderwidth=0,
            padding=(10, 6),
            relief="flat",
        )
        style.map(
            "TButton",
            background=[("pressed", surface), ("active", surface)],
            foreground=[("disabled", fg_muted)],
            relief=[("pressed", "sunken"), ("!pressed", "flat")],
        )
        # Accent button (e.g., Run)
        style.configure(
            "Accent.TButton",
            background=accent,
            foreground="#ffffff",
            borderwidth=0,
            padding=(12, 7),
            relief="flat",
        )
        style.map(
            "Accent.TButton",
            background=[("pressed", accent_active), ("active", accent_active)],
            foreground=[("disabled", fg_muted)],
        )
        # Apply accent to Run button
        try:
            self.run_btn.configure(style="Accent.TButton")
        except Exception:
            pass

        # Entries and scrollbars
        style.configure("TEntry", fieldbackground=surface_alt, foreground=fg, insertcolor=fg, bordercolor=border)
        style.configure("TScrollbar", background=surface_alt, troughcolor=surface, bordercolor=border, arrowcolor=fg)

        # LabelFrames titles
        style.configure("TLabelframe.Label", background=surface, foreground=fg)

        # tk.Text widgets: log
        for text_widget in (self.log,):
            try:
                text_widget.configure(
                    bg=surface_alt,
                    fg=fg,
                    insertbackground=fg,
                    selectbackground=select_bg,
                    selectforeground="#ffffff",
                    highlightthickness=1,
                    highlightbackground=border,
                    highlightcolor=accent,
                )
            except Exception:
                pass

        # Matplotlib dark styling (if present)
        if getattr(self, "fig3d", None) is not None and getattr(self, "ax3d", None) is not None:
            if not getattr(self, "_use_plotly", False) and not getattr(self, "_use_vtk", False):
                # Matplotlib wireframe mode prefers pure black background
                try:
                    self.fig3d.patch.set_facecolor("#000000")
                    self.ax3d.set_facecolor("#000000")
                except Exception:
                    pass
            else:
                self._apply_dark_mpl(surface, fg, border)
        if getattr(self, "toolbar3d", None) is not None:
            self._style_toolbar_dark(self.toolbar3d, surface, fg)
        if getattr(self, "vtk_renderer", None) is not None:
            self._apply_vtk_dark(self.vtk_renderer)

        # Larger fonts for Summary and Config areas via dedicated styles
        try:
            # Summary labels and values
            if getattr(self, "_summary_label_font", None) is not None:
                style.configure("SummaryLabel.TLabel", font=self._summary_label_font, background=surface, foreground=fg)
            if getattr(self, "_summary_value_font", None) is not None:
                style.configure("SummaryValue.TLabel", font=self._summary_value_font, background=surface, foreground=fg)

            # Configuration form widgets
            if getattr(self, "_config_font", None) is not None:
                style.configure("Config.TLabel", font=self._config_font, background=surface, foreground=fg)
                style.configure("Config.TEntry", font=self._config_font)
                style.configure("Config.TCheckbutton", font=self._config_font)
                style.configure("Config.TCombobox", font=self._config_font)
                style.configure("Config.TButton", font=self._config_font)
                style.configure("Config.TNotebook.Tab", font=self._config_font)
        except Exception:
            pass

        # 2D Matplotlib dark styling (lazy canvas)
        try:
            if getattr(self, 'fig2d', None) is not None and getattr(self, 'ax2d', None) is not None:
                self.fig2d.patch.set_facecolor(surface)
                self.ax2d.set_facecolor(surface)
                self.ax2d.tick_params(colors=fg)
                for spine in self.ax2d.spines.values():
                    spine.set_color(border)
                self.ax2d.title.set_color(fg)
                self.ax2d.xaxis.label.set_color(fg)
                self.ax2d.yaxis.label.set_color(fg)
                if getattr(self, 'canvas2d', None) is not None:
                    self.canvas2d.draw_idle()
        except Exception:
            pass

    def _apply_dark_mpl(self, surface: str, fg: str, grid: str):
        try:
            # Figure and axes face
            self.fig3d.patch.set_facecolor(surface)
            self.ax3d.set_facecolor(surface)
            # Axis labels and ticks
            for axis in [self.ax3d.xaxis, self.ax3d.yaxis, self.ax3d.zaxis]:
                axis.label.set_color(fg)
                axis.set_tick_params(colors=fg, pad=1)
            # Title
            self.ax3d.title.set_color(fg)
            # Gridline color is subtle
            for axis in [self.ax3d.xaxis, self.ax3d.yaxis, self.ax3d.zaxis]:
                try:
                    axis._axinfo["grid"]["color"] = grid
                except Exception:
                    pass
            # Tighten margins in dark mode too
            self._tighten_mpl_margins()
            self.canvas3d.draw_idle()
        except Exception:
            pass

    def _tighten_mpl_margins(self):
        try:
            # Minimal padding between subplots and figure edge
            try:
                self.fig3d.set_constrained_layout_pads(w_pad=0.0, h_pad=0.0, hspace=0.0, wspace=0.0)
            except Exception:
                pass
            # Reduce label distance and remove data margins
            try:
                self.ax3d.xaxis.labelpad = 2
                self.ax3d.yaxis.labelpad = 2
                self.ax3d.zaxis.labelpad = 2
            except Exception:
                pass
            try:
                self.ax3d.margins(0.0)
            except Exception:
                pass
        except Exception:
            pass

    def _maximize_mpl_axes(self):
        try:
            # Prefer explicit subplot adjustments to occupy entire canvas
            try:
                # Disable any layout engine (constrained/tight) to fully control position
                le = getattr(self.fig3d, 'get_layout_engine', None)
                if callable(le):
                    ge = self.fig3d.get_layout_engine()
                # Prefer new API if available
                sle = getattr(self.fig3d, 'set_layout_engine', None)
                if callable(sle):
                    self.fig3d.set_layout_engine(None)
                else:
                    self.fig3d.set_constrained_layout(False)
            except Exception:
                pass
            try:
                self.fig3d.subplots_adjust(left=0, right=1, bottom=0, top=1)
            except Exception:
                pass
            try:
                self.ax3d.set_position([0.0, 0.0, 1.0, 1.0])
            except Exception:
                pass
            try:
                # Hide spines if any
                for sp in getattr(self.ax3d, 'spines', {}).values():
                    sp.set_visible(False)
            except Exception:
                pass
        except Exception:
            pass

    def _toggle_axes(self):
        try:
            show = bool(self.show_axes_var.get())
            if not self._use_plotly and not self._use_vtk and getattr(self, "ax3d", None) is not None:
                try:
                    if show:
                        self.ax3d.set_axis_on()
                    else:
                        self.ax3d.set_axis_off()
                except Exception:
                    pass
                # Re-apply equal aspect using last surface extents if available
                try:
                    surf = getattr(self, "_last_surface", None)
                    if surf is not None:
                        X, Y, Z = surf
                        self._set_axes_equal(self.ax3d, X, Y, Z)
                        try:
                            self.ax3d.set_box_aspect([1, 1, 1])
                        except Exception:
                            pass
                except Exception:
                    pass
                self.canvas3d.draw_idle()
            elif self._use_plotly:
                # Re-render a wireframe-like plot with axis visibility according to toggle
                try:
                    surf = getattr(self, "_last_surface", None)
                    if surf is None:
                        return
                    X, Y, Z = surf
                    import plotly.graph_objects as go
                    fig = go.Figure(
                        data=[
                            go.Surface(x=X, y=Y, z=Z, colorscale=[[0, "#ffffff"],[1, "#ffffff"]], showscale=False, opacity=0.0,
                                       contours=dict(
                                           x=dict(show=True, color="#ffffff"),
                                           y=dict(show=True, color="#ffffff"),
                                           z=dict(show=True, color="#ffffff"),
                                       ))
                        ]
                    )
                    fig.update_layout(
                        paper_bgcolor="#000000", plot_bgcolor="#000000",
                        scene=dict(
                            bgcolor="#000000",
                            xaxis=dict(visible=show, color="#f0f0f0"),
                            yaxis=dict(visible=show, color="#f0f0f0"),
                            zaxis=dict(visible=show, color="#f0f0f0"),
                            aspectmode="data",
                        ),
                        margin=dict(l=0, r=0, t=20, b=0),
                        title="Fuselage (wireframe)",
                        uirevision=str(self._plotly_uirev),
                    )
                    config = dict(scrollZoom=True, displaylogo=False)
                    html = fig.to_html(include_plotlyjs=True, full_html=False, config=config)
                    if hasattr(self.view3d_html, "load_html"):
                        self.view3d_html.load_html(html)
                    elif hasattr(self.view3d_html, "set_html"):
                        self.view3d_html.set_html(html)
                except Exception:
                    pass
            # VTK path omitted (no axes actor by default)
        except Exception:
            pass

    def _open_interactive_3d(self):
        try:
            # Ensure we have an HTML file for interactive 3D
            path = self._last_plotly_html_path
            if not path or not os.path.exists(path):
                # Generate from last surface if available
                surf = getattr(self, "_last_surface", None)
                if surf is None:
                    messagebox.showinfo("Interactive 3D", "No 3D view available yet. Run a case first.")
                    return
                X, Y, Z = surf
                try:
                    import plotly.graph_objects as go
                except Exception:
                    messagebox.showinfo("Interactive 3D", "Plotly is not installed. Install with: pip install plotly")
                    return
                fig = go.Figure(
                    data=[
                        go.Surface(x=X, y=Y, z=Z, colorscale="Blues", showscale=False, opacity=1.0)
                    ]
                )
                fig.update_layout(
                    title="Fuselage (revolved)",
                    margin=dict(l=0, r=0, t=30, b=0),
                    scene=dict(xaxis_title="x [m]", yaxis_title="y [m]", zaxis_title="z [m]", aspectmode="data"),
                    uirevision=str(self._plotly_uirev),
                )
                # Prefer dark background
                try:
                    self._apply_plotly_dark(fig)
                except Exception:
                    pass
                config = dict(scrollZoom=True, displaylogo=False)
                html = fig.to_html(include_plotlyjs=True, full_html=False, config=config)
                try:
                    os.makedirs("results", exist_ok=True)
                    path = os.path.join("results", "interactive_3d.html")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write("<meta charset='utf-8'>\n" + html)
                    self._last_plotly_html = html
                    self._last_plotly_html_path = os.path.abspath(path)
                except Exception as e:
                    self._log(f"Could not save interactive 3D HTML: {e}\n")
                    messagebox.showerror("Interactive 3D", f"Could not save HTML file.\n\n{e}")
                    return
            # Open via pywebview if available; else default browser
            path = self._last_plotly_html_path
            if HAS_PYWEBVIEW:
                try:
                    # Launch pywebview in a background thread to avoid blocking Tk
                    import webview as _wv
                    with open(path, "r", encoding="utf-8") as f:
                        html = f.read()
                    def _run_webview():
                        try:
                            _wv.create_window("Fuselage 3D", html=html, width=1000, height=700)
                            _wv.start()
                        except Exception as e:
                            # Fallback to browser from main thread
                            self.after(0, lambda: self._log(f"pywebview failed, opening browser: {e}\n"))
                            try:
                                import webbrowser as _wb
                                _wb.open_new_tab(f"file://{path}")
                            except Exception:
                                pass
                    threading.Thread(target=_run_webview, daemon=True).start()
                    return
                except Exception as e:
                    self._log(f"pywebview launch failed, falling back to browser: {e}\n")
            try:
                import webbrowser
                webbrowser.open_new_tab(f"file://{path}")
            except Exception as e:
                messagebox.showerror("Interactive 3D", f"Could not open browser.\n\n{e}")
        except Exception as e:
            self._log(f"Open interactive 3D failed: {e}\n")

    def _style_toolbar_dark(self, toolbar: NavigationToolbar2Tk, bg: str, fg: str):
        try:
            toolbar.configure(background=bg)
            for child in toolbar.winfo_children():
                widget_class = child.winfo_class().lower()
                try:
                    if "label" in widget_class:
                        child.configure(background=bg, foreground=fg)
                    elif "button" in widget_class:
                        child.configure(background=bg, activebackground=bg, foreground=fg, relief=tk.FLAT, bd=0, highlightthickness=0)
                except Exception:
                    pass
        except Exception:
            pass

    def _apply_plotly_dark(self, fig):
        """Apply dark colors to Plotly figure consistent with the app theme."""
        try:
            fig.update_layout(
                paper_bgcolor="#1e1e1e",
                plot_bgcolor="#1e1e1e",
                font=dict(color="#e5e5e5"),
                scene=dict(
                    xaxis=dict(
                        gridcolor="#2a2a2a", zerolinecolor="#2a2a2a", color="#e5e5e5"
                    ),
                    yaxis=dict(
                        gridcolor="#2a2a2a", zerolinecolor="#2a2a2a", color="#e5e5e5"
                    ),
                    zaxis=dict(
                        gridcolor="#2a2a2a", zerolinecolor="#2a2a2a", color="#e5e5e5"
                    ),
                    bgcolor="#1e1e1e",
                ),
            )
        except Exception:
            pass

    # ---------- VTK helpers ----------
    def _build_vtk_surface(self, X, Y, Z):
        """Create a VTK surface from gridded X,Y,Z arrays."""
        n_i, n_j = X.shape
        points = vtkPoints()
        points.SetNumberOfPoints(n_i * n_j)
        # Insert points row-major
        idx = 0
        for i in range(n_i):
            for j in range(n_j):
                points.SetPoint(idx, float(X[i, j]), float(Y[i, j]), float(Z[i, j]))
                idx += 1

        polys = vtkCellArray()
        # Build quads as two triangles
        def idx_of(i, j):
            return i * n_j + j
        for i in range(n_i - 1):
            for j in range(n_j - 1):
                p0 = idx_of(i, j)
                p1 = idx_of(i + 1, j)
                p2 = idx_of(i + 1, j + 1)
                p3 = idx_of(i, j + 1)
                # Triangle 1: p0, p1, p2
                polys.InsertNextCell(3)
                polys.InsertCellPoint(p0)
                polys.InsertCellPoint(p1)
                polys.InsertCellPoint(p2)
                # Triangle 2: p0, p2, p3
                polys.InsertNextCell(3)
                polys.InsertCellPoint(p0)
                polys.InsertCellPoint(p2)
                polys.InsertCellPoint(p3)

        # Wrap last column to first to close the surface (if ring is closed)
        j_last = n_j - 1
        for i in range(n_i - 1):
            p0 = idx_of(i, j_last)
            p1 = idx_of(i + 1, j_last)
            p2 = idx_of(i + 1, 0)
            p3 = idx_of(i, 0)
            polys.InsertNextCell(3)
            polys.InsertCellPoint(p0)
            polys.InsertCellPoint(p1)
            polys.InsertCellPoint(p2)
            polys.InsertNextCell(3)
            polys.InsertCellPoint(p0)
            polys.InsertCellPoint(p2)
            polys.InsertCellPoint(p3)

        polydata = vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetPolys(polys)

        mapper = vtkPolyDataMapper()
        mapper.SetInputData(polydata)

        actor = vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetColor(0.45, 0.64, 0.85)  # steelblue-ish
        prop.SetOpacity(1.0)
        prop.SetInterpolationToPhong()
        return actor

    def _apply_vtk_dark(self, renderer):
        try:
            # Dark background and subtle gray grid-like ambiance (no grid in VTK)
            renderer.SetBackground(0.117, 0.117, 0.117)  # ~#1e1e1e
        except Exception:
            pass

    def _open_plotly_in_browser(self):
        try:
            path = self._last_plotly_html_path
            if not path or not os.path.exists(path):
                messagebox.showinfo("3D Viewer", "No 3D view available yet. Run a case first.")
                return
            import webbrowser
            webbrowser.open_new_tab(f"file://{path}")
        except Exception as e:
            self._log(f"Could not open 3D view in browser: {e}\n")

    # ---------- Plot builders ----------
    def _compute_distributions(self, payload: dict, cfg: dict):
        geom = payload.get("geom", {})
        x = np.asarray(geom.get("x")); y = np.asarray(geom.get("y"))
        op = cfg.get("op", {})
        cf_model = cfg.get("cf_model", {})
        V = float(op.get("V", 0.0)); rho = float(op.get("rho", 0.0)); nu = float(op.get("nu", 1.0))
        mode = cf_model.get("mode", "turbulent"); ktr = float(cf_model.get("k_transition", 1700.0))
        if x is None or y is None or x.size == 0:
            raise ValueError("No geometry available for distributions")
        dx = np.gradient(x)
        dy = np.gradient(y, x)
        Re_x = np.clip(V * x / max(nu, 1e-12), a_min=1e-6, a_max=None)
        # Local Cf approximations (flat plate correlations)
        Cf_lam = 0.664 / np.sqrt(np.maximum(Re_x, 1.0))
        Cf_turb = 0.0592 / np.power(np.maximum(Re_x, 1.0), 0.2)
        if mode == 'laminar':
            Cf_local = Cf_lam
        elif mode == 'turbulent':
            Cf_local = np.maximum(Cf_turb, 0.0)
        else:
            # Transition (Hoerner-like local correction)
            Cf_local = np.maximum(Cf_turb - ktr/np.sqrt(np.maximum(Re_x,1.0)), 0.0)
        q = 0.5 * rho * V * V
        tau_w = q * Cf_local
        dSdx = 2.0 * np.pi * y * np.sqrt(1.0 + dy*dy)
        Df_cum = np.cumsum(tau_w * dSdx * dx)
        return {
            'x': x, 'Re_x': Re_x, 'Cf_local': Cf_local, 'tau_w': tau_w, 'Df_cum': Df_cum
        }

    def _clear_ax2d(self):
        self.ax2d.clear()
        self.ax2d.grid(True, alpha=0.3)

    def _render_plot_rex(self, payload: dict, cfg: dict):
        self._ensure_2d_canvas()
        self.view_frame.configure(text="Re_x vs x")
        dat = self._compute_distributions(payload, cfg)
        self._clear_ax2d()
        self.ax2d.plot(dat['x'], dat['Re_x'], lw=1.6)
        self.ax2d.set_xlabel('x [m]'); self.ax2d.set_ylabel('Re_x')
        self.ax2d.set_title('Local Reynolds number Re_x(x)')
        self.canvas2d.draw()

    def _render_plot_cflocal(self, payload: dict, cfg: dict):
        self._ensure_2d_canvas()
        self.view_frame.configure(text="Cf_local vs x")
        dat = self._compute_distributions(payload, cfg)
        self._clear_ax2d()
        self.ax2d.plot(dat['x'], dat['Cf_local'], lw=1.6)
        self.ax2d.set_xlabel('x [m]'); self.ax2d.set_ylabel('Cf_local [-]')
        self.ax2d.set_title('Local skin-friction coefficient Cf(x) (approx.)')
        self.canvas2d.draw()

    def _render_plot_tau(self, payload: dict, cfg: dict):
        self._ensure_2d_canvas()
        self.view_frame.configure(text="tau_w vs x")
        dat = self._compute_distributions(payload, cfg)
        self._clear_ax2d()
        self.ax2d.plot(dat['x'], dat['tau_w'], lw=1.6)
        self.ax2d.set_xlabel('x [m]'); self.ax2d.set_ylabel('tau_w [Pa]')
        self.ax2d.set_title('Wall shear stress τ_w(x) (approx.)')
        self.canvas2d.draw()

    def _render_plot_df_cum(self, payload: dict, cfg: dict):
        self._ensure_2d_canvas()
        self.view_frame.configure(text="Cumulative friction drag")
        dat = self._compute_distributions(payload, cfg)
        self._clear_ax2d()
        self.ax2d.plot(dat['x'], dat['Df_cum'], lw=1.6)
        self.ax2d.set_xlabel('x [m]'); self.ax2d.set_ylabel('∫ τ_w dS [N]')
        self.ax2d.set_title('Cumulative friction drag vs x (approx.)')
        self.canvas2d.draw()

    def _render_sweep_ld(self, cfg: dict):
        from src.calcs import aero_from_geometry
        self._ensure_2d_canvas()
        self.view_frame.configure(text="Sweep: CD_total vs l/d")
        d = float(cfg['geom']['d']); op = cfg['op']; cf_model = cfg['cf_model']
        ld_grid = np.linspace(1.5, 12.0, 60)
        CDs = []
        for ld in ld_grid:
            l = ld * d
            geom_tmp = {'l': l, 'd': d}
            aero = aero_from_geometry(geom_tmp, op, cf_model)
            CDs.append(aero['CD_total'])
        CDs = np.asarray(CDs)
        self._clear_ax2d()
        self.ax2d.plot(ld_grid, CDs, lw=1.8)
        self.ax2d.set_xlabel('l/d'); self.ax2d.set_ylabel('C_D total [-]')
        self.ax2d.set_title('C_D vs thinness ratio (with base drag)')
        self.canvas2d.draw()

    def _render_sweep_base_ratio(self, cfg: dict):
        from src.calcs import aero_from_geometry
        self._ensure_2d_canvas()
        self.view_frame.configure(text="Sweep: CD_total vs base_ratio")
        geom = cfg['geom']; op = dict(cfg['op']); cf_model = cfg['cf_model']
        br_grid = np.linspace(0.0, 0.8, 41)
        CDs = []
        for br in br_grid:
            op_tmp = dict(op); op_tmp['base_ratio'] = br
            aero = aero_from_geometry(geom, op_tmp, cf_model)
            CDs.append(aero['CD_total'])
        CDs = np.asarray(CDs)
        self._clear_ax2d()
        self.ax2d.plot(br_grid, CDs, lw=1.8)
        self.ax2d.set_xlabel('base_ratio'); self.ax2d.set_ylabel('C_D total [-]')
        self.ax2d.set_title('C_D vs base_ratio (flat base penalty)')
        self.canvas2d.draw()

    def _render_sweep_V(self, cfg: dict):
        from src.calcs import aero_from_geometry
        self._ensure_2d_canvas()
        self.view_frame.configure(text="Sweep: CD_total vs V")
        geom = cfg['geom']; op = dict(cfg['op']); cf_model = cfg['cf_model']
        V0 = float(op['V']); V_grid = np.linspace(max(0.1, 0.25*V0), 2.5*V0, 60)
        CDs = []
        for V in V_grid:
            op_tmp = dict(op); op_tmp['V'] = float(V)
            aero = aero_from_geometry(geom, op_tmp, cf_model)
            CDs.append(aero['CD_total'])
        CDs = np.asarray(CDs)
        self._clear_ax2d()
        self.ax2d.plot(V_grid, CDs, lw=1.8)
        self.ax2d.set_xlabel('V [m/s]'); self.ax2d.set_ylabel('C_D total [-]')
        self.ax2d.set_title('C_D vs speed V (Re effects)')
        self.canvas2d.draw()

    def _render_sweep_k3d(self, cfg: dict):
        from src.calcs import aero_from_geometry
        self._ensure_2d_canvas()
        self.view_frame.configure(text="Sweep: CD_total vs 3D correction")
        geom = cfg['geom']; op = cfg['op']; cf_model = dict(cfg['cf_model'])
        k0 = float(cf_model['threeD_correction']); k_grid = np.linspace(0.8*k0, 1.3*k0, 41)
        CDs = []
        for k in k_grid:
            cfm = dict(cf_model); cfm['threeD_correction'] = float(k)
            aero = aero_from_geometry(geom, op, cfm)
            CDs.append(aero['CD_total'])
        CDs = np.asarray(CDs)
        self._clear_ax2d()
        self.ax2d.plot(k_grid, CDs, lw=1.8)
        self.ax2d.set_xlabel('threeD_correction'); self.ax2d.set_ylabel('C_D total [-]')
        self.ax2d.set_title('C_D vs 3D correction factor')
        self.canvas2d.draw()

    def _render_overlay_modes(self, cfg: dict):
        from src.calcs import aero_from_geometry
        self._ensure_2d_canvas()
        self.view_frame.configure(text="Overlay: CD_total vs l/d (modes)")
        d = float(cfg['geom']['d']); op = cfg['op']; cf_model = cfg['cf_model']
        ld_grid = np.linspace(1.5, 12.0, 60)
        modes = ['laminar', 'transition', 'turbulent']
        self._clear_ax2d()
        for m in modes:
            CDs = []
            cfm = dict(cf_model); cfm['mode'] = m
            for ld in ld_grid:
                l = ld * d
                geom_tmp = {'l': l, 'd': d}
                aero = aero_from_geometry(geom_tmp, op, cfm)
                CDs.append(aero['CD_total'])
            self.ax2d.plot(ld_grid, np.asarray(CDs), lw=1.6, label=m)
        self.ax2d.set_xlabel('l/d'); self.ax2d.set_ylabel('C_D total [-]')
        self.ax2d.set_title('C_D vs l/d for laminar/transition/turbulent')
        self.ax2d.legend()
        self.canvas2d.draw()


def main():
    app = FuselageLabApp()
    app.mainloop()


if __name__ == "__main__":
    main()
