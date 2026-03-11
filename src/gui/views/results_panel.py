import customtkinter as ctk
import tkinter as tk

class ResultsPanel(ctk.CTkFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        # Add a title
        self.label = ctk.CTkLabel(self, text="Summary", font=ctk.CTkFont(size=16, weight="bold"))
        self.label.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
        
        self.summary_vars = {
            "Lf": tk.StringVar(value="-"),
            "df": tk.StringVar(value="-"),
            "ReL": tk.StringVar(value="-"),
            "Cf_eff": tk.StringVar(value="-"),
            "CD_total": tk.StringVar(value="-"),
            "D_total": tk.StringVar(value="-"),
            "S_total": tk.StringVar(value="-"),
        }
        
        self._build_ui()

    def _build_ui(self):
        self._add_summary_row("L_f [m]", 1, key="Lf")
        self._add_summary_row("d_f [m]", 2, key="df")
        self._add_summary_row("Reₗ", 3, key="ReL")
        self._add_summary_row("C_f,eff", 4, key="Cf_eff")
        self._add_summary_row("C_D,ₜₒₜₐₗ", 5, key="CD_total")
        self._add_summary_row("Dₜₒₜₐₗ [N]", 6, key="D_total")
        self._add_summary_row("Sₜₒₜₐₗ [m²]", 7, key="S_total")

    def _add_summary_row(self, label: str, row: int, key: str | None = None):
        if key is None:
            key = label
        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text=label + ":", text_color="gray70").grid(row=row, column=0, sticky="w", padx=10, pady=2)
        ctk.CTkLabel(self, textvariable=self.summary_vars[key], font=ctk.CTkFont(weight="bold")).grid(row=row, column=1, sticky="e", padx=10, pady=2)

    def update_results(self, payload: dict):
        try:
            aero = payload.get("aero", {})
            integrals = payload.get("integrals", {})
            geom = payload.get("geom", {})
            
            # Dimensions
            l_val = geom.get("L_f") if "L_f" in geom else geom.get("l", 0.0)
            d_val = geom.get("d", 0.0)
            self.summary_vars["Lf"].set(f"{l_val:.2f}")
            self.summary_vars["df"].set(f"{d_val:.2f}")

            # Common
            self.summary_vars["ReL"].set(f"{aero.get('ReL', float('nan')):.3g}")
            
            # Helper to safely get float
            def g(k): return aero.get(k, float('nan'))
            
            # Check if we have tubular results
            if "CD_fus" in aero:
                # Tubular mode
                self.summary_vars["Cf_eff"].set(f"{g('CD_fp'):.5f} (fp)")
                self.summary_vars["CD_total"].set(f"{g('CD_fus'):.5f}")
                self.summary_vars["D_total"].set(f"{g('Drag'):.4g}")
            else:
                # Classic mode
                self.summary_vars["Cf_eff"].set(f"{g('Cf_eff'):.5f}")
                self.summary_vars["CD_total"].set(f"{g('CD_total'):.5f}")
                self.summary_vars["D_total"].set(f"{g('D_total'):.4g}")
            
            self.summary_vars["S_total"].set(f"{integrals.get('S_total', float('nan')):.4g}")
        except Exception as e:
            print(f"Could not update summary: {e}")
