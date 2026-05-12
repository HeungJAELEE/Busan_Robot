import customtkinter as ctk
from .base_editor import BaseNodeEditor


class PickPlaceEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.header_label = None
        self.style_seg_var = ctk.StringVar(value="단일 위치 사용")
        self.step3_frame = None
        self.pallet_name_label = None
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color="#2A2D35", height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="사용자 설정", font=ctk.CTkFont(size=16, weight="bold"))
        self.header_label.pack(pady=10)
        style_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        style_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(style_frame, text="1단계. 스타일 설정").pack(anchor="w")
        self.style_seg_btn = ctk.CTkSegmentedButton(style_frame, values=["단일 위치 사용", "팔레타이징 사용", "비전 사용"], variable=self.style_seg_var, command=self._on_style_changed)
        self.style_seg_btn.pack(fill="x", pady=5)
        
        # Update Button under Step 1
        uf = ctk.CTkFrame(style_frame, fg_color="transparent")
        uf.pack(fill="x", pady=5)
        self.teach_btn = ctk.CTkButton(uf, text="[위치 업데이트]", fg_color="#1976D2", hover_color="#1565C0", font=ctk.CTkFont(weight="bold"), width=100)
        self.teach_btn.pack(side="left")
        self.load_btn = ctk.CTkButton(uf, text="[조그로 불러오기]", fg_color="#F57C00", hover_color="#E65100", font=ctk.CTkFont(weight="bold"), width=120)
        self.load_btn.pack(side="left", padx=5)
        self.move_btn = ctk.CTkButton(uf, text="[로봇 이동]", fg_color="#2E7D32", hover_color="#1B5E20", font=ctk.CTkFont(weight="bold"), width=100)
        self.move_btn.pack(side="left", padx=5)
        
        self.pos_info_label = ctk.CTkLabel(uf, text="저장된 좌표 없음", text_color="#B0BEC5")
        self.pos_info_label.pack(side="left", padx=10)
        
        # 3동작 세트 이동 패널 (Approach -> Target -> Retract)
        self.move_panel = ctk.CTkFrame(style_frame, fg_color="transparent")
        self.move_panel.pack(fill="x", pady=5)
        
        ctk.CTkButton(self.move_panel, text="1. 투입위치(App)", width=100, height=28, fg_color="#F57C00", command=lambda: self._execute_move_step("approach")).pack(side="left", padx=5)
        ctk.CTkButton(self.move_panel, text="2. 정위치(Target)", width=100, height=28, fg_color="#2E7D32", command=lambda: self._execute_move_step("target")).pack(side="left", padx=5)
        ctk.CTkButton(self.move_panel, text="3. 배출위치(Ret)", width=100, height=28, fg_color="#D32F2F", command=lambda: self._execute_move_step("retract")).pack(side="left", padx=5)
        self.auto_move_btn = ctk.CTkButton(self.move_panel, text="[3동작 자동 실행]", width=120, height=28, font=ctk.CTkFont(weight="bold"), fg_color="#1976D2", command=lambda: self._execute_move_step("sequence"))
        self.auto_move_btn.pack(side="left", padx=15)
        
        # Tool 선택 (Gripper / Suction)
        tool_frame = ctk.CTkFrame(style_frame, fg_color="transparent")
        tool_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(tool_frame, text="툴 동작:").pack(side="left", padx=(0, 10))
        self.tool_type_var = ctk.StringVar(value="Gripper")
        self.tool_seg = ctk.CTkSegmentedButton(tool_frame, values=["Gripper", "Suction (흡착)"], variable=self.tool_type_var, width=220)
        self.tool_seg.pack(side="left")
        # Hidden tool_id_cb for compatibility with save/load
        self.tool_id_cb = ctk.CTkComboBox(tool_frame, values=["0", "1", "2", "3", "4"], width=50)
        self.tool_id_cb.set("1")
        # Not packed (hidden) - we use tool_seg instead

        
        # 2단계 접근 후퇴 작업 설정
        step2 = ctk.CTkFrame(self.parent, fg_color="transparent")
        step2.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(step2, text="2단계. 접근/후퇴 작업 설정", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        
        g = ctk.CTkFrame(step2, fg_color="#2A2D35")
        g.pack(fill="x", pady=5)
        
        # 접근(Approach) vs 후퇴(Retract) Columns
        ctk.CTkLabel(g, text="접근").grid(row=0, column=1, padx=20, pady=5)
        ctk.CTkLabel(g, text="후퇴").grid(row=0, column=2, padx=20, pady=5)
        
        # 1. 이동 방향
        ctk.CTkLabel(g, text="이동 방향").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.app_dir_cb = ctk.CTkComboBox(g, values=["Z", "-Z", "X", "-X", "Y", "-Y"], width=100)
        self.app_dir_cb.grid(row=1, column=1, pady=5, padx=10)
        self.ret_dir_cb = ctk.CTkComboBox(g, values=["-Z", "Z", "X", "-X", "Y", "-Y"], width=100)
        self.ret_dir_cb.grid(row=1, column=2, pady=5, padx=10)
        
        # 2. 거리 (mm)
        ctk.CTkLabel(g, text="거리 (mm)").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.app_dist = ctk.CTkEntry(g, width=100, justify="center")
        self.app_dist.insert(0, "0.00")
        self.app_dist.grid(row=2, column=1, pady=5, padx=10)
        self.ret_dist = ctk.CTkEntry(g, width=100, justify="center")
        self.ret_dist.insert(0, "0.00")
        self.ret_dist.grid(row=2, column=2, pady=5, padx=10)
        
        # 3. 속도 레벨
        ctk.CTkLabel(g, text="접근 속도").grid(row=3, column=0, padx=10, pady=15, sticky="w")
        self.app_spd = ctk.CTkSlider(g, from_=1, to=9, number_of_steps=8, width=100)
        self.app_spd.grid(row=3, column=1, pady=15, padx=10)
        self.ret_spd = ctk.CTkSlider(g, from_=1, to=9, number_of_steps=8, width=100)
        self.ret_spd.grid(row=3, column=2, pady=15, padx=10)
        
        # Add target speed
        ctk.CTkLabel(g, text="타겟 이동 속도").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.target_spd = ctk.CTkSlider(g, from_=1, to=9, number_of_steps=8, width=100)
        self.target_spd.grid(row=4, column=1, pady=5, padx=10)
        
        # 4. waitfor
        ctk.CTkLabel(g, text="waitfor").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.app_wf_cb = ctk.CTkComboBox(g, values=["사용 안함", "사용"], width=100)
        self.app_wf_cb.grid(row=5, column=1, pady=5, padx=10)
        self.ret_wf_cb = ctk.CTkComboBox(g, values=["사용 안함", "사용"], width=100)
        self.ret_wf_cb.grid(row=5, column=2, pady=5, padx=10)
        
        # 5. waitfor 주기 (초)
        ctk.CTkLabel(g, text="waitfor 주기 (초)").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.app_wait_period = ctk.CTkEntry(g, width=100, justify="center")
        self.app_wait_period.insert(0, "0")
        self.app_wait_period.grid(row=6, column=1, pady=5, padx=10)
        self.ret_wait_period = ctk.CTkEntry(g, width=100, justify="center")
        self.ret_wait_period.insert(0, "0")
        self.ret_wait_period.grid(row=6, column=2, pady=5, padx=10)
        
        # 6. 대기 시간
        ctk.CTkLabel(g, text="대기 시간 (초)").grid(row=7, column=0, padx=10, pady=5, sticky="w")
        self.app_wait_time = ctk.CTkEntry(g, width=100, justify="center")
        self.app_wait_time.insert(0, "0")
        self.app_wait_time.grid(row=7, column=1, pady=5, padx=10)
        self.ret_wait_time = ctk.CTkEntry(g, width=100, justify="center")
        self.ret_wait_time.insert(0, "0")
        self.ret_wait_time.grid(row=7, column=2, pady=5, padx=10)
        
        # (Teach Button was moved to Step 1 above)
        
        # 3단계 팔레타이징 상세 설정
        self.step3_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        ctk.CTkLabel(self.step3_frame, text="3단계. 팔레트 패턴 상세 설정", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 0))
        
        self.pallet_detail_frame = ctk.CTkFrame(self.step3_frame, fg_color="#2A2D35")
        self.pallet_detail_frame.pack(fill="x", pady=5)
        
        top_row = ctk.CTkFrame(self.pallet_detail_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(top_row, text="팔레트:").pack(side="left", padx=(0, 10))
        self.pallet_sel = ctk.CTkOptionMenu(top_row, values=["선택 안 됨"], width=120, command=self.on_pallet_changed)
        self.pallet_sel.pack(side="left", padx=(0, 20))
        
        # ──────────── 통합 팔레트 UI (그림 + 스펙 + 좌표) ────────────
        
        # 1. 상단 프레임: 그림 (좌) / M,N 배열 (우)
        top_split = ctk.CTkFrame(self.pallet_detail_frame, fg_color="transparent")
        top_split.pack(fill="x", padx=10, pady=5)
        
        # 좌측: 시각적 팔레트 캔버스
        canvas_frame = ctk.CTkFrame(top_split, fg_color="#1E2128", corner_radius=8)
        canvas_frame.pack(side="left", padx=5)
        ctk.CTkLabel(canvas_frame, text="선택한 팔레타이징 타입 : 0", font=ctk.CTkFont(size=11), text_color="#A0A0A0").pack(pady=(5, 0))
        self.preview_canvas = ctk.CTkCanvas(canvas_frame, width=160, height=120, bg="#1E2128", highlightthickness=0)
        self.preview_canvas.pack(padx=10, pady=5)
        self._draw_pallet_preview()
        
        # 우측: M, N 배열 및 자동계산
        mn_frame = ctk.CTkFrame(top_split, fg_color="#1E2128", corner_radius=8)
        mn_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        row_m = ctk.CTkFrame(mn_frame, fg_color="transparent")
        row_m.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(row_m, text="M (행)", font=ctk.CTkFont(weight="bold", size=14)).pack(side="left", padx=10)
        self.m_entry = ctk.CTkEntry(row_m, width=60, justify="center", font=ctk.CTkFont(size=14))
        self.m_entry.pack(side="right", padx=10)
        self.m_entry.insert(0, "2")
        
        row_n = ctk.CTkFrame(mn_frame, fg_color="transparent")
        row_n.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(row_n, text="N (열)", font=ctk.CTkFont(weight="bold", size=14)).pack(side="left", padx=10)
        self.n_entry = ctk.CTkEntry(row_n, width=60, justify="center", font=ctk.CTkFont(size=14))
        self.n_entry.pack(side="right", padx=10)
        self.n_entry.insert(0, "2")
        
        # 2. 중단 프레임: 제품 크기 및 간격 (자동 계산용)
        spec_frame = ctk.CTkFrame(self.pallet_detail_frame, fg_color="#1E2128", corner_radius=8)
        spec_frame.pack(fill="x", padx=15, pady=5)
        
        spec_row1 = ctk.CTkFrame(spec_frame, fg_color="transparent")
        spec_row1.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(spec_row1, text="📦 크기(Ix,Iy,Iz):", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=5)
        self.prod_entries = {}
        for key in ["Ix", "Iy", "Iz"]:
            e = ctk.CTkEntry(spec_row1, width=45, justify="center")
            e.insert(0, "100")
            e.pack(side="left", padx=2)
            self.prod_entries[key] = e
            
        ctk.CTkLabel(spec_row1, text=" ↔ 간격(Gx,Gy):", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(10,5))
        self.gap_entries = {}
        for key in ["Gx", "Gy"]:
            e = ctk.CTkEntry(spec_row1, width=45, justify="center")
            e.insert(0, "10")
            e.pack(side="left", padx=2)
            self.gap_entries[key] = e
            
        ctk.CTkLabel(spec_row1, text=" L:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(10,2))
        self.layer_entry = ctk.CTkEntry(spec_row1, width=35, justify="center")
        self.layer_entry.insert(0, "1")
        self.layer_entry.pack(side="left", padx=2)
        
        ctk.CTkButton(spec_row1, text="⚡ 자동 계산", width=90, height=26, fg_color="#1565C0", hover_color="#0D47A1", command=self._auto_calc_p2p3).pack(side="right", padx=5)

        # 3. 하단 프레임: P1, P2, P3 표 형태 레이아웃
        self.p_entries = {}
        axes = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
        
        coord_frame = ctk.CTkFrame(self.pallet_detail_frame, fg_color="#1E2128", corner_radius=8)
        coord_frame.pack(fill="x", padx=15, pady=5)
        
        header_row = ctk.CTkFrame(coord_frame, fg_color="transparent")
        header_row.pack(fill="x", padx=2, pady=(5, 0))
        ctk.CTkLabel(header_row, text="", width=110).pack(side="left")
        for ax in axes:
            ctk.CTkLabel(header_row, text=ax, width=50, anchor="center").pack(side="left", padx=2)
            
        for p_name in ["P1", "P2", "P3", "P4"]:
            row = ctk.CTkFrame(coord_frame, fg_color="transparent")
            row.pack(fill="x", padx=2, pady=3)
            
            btn_frame = ctk.CTkFrame(row, fg_color="transparent", width=110)
            btn_frame.pack(side="left")
            btn_frame.pack_propagate(False)
            
            ctk.CTkButton(btn_frame, text="Get", width=34, height=24, fg_color="#FF4B4B", hover_color="#FF6B6B", command=lambda p=p_name: self._get_current_pos_to_p(p)).pack(side="left", padx=1)
            ctk.CTkButton(btn_frame, text="Move", width=38, height=24, fg_color="#4B4BFF", hover_color="#6B6BFF", command=lambda p=p_name: self._execute_pallet_move(p)).pack(side="left", padx=1)
            ctk.CTkLabel(btn_frame, text=p_name, width=26, font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFB74D" if p_name == "P1" else "white").pack(side="left", padx=2)
            
            # Map P1 -> P1 (시작점) to maintain compatibility with existing methods
            p_key = f"{p_name} ({'시작점' if p_name=='P1' else '행 끝점' if p_name=='P2' else '열 끝점' if p_name=='P3' else '층 끝점'})"
            self.p_entries[p_key] = {}
            for ax in axes:
                entry = ctk.CTkEntry(row, width=50, justify="right", font=ctk.CTkFont(size=11))
                entry.pack(side="left", padx=2)
                entry.insert(0, "0.000")
                self.p_entries[p_key][ax] = entry

    def _draw_pallet_preview(self):
        """Draws the matrix Z-pattern pallet graphic on the canvas."""
        c = self.preview_canvas
        c.delete("all")
        w, h = 160, 120
        # Background rect
        c.create_rectangle(10, 10, w-10, h-10, fill="#3A3D4A", outline="#505565", width=2)
        
        # Grid points
        pts = [
            (30, 30), (80, 30), (130, 30),
            (30, 60), (80, 60), (130, 60),
            (30, 90), (80, 90), (130, 90)
        ]
        
        # Z-pattern lines
        lines = [
            (pts[0], pts[1]), (pts[1], pts[2]),
            (pts[2], pts[3]), (pts[3], pts[4]), (pts[4], pts[5]),
            (pts[5], pts[6]), (pts[6], pts[7]), (pts[7], pts[8])
        ]
        
        for p1, p2 in lines:
            c.create_line(p1[0], p1[1], p2[0], p2[1], fill="#1E88E5", width=3)
            
        for i, (cx, cy) in enumerate(pts):
            c.create_oval(cx-8, cy-8, cx+8, cy+8, fill="#0D47A1", outline="#1976D2")
            if i == 0:
                c.create_text(cx, cy, text="P1", fill="white", font=("Arial", 8, "bold"))
            elif i == 6:
                c.create_text(cx, cy, text="P2", fill="white", font=("Arial", 8, "bold"))
            elif i == 2:
                c.create_text(cx, cy, text="P3", fill="white", font=("Arial", 8, "bold"))

    def _on_style_changed(self, choice):
        """Called when user clicks 단일 위치 / 팔레타이징 / 비전 segmented button."""
        if choice == "팔레타이징 사용":
            if self.step3_frame:
                self.step3_frame.pack(fill="x", padx=10, pady=10)
        else:
            if self.step3_frame:
                self.step3_frame.pack_forget()

    def on_pallet_changed(self, choice):
        """Called when user selects a different pallet from the dropdown."""
        pass

    def _get_current_pos_to_p(self, p_name):
        """Read current target_p (task position) into the specified P entry."""
        p_data = getattr(self, 'target_p', None)
        if not p_data or len(p_data) < 6:
            print(">> [경고] 현재 저장된 좌표가 없습니다. 먼저 위치 업데이트를 해주세요.")
            return
        
        p_key = f"{p_name} ({'시작점' if p_name=='P1' else '행 끝점' if p_name=='P2' else '열 끝점' if p_name=='P3' else '층 끝점'})"
        axes = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
        for i, ax in enumerate(axes):
            self.p_entries[p_key][ax].delete(0, "end")
            self.p_entries[p_key][ax].insert(0, f"{p_data[i]:.4f}")
        print(f">> [{p_name} 설정] 현재 좌표를 {p_name}으로 설정: X={p_data[0]:.3f} Y={p_data[1]:.3f} Z={p_data[2]:.3f}")
    
    def _auto_calc_p2p3(self):
        """
        P1 원점 + 제품 크기(Ix,Iy,Iz) + 간격(Gx,Gy) + 배열(M,N)으로
        P1의 방향(각도)을 반영한 정확한 P2(행 끝점), P3(열 끝점) 글로벌 좌표 자동 계산
        """
        axes = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
        try:
            p1_key = "P1 (시작점)"
            p1 = [float(self.p_entries[p1_key][ax].get()) for ax in axes]
            
            ix = float(self.prod_entries["Ix"].get()) / 1000.0
            iy = float(self.prod_entries["Iy"].get()) / 1000.0
            iz = float(self.prod_entries["Iz"].get()) / 1000.0
            
            gx = float(self.gap_entries["Gx"].get()) / 1000.0
            gy = float(self.gap_entries["Gy"].get()) / 1000.0
            
            m = int(self.m_entry.get()) if self.m_entry.get() else 2
            n = int(self.n_entry.get()) if self.n_entry.get() else 2
            l_val = int(self.layer_entry.get()) if self.layer_entry.get() else 1
            if m < 1: m = 1
            if n < 1: n = 1
            if l_val < 1: l_val = 1
            
            dx_total = (ix + gx) * (m - 1)
            dy_total = (iy + gy) * (n - 1)
            dz_total = iz * (l_val - 1)  # Z층 높이는 Z방향 적재 간격
            
            # 수평 기준 단순 병진 이동 (회전 무시)
            p2 = [p1[0] + dx_total, p1[1], p1[2], p1[3], p1[4], p1[5]]
            p3 = [p1[0], p1[1] + dy_total, p1[2], p1[3], p1[4], p1[5]]
            p4 = [p1[0], p1[1], p1[2] + dz_total, p1[3], p1[4], p1[5]]
            
            p2_key = "P2 (행 끝점)"
            p3_key = "P3 (열 끝점)"
            p4_key = "P4 (층 끝점)"
            
            for j, ax in enumerate(axes):
                self.p_entries[p2_key][ax].delete(0, "end")
                self.p_entries[p2_key][ax].insert(0, f"{p2[j]:.4f}")
                self.p_entries[p3_key][ax].delete(0, "end")
                self.p_entries[p3_key][ax].insert(0, f"{p3[j]:.4f}")
                self.p_entries[p4_key][ax].delete(0, "end")
                self.p_entries[p4_key][ax].insert(0, f"{p4[j]:.4f}")
            
            self.m_entry.delete(0, "end")
            self.m_entry.insert(0, str(m))
            self.n_entry.delete(0, "end")
            self.n_entry.insert(0, str(n))
            self.layer_entry.delete(0, "end")
            self.layer_entry.insert(0, str(l_val))
            
            print(f">> [자동계산] 수평 기준 3D 다단 적재(P2, P3, P4) 생성 완료")
        except Exception as e:
            print(f">> [오류] 자동 계산 중 에러: {e}")
    def _execute_pallet_move(self, p_name):
        """Move robot to one of the pallet reference points (P1/P2/P3)."""
        from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
        axes = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
        try:
            pos = [float(self.p_entries[p_name][ax].get()) for ax in axes]
            print(f">> [이동] 팔레트 기준점 '{p_name}' 좌표로 이동: {pos}")
            RobotControlUseCase.move_to_task(pos)
        except Exception as e:
            print(f">> [에러] 팔레트 이동 실패: {e}")


    def update_ui(self, node_data, all_pallets=None):
        # Update Target Type
        ttype = node_data.get("target_type", 0)
        if ttype == 0: self.style_seg_var.set("단일 위치 사용")
        elif ttype == 1: self.style_seg_var.set("팔레타이징 사용")
        elif ttype == 2: self.style_seg_var.set("비전 사용")
        self._on_style_changed(self.style_seg_var.get())
        
        # Tool ID
        tid = node_data.get("toolId", 1)
        self.tool_type_var.set("Gripper" if tid in [1, 2] else "Suction (흡착)")
        
        # Approach
        app = node_data.get("approach", {})
        dir_map = {0: "Z", 1: "-Z", 2: "X", 3: "-X", 4: "Y", 5: "-Y"}
        self.app_dir_cb.set(dir_map.get(app.get("direction", 0), "Z"))
        self.app_dist.delete(0, "end"); self.app_dist.insert(0, str(app.get("distance", 0.0)))
        self.app_spd.set(app.get("boundary", {}).get("velLevel", 3))
        self.app_wait_time.delete(0, "end"); self.app_wait_time.insert(0, str(app.get("waitTime", 0.0)))
        wf = app.get("waitFor", {"type": 0, "time": 0})
        self.app_wf_cb.set("사용" if wf.get("type", 0) != 0 else "사용 안함")
        self.app_wait_period.delete(0, "end"); self.app_wait_period.insert(0, str(wf.get("time", 0.0)))
        
        # Retract
        ret = node_data.get("retract", {})
        self.ret_dir_cb.set(dir_map.get(ret.get("direction", 1), "-Z"))
        self.ret_dist.delete(0, "end"); self.ret_dist.insert(0, str(ret.get("distance", 0.0)))
        self.ret_spd.set(ret.get("boundary", {}).get("velLevel", 3))
        self.ret_wait_time.delete(0, "end"); self.ret_wait_time.insert(0, str(ret.get("waitTime", 0.0)))
        wf_r = ret.get("waitFor", {"type": 0, "time": 0})
        self.ret_wf_cb.set("사용" if wf_r.get("type", 0) != 0 else "사용 안함")
        self.ret_wait_period.delete(0, "end"); self.ret_wait_period.insert(0, str(wf_r.get("time", 0.0)))
        
        # Pallet data
        if ttype == 1:
            if all_pallets:
                pallet_names = [p.get("name", str(p.get("id", ""))) for p in all_pallets]
                if pallet_names:
                    self.pallet_sel.configure(values=pallet_names)
            
            if "target_pallet_name" in node_data:
                self.pallet_sel.set(str(node_data["target_pallet_name"]))
            
            p_data = node_data.get("p_data", {})
            if "size" in p_data:
                self.m_entry.delete(0, "end"); self.m_entry.insert(0, str(p_data["size"][0]))
                self.n_entry.delete(0, "end"); self.n_entry.insert(0, str(p_data["size"][1]))
                if len(p_data["size"]) >= 3:
                    self.layer_entry.delete(0, "end"); self.layer_entry.insert(0, str(p_data["size"][2]))
            
            if "points" in p_data and len(p_data["points"]) >= 3:
                axes = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
                pts = [p_data["points"][0], p_data["points"][1], p_data["points"][2]]
                keys = ["P1 (시작점)", "P2 (행 끝점)", "P3 (열 끝점)"]
                if len(p_data["points"]) >= 4:
                    pts.append(p_data["points"][3])
                    keys.append("P4 (층 끝점)")
                
                for i, p_info in enumerate(pts):
                    p_val = p_info.get("p", [0]*6)
                    for j, ax in enumerate(axes):
                        try:
                            self.p_entries[keys[i]][ax].delete(0, "end")
                            self.p_entries[keys[i]][ax].insert(0, f"{p_val[j]:.4f}")
                        except: pass

    def apply_changes(self, node_data):
        # Save Target Type
        tt = self.style_seg_var.get()
        if tt == "단일 위치 사용": node_data["target_type"] = 0
        elif tt == "팔레타이징 사용": node_data["target_type"] = 1
        else: node_data["target_type"] = 2
        
        # Tool ID
        tid = 1 if self.tool_type_var.get() == "Gripper" else 3
        node_data["toolId"] = tid
        
        # Direction map
        dir_map_rev = {"Z": 0, "-Z": 1, "X": 2, "-X": 3, "Y": 4, "-Y": 5}
        
        # Approach
        node_data["approach"] = {
            "direction": dir_map_rev.get(self.app_dir_cb.get(), 0),
            "distance": float(self.app_dist.get() or 0),
            "boundary": {"velLevel": int(self.app_spd.get()), "accLevel": int(self.app_spd.get())},
            "waitTime": float(self.app_wait_time.get() or 0),
            "waitFor": {"type": 1 if self.app_wf_cb.get() == "사용" else 0, "time": float(self.app_wait_period.get() or 0)}
        }
        
        # Retract
        node_data["retract"] = {
            "direction": dir_map_rev.get(self.ret_dir_cb.get(), 1),
            "distance": float(self.ret_dist.get() or 0),
            "boundary": {"velLevel": int(self.ret_spd.get()), "accLevel": int(self.ret_spd.get())},
            "waitTime": float(self.ret_wait_time.get() or 0),
            "waitFor": {"type": 1 if self.ret_wf_cb.get() == "사용" else 0, "time": float(self.ret_wait_period.get() or 0)}
        }
        
        # Pallet data
        if node_data["target_type"] == 1:
            p_name = self.pallet_sel.get()
            if p_name != "선택 안 됨":
                node_data["target_pallet_name"] = p_name
            
            axes = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
            try:
                p1 = [float(self.p_entries["P1 (시작점)"][ax].get()) for ax in axes]
                p2 = [float(self.p_entries["P2 (행 끝점)"][ax].get()) for ax in axes]
                p3 = [float(self.p_entries["P3 (열 끝점)"][ax].get()) for ax in axes]
                p4 = [0.0]*6
                if "P4 (층 끝점)" in self.p_entries and self.p_entries["P4 (층 끝점)"]["X"].get() != "":
                    try:
                        p4 = [float(self.p_entries["P4 (층 끝점)"][ax].get()) for ax in axes]
                    except Exception:
                        p4 = [0.0]*6
                
                # Default Q values, normally would be calculated by IK but we put 0s or keep existing
                q1 = [0]*6; q2 = [0]*6; q3 = [0]*6; q4 = [0]*6
                
                m = int(self.m_entry.get())
                n = int(self.n_entry.get())
                l_val = int(self.layer_entry.get()) if self.layer_entry.get() else 1
                
                node_data["p_data"] = {
                    "size": [m, n, l_val],
                    "points": [
                        {"p": p1, "q": q1},
                        {"p": p2, "q": q2},
                        {"p": p3, "q": q3}
                    ]
                }
                
                if l_val > 1 or any(p4):
                    node_data["p_data"]["points"].append({"p": p4, "q": q4})
            except Exception as e:
                print(f"Error applying pallet points: {e}")

class VisionEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color="#2A2D35", height=40)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="비전(Vision) 설정", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00BCD4").pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(main_frame, text="카메라 번호:").pack(anchor="w")
        self.cam_sel = ctk.CTkOptionMenu(main_frame, values=["Camera 1", "Camera 2"])
        self.cam_sel.pack(fill="x", pady=5)
        
        ctk.CTkLabel(main_frame, text="템플릿 매칭 ID:").pack(anchor="w", pady=(10,0))
        self.tpl_entry = ctk.CTkEntry(main_frame)
        self.tpl_entry.insert(0, "1")
        self.tpl_entry.pack(fill="x", pady=5)

    def update_ui(self, node_name): pass

class SyncEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color="#2A2D35", height=40)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="컨베이어 동기화(Sync) 설정", font=ctk.CTkFont(size=16, weight="bold"), text_color="#FFEB3B").pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(main_frame, text="컨베이어 벨트 ID:").pack(anchor="w")
        self.conv_entry = ctk.CTkEntry(main_frame)
        self.conv_entry.insert(0, "1")
        self.conv_entry.pack(fill="x", pady=5)
        
        self.sync_var = ctk.StringVar(value="시작")
        ctk.CTkSegmentedButton(main_frame, values=["시작", "종료"], variable=self.sync_var).pack(fill="x", pady=10)

    def update_ui(self, node_name): pass

class SetAOEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color="#2A2D35", height=40)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="아날로그 출력(Set AO) 설정", font=ctk.CTkFont(size=16, weight="bold"), text_color="#CDDC39").pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(main_frame, text="포트 번호 (AO):").pack(anchor="w")
        self.port_entry = ctk.CTkEntry(main_frame)
        self.port_entry.insert(0, "0")
        self.port_entry.pack(fill="x", pady=5)
        
        ctk.CTkLabel(main_frame, text="출력 전압 (V):").pack(anchor="w", pady=(10,0))
        self.volt_entry = ctk.CTkEntry(main_frame)
        self.volt_entry.insert(0, "5.0")
        self.volt_entry.pack(fill="x", pady=5)

    def update_ui(self, node_name): pass