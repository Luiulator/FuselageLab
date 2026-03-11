import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
import os
from PIL import Image

class ConfigForm(ctk.CTkFrame):
    def __init__(self, parent, on_method_change=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.on_method_change = on_method_change
        
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
                "Mach": tk.StringVar(),
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
                "nose_type": tk.StringVar(value="Haack"),
                # Tubular params
                "parametrization_method": tk.StringVar(value="fractions"),
                "FRn": tk.StringVar(),
                "FRt": tk.StringVar(),
                "Lc": tk.StringVar(),
                "Ln": tk.StringVar(),
                "Lt": tk.StringVar(),
                "hw": tk.StringVar(),
                "hu": tk.StringVar(),
                "rn": tk.StringVar(),
                "use_double_nose": tk.BooleanVar(),
                "psi": tk.StringVar(),
                "theta": tk.StringVar(),
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
        }

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 0. Top Level Mode Selector
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        ctk.CTkLabel(self.top_frame, text="Fuselage Type:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        self.mode_selector = ctk.CTkSegmentedButton(self.top_frame, values=["Fractions", "Tubular"], command=self._on_mode_change)
        self.mode_selector.pack(side="left", padx=5)
        
        # 1. Tabview container
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Initial build
        current_method = self.cfg_vars["builder"]["parametrization_method"].get() or "fractions"
        self.mode_selector.set("Tubular" if current_method == "tubular" else "Fractions")
        self._rebuild_tabs(current_method)

        # Mass
        tab_mass = self.tabview.tab("Mass")
        tab_mass.grid_columnconfigure(1, weight=1)
        self.mass_sigma_entry = None
        self.mass_rho_entry = None
        self.mass_tskin_entry = None
        cb_usd = ctk.CTkCheckBox(tab_mass, text="Use surface density", variable=self.cfg_vars["mass"]["use_surface_density"], command=self._toggle_mass_mode)
        cb_usd.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        self._form_row(tab_mass, 1, "σ_s - Surface Density [kg/m²]", self.cfg_vars["mass"]["sigma_surface"], entry_ref_attr="mass_sigma_entry")
        self._form_row(tab_mass, 2, "ρ_m - Material Density [kg/m³]", self.cfg_vars["mass"]["rho_material"], entry_ref_attr="mass_rho_entry")
        self._form_row(tab_mass, 3, "t_s - Skin Thickness [m]", self.cfg_vars["mass"]["t_skin"], entry_ref_attr="mass_tskin_entry")
        cb_base = ctk.CTkCheckBox(tab_mass, text="Include base disk area", variable=self.cfg_vars["mass"]["include_base_disk_area"])
        cb_base.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        self._form_row(tab_mass, 5, "g - Gravity [m/s²]", self.cfg_vars["mass"]["g"])

    def _on_mode_change(self, value):
        method = "tubular" if value == "Tubular" else "fractions"
        self.cfg_vars["builder"]["parametrization_method"].set(method)
        self._rebuild_tabs(method)
        if self.on_method_change:
            self.on_method_change(method)

    def _rebuild_tabs(self, method):
        # 1. Clear existing tabs
        existing = ["Geometry", "Operation", "CF Model", "Builder", "Mass", "I/O"]
        for tab_name in existing:
            try:
                self.tabview.delete(tab_name)
            except Exception:
                pass
        
        # 2. Add tabs based on method
        
        # --- Geometry ---
        self.tabview.add("Geometry")
        tab_geom = self.tabview.tab("Geometry")
        geom_rows = []
        if method == "fractions":
            # --- Nose Type Combo ---
            # We add it manually to grid before dynamic rows
            ctk.CTkLabel(tab_geom, text="Nose Profile").grid(row=0, column=0, sticky="w", padx=10, pady=5)
            
            # Ensure var exists (should be loaded from config/defaults)
            if "nose_type" not in self.cfg_vars["builder"]:
                 self.cfg_vars["builder"]["nose_type"] = tk.StringVar(value="Haack")
            
            nose_cb = ctk.CTkComboBox(tab_geom, variable=self.cfg_vars["builder"]["nose_type"], 
                                      values=["Haack", "Simple"], 
                                      command=lambda val: self._rebuild_tabs("fractions"))
            nose_cb.grid(row=0, column=1, sticky="w", padx=10, pady=5)
            
            # --- Dynamic Rows ---
            geom_rows.extend([
                ("L_f - Total Length [m]", self.cfg_vars["geom"]["l"]),
                ("d_f - Fuselage Diameter [m]", self.cfg_vars["geom"]["d"]),
                ("kᵦ - Base Ratio [-]", self.cfg_vars["geom"]["base_ratio"]),
                ("λₙ - Nose Fraction [-]", self.cfg_vars["builder"]["Ln_frac"]),
                ("λₜ - Tail Fraction [-]", self.cfg_vars["builder"]["Lt_frac"]),
            ])
            
            # Nose Specifics
            current_nose = self.cfg_vars["builder"]["nose_type"].get()
            if current_nose == "Haack":
                geom_rows.append(("C_h - Haack Parameter [-]", self.cfg_vars["builder"]["C_haack"]))
            else: # Simple
                geom_rows.extend([
                    ("Bₙ - Nose Bluntness [-]", self.cfg_vars["builder"]["rn"]), # Using 'rn' as bluntness
                    ("h_w - Nose Offset [m]", self.cfg_vars["builder"]["hw"]),
                    ("Ψ - Nose Entry Angle [deg]", self.cfg_vars["builder"]["psi"]),
                ])
                
            # Tail Specifics (Added: hu, theta)
            geom_rows.extend([
                ("Limit Tail Angle", self.cfg_vars["builder"]["enforce_tail_angle"], ctk.CTkCheckBox),
                ("αₘₐₓ - Max Tail Angle [deg]", self.cfg_vars["builder"]["alpha_max_deg"]),
                ("h_u - Tail Vertical Offset [m]", self.cfg_vars["builder"]["hu"]),
                ("θ - Tail Upsweep Angle [deg]", self.cfg_vars["builder"]["theta"]),
            ])
            
            # Note: r_tip is appended commonly below
        else: # tubular
            geom_rows.extend([
                ("d_f - Fuselage Diameter [m]", self.cfg_vars["geom"]["d"]),
                ("Lₙ - Nose Length [m]", self.cfg_vars["builder"]["Ln"]),
                ("L_c - Cabin Length [m]", self.cfg_vars["builder"]["Lc"]),
                ("Lₜ - Tail Length [m]", self.cfg_vars["builder"]["Lt"]),
                ("h_w - Nose Vertical Offset [m]", self.cfg_vars["builder"]["hw"]),
                ("h_u - Tail Vertical Offset [m]", self.cfg_vars["builder"]["hu"]),
                ("Bₙ - Nose Bluntness [-]", self.cfg_vars["builder"]["rn"]),
                ("Ψ - Nose Entry Angle [deg]", self.cfg_vars["builder"]["psi"]),
                ("θ - Tail Upsweep Angle [deg]", self.cfg_vars["builder"]["theta"]),
            ])
        
        # Tip radius (common)
        geom_rows.append(("rₜᵢₚ - Tail Tip Radius [m]", self.cfg_vars["builder"]["r_tip"]))
        
        self._build_dynamic_rows(tab_geom, geom_rows, start_row=1 if method=="fractions" else 0)
        
        # --- Operation ---
        self.tabview.add("Operation")
        tab_op = self.tabview.tab("Operation")
        op_rows = [
            ("V - Cruise Velocity [m/s]", self.cfg_vars["op"]["V"]),
            ("ρ - Air Density [kg/m³]", self.cfg_vars["op"]["rho"]),
            ("ν - Kinematic Viscosity [m²/s]", self.cfg_vars["op"]["nu"]),
        ]
        if method == "tubular":
             # Ensure Mach is available
             if "Mach" not in self.cfg_vars["op"]:
                 self.cfg_vars["op"]["Mach"] = tk.StringVar(value="0.0")
             op_rows.append(("M - Mach Number [-]", self.cfg_vars["op"]["Mach"]))
        
        self._form_grid(tab_op, op_rows)
        
        # --- CF Model (Classic only) ---
        if method == "fractions":
            self.tabview.add("CF Model")
            tab_cf = self.tabview.tab("CF Model")
            ctk.CTkLabel(tab_cf, text="Mode").grid(row=0, column=0, sticky="w", padx=10, pady=5)
            mode_cb = ctk.CTkComboBox(tab_cf, variable=self.cfg_vars["cf_model"]["mode"], values=["laminar", "transition", "turbulent"], state="readonly")
            mode_cb.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
            tab_cf.grid_columnconfigure(1, weight=1)
            self._form_row(tab_cf, 1, "kₜᵣ - Transition k [-]", self.cfg_vars["cf_model"]["k_transition"])
            self._form_row(tab_cf, 2, "C₃_D - 3D Correction [-]", self.cfg_vars["cf_model"]["threeD_correction"])
            
        # --- Builder ---
        self.tabview.add("Builder")
        tab_bld = self.tabview.tab("Builder")
        
        rows_bld = []
        rows_bld.extend([
             ("Nₙ - Nose Points [-]", self.cfg_vars["builder"]["Nn"]),
             ("Nₜ - Tail Points [-]", self.cfg_vars["builder"]["Nt"]),
        ])
        
        self._build_dynamic_rows(tab_bld, rows_bld)

        # --- Mass ---
        self.tabview.add("Mass")
        tab_mass = self.tabview.tab("Mass")
        tab_mass.grid_columnconfigure(1, weight=1)
        self.mass_sigma_entry = None
        self.mass_rho_entry = None
        self.mass_tskin_entry = None
        cb_usd = ctk.CTkCheckBox(tab_mass, text="Use surface density", variable=self.cfg_vars["mass"]["use_surface_density"], command=self._toggle_mass_mode)
        cb_usd.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        self._form_row(tab_mass, 1, "σ_s - Surface Density [kg/m²]", self.cfg_vars["mass"]["sigma_surface"], entry_ref_attr="mass_sigma_entry")
        self._form_row(tab_mass, 2, "ρ_m - Material Density [kg/m³]", self.cfg_vars["mass"]["rho_material"], entry_ref_attr="mass_rho_entry")
        self._form_row(tab_mass, 3, "t_s - Skin Thickness [m]", self.cfg_vars["mass"]["t_skin"], entry_ref_attr="mass_tskin_entry")
        cb_base = ctk.CTkCheckBox(tab_mass, text="Include base disk area", variable=self.cfg_vars["mass"]["include_base_disk_area"])
        cb_base.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        self._form_row(tab_mass, 5, "g - Gravity [m/s²]", self.cfg_vars["mass"]["g"])
        self._toggle_mass_mode()

        # --- I/O ---
        self.tabview.add("I/O")
        tab_io = self.tabview.tab("I/O")
        tab_io.grid_columnconfigure(1, weight=1)
        cb_csv = ctk.CTkCheckBox(tab_io, text="Export CSV", variable=self.cfg_vars["io"]["export_csv"])
        cb_csv.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))
        ctk.CTkLabel(tab_io, text="CSV path").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        e_csv = ctk.CTkEntry(tab_io, textvariable=self.cfg_vars["io"]["csv_path"])
        e_csv.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        ctk.CTkButton(tab_io, text="Browse…", command=self._browse_csv_path, width=80).grid(row=1, column=2, sticky="w", padx=(0,10), pady=5)
        
        # Ensure Geometry tab is shown and rendered
        # We use after() to ensure the tabview is mapped before setting the tab,
        # which fixes the "empty tab on startup" rendering bug.
        self.after(10, lambda: self.tabview.set("Geometry"))


    def _build_dynamic_rows(self, parent, rows, start_row=0):
        parent.grid_columnconfigure(1, weight=1)
        for i, row_data in enumerate(rows):
            label = row_data[0]
            var = row_data[1]
            widget_cls = row_data[2] if len(row_data) > 2 else ctk.CTkEntry
            
            ctk.CTkLabel(parent, text=label).grid(row=start_row + i, column=0, sticky="w", padx=10, pady=5)
            if widget_cls in (ctk.CTkCheckBox, ctk.CTkComboBox, ctk.CTkSwitch):
                # These widgets use 'variable'
                kwargs = {"variable": var}
                if widget_cls == ctk.CTkCheckBox:
                     kwargs["text"] = ""
                elif widget_cls == ctk.CTkComboBox:
                     # ComboBox needs values, but here we can't easily pass them in this generic structure
                     # unless we extend the structure. 
                     # However, for my specific 'nose_type' case, I am building it MANUALLY outside this function.
                     # So this change logic is strictly for generic support if needed, 
                     # but mainly I need 'start_row' support for the loop.
                     pass
                w = widget_cls(parent, **kwargs)
            else:
                # Entries use 'textvariable'
                w = widget_cls(parent, textvariable=var)
            w.grid(row=start_row + i, column=1, sticky="ew", padx=10, pady=5)



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
            self.cfg_vars["op"]["Mach"].set(s(op.get("Mach", 0.0)))

            cf = cfg.get("cf_model", {})
            self.cfg_vars["cf_model"]["mode"].set(cf.get("mode", "turbulent"))
            self.cfg_vars["cf_model"]["k_transition"].set(s(cf.get("k_transition", "")))
            self.cfg_vars["cf_model"]["threeD_correction"].set(s(cf.get("threeD_correction", "")))

            b = cfg.get("builder", {})
            self.cfg_vars["builder"]["parametrization_method"].set(s(b.get("parametrization_method", "fractions")))
            self.cfg_vars["builder"]["Ln_frac"].set(s(b.get("Ln_frac", "")))
            self.cfg_vars["builder"]["C_haack"].set(s(b.get("C_haack", "")))
            self.cfg_vars["builder"]["Nn"].set(s(b.get("Nn", "")))
            self.cfg_vars["builder"]["Lt_frac"].set(s(b.get("Lt_frac", "")))
            self.cfg_vars["builder"]["r_tip"].set(s(b.get("r_tip", "")))
            self.cfg_vars["builder"]["enforce_tail_angle"].set(bool(b.get("enforce_tail_angle", True)))
            self.cfg_vars["builder"]["alpha_max_deg"].set(s(b.get("alpha_max_deg", "")))
            self.cfg_vars["builder"]["Nt"].set(s(b.get("Nt", "")))
            
            # Tubular
            self.cfg_vars["builder"]["FRn"].set(s(b.get("FRn", "")))
            self.cfg_vars["builder"]["FRt"].set(s(b.get("FRt", "")))
            self.cfg_vars["builder"]["Lc"].set(s(b.get("Lc", "")))
            self.cfg_vars["builder"]["Ln"].set(s(b.get("Ln", "")))
            self.cfg_vars["builder"]["Lt"].set(s(b.get("Lt", "")))
            self.cfg_vars["builder"]["hw"].set(s(b.get("hw", "")))
            self.cfg_vars["builder"]["hu"].set(s(b.get("hu", "")))
            self.cfg_vars["builder"]["rn"].set(s(b.get("rn", "")))
            self.cfg_vars["builder"]["use_double_nose"].set(bool(b.get("use_double_nose", False)))
            self.cfg_vars["builder"]["psi"].set(s(b.get("psi", "")))
            self.cfg_vars["builder"]["theta"].set(s(b.get("theta", "")))
            
            self.cfg_vars["builder"]["theta"].set(s(b.get("theta", "")))
            
            # Sync tab with loaded method
            if hasattr(self, "mode_selector"):
               m = self.cfg_vars["builder"]["parametrization_method"].get()
               self.mode_selector.set("Tubular" if m == "tubular" else "Fractions")
               self._rebuild_tabs(m)
               if self.on_method_change:
                   self.on_method_change(m)

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
                "Mach": to_float("Mach", self.cfg_vars["op"]["Mach"].get() or 0.0),
            },
            "cf_model": {
                "mode": (self.cfg_vars["cf_model"]["mode"].get() or "turbulent"),
                "k_transition": to_float("Transition k", self.cfg_vars["cf_model"]["k_transition"].get()),
                "threeD_correction": to_float("3D correction", self.cfg_vars["cf_model"]["threeD_correction"].get()),
            },
            "builder": {
                "parametrization_method": self.cfg_vars["builder"]["parametrization_method"].get(),
                "nose_type": self.cfg_vars["builder"]["nose_type"].get(),
                
                "Ln_frac": to_float("Nose length fraction", self.cfg_vars["builder"]["Ln_frac"].get() or 0.2),
                "C_haack": to_float("Haack C", self.cfg_vars["builder"]["C_haack"].get() or 0.0),
                "Nn": to_int("Nose points Nn", self.cfg_vars["builder"]["Nn"].get() or 40),
                "Lt_frac": to_float("Tail length fraction", self.cfg_vars["builder"]["Lt_frac"].get() or 0.3),
                "r_tip": to_float("Tip radius r_tip", self.cfg_vars["builder"]["r_tip"].get() or 0.0),
                "enforce_tail_angle": bool(self.cfg_vars["builder"]["enforce_tail_angle"].get()),
                "alpha_max_deg": to_float("Max tail angle", self.cfg_vars["builder"]["alpha_max_deg"].get() or 18.0),
                "Nt": to_int("Tail points Nt", self.cfg_vars["builder"]["Nt"].get() or 40),
                
                "FRn": to_float("FRn", self.cfg_vars["builder"]["FRn"].get() or 1.5),
                "FRt": to_float("FRt", self.cfg_vars["builder"]["FRt"].get() or 2.0),
                "Lc": to_float("Lc", self.cfg_vars["builder"]["Lc"].get() or 0.0),
                "Ln": to_float("Ln", self.cfg_vars["builder"]["Ln"].get() or 0.5),
                "Lt": to_float("Lt", self.cfg_vars["builder"]["Lt"].get() or 0.5),
                "hw": to_float("hw", self.cfg_vars["builder"]["hw"].get() or 0.1),
                "hu": to_float("hu", self.cfg_vars["builder"]["hu"].get() or 0.1),
                "rn": to_float("rn", self.cfg_vars["builder"]["rn"].get() or 0.1),
                "use_double_nose": bool(self.cfg_vars["builder"]["use_double_nose"].get()),
                "psi": to_float("psi", self.cfg_vars["builder"]["psi"].get() or 40.0),
                "theta": to_float("theta", self.cfg_vars["builder"]["theta"].get() or 15.0),
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
        }
        return cfg
