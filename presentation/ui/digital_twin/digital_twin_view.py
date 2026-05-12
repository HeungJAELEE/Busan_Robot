import customtkinter as ctk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from core.domains.robot.communication.client_manager import robot_manager
import math

class DigitalTwinView:
    def __init__(self, parent_tab):
        self.parent = parent_tab
        self.parent.grid_columnconfigure(0, weight=0, minsize=250)
        self.parent.grid_columnconfigure(1, weight=1)
        self.parent.grid_columnconfigure(2, weight=0, minsize=350)
        self.parent.grid_rowconfigure(0, weight=1)
        
        self.robot_arm_lines = {}
        self.robot_joints_dots = {}
        self.robot_trails = {}
        self.robot_pos_labels = {}
        
        self.history_x = {n: [] for n in ["Robot A", "Robot B", "Robot C"]}
        self.history_y = {n: [] for n in ["Robot A", "Robot B", "Robot C"]}
        self.history_z = {n: [] for n in ["Robot A", "Robot B", "Robot C"]}
        
        self.dh_params = [
            {"a": 0.0,    "alpha": 0.0,       "d": 0.3,    "theta_offset": 0.0},
            {"a": 0.0,    "alpha": np.pi/2,   "d": 0.0,    "theta_offset": np.pi/2},
            {"a": 0.45,   "alpha": 0.0,       "d": 0.0035, "theta_offset": np.pi/2},
            {"a": 0.0,    "alpha": np.pi/2,   "d": 0.35,   "theta_offset": np.pi},
            {"a": 0.0,    "alpha": np.pi/2,   "d": 0.1835, "theta_offset": 0.0},
            {"a": 0.0,    "alpha": -np.pi/2,  "d": 0.228,  "theta_offset": 0.0}
        ]
        
        # TCP offset (Tool Center Point) - loaded from JSON or default Indy7 gripper
        self.tcp_offset = np.array([0.0, 0.0, 0.21, 0.0, 0.0, 0.0])
        
        self.setup_ui()
        self._init_3d_viewer()
        
    def setup_ui(self):
        self.left_panel = ctk.CTkFrame(self.parent, fg_color="#18181B", corner_radius=12)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(self.left_panel, text="QUICK CONTROLS", font=ctk.CTkFont(size=14, weight="bold"), text_color="#8B8B96").pack(pady=(15, 10))
        
        self.robot_selector = ctk.CTkOptionMenu(self.left_panel, values=["Robot A", "Robot B", "Robot C"], command=self.change_target_robot)
        self.robot_selector.pack(pady=5, padx=20, fill="x")
        self.robot_selector.set("Robot A")
        
        ctk.CTkButton(self.left_panel, text="🏠 Home 위치", height=40, fg_color="#1976D2", command=lambda: self._safe_action("go_home")).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.left_panel, text="0️⃣ Zero 위치", height=40, fg_color="#F57C00", command=lambda: self._safe_action("go_zero")).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.left_panel, text="🔄 에러 리셋", height=40, fg_color="#9C27B0", command=lambda: self._safe_action("reset_robot")).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.left_panel, text="🚨 비상정지 (E-STOP)", height=50, font=ctk.CTkFont(weight="bold", size=15), fg_color="#D32F2F", hover_color="#B71C1C", command=self.emergency_stop).pack(pady=(15, 5), padx=20, fill="x")
        
        self.right_panel = ctk.CTkFrame(self.parent, fg_color="#18181B", corner_radius=12)
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(self.right_panel, text="📡 TELEMETRY DATA", font=ctk.CTkFont(size=14, weight="bold"), text_color="#8B8B96").pack(pady=15)
        
        task_box = ctk.CTkFrame(self.right_panel, fg_color="#121215")
        task_box.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(task_box, text="TCP POS (Base ➔ Tool)").pack(anchor="w", padx=10, pady=5)
        self.task_label = ctk.CTkLabel(task_box, text="WAITING SIGNAL...", text_color="#00E5FF", font=ctk.CTkFont(family="Consolas", size=14, weight="bold"), justify="left")
        self.task_label.pack(anchor="w", padx=10, pady=(0, 10))

        joint_box = ctk.CTkFrame(self.right_panel, fg_color="#121215")
        joint_box.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(joint_box, text="JOINT ANGLES (J1 ~ J6)").pack(anchor="w", padx=10, pady=5)
        self.joint_label = ctk.CTkLabel(joint_box, text="WAITING SIGNAL...", text_color="#00FF41", font=ctk.CTkFont(family="Consolas", size=14, weight="bold"), justify="left")
        self.joint_label.pack(anchor="w", padx=10, pady=(0, 10))
        
        self.center_panel = ctk.CTkFrame(self.parent, fg_color="#18181B", corner_radius=12)
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=10)
        ctk.CTkLabel(self.center_panel, text="🛰️ 3D DIGITAL TWIN VIEWER (LIVE)", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        
        self.viewer_container = ctk.CTkFrame(self.center_panel, fg_color="black")
        self.viewer_container.pack(fill="both", expand=True, padx=10, pady=10)
        
    def _init_3d_viewer(self):
        self.fig = plt.Figure(figsize=(8, 6), facecolor="#121215")
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_facecolor("#121215")
        
        for pane in (self.ax.xaxis, self.ax.yaxis, self.ax.zaxis):
            pane.set_pane_color((0.09, 0.09, 0.11, 1.0))
        
        self.ax.grid(color='#2A2A35', linestyle=':', linewidth=0.5)
        self.ax.tick_params(colors="#8B8B96", labelsize=8)
        self.ax.set_xlim([-0.8, 0.8])
        self.ax.set_ylim([-1.5, 1.5])
        self.ax.set_zlim([0, 1.2])
        self.ax.view_init(elev=20, azim=45)
        
        self.robot_offsets = {
            "Robot C": np.array([0, 1.0, 0]),
            "Robot B": np.array([0, 0.0, 0]),
            "Robot A": np.array([0, -1.0, 0])
        }

        color_map = {"Robot C": "#FF1744", "Robot B": "#00E5FF", "Robot A": "#00FF41"}
        
        label_frame = ctk.CTkFrame(self.center_panel, fg_color="transparent")
        label_frame.pack(side="bottom", fill="x", pady=5)

        for name in ["Robot A", "Robot B", "Robot C"]:
            col = color_map.get(name, "#FFFFFF")
            self.robot_arm_lines[name], = self.ax.plot([], [], [], '-', color=col, lw=3)
            self.robot_joints_dots[name], = self.ax.plot([], [], [], 'o', color=col, markersize=6, markerfacecolor='white', markeredgecolor=col, markeredgewidth=2)
            self.robot_trails[name], = self.ax.plot([], [], [], '-', color=col, alpha=0.4, lw=1.5)
            
            wrapper = ctk.CTkFrame(label_frame, fg_color="transparent")
            wrapper.pack(side="left", expand=True)
            status_box = ctk.CTkFrame(wrapper, width=12, height=12, corner_radius=2, fg_color="#555555")
            status_box.pack(side="left", padx=5)
            status_box.pack_propagate(False)
            lbl = ctk.CTkLabel(wrapper, text=f"{name}: 연결 대기중", font=ctk.CTkFont(size=12, weight="bold"), text_color=col)
            lbl.pack(side="left")
            self.robot_pos_labels[name] = {"label": lbl, "box": status_box}
            
        self.robot_pos_labels["Robot A"]["box"].configure(fg_color="#00FF41")
            
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.viewer_container)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=2, pady=2)
        
    def compute_forward_kinematics(self, joint_angles):
        T_matrices = [np.eye(4)] 
        T = np.eye(4)
        for i in range(6):
            theta = np.radians(joint_angles[i]) + self.dh_params[i]['theta_offset']
            a = self.dh_params[i]['a']
            alpha = self.dh_params[i]['alpha']
            d = self.dh_params[i]['d']
            ct, st = np.cos(theta), np.sin(theta)
            ca, sa = np.cos(alpha), np.sin(alpha)
            T_i = np.array([
                [           ct,            -st,   0,             a],
                [        st*ca,          ct*ca, -sa,         -d*sa],
                [        st*sa,          ct*sa,  ca,          d*ca],
                [            0,              0,   0,             1]
            ])
            T = T @ T_i 
            T_matrices.append(T)
        return T_matrices
        
    def update_3d_graph(self, name, j_pos):
        if not j_pos: return
        try:
            T = self.compute_forward_kinematics(j_pos)
            offset_y = 0.1835  
            P0 = T[0][:3, 3]
            P1 = T[1][:3, 3] 
            P2 = (T[2] @ np.array([0, 0, offset_y, 1]))[:3] 
            P3 = (T[3] @ np.array([0, 0, offset_y, 1]))[:3] 
            P3_corner = T[3][:3, 3]
            P4 = T[4][:3, 3]
            P5 = T[5][:3, 3]
            P6_flange = T[6][:3, 3] 
            
            # Apply TCP offset to get actual tool tip position
            tcp_local = np.array([self.tcp_offset[0], self.tcp_offset[1], self.tcp_offset[2], 1.0])
            P6 = (T[6] @ tcp_local)[:3]

            offset = self.robot_offsets.get(name, np.array([0, 0, 0]))
            P0 += offset; P1 += offset; P2 += offset; P3 += offset; P3_corner += offset
            P4 += offset; P5 += offset; P6 += offset

            line_xs = [P0[0], P1[0], P2[0], P3[0], P3_corner[0], P4[0], P5[0], P6[0]]
            line_ys = [P0[1], P1[1], P2[1], P3[1], P3_corner[1], P4[1], P5[1], P6[1]]
            line_zs = [P0[2], P1[2], P2[2], P3[2], P3_corner[2], P4[2], P5[2], P6[2]]
            self.robot_arm_lines[name].set_data(line_xs, line_ys)
            self.robot_arm_lines[name].set_3d_properties(line_zs)

            joint_xs = [P0[0], P2[0], P3[0], P4[0], P5[0], P6[0]]
            joint_ys = [P0[1], P2[1], P3[1], P4[1], P5[1], P6[1]]
            joint_zs = [P0[2], P2[2], P3[2], P4[2], P5[2], P6[2]]
            self.robot_joints_dots[name].set_data(joint_xs, joint_ys)
            self.robot_joints_dots[name].set_3d_properties(joint_zs)

            self.canvas.draw_idle()
        except Exception as e:
            pass

    def change_target_robot(self, name):
        robot_manager.set_active_robot(name)
        print(f"\n>> 🎯 제어 타겟 로봇 변경: {name}")
        for n in ["Robot A", "Robot B", "Robot C"]:
            self.history_x[n].clear()
            self.history_y[n].clear()
            self.history_z[n].clear()
            if n in self.robot_pos_labels:
                box = self.robot_pos_labels[n]["box"]
                if n == name:
                    box.configure(fg_color="#00FF41")
                else:
                    box.configure(fg_color="#555555")
                    
    def emergency_stop(self):
        print("\n🚨 [긴급] 사용자가 비상정지(E-STOP) 버튼을 눌렀습니다!")
        import threading
        def _bg():
            inst = robot_manager.get_active_instance()
            if inst:
                try:
                    with robot_manager.get_lock():
                        inst.stop_emergency()
                    print(">> 🚨 정지 명령이 전송되었습니다.")
                except Exception as e:
                    print(f"❌ [에러] 비상정지 실패: {e}")
            else:
                print(">> [알림] 현재 연결된 활성 로봇이 없습니다.")
        threading.Thread(target=_bg, daemon=True).start()
            
    def _safe_action(self, func_name):
        def _bg():
            inst = robot_manager.get_active_instance()
            if inst:
                try:
                    with robot_manager.get_lock():
                        getattr(inst, func_name)()
                except Exception as e:
                    print(f"❌ [에러] 명령 실행 실패: {e}")
        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def _update_lamp(self, addr, state):
        color = "#424242" # Off
        if state == 1:
            if addr == "M102": color = "#F44336" # Red for Alarm
            elif addr in ["M100", "M105"]: color = "#2196F3" # Blue for Inputs
            else: color = "#4CAF50" # Green for Outputs
            
        if addr in self.lamps:
            self.lamps[addr].configure(fg_color=color)

    def _on_plc_state_change(self, addr, state):
        if hasattr(self.parent, "after"):
            self.parent.after(0, lambda: self._update_lamp(addr, state))

    def _start_auto_mode(self):
        from infrastructure.robot_control.conty_executor import ContyExecutor
        import os, json
        
        active_robot = robot_manager.get_active_robot_name()
        if not active_robot:
            print(">> [에러] 선택된 활성 로봇이 없습니다.")
            return
            
        ip = self.plc_ip_entry.get()
        port = int(self.plc_port_entry.get())
        robot_ip = robot_manager.get_all_robots().get(active_robot, {}).get("ip", "127.0.0.1")
        
        # Load the latest program for the active robot
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        path = os.path.join(base_dir, 'user_programs', active_robot.replace(" ", "_"), 'program.json')
        
        if not os.path.exists(path):
            print(f">> [에러] 프로그램 파일을 찾을 수 없습니다: {path}")
            return
            
        with open(path, "r", encoding="utf-8") as f:
            json_str = f.read()
            
        self.executor = ContyExecutor(robot_ip=robot_ip, plc_ip=ip, plc_port=port, robot_name=active_robot)
        self.executor.state_callback = self._on_plc_state_change
        
        if self.executor.connect():
            self.btn_auto_start.configure(state="disabled", fg_color="#424242")
            self.btn_auto_stop.configure(state="normal")
            print(">> [UI] PLC 연동 엔진 구동을 시작합니다.")
            self.executor.start_auto_mode(json_str)
        else:
            print(">> [에러] PLC 연동 엔진 연결에 실패했습니다.")

    def _stop_auto_mode(self):
        if self.executor:
            print(">> [UI] PLC 연동 엔진 구동을 정지합니다.")
            self.executor.stop()
            self.executor.disconnect()
            self.executor = None
            
        self.btn_auto_start.configure(state="normal", fg_color="#2E7D32")
        self.btn_auto_stop.configure(state="disabled")
        for addr in self.lamps:
            self._update_lamp(addr, 0)
