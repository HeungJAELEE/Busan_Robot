import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import customtkinter as ctk
from presentation.ui.robot_hmi.editors.process_editors import PickPlaceEditor

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

# Ensure tkcap is installed
import os
os.system('pip install tkcap')

import tkcap
cap = tkcap.CAP(root)
cap.capture('artifacts/ui_test_screenshot.jpg')

print("Screenshot saved to artifacts/ui_test_screenshot.jpg")
