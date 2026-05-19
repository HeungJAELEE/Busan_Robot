import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import customtkinter as ctk
from presentation.ui.robot_hmi.editors.process_editors import PickPlaceEditor

try:
    import tkcap
except ImportError:
    print("tkcap is required for this optional screenshot helper.")
    print("Install it from the project root with: python -m pip install -r requirements-dev.txt")
    sys.exit(1)

ctk.set_appearance_mode("dark")
root = ctk.CTk()
root.geometry("800x600")
root.update()

frame = ctk.CTkFrame(root)
frame.pack(fill='both', expand=True)

editor = PickPlaceEditor(frame)
editor.render()
editor.update_ui("PickNode", 1, p_name="Pallet A")  # Target type 1 = Pallet

root.update()
import time
time.sleep(1)

cap = tkcap.CAP(root)
output_path = Path("artifacts/ui_test_screenshot.jpg")
output_path.parent.mkdir(parents=True, exist_ok=True)
cap.capture(str(output_path))

print(f"Screenshot saved to {output_path}")
