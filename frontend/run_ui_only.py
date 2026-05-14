import sys
import os

# 프로젝트 루트 경로를 sys.path에 추가하여 모듈을 찾을 수 있게 함
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
from presentation.ui.main_window import ModernContyApp

def main():
    app = ModernContyApp()
    app.mainloop()

if __name__ == "__main__":
    main()
