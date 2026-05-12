import customtkinter as ctk
import threading
import time
import sys
import os
import queue
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from presentation.ui.robot_hmi.robot_hmi_view import RobotHmiView
from presentation.ui.digital_twin.digital_twin_view import DigitalTwinView
from core.domains.robot.communication.client_manager import robot_manager

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class PrintLogger:
    def __init__(self, msg_queue):
        self.msg_queue = msg_queue
    def write(self, text):
        if text.strip() or text == '\n':
            self.msg_queue.put(text)
    def flush(self): pass
    def isatty(self):
        return False

class ModernContyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Indy7 Command Center (DDD Architecture)")
        self.geometry("1400x900")
        
        self.log_queue = queue.Queue()
        self._poll_log_queue()
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 상단 네비게이션 (헤더)
        self.header = ctk.CTkFrame(self, height=60, fg_color="#18181B", corner_radius=0)
        self.header.grid(row=0, column=0, sticky="ew")
        
        # 좌측 상단 로고
        ctk.CTkLabel(self.header, text="⚡ INDY7 COMMAND CENTER", font=ctk.CTkFont(size=20, weight="bold", slant="italic"), text_color="#00E5FF").pack(side="left", padx=20)
        
        # 중앙 페이지 탭 버튼
        tab_container = ctk.CTkFrame(self.header, fg_color="transparent")
        tab_container.pack(side="left", expand=True)
        
        # 활성/비활성 스타일 정의
        self.style_active = {"fg_color": "#1976D2", "text_color": "white", "hover_color": "#1565C0"}
        self.style_inactive = {"fg_color": "transparent", "text_color": "#8B8B96", "hover_color": "#3A3D45"}
        
        self.btn_page1 = ctk.CTkButton(tab_container, text="[Page 1] Auto / Monitor Mode", corner_radius=15, command=lambda: self.switch_page(1), **self.style_inactive)
        self.btn_page1.pack(side="left", padx=5)
        
        self.btn_page2 = ctk.CTkButton(tab_container, text="[Page 2] Setting / Teaching Mode", corner_radius=15, command=lambda: self.switch_page(2), **self.style_active)
        self.btn_page2.pack(side="left", padx=5)
        
        # 우측 연결 버튼
        ctk.CTkButton(self.header, text="로봇 통신 연결", fg_color="#2E7D32", command=self.connect_all).pack(side="right", padx=20)
        
        # 서브 메뉴 바
        self.menu_bar = ctk.CTkFrame(self, height=40, fg_color="#1E1E22", corner_radius=0)
        self.menu_bar.grid(row=1, column=0, sticky="ew")
        menu_container = ctk.CTkFrame(self.menu_bar, fg_color="transparent")
        menu_container.pack(expand=True, fill="y")
        for m in ["옵션", "로봇설정", "프로그램", "로그"]:
            ctk.CTkLabel(menu_container, text=m, font=ctk.CTkFont(size=13), text_color="#B0BEC5").pack(side="left", padx=40, pady=5)
        
        # 하단 터미널
        self.terminal = ctk.CTkTextbox(self, height=150, fg_color="#121215", text_color="#00FF41", font=ctk.CTkFont(family="Consolas", size=13))
        self.terminal.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        sys.stdout = PrintLogger(self.log_queue)
        
        # 페이지 컨테이너
        self.pages_container = ctk.CTkFrame(self, fg_color="transparent")
        self.pages_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.pages_container.grid_columnconfigure(0, weight=1)
        self.pages_container.grid_rowconfigure(0, weight=1)
        
        # Page 1 (Digital Twin)
        self.page1_frame = ctk.CTkFrame(self.pages_container, fg_color="transparent")
        self.page1_frame.grid(row=0, column=0, sticky="nsew")
        self.dt_view = DigitalTwinView(self.page1_frame)
        
        # Page 2 (HMI)
        self.page2_frame = ctk.CTkFrame(self.pages_container, fg_color="transparent")
        self.page2_frame.grid(row=0, column=0, sticky="nsew")
        self.hmi_view = RobotHmiView(self.page2_frame)
        
        # 로봇 기본 설정
        robot_manager.add_robot("Robot A", "192.168.3.7")
        robot_manager.add_robot("Robot B", "192.168.3.6")
        robot_manager.add_robot("Robot C", "192.168.3.5")
        
        # 기본 페이지 설정
        self.switch_page(2)
        
        # 폴링 스레드
        threading.Thread(target=self._poll_loop, daemon=True).start()
        
    def _poll_log_queue(self):
        try:
            while True:
                text = self.log_queue.get_nowait()
                if hasattr(self, 'terminal') and self.terminal.winfo_exists():
                    self.terminal.insert(ctk.END, text)
                    self.terminal.see(ctk.END)
        except queue.Empty:
            pass
        finally:
            self.after(50, self._poll_log_queue)
            
    def switch_page(self, page_num):
        if page_num == 1:
            self.btn_page1.configure(**self.style_active)
            self.btn_page2.configure(**self.style_inactive)
            self.page1_frame.tkraise()
        else:
            self.btn_page1.configure(**self.style_inactive)
            self.btn_page2.configure(**self.style_active)
            self.page2_frame.tkraise()
            
    def connect_all(self):
        def _bg():
            for name, info in robot_manager.get_all_robots().items():
                print(f">> [통신] {name} ({info['ip']}) 연결 시도...")
                if robot_manager.connect(name):
                    print(f">> [성공] {name} 연결 완료!")
        threading.Thread(target=_bg, daemon=True).start()
        
    def _poll_loop(self):
        while True:
            active = robot_manager.get_active_robot_name()
            
            # 모든 등록된 로봇을 순회하며 상태(좌표) 수집
            for name, info in robot_manager.get_all_robots().items():
                inst = info.get("instance")
                if inst is not None:
                    try:
                        with robot_manager.get_lock():
                            t_pos = inst.get_task_pos()
                            j_pos = inst.get_joint_pos()
                            
                        if t_pos and j_pos:
                            t_str = f"X: {t_pos[0]:.2f}  Y: {t_pos[1]:.2f}  Z: {t_pos[2]:.2f}\nU: {t_pos[3]:.2f}  V: {t_pos[4]:.2f}  W: {t_pos[5]:.2f}"
                            j_str = f"J1: {j_pos[0]:.2f}  J2: {j_pos[1]:.2f}  J3: {j_pos[2]:.2f}\nJ4: {j_pos[3]:.2f}  J5: {j_pos[4]:.2f}  J6: {j_pos[5]:.2f}"
                            
                            # active 로봇인지 여부 전달 (메인 텍스트 갱신용)
                            is_active = (name == active)
                            
                            self.after(0, lambda t=t_str, j=j_str, p=t_pos, jp=j_pos, n=name, a=is_active: self._update_labels(t, j, p, jp, n, a))
                    except Exception as e:
                        pass
            time.sleep(0.05)
            
    def _update_labels(self, t_str, j_str, t_pos, j_pos, name, is_active):
        # 현재 선택된 타겟 로봇일 경우에만 우측 텔레메트리 메인 패널 갱신
        if is_active:
            self.dt_view.task_label.configure(text=t_str)
            self.dt_view.joint_label.configure(text=j_str)
        
        # 각 로봇별 3D 뷰어 하단 미니 좌표 텍스트 갱신 (모든 로봇)
        if name in self.dt_view.robot_pos_labels:
            lbl = self.dt_view.robot_pos_labels[name]["label"]
            lbl.configure(text=f"{name} X: {t_pos[0]:.1f} Y: {t_pos[1]:.1f} Z: {t_pos[2]:.1f}")
        
        # 3D 뷰어 그래프 업데이트 (모든 연결된 로봇)
        self.dt_view.update_3d_graph(name, j_pos)
            
if __name__ == "__main__":
    app = ModernContyApp()
    app.mainloop()
