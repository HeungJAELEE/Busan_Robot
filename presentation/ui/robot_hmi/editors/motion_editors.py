import customtkinter as ctk
from .base_editor import BaseNodeEditor
from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
import threading
from core.domains.robot.communication.client_manager import robot_manager


class JogController:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.entries = {}
        self.target_q = None
        self.target_p = None
        self.target_labels = {}
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        jog_frame = ctk.CTkFrame(self.parent, fg_color="#18181B", corner_radius=8)
        jog_frame.pack(fill="x", padx=5, pady=2)
        
        top_f = ctk.CTkFrame(jog_frame, fg_color="transparent")
        top_f.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(top_f, text="🕹️ JOG CONTROL", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
        
        speed_f = ctk.CTkFrame(top_f, fg_color="transparent")
        speed_f.pack(side="right", padx=10)
        ctk.CTkLabel(speed_f, text="속도:", font=ctk.CTkFont(size=11)).pack(side="left", padx=2)
        self.speed_slider = ctk.CTkSlider(speed_f, from_=1, to=100, width=80)
        self.speed_slider.set(20)
        self.speed_slider.pack(side="left", padx=2)
        
        tabs = ctk.CTkTabview(jog_frame, corner_radius=8, height=150)
        tabs.pack(fill="x", padx=5, pady=2)

        def _sync_robot_pos():
            inst = robot_manager.get_active_instance()
            if inst:
                try:
                    q = inst.get_joint_pos()
                    p = inst.get_task_pos()
                    if q and p:
                        # 포커스된 항목 제외하고 갱신
                        focused = self.parent.focus_get()
                        for i, ax in enumerate(["J1","J2","J3","J4","J5","J6"]):
                            if focused != self.entries[ax]:
                                self.entries[ax].delete(0, "end")
                                self.entries[ax].insert(0, f"{q[i]:.2f}")
                        for i, ax in enumerate(["X","Y","Z","Rx","Ry","Rz"]):
                            if focused != self.entries[ax]:
                                self.entries[ax].delete(0, "end")
                                self.entries[ax].insert(0, f"{p[i]:.2f}")
                        # TCP는 생략하거나 p 재사용
                except Exception:
                    pass
            # 조깅 중에는 100ms, 아닐 때는 500ms 주기로 갱신
            interval = 100 if self.is_jogging else 500
            self.jog_sync_id = self.parent.after(interval, _sync_robot_pos)
            
        self.jog_sync_id = self.parent.after(500, _sync_robot_pos)

        
        self.jog_loops = {}
        self.is_jogging = False

        
        def start_jog(event, ax, amount):
            """누르는 동안 계속 움직이도록 큰 값으로 기동 시작"""
            self.is_jogging = True
            try:
                # 1. 속도 설정 (슬라이더 1~100 -> 레벨 1~9)
                speed_val = self.speed_slider.get()
                vel_level = max(1, min(9, int(speed_val / 11) + 1))
                is_joint = "J" in ax
                from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
                RobotControlUseCase.set_velocity_level(vel_level, is_joint)
                
                # 2. 아주 큰 거리로 기동 (누르는 동안 계속 가도록)
                large_amount = amount * 180.0 if is_joint else amount * 1000.0
                RobotControlUseCase.jog_axis(ax, large_amount)
                
                # 3. 조깅 중 좌표 갱신 빠르게 (100ms)
                if hasattr(self, "jog_sync_id"):
                    self.parent.after_cancel(self.jog_sync_id)
                _sync_robot_pos()
            except Exception as e:
                print(f"조그 시작 에러: {e}")
                
        def stop_jog(event, ax):
            """버튼을 떼면 즉시 정지"""
            self.is_jogging = False
            try:
                from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
                RobotControlUseCase.stop_robot()
            except:
                pass
            
            # 갱신 주기를 평소(500ms)로 원복
            if hasattr(self, "jog_sync_id"):
                self.parent.after_cancel(self.jog_sync_id)
            _sync_robot_pos()

        for t, axes in [("조인트 (Joint)", ["J1","J2","J3","J4","J5","J6"]), 
                        ("서버(Base)", ["X","Y","Z","Rx","Ry","Rz"]),
                        ("툴(TCP)", ["tX","tY","tZ","tRx","tRy","tRz"])]:
            tab = tabs.add(t)
            for ax in axes:
                f = ctk.CTkFrame(tab, fg_color="transparent")
                f.pack(fill="x", pady=1)
                ctk.CTkLabel(f, text=ax, width=40, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
                
                btn_minus = ctk.CTkButton(f, text="-", width=30, height=24)
                btn_minus.bind("<ButtonPress-1>", lambda e, a=ax: start_jog(e, a, -1.0))
                btn_minus.bind("<ButtonRelease-1>", lambda e, a=ax: stop_jog(e, a))
                btn_minus.pack(side="left", padx=2)
                
                ent = ctk.CTkEntry(f, justify="center", height=24)
                ent.pack(side="left", expand=True, fill="x", padx=2)
                ent.insert(0, "0.0")
                self.entries[ax] = ent
                
                btn_plus = ctk.CTkButton(f, text="+", width=30, height=24)
                btn_plus.bind("<ButtonPress-1>", lambda e, a=ax: start_jog(e, a, 1.0))
                btn_plus.bind("<ButtonRelease-1>", lambda e, a=ax: stop_jog(e, a))
                btn_plus.pack(side="left", padx=2)
                
        # 타겟 패널 (선택된 노드의 목표 좌표 표시 및 이동 버튼)
        self.target_frame = ctk.CTkFrame(jog_frame, fg_color="#121215", corner_radius=6)
        self.target_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        target_info_f = ctk.CTkFrame(self.target_frame, fg_color="transparent")
        target_info_f.pack(side="left", fill="x", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(target_info_f, text="🎯 선택 노드 목표 (Target)", font=ctk.CTkFont(weight="bold", size=11), text_color="#F57C00").pack(anchor="w")
        
        self.t_q_lbl = ctk.CTkLabel(target_info_f, text="J1: 0.00 | J2: 0.00 | J3: 0.00 | J4: 0.00 | J5: 0.00 | J6: 0.00", font=ctk.CTkFont(size=10), text_color="#8B8B96")
        self.t_q_lbl.pack(anchor="w")
        
        self.t_p_lbl = ctk.CTkLabel(target_info_f, text="X: 0.00 | Y: 0.00 | Z: 0.00 | Rx: 0.00 | Ry: 0.00 | Rz: 0.00", font=ctk.CTkFont(size=10), text_color="#8B8B96")
        self.t_p_lbl.pack(anchor="w")
        
        move_btn = ctk.CTkButton(self.target_frame, text="▶ 로봇 이동", width=80, height=36, fg_color="#2E7D32", hover_color="#1B5E20", command=self._move_to_target)
        move_btn.pack(side="right", padx=10, pady=5)

    def set_target(self, q, p):
        self.target_q = q
        self.target_p = p
        if q and len(q) >= 6:
            self.t_q_lbl.configure(text=f"J1:{q[0]:.2f} | J2:{q[1]:.2f} | J3:{q[2]:.2f} | J4:{q[3]:.2f} | J5:{q[4]:.2f} | J6:{q[5]:.2f}", text_color="#4CAF50")
        else:
            self.t_q_lbl.configure(text="J: 미설정", text_color="#8B8B96")
            
        if p and len(p) >= 6:
            self.t_p_lbl.configure(text=f"X:{p[0]:.2f} | Y:{p[1]:.2f} | Z:{p[2]:.2f} | Rx:{p[3]:.2f} | Ry:{p[4]:.2f} | Rz:{p[5]:.2f}", text_color="#4CAF50")
        else:
            self.t_p_lbl.configure(text="P: 미설정", text_color="#8B8B96")
            
    def _move_to_target(self):
        if self.target_q and len(self.target_q) >= 6 and not all(v == 0.0 for v in self.target_q):
            try:
                RobotControlUseCase.move_j(self.target_q)
            except Exception as e:
                print(f">> [조그] 타겟 이동 실패: {e}")
        elif self.target_p and len(self.target_p) >= 6 and not all(v == 0.0 for v in self.target_p):
            try:
                RobotControlUseCase.move_l(self.target_p)
            except Exception as e:
                print(f">> [조그] 타겟 이동 실패: {e}")

    def update_coordinates(self, q=None, p=None):
        if q and len(q) >= 6:
            for i, ax in enumerate(["J1","J2","J3","J4","J5","J6"]):
                self.entries[ax].delete(0, "end")
                self.entries[ax].insert(0, f"{q[i]:.2f}")
        if p and len(p) >= 6:
            for i, ax in enumerate(["X","Y","Z","Rx","Ry","Rz"]):
                self.entries[ax].delete(0, "end")
                self.entries[ax].insert(0, f"{p[i]:.2f}")
            for i, ax in enumerate(["tX","tY","tZ","tRx","tRy","tRz"]):
                self.entries[ax].delete(0, "end")
                self.entries[ax].insert(0, f"{p[i]:.2f}")

class MoveEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.header_label = None
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color="#2A2D35", height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="이동(Move) 설정", font=ctk.CTkFont(size=16, weight="bold"))
        self.header_label.pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(main_frame, text="기본 이동 설정입니다. 상세 로봇 좌표는 좌측 트리 선택 시 갱신됩니다.").pack(anchor="w", pady=(0, 10))
        
        # Blending 설정
        bf = ctk.CTkFrame(main_frame, fg_color="#2A2D35")
        bf.pack(fill="x", pady=5)
        ctk.CTkLabel(bf, text="블렌딩 (연속 동작) 설정", text_color="#1976D2").pack(anchor="w", padx=10, pady=5)
        
        br = ctk.CTkFrame(bf, fg_color="transparent")
        br.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(br, text="블렌딩 반경(Radius):").pack(side="left", padx=5)
        self.blend_entry = ctk.CTkEntry(br, width=60)
        self.blend_entry.insert(0, "0.0")
        self.blend_entry.pack(side="left", padx=5)
        ctk.CTkLabel(br, text="mm").pack(side="left")
        
        # Teach Button (Position Registration)
        tf = ctk.CTkFrame(main_frame, fg_color="transparent")
        tf.pack(fill="x", pady=10)
        self.teach_btn = ctk.CTkButton(tf, text="[위치 업데이트]", fg_color="#1976D2", hover_color="#1565C0", font=ctk.CTkFont(weight="bold"), width=100)
        self.teach_btn.pack(side="left", padx=(10, 5))
        self.load_btn = ctk.CTkButton(tf, text="[조그로 불러오기]", fg_color="#F57C00", hover_color="#E65100", font=ctk.CTkFont(weight="bold"), width=120)
        self.load_btn.pack(side="left", padx=5)
        self.move_btn = ctk.CTkButton(tf, text="[로봇 이동]", fg_color="#2E7D32", hover_color="#1B5E20", font=ctk.CTkFont(weight="bold"), width=100)
        self.move_btn.pack(side="left", padx=5)
        
        self.pos_info_label = ctk.CTkLabel(tf, text="저장된 좌표 없음", text_color="#B0BEC5")
        self.pos_info_label.pack(side="left", padx=10)
        
    def update_ui(self, node_name, b_radius=0.0, vel=5, acc=5):
        if self.header_label:
            name_only = node_name.replace("Node", "").strip()
            self.header_label.configure(text=f"사용자 {name_only} 설정")
        if hasattr(self, 'blend_entry'):
            self.blend_entry.delete(0, "end")
            self.blend_entry.insert(0, str(b_radius))
            if hasattr(self, 'vel_entry'):
                self.vel_entry.delete(0, "end")
                self.vel_entry.insert(0, str(vel))
                self.acc_entry.delete(0, "end")
                self.acc_entry.insert(0, str(acc))
                
    def apply_changes(self, node_data):
        if "boundary" not in node_data: node_data["boundary"] = {}
        try:
            node_data["boundary"]["velLevel"] = int(self.vel_entry.get())
            node_data["boundary"]["accLevel"] = int(self.acc_entry.get())
            node_data["b_radius"] = float(self.blend_entry.get())
        except Exception: pass
        if hasattr(self, 'pos_info_label'):
            self.pos_info_label.configure(text="J1: 0.0, J2: 0.0 ... (저장됨)")

class MoveByEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.header_label = None
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color="#2A2D35", height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="상대 위치(Move By) 설정", font=ctk.CTkFont(size=16, weight="bold"))
        self.header_label.pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(main_frame, text="현재 로봇 위치를 기준으로 지정된 거리만큼 이동합니다.").pack(anchor="w", pady=(0, 10))
        
        g = ctk.CTkFrame(main_frame, fg_color="#2A2D35")
        g.pack(fill="x", pady=5)
        
        self.entries = {}
        for idx, (ax, label_text) in enumerate([("dx", "X (mm)"), ("dy", "Y (mm)"), ("dz", "Z (mm)")]):
            row = ctk.CTkFrame(g, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(row, text=f"이동 거리 {label_text}:", width=120, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, width=100, justify="right")
            entry.insert(0, "0.0")
            entry.pack(side="left", padx=10)
            self.entries[ax] = entry
            
    def update_ui(self, node_name, dx=0.0, dy=0.0, dz=0.0):
        if self.header_label:
            name_only = node_name.replace("Node", "").strip()
            self.header_label.configure(text=f"사용자 {name_only} 설정")
        if hasattr(self, 'entries'):
            self.entries["dx"].delete(0, "end")
            self.entries["dx"].insert(0, str(dx))
            self.entries["dy"].delete(0, "end")
            self.entries["dy"].insert(0, str(dy))
            self.entries["dz"].delete(0, "end")
            self.entries["dz"].insert(0, str(dz))

class ForceEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.header_label = None
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color="#2A2D35", height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="힘 제어(Force) 설정", font=ctk.CTkFont(size=16, weight="bold"), text_color="#FF9800")
        self.header_label.pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(main_frame, text="임피던스(Impedance) 및 컴플라이언스 파라미터").pack(anchor="w", pady=(0, 10))
        
        g = ctk.CTkFrame(main_frame, fg_color="#2A2D35")
        g.pack(fill="x", pady=5)
        
        self.entries = {}
        fields = [("stiffness", "강성 (Stiffness, N/m)", "500.0"),
                  ("damping", "댐핑 (Damping, Ns/m)", "100.0"),
                  ("f_max", "최대 허용 힘 (F_max, N)", "50.0")]
                  
        for idx, (key, label, default) in enumerate(fields):
            row = ctk.CTkFrame(g, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(row, text=f"{label}:", width=160, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, width=80, justify="right")
            entry.insert(0, default)
            entry.pack(side="left", padx=10)
            self.entries[key] = entry
            
    def update_ui(self, node_name, stiffness=500.0, damping=100.0, f_max=50.0):
        if self.header_label:
            name_only = node_name.replace("Node", "").strip()
            self.header_label.configure(text=f"사용자 {name_only} 설정")
        if hasattr(self, 'entries'):
            self.entries["stiffness"].delete(0, "end")
            self.entries["stiffness"].insert(0, str(stiffness))
            self.entries["damping"].delete(0, "end")
            self.entries["damping"].insert(0, str(damping))
            self.entries["f_max"].delete(0, "end")
            self.entries["f_max"].insert(0, str(f_max))

class MoveHomeEditor:
    def __init__(self, parent_frame): self.parent = parent_frame
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color="#2A2D35", height=40)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="홈 이동(Move Home) 설정", font=ctk.CTkFont(size=16, weight="bold"), text_color="#1976D2").pack(pady=10)
        ctk.CTkLabel(self.parent, text="로봇이 미리 지정된 홈(Home) 위치로 이동합니다.").pack(pady=20)
    def update_ui(self, node_name): pass

class MoveCEditor(MoveEditor):
    def render(self):
        super().render()
        if self.header_label: self.header_label.configure(text="원호 이동(Move C) 설정")
        # For Move C, we need Waypoint 1 (via) and Waypoint 2 (target)
        tf = ctk.CTkFrame(self.parent, fg_color="#2A2D35")
        tf.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(tf, text="경유점 (Via Point) 티칭", text_color="#E91E63").pack(anchor="w", padx=10, pady=5)
        btn1 = ctk.CTkButton(tf, text="📍 현재 위치를 경유점으로 저장", fg_color="#9C27B0")
        btn1.pack(side="left", padx=10, pady=5)
        self.via_label = ctk.CTkLabel(tf, text="저장된 좌표 없음")
        self.via_label.pack(side="left", padx=10)