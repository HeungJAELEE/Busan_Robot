import customtkinter as ctk
import threading
import time
from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
from presentation.ui.theme import Theme


class IOMonitorPanel:
    """
    I/O 모니터링 대시보드 — DO/DI + EndTool + AI/AO 실시간 상태 표시 및 수동 제어.
    """
    
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.do_btns = []
        self.di_labels = []
        self.et_do_btns = []
        self.et_di_labels = []
        self._monitoring = False
        self._monitor_thread = None
        self.render()
    
    def render(self):
        main = ctk.CTkFrame(self.parent, fg_color=Theme.BG_BASE, corner_radius=6)
        main.pack(fill="x", padx=5, pady=5)
        
        # Header
        header = ctk.CTkFrame(main, fg_color=Theme.BG_SURFACE, height=30)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="🔌 I/O 모니터", font=Theme.font(size=12, weight="bold"), 
                     text_color="#90CAF9").pack(side="left", padx=10, pady=5)
        
        self.monitor_btn = ctk.CTkButton(header, text="● 모니터링 시작", width=100, height=24,
                                          fg_color=Theme.SUCCESS, hover_color="#1B5E20",
                                          command=self._toggle_monitoring)
        self.monitor_btn.pack(side="right", padx=10, pady=5)
        
        # === 제어박스 DO ===
        do_frame = ctk.CTkFrame(main, fg_color="transparent")
        do_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(do_frame, text="DO (디지털 출력)", font=Theme.font(size=10, weight="bold"), 
                     text_color=Theme.SUCCESS).pack(anchor="w", padx=5)
        do_grid = ctk.CTkFrame(do_frame, fg_color="transparent")
        do_grid.pack(fill="x", padx=5, pady=2)
        self.do_btns = []
        self.do_states = [0] * 8
        for i in range(8):
            btn = ctk.CTkButton(do_grid, text=f"DO{i}\nOFF", width=45, height=36,
                                fg_color=Theme.BG_SURFACE, hover_color=Theme.BG_SURFACE,
                                font=Theme.font(size=9),
                                command=lambda idx=i: self._toggle_do(idx))
            btn.grid(row=0, column=i, padx=2, pady=1)
            self.do_btns.append(btn)
        
        # === 제어박스 DI ===
        di_frame = ctk.CTkFrame(main, fg_color="transparent")
        di_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(di_frame, text="DI (디지털 입력)", font=Theme.font(size=10, weight="bold"), 
                     text_color=Theme.INFO).pack(anchor="w", padx=5)
        di_grid = ctk.CTkFrame(di_frame, fg_color="transparent")
        di_grid.pack(fill="x", padx=5, pady=2)
        self.di_labels = []
        for i in range(8):
            lbl = ctk.CTkLabel(di_grid, text=f"DI{i}\n—", width=45, height=36,
                               fg_color=Theme.BG_SURFACE, corner_radius=4,
                               font=Theme.font(size=9), text_color=Theme.TEXT_SECONDARY)
            lbl.grid(row=0, column=i, padx=2, pady=1)
            self.di_labels.append(lbl)
        
        # === EndTool I/O ===
        et_frame = ctk.CTkFrame(main, fg_color="transparent")
        et_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(et_frame, text="🔧 EndTool I/O (플랜지)", font=Theme.font(size=10, weight="bold"), 
                     text_color=Theme.WARNING).pack(anchor="w", padx=5)
        et_grid = ctk.CTkFrame(et_frame, fg_color="transparent")
        et_grid.pack(fill="x", padx=5, pady=2)
        
        self.et_do_btns = []
        self.et_do_states = [0] * 2
        for i in range(2):
            btn = ctk.CTkButton(et_grid, text=f"ET_DO{i}\nOFF", width=55, height=36,
                                fg_color=Theme.BG_SURFACE, hover_color=Theme.BG_SURFACE,
                                font=Theme.font(size=9),
                                command=lambda idx=i: self._toggle_endtool_do(idx))
            btn.grid(row=0, column=i, padx=2, pady=1)
            self.et_do_btns.append(btn)
        
        self.et_di_labels = []
        for i in range(2):
            lbl = ctk.CTkLabel(et_grid, text=f"ET_DI{i}\n—", width=55, height=36,
                               fg_color=Theme.BG_SURFACE, corner_radius=4,
                               font=Theme.font(size=9), text_color=Theme.TEXT_SECONDARY)
            lbl.grid(row=0, column=i+2, padx=2, pady=1)
            self.et_di_labels.append(lbl)
        
        # === AI/AO (아날로그) ===
        analog_frame = ctk.CTkFrame(main, fg_color="transparent")
        analog_frame.pack(fill="x", padx=5, pady=(2, 5))
        ctk.CTkLabel(analog_frame, text="📊 Analog I/O", font=Theme.font(size=10, weight="bold"), 
                     text_color="#AB47BC").pack(anchor="w", padx=5)
        
        analog_grid = ctk.CTkFrame(analog_frame, fg_color="transparent")
        analog_grid.pack(fill="x", padx=5, pady=2)
        
        # AO 슬라이더 (2채널)
        self.ao_sliders = []
        self.ao_labels = []
        for i in range(2):
            ctk.CTkLabel(analog_grid, text=f"AO{i}:", font=Theme.font(size=9), 
                         text_color=Theme.TEXT_SECONDARY).grid(row=i, column=0, padx=3, pady=1, sticky="w")
            slider = ctk.CTkSlider(analog_grid, from_=0, to=10, width=100,
                                    command=lambda val, idx=i: self._on_ao_change(idx, val))
            slider.set(0)
            slider.grid(row=i, column=1, padx=3, pady=1)
            self.ao_sliders.append(slider)
            
            lbl = ctk.CTkLabel(analog_grid, text="0.0V", font=Theme.font(size=9), text_color=Theme.WARNING)
            lbl.grid(row=i, column=2, padx=3, pady=1)
            self.ao_labels.append(lbl)
        
        # AI 표시 (2채널)
        self.ai_labels = []
        for i in range(2):
            ctk.CTkLabel(analog_grid, text=f"AI{i}:", font=Theme.font(size=9), 
                         text_color=Theme.TEXT_SECONDARY).grid(row=i, column=3, padx=10, pady=1, sticky="w")
            lbl = ctk.CTkLabel(analog_grid, text="—", font=Theme.font(size=9), text_color=Theme.INFO)
            lbl.grid(row=i, column=4, padx=3, pady=1)
            self.ai_labels.append(lbl)
    
    def _toggle_do(self, idx):
        self.do_states[idx] = 1 - self.do_states[idx]
        val = self.do_states[idx]
        RobotControlUseCase.set_do(idx, val)
        if val:
            self.do_btns[idx].configure(text=f"DO{idx}\nON", fg_color=Theme.SUCCESS)
        else:
            self.do_btns[idx].configure(text=f"DO{idx}\nOFF", fg_color=Theme.BG_SURFACE)
        print(f">> [I/O] DO{idx} = {'ON' if val else 'OFF'}")
    
    def _toggle_endtool_do(self, idx):
        self.et_do_states[idx] = 1 - self.et_do_states[idx]
        val = self.et_do_states[idx]
        RobotControlUseCase.set_endtool_do_port(idx, val)
        if val:
            self.et_do_btns[idx].configure(text=f"ET_DO{idx}\nON", fg_color=Theme.WARNING)
        else:
            self.et_do_btns[idx].configure(text=f"ET_DO{idx}\nOFF", fg_color=Theme.BG_SURFACE)
    
    def _on_ao_change(self, idx, val):
        voltage = round(val, 1)
        self.ao_labels[idx].configure(text=f"{voltage}V")
        RobotControlUseCase.set_ao(idx, int(voltage * 100))  # 0~1000 (0.0~10.0V)
    
    def _toggle_monitoring(self):
        self._monitoring = not self._monitoring
        if self._monitoring:
            self.monitor_btn.configure(text="■ 모니터링 정지", fg_color=Theme.DANGER)
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
        else:
            self.monitor_btn.configure(text="● 모니터링 시작", fg_color=Theme.SUCCESS)
    
    def _monitor_loop(self):
        while self._monitoring:
            try:
                # 제어박스 DI/DO
                di_vals = RobotControlUseCase.get_di()
                do_vals = RobotControlUseCase.get_do()
                
                if di_vals:
                    for i in range(min(8, len(di_vals))):
                        if di_vals[i]:
                            self.di_labels[i].configure(text=f"DI{i}\nHI", fg_color="#1565C0", text_color=Theme.TEXT_PRIMARY)
                        else:
                            self.di_labels[i].configure(text=f"DI{i}\nLO", fg_color=Theme.BG_SURFACE, text_color=Theme.TEXT_SECONDARY)
                
                if do_vals:
                    for i in range(min(8, len(do_vals))):
                        self.do_states[i] = do_vals[i]
                        if do_vals[i]:
                            self.do_btns[i].configure(text=f"DO{i}\nON", fg_color=Theme.SUCCESS)
                        else:
                            self.do_btns[i].configure(text=f"DO{i}\nOFF", fg_color=Theme.BG_SURFACE)
                
                # EndTool DI
                et_di = RobotControlUseCase.get_endtool_di()
                if et_di:
                    for i in range(min(2, len(et_di))):
                        if et_di[i]:
                            self.et_di_labels[i].configure(text=f"ET_DI{i}\nHI", fg_color=Theme.WARNING, text_color=Theme.TEXT_PRIMARY)
                        else:
                            self.et_di_labels[i].configure(text=f"ET_DI{i}\nLO", fg_color=Theme.BG_SURFACE, text_color=Theme.TEXT_SECONDARY)
                
                # AI 읽기
                for i in range(2):
                    ai_val = RobotControlUseCase.get_ai(i)
                    self.ai_labels[i].configure(text=f"{ai_val/100.0:.1f}V")
                    
            except Exception:
                pass
            time.sleep(0.5)
    
    def stop(self):
        self._monitoring = False
