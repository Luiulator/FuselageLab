import customtkinter as ctk
import tkinter as tk
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class MatplotlibViewer(ctk.CTkFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        # Configure frame
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Initialize Figure
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111, projection="3d")
        
        # Dark theme setup
        self.fig.patch.set_facecolor("#1a1a1a") # Match CTK dark theme roughly
        self.ax.set_facecolor("#1a1a1a")
        self.ax.tick_params(colors="white")
        self.ax.xaxis.label.set_color("white")
        self.ax.yaxis.label.set_color("white")
        self.ax.zaxis.label.set_color("white")
        self.ax.set_title("Fuselage Geometry", color="white", pad=10)
        
        # Hide axes initially
        self.ax.set_axis_off()
        
        # Canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        
        # Pack canvas
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")
        self.canvas_widget.configure(highlightthickness=0, bd=0)
        
        # Toolbar (optional, maybe hide it or style it)
        # For now, let's skip the toolbar or put it in a separate frame if needed.
        # The original had it at the bottom.
        self.toolbar_frame = ctk.CTkFrame(self, height=30)
        self.toolbar_frame.grid(row=1, column=0, sticky="ew")
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(side="bottom", fill="x")
        
        # Style toolbar background if possible (tricky with Tkinter toolbar)
        self.toolbar.config(background="#1a1a1a")
        for button in self.toolbar.winfo_children():
            try:
                button.config(background="#1a1a1a")
            except: pass

    def update_geometry(self, geom):
        x = np.asarray(geom.get("x"))
        y = np.asarray(geom.get("y"))
        if x is None or y is None or x.size == 0:
            return

        # Revolve
        n_theta = 64
        theta = np.linspace(0.0, 2*np.pi, n_theta)
        X = np.repeat(x[:, None], n_theta, axis=1)
        R = np.repeat(y[:, None], n_theta, axis=1)
        Y = R * np.cos(theta)
        Z = R * np.sin(theta)
        
        self.ax.clear()
        self.ax.plot_wireframe(X, Y, Z, 
                               rstride=max(1, X.shape[0] // 60),
                               cstride=max(1, X.shape[1] // 32),
                               color="#00aaff", linewidth=0.6, alpha=0.8)
        
        self._set_axes_equal(self.ax, X, Y, Z)
        self.ax.set_axis_off() # Keep clean look
        self.canvas.draw()

    def _set_axes_equal(self, ax, X, Y, Z):
        x_min, x_max = np.nanmin(X), np.nanmax(X)
        y_min, y_max = np.nanmin(Y), np.nanmax(Y)
        z_min, z_max = np.nanmin(Z), np.nanmax(Z)
        max_range = max(x_max-x_min, y_max-y_min, z_max-z_min)
        
        x_mid = 0.5 * (x_max + x_min)
        y_mid = 0.5 * (y_max + y_min)
        z_mid = 0.5 * (z_max + z_min)
        
        half = 0.5 * max_range
        ax.set_xlim(x_mid - half, x_mid + half)
        ax.set_ylim(y_mid - half, y_mid + half)
        ax.set_zlim(z_mid - half, z_mid + half)

    def clear(self):
        self.ax.clear()
        self.ax.set_axis_off()
        self.canvas.draw()
