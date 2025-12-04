import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import threading
import traceback
import json

from src.configio import load_config
from src.pipeline import run_case
from src.utils import export_fuselage_stl, stamp_name
from src.gui.views.config_form import ConfigForm
from src.gui.views.results_panel import ResultsPanel
from src.gui.viewers.matplotlib_viewer import MatplotlibViewer

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("FuselageLab")
        self.geometry("1600x900")
        
        # State
        self.config_path = os.path.abspath("config.json")
        self.running = False
        self.worker = None
        self._last_payload = None
        
        self._build_ui()
        self._load_config(self.config_path)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=3) # 3D View
        self.grid_columnconfigure(1, weight=1) # Sidebar
        self.grid_rowconfigure(0, weight=1)
        
        # --- Left: 3D View ---
        self.view_frame = ctk.CTkFrame(self, corner_radius=0)
        self.view_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=0)
        
        self.view3d = MatplotlibViewer(self.view_frame)
        self.view3d.pack(fill="both", expand=True)
        
        # --- Right: Sidebar ---
        self.sidebar = ctk.CTkFrame(self, corner_radius=0)
        self.sidebar.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_rowconfigure(1, weight=1) # Config form expands
        self.sidebar.grid_columnconfigure(0, weight=1)
        
        # 1. Top Bar (Load/Save)
        self.top_bar = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkButton(self.top_bar, text="Load Config", command=self._on_load_clicked, width=100).pack(side="left", padx=(0, 5))
        ctk.CTkButton(self.top_bar, text="Save Config", command=self._on_save_clicked, width=100).pack(side="left", padx=5)
        
        # 2. Config Form
        self.config_form = ConfigForm(self.sidebar)
        self.config_form.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # 3. Results Panel
        self.results_panel = ResultsPanel(self.sidebar)
        self.results_panel.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        # 4. Actions
        self.actions_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.actions_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=20)
        
        self.btn_run = ctk.CTkButton(self.actions_frame, text="RUN PIPELINE", command=self._on_run_clicked, height=40, font=ctk.CTkFont(size=14, weight="bold"), fg_color="green", hover_color="darkgreen")
        self.btn_run.pack(fill="x", pady=(0, 10))
        
        ctk.CTkButton(self.actions_frame, text="Export STL", command=self._export_stl).pack(fill="x", pady=5)
        ctk.CTkButton(self.actions_frame, text="Open Results", command=self._open_results).pack(fill="x", pady=5)

    def _load_config(self, path):
        self.config_path = path
        try:
            data = load_config(path)
        except FileNotFoundError:
            data = {}
        except Exception as e:
            print(f"Error loading config: {e}")
            return
        
        try:
            self.config_form.load_from_dict(data)
        except Exception as e:
            print(f"Error populating form: {e}")

    def _on_load_clicked(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if path:
            self._load_config(path)

    def _on_save_clicked(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if path:
            self._save_config(path)

    def _save_config(self, path):
        cfg = self.config_form.get_config()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        self.config_path = path

    def _on_run_clicked(self):
        if self.running: return
        
        # Save temp config
        try:
            self._save_config(self.config_path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save config: {e}")
            return

        self.running = True
        self.btn_run.configure(state="disabled", text="Running...")
        
        def worker():
            try:
                cfg = load_config(self.config_path)
                payload = run_case(cfg)
                self._last_payload = payload
                
                # Update UI
                self.after(0, lambda: self.results_panel.update_results(payload))
                self.after(0, lambda: self.view3d.update_geometry(payload["geom"]))
                self.after(0, lambda: messagebox.showinfo("Success", "Run completed successfully"))
            except Exception:
                err = traceback.format_exc()
                self.after(0, lambda: messagebox.showerror("Run Failed", err))
            finally:
                self.after(0, lambda: self._reset_run_state())
        
        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()

    def _reset_run_state(self):
        self.running = False
        self.btn_run.configure(state="normal", text="RUN PIPELINE")

    def _export_stl(self):
        if not self._last_payload or "geom" not in self._last_payload:
            messagebox.showwarning("Warning", "Run a case first.")
            return
            
        path = filedialog.asksaveasfilename(defaultextension=".stl", filetypes=[("STL files", "*.stl")])
        if path:
            try:
                export_fuselage_stl(self._last_payload["geom"], path)
                messagebox.showinfo("Success", f"Exported to {path}")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {e}")

    def _open_results(self):
        results_dir = os.path.abspath("results")
        os.makedirs(results_dir, exist_ok=True)
        import platform, subprocess
        try:
            if platform.system() == "Windows":
                os.startfile(results_dir)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", results_dir])
            else:
                subprocess.Popen(["xdg-open", results_dir])
        except Exception as e:
            print(f"Error opening results: {e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
