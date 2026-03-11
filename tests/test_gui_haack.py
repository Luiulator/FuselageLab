import customtkinter as ctk
import sys
import os
import tkinter as tk
sys.path.append(os.path.abspath("."))
from src.gui.views.config_form import ConfigForm

def test_haack_visibility():
    app = ctk.CTk()
    app.geometry("800x600")
    
    cf = ConfigForm(app)
    cf.pack(fill="both", expand=True)

    # Helper function to check if "Haack C" label exists in the builder tab
    def has_haack_label(cf):
        # We need to traverse the widget tree inside the Builder tab
        try:
            tab_bld = cf.tabview.tab("Builder")
            # The tab contains Frames (builder_frames["fractions"], builder_frames["tubular"]) and Common Frame
            # Haack C was in common frame, now should be in fractions frame
            
            # Check for label "Haack C"
            found = False
            
            # A simple way is to iterate all children of the tab
            def check_children(widget):
                nonlocal found
                if isinstance(widget, ctk.CTkLabel) and "Haack C" in widget.cget("text"):
                    found = True
                    return
                for child in widget.winfo_children():
                    check_children(child)
            
            check_children(tab_bld)
            return found
        except Exception:
            return False

    # 1. Switch directly to Fractions
    print("Switching to Fractions...")
    cf._on_mode_change("Fractions")
    app.update()
    
    # Check
    if has_haack_label(cf):
        print("SUCCESS: Haack C label found in Fractions mode")
    else:
        print("ERROR: Haack C label MISSING in Fractions mode")

    # 2. Switch to Tubular
    print("Switching to Tubular...")
    cf._on_mode_change("Tubular")
    app.update()
    
    # Check
    if not has_haack_label(cf):
        print("SUCCESS: Haack C label hidden in Tubular mode")
    else:
        print("ERROR: Haack C label FOUND in Tubular mode (should be hidden)")

    app.destroy()

if __name__ == "__main__":
    test_haack_visibility()
