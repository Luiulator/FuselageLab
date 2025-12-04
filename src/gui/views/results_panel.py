import customtkinter as ctk
import tkinter as tk

class ResultsPanel(ctk.CTkFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        # Add a title
        self.label = ctk.CTkLabel(self, text="Summary", font=ctk.CTkFont(size=16, weight="bold"))
        self.label.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
        
        self.summary_vars = {
            "ReL": tk.StringVar(value="-"),
            "Cf_eff": tk.StringVar(value="-"),
            "CD_total": tk.StringVar(value="-"),
            "D_total": tk.StringVar(value="-"),
            "S_total": tk.StringVar(value="-"),
        }
        
        self._build_ui()

    def _build_ui(self):
        self._add_summary_row("ReL", 1)
        self._add_summary_row("Cf_eff", 2)
        self._add_summary_row("CD_total", 3)
        self._add_summary_row("D_total [N]", 4, key="D_total")
        self._add_summary_row("S_total [m²]", 5, key="S_total")

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
            self.summary_vars["ReL"].set(f"{aero.get('ReL', float('nan')):.3g}")
            self.summary_vars["Cf_eff"].set(f"{aero.get('Cf_eff', float('nan')):.5f}")
            self.summary_vars["CD_total"].set(f"{aero.get('CD_total', float('nan')):.5f}")
            self.summary_vars["D_total"].set(f"{aero.get('D_total', float('nan')):.4g}")
            self.summary_vars["S_total"].set(f"{integrals.get('S_total', float('nan')):.4g}")
        except Exception as e:
            print(f"Could not update summary: {e}")
