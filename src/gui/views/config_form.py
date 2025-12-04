import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
import os

class ConfigForm(ctk.CTkFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.cfg_vars = {}
        self._init_vars()
        self._build_ui()
        
    def _init_vars(self):
        self.cfg_vars = {
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

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Tabview (replaces Notebook)
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Create tabs
        self.tabview.add("Geometry")
        self.tabview.add("Operation")
        self.tabview.add("CF Model")
        self.tabview.add("Builder")
        self.tabview.add("Mass")
        self.tabview.add("I/O")
        self.tabview.add("Plots")

        # Geometry
        tab_geom = self.tabview.tab("Geometry")
        self._form_grid(tab_geom, [
            ("Length [m]", self.cfg_vars["geom"]["l"]),
            ("Diameter [m]", self.cfg_vars["geom"]["d"]),
            ("Base ratio", self.cfg_vars["geom"]["base_ratio"]),
        ])

        # Operation
        tab_op = self.tabview.tab("Operation")
        self._form_grid(tab_op, [
            ("Velocity V [m/s]", self.cfg_vars["op"]["V"]),
            ("Density rho [kg/m³]", self.cfg_vars["op"]["rho"]),
            ("Kinematic viscosity nu [m²/s]", self.cfg_vars["op"]["nu"]),
        ])

        # Cf Model
        tab_cf = self.tabview.tab("CF Model")
        ctk.CTkLabel(tab_cf, text="Mode").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        mode_cb = ctk.CTkComboBox(tab_cf, variable=self.cfg_vars["cf_model"]["mode"], values=["laminar", "transition", "turbulent"], state="readonly")
        mode_cb.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        tab_cf.grid_columnconfigure(1, weight=1)
        self._form_row(tab_cf, 1, "Transition k", self.cfg_vars["cf_model"]["k_transition"])
        self._form_row(tab_cf, 2, "3D correction", self.cfg_vars["cf_model"]["threeD_correction"])

        # Builder
        tab_bld = self.tabview.tab("Builder")
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
        cb = ctk.CTkCheckBox(tab_bld, text="Limit tail angle", variable=self.cfg_vars["builder"]["enforce_tail_angle"])
        cb.grid(row=len(rows), column=0, columnspan=2, sticky="w", padx=10, pady=5)

        # Mass
        tab_mass = self.tabview.tab("Mass")
        tab_mass.grid_columnconfigure(1, weight=1)
        self.mass_sigma_entry = None
        self.mass_rho_entry = None
        self.mass_tskin_entry = None
        cb_usd = ctk.CTkCheckBox(tab_mass, text="Use surface density", variable=self.cfg_vars["mass"]["use_surface_density"], command=self._toggle_mass_mode)
        cb_usd.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        self._form_row(tab_mass, 1, "Surface density sigma [kg/m²]", self.cfg_vars["mass"]["sigma_surface"], entry_ref_attr="mass_sigma_entry")
        self._form_row(tab_mass, 2, "Material density rho [kg/m³]", self.cfg_vars["mass"]["rho_material"], entry_ref_attr="mass_rho_entry")
        self._form_row(tab_mass, 3, "Skin thickness t_skin [m]", self.cfg_vars["mass"]["t_skin"], entry_ref_attr="mass_tskin_entry")
        cb_base = ctk.CTkCheckBox(tab_mass, text="Include base disk area", variable=self.cfg_vars["mass"]["include_base_disk_area"])
        cb_base.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        self._form_row(tab_mass, 5, "Gravity g [m/s²]", self.cfg_vars["mass"]["g"])

        # I/O
        tab_io = self.tabview.tab("I/O")
        tab_io.grid_columnconfigure(1, weight=1)
        cb_csv = ctk.CTkCheckBox(tab_io, text="Export CSV", variable=self.cfg_vars["io"]["export_csv"])
        cb_csv.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        ctk.CTkLabel(tab_io, text="CSV path").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        e_csv = ctk.CTkEntry(tab_io, textvariable=self.cfg_vars["io"]["csv_path"])
        e_csv.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        ctk.CTkButton(tab_io, text="Browse…", command=self._browse_csv_path, width=80).grid(row=1, column=2, sticky="w", padx=(0,10), pady=5)

        # Plots
        tab_plots = self.tabview.tab("Plots")
        tab_plots.grid_columnconfigure(1, weight=1)
        cb_plots = ctk.CTkCheckBox(tab_plots, text="Make plots", variable=self.cfg_vars["plots"]["make_plots"])
        cb_plots.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        self._form_row(tab_plots, 1, "DPI", self.cfg_vars["plots"]["dpi"])

    def _form_grid(self, parent, rows):
        parent.grid_columnconfigure(1, weight=1)
        for i, (label, var) in enumerate(rows):
            ctk.CTkLabel(parent, text=label).grid(row=i, column=0, sticky="w", padx=10, pady=5)
            e = ctk.CTkEntry(parent, textvariable=var)
            e.grid(row=i, column=1, sticky="ew", padx=10, pady=5)

    def _form_row(self, parent, row, label, var, entry_ref_attr=None):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=5)
        e = ctk.CTkEntry(parent, textvariable=var)
        e.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
        parent.grid_columnconfigure(1, weight=1)
        if entry_ref_attr:
            setattr(self, entry_ref_attr, e)

    def _toggle_mass_mode(self):
        try:
            use_sigma = bool(self.cfg_vars["mass"]["use_surface_density"].get())
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

    def load_from_dict(self, cfg):
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
            self._toggle_mass_mode()

    def get_config(self):
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
        return cfg
