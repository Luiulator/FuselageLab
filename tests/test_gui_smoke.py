import customtkinter as ctk
import sys
import os
sys.path.append(os.path.abspath("."))
from src.gui.views.config_form import ConfigForm

def test_gui():
    app = ctk.CTk()
    app.geometry("800x600")
    
    cf = ConfigForm(app)
    cf.pack(fill="both", expand=True)

    # Simulate method switch
    print("Switching to Tubular...")
    cf._on_mode_change("Tubular")
    app.update()
    
    # Check if correct tabs exist
    try:
        cf.tabview.tab("Geometry")
        cf.tabview.tab("Operation")
        cf.tabview.tab("Builder")
        # CF Model should be gone
        try:
            cf.tabview.tab("CF Model")
            print("ERROR: CF Model tab should be gone in Tubular mode")
        except:
            print("SUCCESS: CF Model tab is gone in Tubular mode")
            
    except Exception as e:
        print(f"ERROR: {e}")

    print("Switching to Fractions...")
    cf._on_mode_change("Fractions")
    app.update()
    
    try:
        cf.tabview.tab("CF Model")
        print("SUCCESS: CF Model tab is back in Fractions mode")
    except:
        print("ERROR: CF Model tab missing in Fractions mode")

    app.destroy()

if __name__ == "__main__":
    test_gui()
