"""
오실로스코프 — 실시간 관절 전류/속도/힘 데이터 그래프.
matplotlib를 tkinter에 임베드하여 실시간 라인 차트를 표시합니다.
"""
import customtkinter as ctk
import threading
import time
from collections import deque

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
from presentation.ui.theme import Theme


class OscilloscopeDialog(ctk.CTkToplevel):
    """실시간 데이터 로거 / 오실로스코프."""
    
    MAX_POINTS = 200  # 화면에 표시할 최대 데이터 포인트 수
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("📈 오실로스코프 — 실시간 데이터 로거")
        self.geometry("750x520")
        self.configure(fg_color=Theme.BG_BASE)
        self._running = False
        self._data_type = "joint"  # joint, ft, velocity
        
        # 데이터 버퍼 (6축)
        self.buffers = [deque(maxlen=self.MAX_POINTS) for _ in range(6)]
        self.time_buf = deque(maxlen=self.MAX_POINTS)
        self._t0 = time.time()
        
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _build_ui(self):
        # 컨트롤 바
        ctrl = ctk.CTkFrame(self, fg_color=Theme.BG_SURFACE, height=40)
        ctrl.pack(fill="x", padx=5, pady=5)
        
        self.start_btn = ctk.CTkButton(ctrl, text="● 기록 시작", width=90, height=28,
                                        fg_color=Theme.SUCCESS, command=self._toggle_recording)
        self.start_btn.pack(side="left", padx=5, pady=5)
        
        ctk.CTkLabel(ctrl, text="데이터:", font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY).pack(side="left", padx=5)
        self.type_sel = ctk.CTkOptionMenu(ctrl, values=["관절 각도", "F/T 센서", "관절 전류"],
                                           width=100, command=self._on_type_change)
        self.type_sel.pack(side="left", padx=5)
        
        self.status_lbl = ctk.CTkLabel(ctrl, text="대기 중", font=Theme.font(size=10), text_color=Theme.WARNING)
        self.status_lbl.pack(side="right", padx=10)
        
        # matplotlib 차트
        if HAS_MPL:
            self.fig = Figure(figsize=(7, 4), dpi=100, facecolor=Theme.BG_BASE)
            self.ax = self.fig.add_subplot(111)
            self.ax.set_facecolor(Theme.BG_BASE)
            self.ax.tick_params(colors=Theme.TEXT_SECONDARY)
            self.ax.spines['bottom'].set_color('#8B8B96')
            self.ax.spines['left'].set_color('#8B8B96')
            self.ax.spines['top'].set_visible(False)
            self.ax.spines['right'].set_visible(False)
            self.ax.set_xlabel("Time (s)", color=Theme.TEXT_SECONDARY)
            self.ax.set_ylabel("Value", color=Theme.TEXT_SECONDARY)
            
            self.colors = ["#FF5252", Theme.WARNING, "#FFEB3B", Theme.SUCCESS, Theme.INFO, "#9C27B0"]
            self.lines = []
            labels = ["J1/Fx", "J2/Fy", "J3/Fz", "J4/Tx", "J5/Ty", "J6/Tz"]
            for i in range(6):
                line, = self.ax.plot([], [], color=self.colors[i], linewidth=1.2, label=labels[i])
                self.lines.append(line)
            self.ax.legend(loc="upper left", fontsize=7, facecolor=Theme.BG_SURFACE, edgecolor="#444",
                           labelcolor=Theme.TEXT_PRIMARY)
            
            self.canvas = FigureCanvasTkAgg(self.fig, master=self)
            self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        else:
            ctk.CTkLabel(self, text="⚠️ matplotlib가 설치되지 않았습니다.\npip install matplotlib",
                         font=Theme.font(size=14), text_color="#FF5252").pack(expand=True)
    
    def _on_type_change(self, val):
        type_map = {"관절 각도": "joint", "F/T 센서": "ft", "관절 전류": "current"}
        self._data_type = type_map.get(val, "joint")
        # 버퍼 초기화
        for buf in self.buffers:
            buf.clear()
        self.time_buf.clear()
        self._t0 = time.time()
    
    def _toggle_recording(self):
        self._running = not self._running
        if self._running:
            self.start_btn.configure(text="■ 기록 정지", fg_color=Theme.DANGER)
            self.status_lbl.configure(text="기록 중...", text_color=Theme.SUCCESS)
            self._t0 = time.time()
            threading.Thread(target=self._record_loop, daemon=True).start()
        else:
            self.start_btn.configure(text="● 기록 시작", fg_color=Theme.SUCCESS)
            self.status_lbl.configure(text="정지", text_color=Theme.WARNING)
    
    def _record_loop(self):
        while self._running:
            try:
                t = time.time() - self._t0
                self.time_buf.append(t)
                
                if self._data_type == "joint":
                    vals = RobotControlUseCase.get_joint_pos()
                elif self._data_type == "ft":
                    vals = RobotControlUseCase.get_ft_sensor()
                else:  # current — 관절 각도를 대리로 사용 (실제로는 motor current API)
                    vals = RobotControlUseCase.get_joint_pos()
                
                if vals and len(vals) >= 6:
                    for i in range(6):
                        self.buffers[i].append(vals[i])
                
                # UI 업데이트 (matplotlib)
                if HAS_MPL and len(self.time_buf) > 1:
                    t_list = list(self.time_buf)
                    for i in range(6):
                        self.lines[i].set_data(t_list, list(self.buffers[i]))
                    self.ax.set_xlim(max(0, t_list[-1] - 10), t_list[-1] + 0.5)
                    
                    all_vals = []
                    for buf in self.buffers:
                        all_vals.extend(buf)
                    if all_vals:
                        self.ax.set_ylim(min(all_vals) - 5, max(all_vals) + 5)
                    
                    self.canvas.draw_idle()
                    
            except Exception:
                pass
            time.sleep(0.1)  # 10Hz 샘플링
    
    def _on_close(self):
        self._running = False
        self.destroy()
