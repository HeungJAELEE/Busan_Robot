import customtkinter as ctk
from .base_editor import BaseNodeEditor
from presentation.ui.theme import Theme


class PickPlaceEditor:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.header_label = None
        self.style_seg_var = ctk.StringVar(value="단일 위치 사용")
        self.step3_frame = None
        self.pallet_name_label = None
        
    def render(self):
        for w in self.parent.winfo_children(): w.destroy()
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        self.header_label = ctk.CTkLabel(header, text="사용자 설정", font=Theme.font(size=16, weight="bold"))
        self.header_label.pack(pady=10)
        style_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        style_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(style_frame, text="1단계. 스타일 설정").pack(anchor="w")
        self.style_seg_btn = ctk.CTkSegmentedButton(style_frame, values=["단일 위치 사용", "팔레타이징 사용", "비전 사용"], variable=self.style_seg_var, command=self._on_style_changed)
        self.style_seg_btn.pack(fill="x", pady=5)
        
        # Update Button under Step 1
        uf = ctk.CTkFrame(style_frame, fg_color="transparent")
        uf.pack(fill="x", pady=5)
        self.teach_btn = ctk.CTkButton(uf, text="[위치 업데이트]", fg_color=Theme.INFO, hover_color="#1565C0", font=Theme.font(size=12, weight="bold"), width=100)
        self.teach_btn.pack(side="left")
        self.load_btn = ctk.CTkButton(uf, text="[조그로 불러오기]", fg_color="#F57C00", hover_color=Theme.WARNING, font=Theme.font(size=12, weight="bold"), width=120)
        self.load_btn.pack(side="left", padx=5)
        self.move_btn = ctk.CTkButton(uf, text="[로봇 이동]", fg_color=Theme.SUCCESS, hover_color="#1B5E20", font=Theme.font(size=12, weight="bold"), width=100)
        self.move_btn.pack(side="left", padx=5)
        
        self.pos_info_label = ctk.CTkLabel(uf, text="저장된 좌표 없음", text_color="#B0BEC5")
        self.pos_info_label.pack(side="left", padx=10)
        
        # 3동작 세트 이동 패널 (Approach -> Target -> Retract)
        self.move_panel = ctk.CTkFrame(style_frame, fg_color="transparent")
        self.move_panel.pack(fill="x", pady=5)
        
        ctk.CTkButton(self.move_panel, text="1. 투입위치(App)", width=100, height=28, fg_color="#F57C00", command=lambda: self._execute_move_step("approach")).pack(side="left", padx=5)
        ctk.CTkButton(self.move_panel, text="2. 정위치(Target)", width=100, height=28, fg_color=Theme.SUCCESS, command=lambda: self._execute_move_step("target")).pack(side="left", padx=5)
        ctk.CTkButton(self.move_panel, text="3. 배출위치(Ret)", width=100, height=28, fg_color=Theme.DANGER, command=lambda: self._execute_move_step("retract")).pack(side="left", padx=5)
        self.auto_move_btn = ctk.CTkButton(self.move_panel, text="[3동작 자동 실행]", width=120, height=28, font=Theme.font(size=12, weight="bold"), fg_color=Theme.INFO, command=lambda: self._execute_move_step("sequence"))
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
        ctk.CTkLabel(step2, text="2단계. 접근/후퇴 작업 설정", font=Theme.font(size=12, weight="bold")).pack(anchor="w")
        
        g = ctk.CTkFrame(step2, fg_color=Theme.BG_SURFACE)
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
        
        # 3단계 팔레타이징 상세 설정
        self.step3_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        ctk.CTkLabel(self.step3_frame, text="3단계. 팔레트 패턴 상세 설정", font=Theme.font(size=12, weight="bold")).pack(anchor="w", pady=(10, 0))
        
        self.pallet_detail_frame = ctk.CTkFrame(self.step3_frame, fg_color=Theme.BG_SURFACE)
        self.pallet_detail_frame.pack(fill="x", pady=5)
        
        top_row = ctk.CTkFrame(self.pallet_detail_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=(8, 4))
        
        ctk.CTkLabel(top_row, text="팔레트:", font=Theme.font(size=11)).pack(side="left", padx=(0, 5))
        self.pallet_sel = ctk.CTkOptionMenu(top_row, values=["선택 안 됨"], width=110, command=self.on_pallet_changed)
        self.pallet_sel.pack(side="left", padx=(0, 10))
        
        # 마법사 연동 버튼
        ctk.CTkButton(top_row, text="🧱 마법사", width=80, height=28,
                       fg_color=Theme.ACCENT_PRIMARY, hover_color=Theme.ACCENT_HOVER,
                       font=Theme.font(size=11, weight="bold"),
                       command=self._open_pallet_wizard).pack(side="left", padx=5)
        
        # 패턴 정보 라벨
        self.pallet_pattern_lbl = ctk.CTkLabel(top_row, text="패턴: 일반(Z형)", font=Theme.font(size=10),
                                                text_color=Theme.WARNING)
        self.pallet_pattern_lbl.pack(side="right", padx=5)
        
        # ──────────── 통합 팔레트 UI (그림 + 스펙 + 좌표) ────────────
        
        # 상단 프레임: 미니 프리뷰 (좌) / 배열 정보 (우)
        top_split = ctk.CTkFrame(self.pallet_detail_frame, fg_color="transparent")
        top_split.pack(fill="x", padx=10, pady=4)
        
        canvas_frame = ctk.CTkFrame(top_split, fg_color=Theme.BG_BASE, corner_radius=8)
        canvas_frame.pack(side="left", padx=5)
        self.preview_type_lbl = ctk.CTkLabel(canvas_frame, text="패턴: 일반(Z형)", font=Theme.font(size=10), text_color="#A0A0A0")
        self.preview_type_lbl.pack(pady=(3, 0))
        self.preview_canvas = ctk.CTkCanvas(canvas_frame, width=160, height=110, bg=Theme.BG_BASE, highlightthickness=0)
        self.preview_canvas.pack(padx=8, pady=4)
        self._current_pattern = "normal"
        self._draw_pallet_preview()
        
        mn_frame = ctk.CTkFrame(top_split, fg_color=Theme.BG_BASE, corner_radius=8)
        mn_frame.pack(side="left", fill="both", expand=True, padx=5)
        ctk.CTkLabel(mn_frame, text="📐 팔레타이징 배열", font=Theme.font(size=13, weight="bold"), text_color="#FFB74D").pack(pady=(10, 3))
        self.pallet_summary_lbl = ctk.CTkLabel(mn_frame, text="M×N×L 설정 후\n⚡계산 또는 🧱마법사 사용", 
                                                font=Theme.font(size=11), text_color="#888")
        self.pallet_summary_lbl.pack(pady=(3, 10))
        
        # 2. 중단 프레임: 제품 크기 및 간격 (자동 계산용)
        spec_frame = ctk.CTkFrame(self.pallet_detail_frame, fg_color=Theme.BG_BASE, corner_radius=8)
        spec_frame.pack(fill="x", padx=15, pady=5)
        
        # Row 1: 제품 크기
        spec_row1 = ctk.CTkFrame(spec_frame, fg_color="transparent")
        spec_row1.pack(fill="x", padx=5, pady=(5, 2))
        ctk.CTkLabel(spec_row1, text="📦 크기(mm):", font=Theme.font(size=11, weight="bold")).pack(side="left", padx=3)
        self.prod_entries = {}
        for key in ["Ix", "Iy", "Iz"]:
            ctk.CTkLabel(spec_row1, text=key, font=Theme.font(size=10), text_color="#AAA").pack(side="left", padx=(3,0))
            e = ctk.CTkEntry(spec_row1, width=50, justify="center")
            e.insert(0, "100")
            e.pack(side="left", padx=2)
            self.prod_entries[key] = e
        
        # Row 2: 간격
        spec_row1b = ctk.CTkFrame(spec_frame, fg_color="transparent")
        spec_row1b.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(spec_row1b, text="↔ 간격(mm):", font=Theme.font(size=11, weight="bold")).pack(side="left", padx=3)
        self.gap_entries = {}
        for key in ["Gx", "Gy"]:
            ctk.CTkLabel(spec_row1b, text=key, font=Theme.font(size=10), text_color="#AAA").pack(side="left", padx=(3,0))
            e = ctk.CTkEntry(spec_row1b, width=50, justify="center")
            e.insert(0, "10")
            e.pack(side="left", padx=2)
            self.gap_entries[key] = e
        
        # Row 3: M, N, L 배열 + 자동 계산 버튼
        spec_row2 = ctk.CTkFrame(spec_frame, fg_color="transparent")
        spec_row2.pack(fill="x", padx=5, pady=(2, 5))
        
        ctk.CTkLabel(spec_row2, text="📐 배열:", font=Theme.font(size=11, weight="bold")).pack(side="left", padx=3)
        
        ctk.CTkLabel(spec_row2, text="M(행)", font=Theme.font(size=11, weight="bold"), text_color="#4FC3F7").pack(side="left", padx=(5,1))
        self.m_entry = ctk.CTkEntry(spec_row2, width=40, justify="center", font=Theme.font(size=12))
        self.m_entry.insert(0, "2")
        self.m_entry.pack(side="left", padx=2)
        
        ctk.CTkLabel(spec_row2, text="N(열)", font=Theme.font(size=11, weight="bold"), text_color="#81C784").pack(side="left", padx=(5,1))
        self.n_entry = ctk.CTkEntry(spec_row2, width=40, justify="center", font=Theme.font(size=12))
        self.n_entry.insert(0, "2")
        self.n_entry.pack(side="left", padx=2)
        
        ctk.CTkLabel(spec_row2, text="L(층)", font=Theme.font(size=11, weight="bold"), text_color="#FFB74D").pack(side="left", padx=(5,1))
        self.layer_entry = ctk.CTkEntry(spec_row2, width=40, justify="center", font=Theme.font(size=12))
        self.layer_entry.insert(0, "1")
        self.layer_entry.pack(side="left", padx=2)
        
        ctk.CTkButton(spec_row2, text="⚡계산", width=60, height=26, fg_color="#1565C0", hover_color="#0D47A1", font=Theme.font(size=11), command=self._auto_calc_p2p3).pack(side="right", padx=3)

        # 3. 하단 프레임: P1, P2, P3 표 형태 레이아웃 (컴팩트)
        self.p_entries = {}
        axes = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
        
        coord_frame = ctk.CTkFrame(self.pallet_detail_frame, fg_color=Theme.BG_BASE, corner_radius=8)
        coord_frame.pack(fill="x", padx=15, pady=(2, 5))
        
        header_row = ctk.CTkFrame(coord_frame, fg_color="transparent", height=20)
        header_row.pack(fill="x", padx=1, pady=(2, 0))
        header_row.pack_propagate(False)
        ctk.CTkLabel(header_row, text="", width=90).pack(side="left")
        for ax in axes:
            ctk.CTkLabel(header_row, text=ax, width=44, anchor="center", font=Theme.font(size=10)).pack(side="left", padx=1)
            
        for p_name in ["P1", "P2", "P3", "P4"]:
            row = ctk.CTkFrame(coord_frame, fg_color="transparent", height=28)
            row.pack(fill="x", padx=1, pady=1)
            row.pack_propagate(False)
            
            btn_frame = ctk.CTkFrame(row, fg_color="transparent", width=90)
            btn_frame.pack(side="left")
            btn_frame.pack_propagate(False)
            
            ctk.CTkButton(btn_frame, text="Get", width=28, height=20, fg_color="#FF4B4B", hover_color="#FF6B6B", font=Theme.font(size=10, weight="bold"), command=lambda p=p_name: self._get_current_pos_to_p(p)).pack(side="left", padx=1)
            ctk.CTkButton(btn_frame, text="Move", width=34, height=20, fg_color="#4B4BFF", hover_color="#6B6BFF", font=Theme.font(size=10, weight="bold"), command=lambda p=p_name: self._execute_pallet_move(p)).pack(side="left", padx=1)
            ctk.CTkLabel(btn_frame, text=p_name, width=20, font=Theme.font(size=10, weight="bold"), text_color="#FFB74D" if p_name == "P1" else Theme.TEXT_PRIMARY).pack(side="left", padx=1)
            
            p_key = f"{p_name} ({'시작점' if p_name=='P1' else '행 끝점' if p_name=='P2' else '열 끝점' if p_name=='P3' else '층 끝점'})"
            self.p_entries[p_key] = {}
            for ax in axes:
                entry = ctk.CTkEntry(row, width=44, height=22, justify="right", font=Theme.font(size=10))
                entry.pack(side="left", padx=1)
                entry.insert(0, "0.000")
                self.p_entries[p_key][ax] = entry

    def _draw_pallet_preview(self):
        """현재 패턴에 맞는 미니 프리뷰를 캔버스에 그린다."""
        c = self.preview_canvas
        c.delete("all")
        w, h = 160, 110
        
        # 3x3 그리드 점 배치
        rows, cols = 3, 3
        margin_x, margin_y = 20, 15
        cell_w = (w - 2 * margin_x) / (cols - 1)
        cell_h = (h - 2 * margin_y) / (rows - 1)
        
        pts = []
        for r in range(rows):
            for co in range(cols):
                pts.append((margin_x + co * cell_w, margin_y + r * cell_h))
        
        # 패턴에 따른 방문 순서
        pattern = getattr(self, '_current_pattern', 'normal')
        if pattern == "zigzag":
            order = []
            for r in range(rows):
                if r % 2 == 0: order.extend(range(r*cols, r*cols+cols))
                else: order.extend(range(r*cols+cols-1, r*cols-1, -1))
        elif pattern == "snake":
            order = []
            for co in range(cols):
                if co % 2 == 0: order.extend([r*cols+co for r in range(rows)])
                else: order.extend([r*cols+co for r in range(rows-1, -1, -1)])
        elif pattern == "spiral":
            order = [0, 1, 2, 5, 8, 7, 6, 3, 4]
        elif pattern == "center_out":
            order = [4, 1, 3, 5, 7, 0, 2, 6, 8]
        else:  # normal
            order = list(range(9))
        
        # 경로 그리기
        for i in range(len(order) - 1):
            p1, p2 = pts[order[i]], pts[order[i+1]]
            c.create_line(p1[0], p1[1], p2[0], p2[1], fill="#1E88E5", width=2, arrow="last", arrowshape=(6, 8, 3))
        
        # 점 그리기
        labels = {0: "P1", 2: "P3", 6: "P2"}
        for i, (cx, cy) in enumerate(pts):
            color = "#0D47A1"
            if i in labels: color = "#E65100" if labels[i] == "P1" else "#1B5E20" if labels[i] == "P2" else "#4A148C"
            c.create_oval(cx-7, cy-7, cx+7, cy+7, fill=color, outline="#42A5F5")
            if i in labels:
                c.create_text(cx, cy, text=labels[i], fill="white", font=("", 7, "bold"))
            else:
                c.create_text(cx, cy, text=str(order.index(i)+1), fill="white", font=("", 6))
    
    def _open_pallet_wizard(self):
        """팔레타이징 마법사를 열고 결과를 현재 에디터로 반환받는다."""
        from presentation.ui.robot_hmi.tools.palletizing_wizard import PalletizingWizardDialog
        
        # 현재 값을 마법사 초기값으로 전달
        try:
            init_data = {
                "cols": int(self.n_entry.get()) if self.n_entry.get() else 2,
                "rows": int(self.m_entry.get()) if self.m_entry.get() else 2,
                "layers": int(self.layer_entry.get()) if self.layer_entry.get() else 1,
                "box_w": float(self.prod_entries["Ix"].get()) if self.prod_entries["Ix"].get() else 100,
                "box_h": float(self.prod_entries["Iy"].get()) if self.prod_entries["Iy"].get() else 100,
                "gap": float(self.gap_entries["Gx"].get()) if self.gap_entries["Gx"].get() else 10,
                "pattern": getattr(self, '_current_pattern', 'normal')
            }
        except:
            init_data = None
        
        PalletizingWizardDialog(self.parent, callback=self._on_wizard_result, init_data=init_data)
    
    def _on_wizard_result(self, result):
        """마법사에서 '적용' 버튼을 눌렀을 때 호출되는 콜백."""
        # M(행), N(열), L(층) 업데이트
        self.m_entry.delete(0, "end"); self.m_entry.insert(0, str(result["rows"]))
        self.n_entry.delete(0, "end"); self.n_entry.insert(0, str(result["cols"]))
        self.layer_entry.delete(0, "end"); self.layer_entry.insert(0, str(result["layers"]))
        
        # 제품 크기 / 간격 업데이트
        self.prod_entries["Ix"].delete(0, "end"); self.prod_entries["Ix"].insert(0, str(int(result["box_w"])))
        self.prod_entries["Iy"].delete(0, "end"); self.prod_entries["Iy"].insert(0, str(int(result["box_h"])))
        self.gap_entries["Gx"].delete(0, "end"); self.gap_entries["Gx"].insert(0, str(int(result["gap"])))
        self.gap_entries["Gy"].delete(0, "end"); self.gap_entries["Gy"].insert(0, str(int(result["gap"])))
        
        # 패턴 업데이트
        self._current_pattern = result.get("pattern", "normal")
        pmap = {"normal": "일반(Z형)", "zigzag": "지그재그", "cross": "교차(90°)", 
                "snake": "S자형", "spiral": "외곽나선", "center_out": "중앙확산"}
        pattern_name = pmap.get(self._current_pattern, "일반(Z형)")
        self.preview_type_lbl.configure(text=f"패턴: {pattern_name}")
        self.pallet_pattern_lbl.configure(text=f"패턴: {pattern_name}")
        
        # 요약 라벨 업데이트
        total = result["rows"] * result["cols"] * result["layers"]
        self.pallet_summary_lbl.configure(text=f"총 {total}개\n{result['cols']}열×{result['rows']}행×{result['layers']}층\n패턴: {pattern_name}")
        
        # 프리뷰 캔버스 갱신
        self._draw_pallet_preview()
        
        # 자동으로 P2, P3 좌표 계산
        self._auto_calc_p2p3()
        
        print(f">> [마법사 연동] 설정 반영 완료: {result['cols']}×{result['rows']}×{result['layers']}층, 패턴={pattern_name}")

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
        """Read current real-time task position into the specified P entry."""
        from core.domains.robot.communication.client_manager import robot_manager
        
        active_name = robot_manager.get_active_robot_name()
        if not active_name:
            print(">> [경고] 로봇이 선택되지 않았습니다.")
            return
            
        state = robot_manager.get_robot_state(active_name)
        if not state or not state.get("t_pos"):
            print(">> [경고] 로봇 좌표를 읽어올 수 없습니다.")
            return
            
        p_data = state.get("t_pos")
        
        p_key = f"{p_name} ({'시작점' if p_name=='P1' else '행 끝점' if p_name=='P2' else '열 끝점' if p_name=='P3' else '층 끝점'})"
        axes = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
        for i, ax in enumerate(axes):
            self.p_entries[p_key][ax].delete(0, "end")
            self.p_entries[p_key][ax].insert(0, f"{p_data[i]:.4f}")
        print(f">> [{p_name} 설정] 현재 실시간 좌표를 {p_name}으로 설정: X={p_data[0]:.3f} Y={p_data[1]:.3f} Z={p_data[2]:.3f}")
    
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
        """Move robot to one of the pallet reference points (P1/P2/P3/P4)."""
        from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
        axes = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
        p_key = f"{p_name} ({'시작점' if p_name=='P1' else '행 끝점' if p_name=='P2' else '열 끝점' if p_name=='P3' else '층 끝점'})"
        try:
            pos = [float(self.p_entries[p_key][ax].get()) for ax in axes]
            print(f">> [이동] 팔레트 기준점 '{p_name}' 좌표로 이동: {pos}")
            RobotControlUseCase.move_to_task(pos)
        except Exception as e:
            print(f">> [에러] 팔레트 이동 실패: {e}")

    def _execute_move_step(self, step):
        """Move robot to Approach, Target, or Retract position based on current settings."""
        from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
        import time
            
        try:
            # 1. 정위치(Target) 좌표 구하기
            target_p = None
            ttype = self.style_seg_var.get()
            if ttype == "단일 위치 사용":
                if hasattr(self, 'node_data') and self.node_data:
                    # 단일 위치 사용일 경우 p_data가 없으므로 루트의 'p' 좌표를 사용
                    target_p = self.node_data.get("p", getattr(self, "target_p", None))
            elif ttype == "팔레타이징 사용":
                axes = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
                target_p = [float(self.p_entries["P1 (시작점)"][ax].get()) for ax in axes]
                
            if not target_p or len(target_p) < 6:
                print(">> [경고] 정위치(Target) 좌표가 설정되지 않았습니다.")
                return

            dir_map_rev = {"Z": 0, "-Z": 1, "X": 2, "-X": 3, "Y": 4, "-Y": 5}
            
            def get_offset_pos(base_p, direction_str, dist):
                pos = list(base_p)
                dir_idx = dir_map_rev.get(direction_str, 0)
                if dir_idx == 0: pos[2] += dist
                elif dir_idx == 1: pos[2] -= dist
                elif dir_idx == 2: pos[0] += dist
                elif dir_idx == 3: pos[0] -= dist
                elif dir_idx == 4: pos[1] += dist
                elif dir_idx == 5: pos[1] -= dist
                return pos

            # UI 입력은 mm 단위이므로, 미터(m) 단위로 변환
            app_dist = float(self.app_dist.get() or 0) / 1000.0
            ret_dist = float(self.ret_dist.get() or 0) / 1000.0
            
            app_p = get_offset_pos(target_p, self.app_dir_cb.get(), app_dist)
            ret_p = get_offset_pos(target_p, self.ret_dir_cb.get(), ret_dist)

            if step == "approach":
                print(f">> [이동] 투입위치(Approach)로 이동: {app_p}")
                RobotControlUseCase.move_to_task(app_p)
            elif step == "target":
                print(f">> [이동] 정위치(Target)로 이동: {target_p}")
                RobotControlUseCase.move_to_task(target_p)
            elif step == "retract":
                print(f">> [이동] 배출위치(Retract)로 이동: {ret_p}")
                RobotControlUseCase.move_to_task(ret_p)
            elif step == "sequence":
                # 백그라운드 스레드에서 MoveDoneCheck 포함 시퀀스 실행
                import threading
                from core.domains.robot.use_cases.motion_math import MotionMath
                
                # 팔레타이징 모드: P1~P4 + M×N×L 전체 그리드 순회
                is_pallet = (ttype == "팔레타이징 사용")
                
                if is_pallet:
                    axes = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
                    p1 = [float(self.p_entries["P1 (시작점)"][ax].get()) for ax in axes]
                    p2 = [float(self.p_entries["P2 (행 끝점)"][ax].get()) for ax in axes]
                    p3 = [float(self.p_entries["P3 (열 끝점)"][ax].get()) for ax in axes]
                    p4 = None
                    if "P4 (층 끝점)" in self.p_entries:
                        try:
                            p4 = [float(self.p_entries["P4 (층 끝점)"][ax].get()) for ax in axes]
                        except: p4 = None
                    
                    m = int(self.m_entry.get()) if self.m_entry.get() else 1
                    n = int(self.n_entry.get()) if self.n_entry.get() else 1
                    l_val = int(self.layer_entry.get()) if self.layer_entry.get() else 1
                    if m < 1: m = 1
                    if n < 1: n = 1
                    if l_val < 1: l_val = 1
                else:
                    p1 = p2 = p3 = p4 = None
                    m = n = l_val = 1
                
                def _run_sequence():
                    try:
                        inst = None
                        from core.domains.robot.communication.client_manager import robot_manager
                        inst = robot_manager.get_active_instance()
                        if not inst:
                            print(">> [에러] 로봇이 연결되지 않았습니다.")
                            return
                        
                        is_suction = "Suction" in self.tool_type_var.get()
                        g_pin = 1
                        r_pin = 2
                        
                        total = m * n * l_val
                        count = 0
                        
                        for layer in range(l_val):
                            for row in range(m):
                                for col in range(n):
                                    count += 1
                                    
                                    # 현재 그리드 포인트 좌표 계산
                                    if is_pallet:
                                        cur_target = MotionMath.compute_pallet_point(
                                            p1, p2, p3, m, n, row, col,
                                            p4=p4, size_l=l_val, current_l=layer
                                        )
                                    else:
                                        cur_target = list(target_p)
                                    
                                    cur_app = get_offset_pos(cur_target, self.app_dir_cb.get(), app_dist)
                                    cur_ret = get_offset_pos(cur_target, self.ret_dir_cb.get(), ret_dist)
                                    
                                    print(f"\n>> ═══════════════════════════════════════")
                                    print(f">> 📦 [{count}/{total}] Layer={layer+1}/{l_val}, Row={row+1}/{m}, Col={col+1}/{n}")
                                    print(f">>   Target : {[f'{v:.4f}' for v in cur_target]}")
                                    print(f">>   Approach: {[f'{v:.4f}' for v in cur_app]}")
                                    print(f">>   Retract : {[f'{v:.4f}' for v in cur_ret]}")
                                    print(f">> ═══════════════════════════════════════")
                                    
                                    # 툴 초기화
                                    RobotControlUseCase.set_do(g_pin, 0)
                                    if not is_suction:
                                        RobotControlUseCase.set_do(r_pin, 0)
                                    time.sleep(0.1)
                                    
                                    # 1. Approach
                                    print(f">> [{count}] 1/3 투입위치(Approach)로 이동...")
                                    inst.task_move_to(cur_app)
                                    RobotControlUseCase.wait_for_move_finish(30.0)
                                    
                                    # 2. Target
                                    print(f">> [{count}] 2/3 정위치(Target)로 이동...")
                                    inst.task_move_to(cur_target)
                                    RobotControlUseCase.wait_for_move_finish(30.0)
                                    
                                    # 3. Tool action (Pick/Place)
                                    is_place = False
                                    if hasattr(self, 'node_data') and self.node_data:
                                        is_place = self.node_data.get("type") == 202
                                        
                                    action_str = "Place (놓기)" if is_place else "Pick (집기)"
                                    print(f">> [{count}] 툴 동작: {action_str} - {'Suction' if is_suction else 'Gripper'}")
                                    
                                    if is_place:
                                        # Place (끄기 / 놓기)
                                        RobotControlUseCase.set_do(g_pin, 0)
                                        if not is_suction:
                                            time.sleep(0.1)
                                            RobotControlUseCase.set_do(r_pin, 1)
                                    else:
                                        # Pick (켜기 / 집기)
                                        if is_suction:
                                            RobotControlUseCase.set_do(g_pin, 1)
                                        else:
                                            RobotControlUseCase.set_do(r_pin, 0)
                                            time.sleep(0.1)
                                            RobotControlUseCase.set_do(g_pin, 1)
                                            
                                    time.sleep(0.5)
                                    
                                    # 4. Retract
                                    print(f">> [{count}] 3/3 배출위치(Retract)로 이동...")
                                    inst.task_move_to(cur_ret)
                                    RobotControlUseCase.wait_for_move_finish(30.0)
                                    
                                    print(f">> [{count}] ✅ 완료!")
                        
                        print(f"\n>> 🎉 팔레타이징 전체 시퀀스 완료! (총 {total}개 포인트)")
                    except Exception as e:
                        print(f">> [자동 실행 에러] {e}")
                threading.Thread(target=_run_sequence, daemon=True).start()
                
        except Exception as e:
            print(f">> [에러] 이동 스텝 실행 중 오류: {e}")
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
            
            if "prod_size" in p_data:
                for i, k in enumerate(["Ix", "Iy", "Iz"]):
                    if i < len(p_data["prod_size"]):
                        self.prod_entries[k].delete(0, "end")
                        self.prod_entries[k].insert(0, str(p_data["prod_size"][i]))
                        
            if "gap_size" in p_data:
                for i, k in enumerate(["Gx", "Gy"]):
                    if i < len(p_data["gap_size"]):
                        self.gap_entries[k].delete(0, "end")
                        self.gap_entries[k].insert(0, str(p_data["gap_size"][i]))
            
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
        
        # Tool ID — 기존 toolId 보존 (원본 JSON과 불일치 방지)
        if "toolId" not in node_data:
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
            
            # 🔥 적용 버튼 누를 때마다 무조건 자동 계산 먼저 실행!
            self._auto_calc_p2p3()
            
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
                
                try: ix = float(self.prod_entries["Ix"].get())
                except: ix = 100.0
                try: iy = float(self.prod_entries["Iy"].get())
                except: iy = 100.0
                try: iz = float(self.prod_entries["Iz"].get())
                except: iz = 100.0
                
                try: gx = float(self.gap_entries["Gx"].get())
                except: gx = 10.0
                try: gy = float(self.gap_entries["Gy"].get())
                except: gy = 10.0
                
                node_data["p_data"] = {
                    "size": [m, n, l_val],
                    "prod_size": [ix, iy, iz],
                    "gap_size": [gx, gy],
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
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="비전(Vision) 설정", font=Theme.font(size=16, weight="bold"), text_color=Theme.INFO).pack(pady=10)
        
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
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="컨베이어 동기화(Sync) 설정", font=Theme.font(size=16, weight="bold"), text_color="#FFEB3B").pack(pady=10)
        
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
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, height=40)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="아날로그 출력(Set AO) 설정", font=Theme.font(size=16, weight="bold"), text_color="#CDDC39").pack(pady=10)
        
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