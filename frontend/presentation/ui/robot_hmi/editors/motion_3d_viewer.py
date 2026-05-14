"""
3D Motion Step Viewer — 프로그램의 동작을 단계별로 3D 시각화
Pick/Place 팔레트 그리드, 접근/후퇴 경로, 이동 순서를 모두 표시합니다.
"""
import tkinter as tk
import customtkinter as ctk
import math


class Motion3DViewer:
    """Toplevel window that renders robot motion steps in 3D."""

    # ── 색상 팔레트 ──
    C_BG       = "#0f0f23"
    C_GRID     = "#1a1a3e"
    C_AXIS_X   = "#FF6B6B"
    C_AXIS_Y   = "#4ECDC4"
    C_AXIS_Z   = "#45B7D1"
    C_HOME     = "#FF6B6B"
    C_MOVE     = "#4ECDC4"
    C_PICK     = "#45B7D1"
    C_PLACE    = "#96CEB4"
    C_PATH     = "#FFD93D"
    C_APPROACH = "#FF9F43"
    C_TEXT     = "#e0e0e0"
    C_HIGHLIGHT= "#FFFFFF"
    C_FLOOR    = "#1a1a3e"

    def __init__(self, parent, node_data_dict, tree_widget):
        self.parent = parent
        self.node_data = node_data_dict
        self.tree = tree_widget

        self.steps = []       # [(label, xyz_mm, color, extras)]
        self.current_step = 0
        self.azimuth = -45.0
        self.elevation = 30.0
        self.scale = 1.0
        self.drag_start = None
        self.pan_x = 0
        self.pan_y = 0

        self._build_steps()
        if not self.steps:
            from tkinter import messagebox
            messagebox.showwarning("3D 시각화", "시각화할 동작이 없습니다.\n프로그램을 먼저 구성하세요.")
            return

        # 데이터 범위 기반 자동 뷰 최적화
        self._auto_view()
        self._create_window()

    def _auto_view(self):
        """데이터 분포에 따라 최적의 초기 뷰 각도를 설정합니다."""
        all_pts = [s[1] for s in self.steps]
        for _, _, gpts, _ in self.pallet_grids:
            all_pts.extend(gpts)
        if not all_pts:
            return
        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        zs = [p[2] for p in all_pts]
        dx = max(xs) - min(xs)
        dy = max(ys) - min(ys)
        dz = max(zs) - min(zs)
        # XY 범위가 넓으면 위에서 보기, Z 범위만 넓으면 옆에서 보기
        if dx < 1 and dy < 1:
            # X,Y가 거의 같으면 YZ 면에서 보기
            self.azimuth = -90.0
            self.elevation = 15.0
        elif dz > max(dx, dy) * 2:
            self.elevation = 10.0

    # ─────────── 동작 스텝 추출 ───────────
    def _build_steps(self):
        """node_data에서 실행 순서대로 스텝 리스트를 생성합니다.

        Loop이 자식으로 Pick/Place를 가질 때, 각 Loop 반복(iter)마다 팔레트의 다음 슬롯
        하나만 동작하도록 펼친다.
          iter 1: Pick[1] → Place[1]
          iter 2: Pick[2] → Place[2]
          ...
        Loop count가 무한(-1/None)이거나 그리드 슬롯 수보다 크면 슬롯 수만큼 반복한다.
        Loop 밖의 단발 Pick/Place는 그리드 전체를 한 번에 펼친다(기존 동작 유지).
        """
        self.steps = []
        self.pallet_grids = []  # [(label, color, grid_points, size)]

        def _grid_of(pd):
            """팔레트 p_data에서 (grid_pts, total) 계산. 없으면 ([], 0)."""
            if not pd or not isinstance(pd, dict):
                return [], 0
            size = pd.get("size", [1, 1])
            points = pd.get("points", [])
            rows = size[0] if len(size) > 0 else 1
            cols = size[1] if len(size) > 1 else 1
            layers = size[2] if len(size) > 2 else 1
            p1 = points[0].get("p", [0]*6) if len(points) >= 1 else [0]*6
            p2 = points[1].get("p", p1) if len(points) >= 2 else p1
            p3 = points[2].get("p", p1) if len(points) >= 3 else p1
            p4 = points[3].get("p", p1) if len(points) >= 4 else p1
            base = [p1[0]*1000, p1[1]*1000, p1[2]*1000]
            row_end = [p2[0]*1000, p2[1]*1000, p2[2]*1000]
            col_end = [p3[0]*1000, p3[1]*1000, p3[2]*1000]
            top = [p4[0]*1000, p4[1]*1000, p4[2]*1000]
            grid_pts = []
            for layer in range(layers):
                lf = layer / (layers - 1) if layers > 1 else 0
                lz = base[2] + (top[2] - base[2]) * lf
                for r in range(rows):
                    rf = r / max(rows - 1, 1) if rows > 1 else 0
                    for c in range(cols):
                        cf = c / max(cols - 1, 1) if cols > 1 else 0
                        gx = base[0] + rf * (row_end[0] - base[0]) + cf * (col_end[0] - base[0])
                        gy = base[1] + rf * (row_end[1] - base[1]) + cf * (col_end[1] - base[1])
                        grid_pts.append([gx, gy, lz])
            return grid_pts, rows * cols * layers

        def _pallet_size_under_loop(loop_item):
            """Loop의 자식들에서 팔레트가 있는 Pick/Place를 찾아 그 슬롯 개수를 반환. 없으면 0."""
            for child in self.tree.get_children(loop_item):
                cd = self.node_data.get(child, {})
                cr = cd.get("__raw__", {})
                ct = cr.get("type", -1)
                if ct in (201, 202):
                    pd = cd.get("p_data")
                    _, total = _grid_of(pd)
                    if total:
                        return total
            return 0

        def emit_step(label, xyz, color, meta):
            self.steps.append((label, xyz, color, meta))

        def emit_pick_or_place(item, slot_idx=None):
            """슬롯 인덱스가 주어지면 그 슬롯 하나만, None이면 전체 그리드 전개."""
            d = self.node_data.get(item, {})
            raw = d.get("__raw__", {})
            t = raw.get("type", -1)
            p = d.get("p", [0]*6)
            label = "Pick" if t == 201 else "Place"
            color = self.C_PICK if t == 201 else self.C_PLACE
            icon = "📥" if t == 201 else "📤"
            pd = d.get("p_data")
            app = d.get("app_data", d.get("approach", {}))
            ret = d.get("ret_data", d.get("retract", {}))
            app_dist = app.get("distance", 50) if app else 50
            ret_dist = ret.get("distance", 50) if ret else 50

            grid_pts, total = _grid_of(pd)
            if grid_pts:
                # 그리드를 한 번만 기록 (중복 방지)
                if not any(lbl == label and gp == grid_pts for lbl, _, gp, _ in self.pallet_grids):
                    self.pallet_grids.append((label, color, grid_pts, pd.get("size", [1, 1])))

                if slot_idx is None:
                    idxs = list(range(total))
                else:
                    idxs = [slot_idx % total]
                for idx in idxs:
                    gpt = grid_pts[idx]
                    app_pt = [gpt[0], gpt[1], gpt[2] + app_dist]
                    ret_pt = [gpt[0], gpt[1], gpt[2] + ret_dist]
                    emit_step(f"{icon} {label} [{idx+1}/{total}] 접근", app_pt, color, {"type": "approach"})
                    emit_step(f"{icon} {label} [{idx+1}/{total}] 동작", gpt[:], color, {"type": "action"})
                    emit_step(f"{icon} {label} [{idx+1}/{total}] 후퇴", ret_pt, color, {"type": "retract"})
            else:
                if any(v != 0 for v in p):
                    xyz = [p[0]*1000, p[1]*1000, p[2]*1000]
                    emit_step(f"{icon} {label}", xyz, color, {})

        def walk(parent="", iter_slot=None):
            """iter_slot: 부모 Loop이 정한 현재 팔레트 슬롯 인덱스. None이면 비루프 컨텍스트."""
            for item in self.tree.get_children(parent):
                d = self.node_data.get(item, {})
                raw = d.get("__raw__", {})
                t = raw.get("type", -1)
                p = d.get("p", [0]*6)

                if t == 100:  # Home
                    if p and any(v != 0 for v in p):
                        xyz = [p[0]*1000, p[1]*1000, p[2]*1000]
                        emit_step("🏠 Home", xyz, self.C_HOME, {})
                    walk(item, iter_slot)

                elif t in (102, 103):  # JointMove / FrameMove
                    wps = d.get("waypoints", [])
                    if wps:
                        for wi, wp in enumerate(wps):
                            wp_p = wp.get("p", p)
                            xyz = [wp_p[0]*1000, wp_p[1]*1000, wp_p[2]*1000]
                            lbl = f"{'J' if t==102 else 'F'}Move" + (f" WP{wi+1}" if len(wps) > 1 else "")
                            emit_step(f"🔵 {lbl}", xyz, self.C_MOVE, {})
                    elif any(v != 0 for v in p):
                        xyz = [p[0]*1000, p[1]*1000, p[2]*1000]
                        emit_step("🔵 FrameMove", xyz, self.C_MOVE, {})

                elif t in (201, 202):  # Pick / Place
                    emit_pick_or_place(item, slot_idx=iter_slot)

                elif t == 20:  # Loop — 자식들을 count만큼 반복하면서 팔레트 슬롯 진행
                    cnt = d.get("count")
                    if cnt is None:
                        cnt = raw.get("count")
                    try:
                        cnt = int(cnt) if cnt is not None else -1
                    except (TypeError, ValueError):
                        cnt = -1
                    pallet_total = _pallet_size_under_loop(item)
                    if cnt <= 0:
                        # 무한 → 자식에 팔레트가 있으면 슬롯 수만큼, 없으면 1회만 가상 실행
                        effective = pallet_total if pallet_total > 0 else 1
                    else:
                        effective = cnt
                    for i in range(effective):
                        slot = i if pallet_total > 0 else iter_slot
                        # ★ 마커 스텝은 emit하지 않는다 — [0,0,0] 위치가 Home으로 가는 것처럼
                        # 보이는 시각적 혼동을 일으킴. 자식 walk만 실행.
                        walk(item, slot)

                else:
                    # 그 외 노드는 자식 탐색만 (Wait, DO, If 등은 3D에서 의미 없음)
                    walk(item, iter_slot)

        walk()

    # ─────────── UI 생성 ───────────
    def _create_window(self):
        self.win = ctk.CTkToplevel(self.parent)
        self.win.title("🎯 3D Motion Step Viewer")
        self.win.geometry("1000x750")
        self.win.configure(fg_color=self.C_BG)
        self.win.transient(self.parent)

        # 상단 컨트롤
        ctrl = ctk.CTkFrame(self.win, fg_color="#1a1a2e", height=60)
        ctrl.pack(fill="x", padx=5, pady=5)

        self.step_label = ctk.CTkLabel(ctrl, text="", font=("Pretendard", 16, "bold"),
                                        text_color=self.C_TEXT)
        self.step_label.pack(side="left", padx=15)

        self.info_label = ctk.CTkLabel(ctrl, text="", font=("Pretendard", 12),
                                        text_color="#aaa")
        self.info_label.pack(side="left", padx=10)

        btn_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)

        ctk.CTkButton(btn_frame, text="⏮ 처음", width=60, height=32,
                       command=self._go_first,
                       fg_color="#333", hover_color="#555").pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="◀ 이전", width=60, height=32,
                       command=self._go_prev,
                       fg_color="#555", hover_color="#777").pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="다음 ▶", width=60, height=32,
                       command=self._go_next,
                       fg_color=self.C_MOVE, hover_color="#3ba89e").pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="끝 ⏭", width=60, height=32,
                       command=self._go_last,
                       fg_color="#333", hover_color="#555").pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="🔄 리셋", width=60, height=32,
                       command=self._reset_view,
                       fg_color="#444", hover_color="#666").pack(side="left", padx=5)

        # 캔버스
        self.canvas = tk.Canvas(self.win, bg=self.C_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)

        # 마우스 이벤트
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.canvas.bind("<Configure>", lambda e: self._draw())

        # 키보드
        self.win.bind("<Left>", lambda e: self._go_prev())
        self.win.bind("<Right>", lambda e: self._go_next())
        self.win.bind("<Home>", lambda e: self._go_first())
        self.win.bind("<End>", lambda e: self._go_last())

        self._draw()

    def _reset_view(self):
        self._auto_view()
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self._draw()

    # ─────────── 정규화 & 투영 ───────────
    def _compute_norm_params(self):
        """모든 포인트를 수집하여 정규화 파라미터를 계산합니다."""
        all_pts = [s[1] for s in self.steps]
        for _, _, gpts, _ in self.pallet_grids:
            all_pts.extend(gpts)
        if not all_pts:
            return None
        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        zs = [p[2] for p in all_pts]
        cx = (max(xs) + min(xs)) / 2
        cy = (max(ys) + min(ys)) / 2
        cz = (max(zs) + min(zs)) / 2
        span = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs), 1)
        return cx, cy, cz, span, min(zs)

    def _norm(self, pt, params):
        """3D 포인트를 정규화합니다."""
        cx, cy, cz, span, _ = params
        return [(pt[0]-cx)/span*300, (pt[1]-cy)/span*300, (pt[2]-cz)/span*300]

    def _project(self, x, y, z):
        """3D→2D 투영 (회전 + 투시)"""
        az = math.radians(self.azimuth)
        el = math.radians(self.elevation)

        # Y-up → 화면 좌표
        x1 = x * math.cos(az) - y * math.sin(az)
        y1 = x * math.sin(az) + y * math.cos(az)
        z1 = z

        x2 = x1
        y2 = y1 * math.sin(el) + z1 * math.cos(el)
        z2 = y1 * math.cos(el) - z1 * math.sin(el)

        # 스케일 + 화면 중앙
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        cx, cy = w / 2 + self.pan_x, h / 2 + self.pan_y

        s = self.scale * min(w, h) / 700
        sx = cx + x2 * s
        sy = cy - y2 * s  # y 반전

        return sx, sy, z2  # z2는 깊이(정렬용)

    # ─────────── 렌더링 ───────────
    def _draw(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 10 or h < 10:
            return

        params = self._compute_norm_params()
        if not params:
            return
        cx, cy, cz, span, min_z = params
        norm = lambda pt: self._norm(pt, params)

        # ── 바닥 그리드 ──
        grid_range = 300
        grid_step = 60
        for i in range(-5, 6):
            g1 = norm([cx + i * span/10, cy - span/2, min_z])
            g2 = norm([cx + i * span/10, cy + span/2, min_z])
            s1x, s1y, _ = self._project(*g1)
            s2x, s2y, _ = self._project(*g2)
            c.create_line(s1x, s1y, s2x, s2y, fill=self.C_FLOOR, width=1)

            g3 = norm([cx - span/2, cy + i * span/10, min_z])
            g4 = norm([cx + span/2, cy + i * span/10, min_z])
            s3x, s3y, _ = self._project(*g3)
            s4x, s4y, _ = self._project(*g4)
            c.create_line(s3x, s3y, s4x, s4y, fill=self.C_FLOOR, width=1)

        # ── 축 그리기 (바닥 기준점에서) ──
        axis_len = span * 0.3
        origin = norm([cx - span/2, cy - span/2, min_z])
        for axis_dir, color, label in [
            ([axis_len, 0, 0], self.C_AXIS_X, "X"),
            ([0, axis_len, 0], self.C_AXIS_Y, "Y"),
            ([0, 0, axis_len], self.C_AXIS_Z, "Z")
        ]:
            end = norm([cx - span/2 + axis_dir[0], cy - span/2 + axis_dir[1], min_z + axis_dir[2]])
            ox, oy, _ = self._project(*origin)
            ex, ey, _ = self._project(*end)
            c.create_line(ox, oy, ex, ey, fill=color, width=2, arrow="last", arrowshape=(10, 12, 5))
            c.create_text(ex + 5, ey - 12, text=label, fill=color, font=("Consolas", 11, "bold"))

        # ── 팔레트 그리드 (번호 표시) ──
        for plabel, pcolor, gpts, psize in self.pallet_grids:
            for gi, gpt in enumerate(gpts):
                np = norm(gpt)
                sx, sy, _ = self._project(*np)
                # 바닥으로 수직선
                floor_pt = norm([gpt[0], gpt[1], min_z])
                fx, fy, _ = self._project(*floor_pt)
                c.create_line(sx, sy, fx, fy, fill=pcolor, width=1, dash=(2, 4))
                # 슬롯 점
                c.create_oval(sx-5, sy-5, sx+5, sy+5, fill="", outline=pcolor, width=1.5)
                # 번호 (큰 폰트)
                c.create_text(sx, sy, text=str(gi+1), fill=pcolor, font=("Consolas", 7))

        # ── 경로 선 (현재 스텝까지) ──
        if self.current_step > 0:
            path_coords = []
            for si in range(self.current_step + 1):
                np = norm(self.steps[si][1])
                sx, sy, _ = self._project(*np)
                path_coords.extend([sx, sy])
            if len(path_coords) >= 4:
                c.create_line(path_coords, fill=self.C_PATH, width=1.5, dash=(4, 4))

        # ── 모든 스텝 점 ──
        for si, (slabel, spt, scolor, sextra) in enumerate(self.steps):
            np = norm(spt)
            sx, sy, _ = self._project(*np)

            if si < self.current_step:
                # 지나간 스텝 — 작은 점 + 번호
                r = 4
                c.create_oval(sx-r, sy-r, sx+r, sy+r, fill=scolor, outline="")
                c.create_text(sx, sy-8, text=str(si+1), fill=scolor, font=("Consolas", 7))
            elif si == self.current_step:
                # 현재 스텝 — 큰 점 + 하이라이트 + 방사 효과
                r = 12
                # 방사 원
                c.create_oval(sx-r-6, sy-r-6, sx+r+6, sy+r+6, fill="", outline=scolor, width=1, dash=(3,3))
                c.create_oval(sx-r-2, sy-r-2, sx+r+2, sy+r+2, fill="", outline=self.C_HIGHLIGHT, width=2)
                c.create_oval(sx-r, sy-r, sx+r, sy+r, fill=scolor, outline="white", width=2)
                # 스텝 번호
                c.create_text(sx, sy, text=str(si+1), fill="white", font=("Consolas", 9, "bold"))
                # 레이블
                c.create_text(sx, sy - 25, text=slabel, fill="white",
                              font=("Pretendard", 11, "bold"))
                # 좌표 표시
                coord_text = f"X:{spt[0]:.0f} Y:{spt[1]:.0f} Z:{spt[2]:.0f}mm"
                c.create_text(sx, sy + 22, text=coord_text, fill="#ccc",
                              font=("Consolas", 10))
            else:
                # 미래 스텝 — 작은 빈 원
                r = 3
                c.create_oval(sx-r, sy-r, sx+r, sy+r, fill="", outline=scolor, width=1)

        # ── 스텝 정보 업데이트 ──
        if self.steps:
            cur = self.steps[self.current_step]
            self.step_label.configure(
                text=f"Step {self.current_step+1}/{len(self.steps)}: {cur[0]}"
            )
            self.info_label.configure(
                text=f"X:{cur[1][0]:.0f} Y:{cur[1][1]:.0f} Z:{cur[1][2]:.0f} mm"
            )

        # ── 범례 (오른쪽 상단) ──
        legend_y = 20
        for label, color in [("Home", self.C_HOME), ("Move", self.C_MOVE),
                              ("Pick", self.C_PICK), ("Place", self.C_PLACE),
                              ("경로", self.C_PATH)]:
            c.create_oval(w-120, legend_y, w-110, legend_y+10, fill=color, outline="")
            c.create_text(w-105, legend_y+5, text=label, fill=self.C_TEXT,
                          font=("Pretendard", 10), anchor="w")
            legend_y += 20

        # ── 현재 뷰 정보 ──
        c.create_text(10, h-40, text=f"방위: {self.azimuth:.0f}° 앙각: {self.elevation:.0f}° 줌: {self.scale:.1f}x",
                       fill="#444", font=("Consolas", 9), anchor="w")
        c.create_text(10, h-20, text="🖱 드래그: 회전 | 스크롤: 줌 | ←→: 스텝 이동",
                       fill="#555", font=("Pretendard", 9), anchor="w")

    # ─────────── 스텝 이동 ───────────
    def _go_next(self):
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self._draw()

    def _go_prev(self):
        if self.current_step > 0:
            self.current_step -= 1
            self._draw()

    def _go_first(self):
        self.current_step = 0
        self._draw()

    def _go_last(self):
        self.current_step = len(self.steps) - 1
        self._draw()

    # ─────────── 마우스 인터랙션 ───────────
    def _on_drag_start(self, event):
        self.drag_start = (event.x, event.y)

    def _on_drag(self, event):
        if self.drag_start:
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            self.azimuth += dx * 0.5
            self.elevation = max(-89, min(89, self.elevation + dy * 0.5))
            self.drag_start = (event.x, event.y)
            self._draw()

    def _on_scroll(self, event):
        if event.delta > 0:
            self.scale *= 1.1
        else:
            self.scale /= 1.1
        self.scale = max(0.1, min(10.0, self.scale))
        self._draw()
