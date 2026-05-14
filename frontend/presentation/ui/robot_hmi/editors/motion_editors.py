import customtkinter as ctk
from .base_editor import BaseNodeEditor
from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
import threading
from core.domains.robot.communication.client_manager import robot_manager
from presentation.ui.theme import Theme


class JogController:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.entries = {}
        self.target_q = None
        self.target_p = None
        self.target_labels = {}
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        jog_frame = ctk.CTkFrame(self.parent, fg_color=Theme.BG_BASE, corner_radius=8)
        jog_frame.pack(fill="x", padx=5, pady=2)
        
        top_f = ctk.CTkFrame(jog_frame, fg_color="transparent")
        top_f.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(top_f, text="🕹️ JOG CONTROL", font=Theme.font(size=12, weight="bold")).pack(side="left", padx=10)
        
        speed_f = ctk.CTkFrame(top_f, fg_color="transparent")
        speed_f.pack(side="right", padx=10)
        
        self.status_label = ctk.CTkLabel(speed_f, text="⚠️ 연결 끊김", text_color=Theme.DANGER, font=Theme.font(size=11, weight="bold"))
        self.status_label.pack(side="left", padx=10)
        
        ctk.CTkLabel(speed_f, text="속도:", font=Theme.font(size=11)).pack(side="left", padx=2)
        self.speed_slider = ctk.CTkSlider(speed_f, from_=1, to=100, width=80)
        self.speed_slider.set(20)
        self.speed_slider.pack(side="left", padx=2)
        
        tabs = ctk.CTkTabview(jog_frame, corner_radius=8, height=150)
        tabs.pack(fill="x", padx=5, pady=2)

        def _sync_robot_pos():
            if not self.parent.winfo_exists():
                return
            
            active_name = robot_manager.get_active_robot_name()
            if active_name:
                state = robot_manager.get_robot_state(active_name)
                
                if state:
                    # 로봇 상태에 따른 세밀한 표시
                    rs = state.get("status")
                    if rs:
                        if rs.get("emergency"):
                            self.status_label.configure(text="🚨 비상정지", text_color=Theme.DANGER)
                        elif rs.get("collision"):
                            self.status_label.configure(text="⚠️ 충돌 감지", text_color="#FF6F00")
                        elif rs.get("error"):
                            self.status_label.configure(text="❌ 에러 상태", text_color=Theme.DANGER)
                        elif rs.get("busy"):
                            self.status_label.configure(text="🔄 동작중...", text_color=Theme.WARNING)
                        else:
                            self.status_label.configure(text="✅ 실시간 갱신중", text_color="#00FF41")
                    else:
                        self.status_label.configure(text="✅ 실시간 갱신중", text_color="#00FF41")
                    
                    q = state.get("j_pos")
                    p = state.get("t_pos")
                    
                    if q and p:
                        focused = self.parent.focus_get()
                        for i, ax in enumerate(["J1","J2","J3","J4","J5","J6"]):
                            if focused != self.entries[ax]:
                                self.entries[ax].delete(0, "end")
                                self.entries[ax].insert(0, f"{q[i]:.2f}")
                        for i, ax in enumerate(["X","Y","Z","Rx","Ry","Rz"]):
                            if focused != self.entries[ax]:
                                self.entries[ax].delete(0, "end")
                                self.entries[ax].insert(0, f"{p[i]:.2f}")
                else:
                    self.status_label.configure(text="⚠️ 연결 끊김", text_color=Theme.DANGER)
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
                ctk.CTkLabel(f, text=ax, width=40, font=Theme.font(size=12, weight="bold")).pack(side="left", padx=5)
                
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
        self.target_frame = ctk.CTkFrame(jog_frame, fg_color=Theme.BG_BASE, corner_radius=6)
        self.target_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        target_info_f = ctk.CTkFrame(self.target_frame, fg_color="transparent")
        target_info_f.pack(side="left", fill="x", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(target_info_f, text="🎯 선택 노드 목표 (Target)", font=ctk.CTkFont(weight="bold", size=11), text_color="#F57C00").pack(anchor="w")
        
        self.t_q_lbl = ctk.CTkLabel(target_info_f, text="J1: 0.00 | J2: 0.00 | J3: 0.00 | J4: 0.00 | J5: 0.00 | J6: 0.00", font=Theme.font(size=10), text_color=Theme.TEXT_SECONDARY)
        self.t_q_lbl.pack(anchor="w")
        
        self.t_p_lbl = ctk.CTkLabel(target_info_f, text="X: 0.00 | Y: 0.00 | Z: 0.00 | Rx: 0.00 | Ry: 0.00 | Rz: 0.00", font=Theme.font(size=10), text_color=Theme.TEXT_SECONDARY)
        self.t_p_lbl.pack(anchor="w")
        
        btn_col = ctk.CTkFrame(self.target_frame, fg_color="transparent")
        btn_col.pack(side="right", padx=10, pady=5)
        
        move_btn = ctk.CTkButton(btn_col, text="▶ 로봇 이동", width=80, height=28, fg_color=Theme.SUCCESS, hover_color="#1B5E20", command=self._move_to_target)
        move_btn.pack(pady=1)
        
        home_btn = ctk.CTkButton(btn_col, text="🏠 Home", width=80, height=28, fg_color="#1565C0", hover_color="#0D47A1", command=self._move_to_home)
        home_btn.pack(pady=1)
        
        zero_btn = ctk.CTkButton(btn_col, text="0️⃣ Zero", width=80, height=28, fg_color="#F57C00", hover_color=Theme.WARNING, command=self._move_to_zero)
        zero_btn.pack(pady=1)
        
        # === 로봇 제어 패널 (다이렉트 티칭, 충돌 감도, 서보) ===
        ctrl_frame = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, corner_radius=6)
        ctrl_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        # Row 1: 라벨
        ctrl_row1 = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        ctrl_row1.pack(fill="x", padx=5, pady=(5, 2))
        ctk.CTkLabel(ctrl_row1, text="🤖 로봇 제어", font=Theme.font(size=12, weight="bold"), text_color="#90CAF9").pack(side="left", padx=5)
        
        # Row 2: 버튼 3개 (균일 배분)
        ctrl_row2 = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        ctrl_row2.pack(fill="x", padx=5, pady=2)
        ctrl_row2.grid_columnconfigure((0, 1, 2), weight=1)
        
        self._dt_on = False
        self.dt_btn = ctk.CTkButton(ctrl_row2, text="✋ 직접교시 OFF", height=30, 
                                     fg_color=Theme.BG_BASE, hover_color=Theme.ACCENT_SECONDARY,
                                     font=Theme.font(size=11, weight="bold"),
                                     command=self._toggle_direct_teaching)
        self.dt_btn.grid(row=0, column=0, padx=2, sticky="ew")
        
        self.servo_btn = ctk.CTkButton(ctrl_row2, text="⚡ 서보 ON", height=30,
                                        fg_color="#00695C", hover_color="#004D40",
                                        font=Theme.font(size=11, weight="bold"),
                                        command=self._toggle_servo)
        self.servo_btn.grid(row=0, column=1, padx=2, sticky="ew")
        self._servo_on = True
        
        ctk.CTkButton(ctrl_row2, text="🔄 리셋", height=30,
                       fg_color=Theme.DANGER, hover_color=Theme.DANGER_HOVER,
                       font=Theme.font(size=11, weight="bold"),
                       command=self._reset_robot).grid(row=0, column=2, padx=2, sticky="ew")
        
        # Row 3: 충돌 감도 슬라이더
        ctrl_row3 = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        ctrl_row3.pack(fill="x", padx=5, pady=(2, 5))
        
        ctk.CTkLabel(ctrl_row3, text="충돌 감도:", font=Theme.font(size=10), text_color=Theme.TEXT_SECONDARY).pack(side="left", padx=5)
        self.collision_slider = ctk.CTkSlider(ctrl_row3, from_=1, to=5, number_of_steps=4, width=120,
                                               command=self._on_collision_change)
        self.collision_slider.set(3)
        self.collision_slider.pack(side="left", padx=3, fill="x", expand=True)
        self.collision_lbl = ctk.CTkLabel(ctrl_row3, text="Lv.3", font=Theme.font(size=10), text_color=Theme.WARNING)
        self.collision_lbl.pack(side="left", padx=5)
        
        # === I/O 모니터링 패널 ===
        from .io_monitor import IOMonitorPanel
        self.io_monitor = IOMonitorPanel(self.parent)

    def set_target(self, q, p):
        self.target_q = q
        self.target_p = p
        if q and len(q) >= 6:
            self.t_q_lbl.configure(text=f"J1:{q[0]:.2f} | J2:{q[1]:.2f} | J3:{q[2]:.2f} | J4:{q[3]:.2f} | J5:{q[4]:.2f} | J6:{q[5]:.2f}", text_color=Theme.SUCCESS)
        else:
            self.t_q_lbl.configure(text="J: 미설정", text_color=Theme.TEXT_SECONDARY)
            
        if p and len(p) >= 6:
            self.t_p_lbl.configure(text=f"X:{p[0]:.2f} | Y:{p[1]:.2f} | Z:{p[2]:.2f} | Rx:{p[3]:.2f} | Ry:{p[4]:.2f} | Rz:{p[5]:.2f}", text_color=Theme.SUCCESS)
        else:
            self.t_p_lbl.configure(text="P: 미설정", text_color=Theme.TEXT_SECONDARY)
            
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

    def _move_to_home(self):
        """Move robot to Home position (0, 0, -90, 0, -90, 0)."""
        try:
            print(">> [이동] Home 위치로 이동합니다: [0, 0, -90, 0, -90, 0]")
            RobotControlUseCase.move_to_joint([0.0, 0.0, -90.0, 0.0, -90.0, 0.0])
        except Exception as e:
            print(f">> [에러] Home 이동 실패: {e}")
    
    def _move_to_zero(self):
        """Move robot to Zero position (all joints 0)."""
        try:
            print(">> [이동] Zero 위치로 이동합니다: [0, 0, 0, 0, 0, 0]")
            RobotControlUseCase.move_to_joint([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        except Exception as e:
            print(f">> [에러] Zero 이동 실패: {e}")

    def _toggle_direct_teaching(self):
        """다이렉트 티칭 모드 ON/OFF 토글."""
        self._dt_on = not self._dt_on
        RobotControlUseCase.direct_teaching(self._dt_on)
        if self._dt_on:
            self.dt_btn.configure(text="✋ 직접교시 ON", fg_color=Theme.WARNING)
            print(">> [직접교시] ON — 로봇을 손으로 움직여 위치를 기록하세요.")
        else:
            self.dt_btn.configure(text="✋ 직접교시 OFF", fg_color=Theme.BG_SURFACE)
            print(">> [직접교시] OFF")
    
    def _toggle_servo(self):
        """서보 ON/OFF 토글."""
        self._servo_on = not self._servo_on
        RobotControlUseCase.set_servo(self._servo_on)
        if self._servo_on:
            self.servo_btn.configure(text="⚡ 서보 ON", fg_color="#00695C")
        else:
            self.servo_btn.configure(text="⚡ 서보 OFF", fg_color=Theme.DANGER)
    
    def _reset_robot(self):
        """로봇 에러/충돌/비상정지 리셋."""
        RobotControlUseCase.reset_robot()
        print(">> [리셋] 로봇 에러 리셋 완료")
    
    def _on_collision_change(self, val):
        """충돌 감도 레벨 변경."""
        level = int(round(val))
        self.collision_lbl.configure(text=f"Lv.{level}")
        RobotControlUseCase.set_collision_level(level)
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
        self._waypoints = []  # 저장된 웨이포인트 데이터
        self._selected_wp_idx = 0
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="이동(Move) 설정", font=Theme.font(size=16, weight="bold"))
        self.header_label.pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=2)
        
        # ── 속도 / 가감속 설정 (Conty boundary) ──
        speed_frame = ctk.CTkFrame(main_frame, fg_color=Theme.BG_SURFACE)
        speed_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(speed_frame, text="⚡ 속도 / 가감속 설정", text_color=Theme.WARNING, font=Theme.font(size=12, weight="bold")).pack(anchor="w", padx=10, pady=5)
        
        vel_row = ctk.CTkFrame(speed_frame, fg_color="transparent")
        vel_row.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(vel_row, text="속도 레벨:", width=80).pack(side="left", padx=5)
        self.vel_slider = ctk.CTkSlider(vel_row, from_=1, to=9, number_of_steps=8, width=150)
        self.vel_slider.set(5)
        self.vel_slider.pack(side="left", padx=5, fill="x", expand=True)
        self.vel_label = ctk.CTkLabel(vel_row, text="Lv.5", width=40, font=Theme.font(size=11, weight="bold"), text_color=Theme.SUCCESS)
        self.vel_label.pack(side="left", padx=5)
        self.vel_slider.configure(command=lambda v: self.vel_label.configure(text=f"Lv.{int(v)}"))
        
        acc_row = ctk.CTkFrame(speed_frame, fg_color="transparent")
        acc_row.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(acc_row, text="가감속 레벨:", width=80).pack(side="left", padx=5)
        self.acc_slider = ctk.CTkSlider(acc_row, from_=1, to=9, number_of_steps=8, width=150)
        self.acc_slider.set(5)
        self.acc_slider.pack(side="left", padx=5, fill="x", expand=True)
        self.acc_label = ctk.CTkLabel(acc_row, text="Lv.5", width=40, font=Theme.font(size=11, weight="bold"), text_color=Theme.SUCCESS)
        self.acc_label.pack(side="left", padx=5)
        self.acc_slider.configure(command=lambda v: self.acc_label.configure(text=f"Lv.{int(v)}"))
        
        # ── 블렌딩 설정 ──
        bf = ctk.CTkFrame(main_frame, fg_color=Theme.BG_SURFACE)
        bf.pack(fill="x", pady=5)
        ctk.CTkLabel(bf, text="🔗 블렌딩 (연속 동작)", text_color=Theme.INFO, font=Theme.font(size=12, weight="bold")).pack(anchor="w", padx=10, pady=5)
        
        br = ctk.CTkFrame(bf, fg_color="transparent")
        br.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(br, text="블렌딩 반경:").pack(side="left", padx=5)
        self.blend_entry = ctk.CTkEntry(br, width=60)
        self.blend_entry.insert(0, "0.0")
        self.blend_entry.pack(side="left", padx=5)
        ctk.CTkLabel(br, text="mm").pack(side="left")
        
        # ── 웨이포인트 리스트 (동적) ──
        wp_header = ctk.CTkFrame(main_frame, fg_color=Theme.BG_SURFACE)
        wp_header.pack(fill="x", pady=(5, 0))
        ctk.CTkLabel(wp_header, text="📍 웨이포인트 리스트", text_color="#AB47BC", font=Theme.font(size=12, weight="bold")).pack(side="left", padx=10, pady=5)
        self.wp_count_label = ctk.CTkLabel(wp_header, text="(0개)", text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11))
        self.wp_count_label.pack(side="left")
        
        # 스크롤 가능한 웨이포인트 컨테이너
        self.wp_scroll = ctk.CTkScrollableFrame(main_frame, fg_color=Theme.BG_BASE, height=120)
        self.wp_scroll.pack(fill="x", pady=(0, 5))
        
        # 선택된 WP 상세 정보
        self.wp_detail_frame = ctk.CTkFrame(main_frame, fg_color=Theme.BG_SURFACE)
        self.wp_detail_frame.pack(fill="x", pady=5)
        self.wp_detail_label = ctk.CTkLabel(self.wp_detail_frame, text="웨이포인트를 선택하세요", 
                                             text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=10), 
                                             justify="left", wraplength=320)
        self.wp_detail_label.pack(anchor="w", padx=10, pady=5)
        
        # ── 버튼 (Teach / Load / Move) ──
        tf = ctk.CTkFrame(main_frame, fg_color="transparent")
        tf.pack(fill="x", pady=5)
        self.teach_btn = ctk.CTkButton(tf, text="📌 위치 저장", fg_color=Theme.INFO, hover_color="#1565C0", font=Theme.font(size=12, weight="bold"), width=100)
        self.teach_btn.pack(side="left", padx=(10, 5))
        self.load_btn = ctk.CTkButton(tf, text="📥 조그 불러오기", fg_color="#F57C00", hover_color=Theme.WARNING, font=Theme.font(size=12, weight="bold"), width=110)
        self.load_btn.pack(side="left", padx=5)
        self.move_btn = ctk.CTkButton(tf, text="▶ 로봇 이동", fg_color=Theme.SUCCESS, hover_color="#1B5E20", font=Theme.font(size=12, weight="bold"), width=100)
        self.move_btn.pack(side="left", padx=5)
        
    def update_ui(self, node_name, b_radius=0.0, vel=5, acc=5):
        if self.header_label:
            name_only = node_name.replace("Node", "").strip()
            self.header_label.configure(text=f"사용자 {name_only} 설정")
        if hasattr(self, 'blend_entry'):
            self.blend_entry.delete(0, "end")
            self.blend_entry.insert(0, str(b_radius))
        if hasattr(self, 'vel_slider'):
            vel_v = max(1, min(9, int(vel)))
            acc_v = max(1, min(9, int(acc)))
            self.vel_slider.set(vel_v)
            self.vel_label.configure(text=f"Lv.{vel_v}")
            self.acc_slider.set(acc_v)
            self.acc_label.configure(text=f"Lv.{acc_v}")
            
    def update_waypoint_info(self, waypoints, move_type=102):
        """웨이포인트 리스트를 동적으로 구성"""
        self._waypoints = waypoints or []
        self._selected_wp_idx = 0
        mtype = "JointMove" if move_type == 102 else "FrameMove"
        
        if hasattr(self, 'wp_count_label'):
            self.wp_count_label.configure(text=f"({len(self._waypoints)}개) — {mtype}")
        
        # 기존 WP 위젯 삭제
        if hasattr(self, 'wp_scroll'):
            for w in self.wp_scroll.winfo_children():
                w.destroy()
        
        if not self._waypoints:
            ctk.CTkLabel(self.wp_scroll, text="좌표 미설정", text_color=Theme.TEXT_SECONDARY).pack(pady=5)
            return
            
        # 각 웨이포인트를 카드로 표시
        for i, wp_data in enumerate(self._waypoints):
            wp_obj = wp_data.get("wp", None)
            q = wp_obj.j_pos if wp_obj and hasattr(wp_obj, 'j_pos') else wp_data.get("q", [])
            p = wp_obj.t_pos if wp_obj and hasattr(wp_obj, 't_pos') else wp_data.get("p", [])
            
            # 좌표 요약
            if p and len(p) >= 3:
                coord = f"X={p[0]*1000:.1f}  Y={p[1]*1000:.1f}  Z={p[2]*1000:.1f}"
            elif q and len(q) >= 6:
                coord = f"J1={q[0]:.1f}  J2={q[1]:.1f}  J3={q[2]:.1f}  ..."
            else:
                coord = "좌표 없음"
            
            bg = "#2E2E3E" if i == self._selected_wp_idx else Theme.BG_SURFACE
            card = ctk.CTkFrame(self.wp_scroll, fg_color=bg, corner_radius=4, height=30)
            card.pack(fill="x", pady=1, padx=2)
            
            idx_label = ctk.CTkLabel(card, text=f"WP{i+1}", font=Theme.font(size=11, weight="bold"), 
                                      text_color="#AB47BC", width=35)
            idx_label.pack(side="left", padx=5)
            
            coord_label = ctk.CTkLabel(card, text=coord, font=Theme.font(size=10), 
                                        text_color=Theme.TEXT_PRIMARY)
            coord_label.pack(side="left", padx=5, fill="x", expand=True)
            
            # 클릭으로 선택
            def _on_select(event, idx=i):
                self._select_waypoint(idx)
            card.bind("<Button-1>", _on_select)
            idx_label.bind("<Button-1>", _on_select)
            coord_label.bind("<Button-1>", _on_select)
        
        # 첫 번째 WP 자동 선택
        if self._waypoints:
            self._select_waypoint(0)
    
    def _select_waypoint(self, idx):
        """웨이포인트 선택 시 상세 정보 표시"""
        self._selected_wp_idx = idx
        if idx >= len(self._waypoints):
            return
        
        wp_data = self._waypoints[idx]
        wp_obj = wp_data.get("wp", None)
        q = wp_obj.j_pos if wp_obj and hasattr(wp_obj, 'j_pos') else wp_data.get("q", [])
        p = wp_obj.t_pos if wp_obj and hasattr(wp_obj, 't_pos') else wp_data.get("p", [])
        
        lines = [f"▶ WP{idx+1} 상세 좌표:"]
        if q and len(q) >= 6:
            lines.append(f"  Joint: J1={q[0]:.2f} J2={q[1]:.2f} J3={q[2]:.2f} J4={q[3]:.2f} J5={q[4]:.2f} J6={q[5]:.2f}")
        if p and len(p) >= 6:
            lines.append(f"  Task:  X={p[0]*1000:.1f} Y={p[1]*1000:.1f} Z={p[2]*1000:.1f} Rx={p[3]:.1f} Ry={p[4]:.1f} Rz={p[5]:.1f}")
        
        if hasattr(self, 'wp_detail_label'):
            self.wp_detail_label.configure(text="\n".join(lines), text_color=Theme.TEXT_PRIMARY)
        
        # 카드 하이라이트 갱신
        if hasattr(self, 'wp_scroll'):
            for i, card in enumerate(self.wp_scroll.winfo_children()):
                if hasattr(card, 'configure'):
                    card.configure(fg_color="#2E2E3E" if i == idx else Theme.BG_SURFACE)
                
    def apply_changes(self, node_data):
        if "boundary" not in node_data: node_data["boundary"] = {}
        try:
            node_data["boundary"]["velLevel"] = int(self.vel_slider.get())
            node_data["boundary"]["accLevel"] = int(self.acc_slider.get())
            node_data["b_radius"] = float(self.blend_entry.get())
        except Exception: pass

class MoveByEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.header_label = None
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="상대 위치(Move By) 설정", font=Theme.font(size=16, weight="bold"))
        self.header_label.pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(main_frame, text="현재 로봇 위치를 기준으로 지정된 거리만큼 이동합니다.").pack(anchor="w", pady=(0, 10))
        
        g = ctk.CTkFrame(main_frame, fg_color=Theme.BG_SURFACE)
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
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="힘 제어(Force) 설정", font=Theme.font(size=16, weight="bold"), text_color=Theme.WARNING)
        self.header_label.pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(main_frame, text="임피던스(Impedance) 및 컴플라이언스 파라미터").pack(anchor="w", pady=(0, 10))
        
        g = ctk.CTkFrame(main_frame, fg_color=Theme.BG_SURFACE)
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
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="홈 이동(Move Home) 설정", font=Theme.font(size=16, weight="bold"), text_color=Theme.INFO).pack(pady=10)
        ctk.CTkLabel(self.parent, text="로봇이 미리 지정된 홈(Home) 위치로 이동합니다.").pack(pady=20)
    def update_ui(self, node_name): pass

class MoveCEditor(MoveEditor):
    def render(self):
        super().render()
        if self.header_label: self.header_label.configure(text="원호 이동(Move C) 설정")
        # For Move C, we need Waypoint 1 (via) and Waypoint 2 (target)
        tf = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE)
        tf.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(tf, text="경유점 (Via Point) 티칭", text_color="#E91E63").pack(anchor="w", padx=10, pady=5)
        self.via_teach_btn = ctk.CTkButton(tf, text="📍 현재 위치를 경유점으로 저장", fg_color="#9C27B0")
        self.via_teach_btn.pack(side="left", padx=10, pady=5)
        self.via_label = ctk.CTkLabel(tf, text="저장된 좌표 없음")
        self.via_label.pack(side="left", padx=10)