import customtkinter as ctk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from core.domains.robot.communication.client_manager import robot_manager
import math
from presentation.ui.robot_hmi.robot_hmi_view import ProgramTreeEditor, RobotSettingsEditor
from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
from core.domains.robot.use_cases.singularity_analyzer import SingularityAnalyzer

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
        self.robot_zone_scatters = {}
        self.robot_tcp_dots = {}
        self.robot_pos_labels = {}
        self.program_runners = {}
        self.program_runner_hosts = {}
        self.program_status_labels = {}
        self.program_status_boxes = {}
        self.executor = None
        
        self.history_x = {n: [] for n in ["Robot A", "Robot B", "Robot C"]}
        self.history_y = {n: [] for n in ["Robot A", "Robot B", "Robot C"]}
        self.history_z = {n: [] for n in ["Robot A", "Robot B", "Robot C"]}
        self.history_zone_colors = {n: [] for n in ["Robot A", "Robot B", "Robot C"]}
        self.last_singularity_guides = {}
        self.max_trail_points = 160
        self.zone_sample_distance_m = 0.02
        
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
        self.singularity_analyzer = SingularityAnalyzer(self.dh_params, self.tcp_offset)
        
        self.setup_ui()
        self._init_3d_viewer()
        self._poll_program_status()
        
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
        ctk.CTkButton(self.left_panel, text="🧹 궤적 초기화", height=34, fg_color="#455A64", hover_color="#546E7A", command=self.clear_trajectories).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.left_panel, text="🚨 비상정지 (E-STOP)", height=50, font=ctk.CTkFont(weight="bold", size=15), fg_color="#D32F2F", hover_color="#B71C1C", command=self.emergency_stop).pack(pady=(15, 5), padx=20, fill="x")

        program_box = ctk.CTkFrame(self.left_panel, fg_color="#121215", corner_radius=8)
        program_box.pack(fill="x", padx=15, pady=(10, 5))
        ctk.CTkLabel(program_box, text="PROGRAM RUN", font=ctk.CTkFont(size=13, weight="bold"), text_color="#8B8B96").pack(pady=(10, 6))

        for name in ["Robot A", "Robot B", "Robot C"]:
            row = ctk.CTkFrame(program_box, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=3)

            box = ctk.CTkFrame(row, width=10, height=10, corner_radius=2, fg_color="#555555")
            box.pack(side="left", padx=(0, 5))
            box.pack_propagate(False)

            ctk.CTkLabel(row, text=name.replace("Robot ", ""), width=18, font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
            status = ctk.CTkLabel(row, text="대기", width=48, font=ctk.CTkFont(size=11), text_color="#8B8B96")
            status.pack(side="left", padx=4)

            ctk.CTkButton(row, text="▶", width=32, height=26, fg_color="#2E7D32", hover_color="#388E3C",
                          command=lambda n=name: self._run_saved_program(n)).pack(side="left", padx=2)
            ctk.CTkButton(row, text="■", width=32, height=26, fg_color="#B71C1C", hover_color="#D32F2F",
                          command=lambda n=name: self._stop_saved_program(n)).pack(side="left", padx=2)

            self.program_status_boxes[name] = box
            self.program_status_labels[name] = status
        
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

        zone_box = ctk.CTkFrame(self.right_panel, fg_color="#121215")
        zone_box.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(zone_box, text="SINGULARITY GUIDE ZONE").pack(anchor="w", padx=10, pady=5)
        self.singularity_label = ctk.CTkLabel(
            zone_box,
            text="녹색 <70 권장 안전\n주황 70~90 주의\n빨강 90~100 위험",
            text_color=SingularityAnalyzer.COLOR_SAFE,
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            justify="left",
        )
        self.singularity_label.pack(anchor="w", padx=10, pady=(0, 10))
        
        # 네트워크 및 연결 설정 추가
        ctk.CTkFrame(self.right_panel, height=2, fg_color="#3A3D45").pack(fill="x", padx=15, pady=15)
        self.network_editor = RobotSettingsEditor(self.right_panel)
        
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
            self.robot_trails[name], = self.ax.plot([], [], [], color=col, alpha=0.55, lw=1.8, linestyle='--')
            self.robot_zone_scatters[name] = self.ax.scatter([], [], [], c=[], s=28, alpha=0.9, depthshade=False)
            self.robot_tcp_dots[name], = self.ax.plot([], [], [], 'o', color=col, markersize=9, markerfacecolor=col, markeredgecolor='white', markeredgewidth=1.4)
            
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
        
    def clear_trajectories(self):
        for name in ["Robot A", "Robot B", "Robot C"]:
            self.history_x[name].clear()
            self.history_y[name].clear()
            self.history_z[name].clear()
            self.history_zone_colors[name].clear()
            if name in self.robot_trails:
                self.robot_trails[name].set_data([], [])
                self.robot_trails[name].set_3d_properties([])
            if name in self.robot_zone_scatters:
                self.robot_zone_scatters[name]._offsets3d = ([], [], [])
                self.robot_zone_scatters[name].set_color([])
        try:
            self.canvas.draw_idle()
        except Exception:
            pass

    def update_3d_graph(self, name, j_pos, task_pos=None):
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

            hx, hy, hz = self.history_x[name], self.history_y[name], self.history_z[name]
            hc = self.history_zone_colors[name]
            should_append = True
            if hx:
                dist = float(np.linalg.norm(np.array([P6[0]-hx[-1], P6[1]-hy[-1], P6[2]-hz[-1]])))
                should_append = dist > self.zone_sample_distance_m
            guide = self.last_singularity_guides.get(name)
            if should_append or not guide:
                guide = self.singularity_analyzer.analyze(j_pos, tcp_pos_m=P6)
                self.last_singularity_guides[name] = guide
            zone_color = guide["color"]
            self.robot_tcp_dots[name].set_data([P6[0]], [P6[1]])
            self.robot_tcp_dots[name].set_3d_properties([P6[2]])
            self.robot_tcp_dots[name].set_color(zone_color)
            self.robot_tcp_dots[name].set_markerfacecolor(zone_color)

            if should_append:
                hx.append(float(P6[0]))
                hy.append(float(P6[1]))
                hz.append(float(P6[2]))
                hc.append(zone_color)
                if len(hx) > self.max_trail_points:
                    del hx[:-self.max_trail_points]
                    del hy[:-self.max_trail_points]
                    del hz[:-self.max_trail_points]
                    del hc[:-self.max_trail_points]
                self.robot_trails[name].set_data(hx, hy)
                self.robot_trails[name].set_3d_properties(hz)
                if name in self.robot_zone_scatters:
                    self.robot_zone_scatters[name]._offsets3d = (hx, hy, hz)
                    self.robot_zone_scatters[name].set_color(hc)

            if name == robot_manager.get_active_robot_name() or name == self.robot_selector.get():
                self.singularity_label.configure(
                    text=(
                        f"{guide['label']}  risk={guide['score']:.0f}/100\n"
                        f"Manip={guide['manipulability']:.4f}  Cond={guide['condition']:.1f}\n"
                        "녹색 <70 | 주황 70~90 | 빨강 90~100"
                    ),
                    text_color=zone_color,
                )

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
        target = self.robot_selector.get()
        RobotControlUseCase.emergency_stop(target)
        print(f">> 🚨 {target} 정지 명령이 전송되었습니다.")

    def _safe_action(self, func_name):
        """IndyDCP 내부 lock이 thread-safety를 보장하므로 외부 lock 불필요"""
        target = self.robot_selector.get()
        action_map = {
            "go_home": RobotControlUseCase.go_home,
            "go_zero": RobotControlUseCase.go_zero,
            "reset_robot": RobotControlUseCase.reset_robot,
        }
        action = action_map.get(func_name)
        if action:
            action(target)
        else:
            # Fallback: 직접 inst 호출 (lock 없이 — IndyDCP 내부 lock이 보호)
            def _bg():
                info = robot_manager.get_robot_info(target)
                inst = info.get("instance") if info else None
                if inst:
                    try:
                        getattr(inst, func_name)()
                    except Exception as e:
                        print(f"❌ [에러] 명령 실행 실패: {e}")
            import threading
            threading.Thread(target=_bg, daemon=True).start()

    def _get_program_runner(self, name):
        runner = self.program_runners.get(name)
        if runner:
            return runner
        host = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.program_runner_hosts[name] = host
        runner = ProgramTreeEditor(host)
        runner.current_robot = name
        self.program_runners[name] = runner
        return runner

    def _run_saved_program(self, name):
        info = robot_manager.get_robot_info(name)
        if not info or info.get("instance") is None:
            print(f">> [오류] {name} 로봇이 연결되지 않았습니다.")
            self._set_program_status(name, "미연결", "#F44336")
            return
        runner = self._get_program_runner(name)
        if runner.is_execution_running():
            print(f">> [경고] {name} 프로그램이 이미 실행 중입니다.")
            return
        print(f">> [Page 1] {name} 저장 JSON 프로그램 실행")
        runner.run_program_for_robot(name)
        self._set_program_status(name, "실행중", "#00E676")

    def _stop_saved_program(self, name):
        print(f">> [Page 1] {name} 프로그램 정지 요청")
        RobotControlUseCase.request_stop(name)
        runner = self.program_runners.get(name)
        if runner:
            runner.current_robot = name
            runner._stop_execution()
        else:
            RobotControlUseCase.emergency_stop(name)
        self._set_program_status(name, "정지", "#FF9800")

    def _set_program_status(self, name, text, color):
        label = self.program_status_labels.get(name)
        box = self.program_status_boxes.get(name)
        if label:
            label.configure(text=text, text_color=color)
        if box:
            box.configure(fg_color=color)

    def _poll_program_status(self):
        for name in ["Robot A", "Robot B", "Robot C"]:
            runner = self.program_runners.get(name)
            if runner and runner.is_execution_running():
                self._set_program_status(name, "실행중", "#00E676")
            elif RobotControlUseCase.is_stop_requested(name):
                self._set_program_status(name, "정지", "#FF9800")
            else:
                connected = robot_manager.is_connected(name)
                self._set_program_status(name, "대기", "#8B8B96" if connected else "#555555")
        try:
            self.parent.after(300, self._poll_program_status)
        except Exception:
            pass

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
