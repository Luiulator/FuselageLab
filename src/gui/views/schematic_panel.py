import customtkinter as ctk
from PIL import Image
import os

class SchematicPanel(ctk.CTkFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.label = ctk.CTkLabel(self, text="")
        self.label.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.img_path = os.path.join(os.path.dirname(__file__), "..", "assets", "schematic.png")
        self.pil_img = None
        if os.path.exists(self.img_path):
            self.pil_img = Image.open(self.img_path)
            
        self.bind("<Configure>", self._on_resize)
        
    def _on_resize(self, event):
        if self.pil_img:
            # Use current width but don't let it explode
            w = event.width - 20
            if w > 400: w = 400 # Limit width to sidebar typical size
            
            if w > 50:
                orig_w, orig_h = self.pil_img.size
                aspect = orig_h / orig_w
                h = int(w * aspect)
                
                # Check if height is too much
                if h > 250:
                    h = 250
                    w = int(h / aspect)

                ctk_img = ctk.CTkImage(light_image=self.pil_img, dark_image=self.pil_img, size=(w, h))
                self.label.configure(image=ctk_img)
