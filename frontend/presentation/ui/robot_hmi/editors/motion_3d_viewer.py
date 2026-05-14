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
    C_ROBOT    = "#00E5FF"
    C_PLAN     = "#5C6BC0"

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
        self.di_state = [0] * 32
        self.do_state = [0] * 32
        self.display_do_state = [0] * 32
        self.display_vars = {}
        self.loop_preview_count = 12
        self.autoplay = False
        self._auto_job = None
        self.di_buttons = []
        self.do_labels = []
        self.var_label = None
        self.auto_btn = None
        self.loop_entry = None
        self.dh_params = [
            {"a": 0.0,    "alpha": 0.0,       "d": 0.3,    "theta_offset": 0.0},
            {"a": 0.0,    "alpha": math.pi/2,  "d": 0.0,    "theta_offset": math.pi/2},
            {"a": 0.45,   "alpha": 0.0,       "d": 0.0035, "theta_offset": math.pi/2},
            {"a": 0.0,    "alpha": math.pi/2,  "d": 0.35,   "theta_offset": math.pi},
            {"a": 0.0,    "alpha": math.pi/2,  "d": 0.1835, "theta_offset": 0.0},
            {"a": 0.0,    "alpha": -math.pi/2, "d": 0.228,  "theta_offset": 0.0},
        ]

        self._build_steps()

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
        sim_vars = {}
        sim_do = [0] * 32
        last_xyz = [0.0, 0.0, 0.0]

        class _WaitBlocked(Exception):
            pass

        def _to_number(value, default=0.0):
            try:
                if isinstance(value, str):
                    value = value.strip()
                return float(value)
            except (TypeError, ValueError):
                return default

        def _get_var_or_number(token):
            name = str(token)
            if name in sim_vars:
                return sim_vars[name]
            return _to_number(token, 0.0)

        def _eval_expr(expr):
            import ast
            if isinstance(expr, (int, float)):
                return float(expr)
            expr = str(expr).strip()
            try:
                return float(expr)
            except ValueError:
                pass
            tree = ast.parse(expr, mode="eval")

            def _eval(node):
                if isinstance(node, ast.Expression):
                    return _eval(node.body)
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                    return float(node.value)
                if isinstance(node, ast.Name):
                    return float(sim_vars.get(node.id, 0.0))
                if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                    value = _eval(node.operand)
                    return value if isinstance(node.op, ast.UAdd) else -value
                if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                    left = _eval(node.left)
                    right = _eval(node.right)
                    if isinstance(node.op, ast.Add):
                        return left + right
                    if isinstance(node.op, ast.Sub):
                        return left - right
                    if isinstance(node.op, ast.Mult):
                        return left * right
                    if isinstance(node.op, ast.Div):
                        return left / right if right != 0 else left
                raise ValueError(expr)

            return _eval(tree)

        def _apply_var_list(var_list):
            if not isinstance(var_list, list):
                return
            for entry in var_list:
                if not isinstance(entry, dict):
                    continue
                name = str(entry.get("name", "")).strip()
                if not name:
                    continue
                try:
                    sim_vars[name] = _eval_expr(entry.get("value", 0))
                except Exception:
                    sim_vars[name] = _get_var_or_number(entry.get("value", 0))

        def _operand_value(operand):
            if isinstance(operand, dict):
                value = operand.get("value", 0)
                if operand.get("type", -1) == 10:
                    return _get_var_or_number(value)
                return _to_number(value, 0.0)
            return _get_var_or_number(operand)

        def _eval_condition(cond):
            if not cond:
                return False
            left = _operand_value(cond.get("left", {}))
            right = _operand_value(cond.get("right", {}))
            op = cond.get("op", 0)
            if op == 0:
                return left == right
            if op == 1:
                return left != right
            if op == 2:
                return left > right
            if op == 3:
                return left >= right
            if op == 4:
                return left < right
            if op == 5:
                return left <= right
            return False

        def _eval_di_list(di_list):
            if not di_list:
                return True
            for cond in di_list:
                try:
                    idx = int(cond.get("idx", 0))
                except (TypeError, ValueError):
                    return False
                expected = int(cond.get("value", 1))
                if idx < 0 or idx >= len(self.di_state):
                    return False
                if int(self.di_state[idx]) != expected:
                    return False
            return True

        def _di_text(di_list):
            if not di_list:
                return "DI 미지정"
            parts = []
            for cond in di_list:
                idx = cond.get("idx", 0)
                val = "ON" if cond.get("value", 1) else "OFF"
                parts.append(f"DI{int(idx):02d}={val}")
            return ", ".join(parts)

        def _grid_of(pd):
            """팔레트 p_data에서 (grid_pts, total) 계산. 없으면 ([], 0).

            ★ 실 실행(_run_program)이 쓰는 MotionMath.compute_pallet_point와 동일한
            풀-벡터 보간을 사용한다. 이전 버전은 layer 보간을 Z 성분에만 적용하고
            X/Y/Rx/Ry/Rz는 무시했다 → P4가 비-Z 축정렬이거나 사용자가 P2/P3에 Z 변화를
            준 경우(기울어진/회전된 팔레트) 가상 표시가 실제 동작과 어긋났다.
            """
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
            p4 = points[3].get("p", p1) if len(points) >= 4 else None

            grid_pts = []
            for layer in range(layers):
                for r in range(rows):
                    for c in range(cols):
                        # 실 실행과 동일한 보간 — 모든 축(X,Y,Z,Rx,Ry,Rz) 동기 보간
                        from core.domains.robot.use_cases.motion_math import MotionMath
                        pos = MotionMath.compute_pallet_point(
                            p1, p2, p3, rows, cols, r, c,
                            p4=p4, size_l=layers, current_l=layer
                        )
                        # 미터 → 밀리미터, X/Y/Z만 사용
                        grid_pts.append([pos[0]*1000, pos[1]*1000, pos[2]*1000])
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
            nonlocal last_xyz
            step_meta = dict(meta or {})
            step_meta["di"] = list(self.di_state)
            step_meta["do"] = list(sim_do)
            step_meta["vars"] = dict(sim_vars)
            step_meta.setdefault("p_mm", list(xyz))
            self.steps.append((label, xyz, color, step_meta))
            last_xyz = list(xyz)

        def emit_io_step(label, color="#FFB74D"):
            emit_step(label, list(last_xyz), color, {"type": "io"})

        def apply_do_list(do_list):
            if not isinstance(do_list, list):
                return
            changed = []
            for item in do_list:
                if not isinstance(item, dict):
                    continue
                try:
                    idx = int(item.get("idx", 0))
                except (TypeError, ValueError):
                    continue
                if idx < 0 or idx >= len(sim_do):
                    continue
                value = 1 if int(item.get("value", 0)) else 0
                sim_do[idx] = value
                changed.append(f"DO{idx:02d}={'ON' if value else 'OFF'}")
            if changed:
                emit_io_step(" ".join(changed), "#FFA726")

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
                    q_meta = d.get("q") if d.get("q") and any(v != 0 for v in d.get("q", [])) else None
                    emit_step(f"{icon} {label} [{idx+1}/{total}] 접근", app_pt, color, {"type": "approach", "q": q_meta})
                    emit_step(f"{icon} {label} [{idx+1}/{total}] 동작", gpt[:], color, {"type": "action", "q": q_meta})
                    emit_step(f"{icon} {label} [{idx+1}/{total}] 후퇴", ret_pt, color, {"type": "retract", "q": q_meta})
            else:
                if any(v != 0 for v in p):
                    xyz = [p[0]*1000, p[1]*1000, p[2]*1000]
                    q_meta = d.get("q") if d.get("q") and any(v != 0 for v in d.get("q", [])) else None
                    emit_step(f"{icon} {label}", xyz, color, {"q": q_meta})

        def walk(parent="", iter_slot=None):
            """iter_slot: 부모 Loop이 정한 현재 팔레트 슬롯 인덱스. None이면 비루프 컨텍스트."""
            children = list(self.tree.get_children(parent))
            skip_indices = set()
            for child_idx, item in enumerate(children):
                if child_idx in skip_indices:
                    continue
                d = self.node_data.get(item, {})
                raw = d.get("__raw__", {})
                t = raw.get("type", -1)
                p = d.get("p", [0]*6)

                if t in (24, 25, 26):
                    chain = []
                    scan_idx = child_idx
                    while scan_idx < len(children):
                        sd = self.node_data.get(children[scan_idx], {})
                        sr = sd.get("__raw__", {})
                        if sr.get("type", -1) not in (24, 25, 26):
                            break
                        chain.append(children[scan_idx])
                        scan_idx += 1
                    skip_indices.update(range(child_idx + 1, child_idx + len(chain)))
                    for branch_item in chain:
                        bd = self.node_data.get(branch_item, {})
                        br = bd.get("__raw__", {})
                        bt = br.get("type", -1)
                        if bt == 26 or _eval_condition(bd.get("cond", br.get("cond", {}))):
                            walk(branch_item, iter_slot)
                            break
                    continue

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
                            wp_q = wp.get("q")
                            xyz = [wp_p[0]*1000, wp_p[1]*1000, wp_p[2]*1000]
                            lbl = f"{'J' if t==102 else 'F'}Move" + (f" WP{wi+1}" if len(wps) > 1 else "")
                            emit_step(f"🔵 {lbl}", xyz, self.C_MOVE, {"q": wp_q})
                    elif any(v != 0 for v in p):
                        xyz = [p[0]*1000, p[1]*1000, p[2]*1000]
                        q_meta = d.get("q") if d.get("q") and any(v != 0 for v in d.get("q", [])) else None
                        emit_step("🔵 FrameMove", xyz, self.C_MOVE, {"q": q_meta})

                elif t in (201, 202):  # Pick / Place
                    emit_pick_or_place(item, slot_idx=iter_slot)

                elif t == 2:  # Variables
                    _apply_var_list(d.get("varList", raw.get("varList", [])))

                elif t == 3:  # Math / variable assignment
                    _apply_var_list(d.get("varList", raw.get("varList", [])))

                elif t == 4:  # SmartDO
                    apply_do_list(d.get("doList", raw.get("doList", [])))

                elif t == 6:  # EndToolDO
                    apply_do_list(d.get("endtoolDoList", raw.get("endtoolDoList", [])))

                elif t in (28, 29, 30):  # Wait/If by DI
                    di_list = d.get("diList", raw.get("diList", []))
                    passed = _eval_di_list(di_list)
                    if t == 28:
                        emit_io_step(f"DI 대기 {'충족' if passed else '대기중'} ({_di_text(di_list)})", "#66BB6A" if passed else "#EF5350")
                        if not passed:
                            raise _WaitBlocked()
                        walk(item, iter_slot)
                    else:
                        if passed:
                            emit_io_step(f"If DI TRUE ({_di_text(di_list)})", "#66BB6A")
                            walk(item, iter_slot)
                        else:
                            emit_io_step(f"If DI FALSE ({_di_text(di_list)})", "#78909C")

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
                        effective = max(1, int(getattr(self, "loop_preview_count", 12) or 12))
                    else:
                        effective = cnt
                    for i in range(effective):
                        slot = i if pallet_total > 0 else iter_slot
                        # ★ 마커 스텝은 emit하지 않는다 — [0,0,0] 위치가 Home으로 가는 것처럼
                        # 보이는 시각적 혼동을 일으킴. 자식 walk만 실행.
                        try:
                            walk(item, slot)
                        except _WaitBlocked:
                            break

                else:
                    # 그 외 노드는 자식 탐색만 (Wait, DO, If 등은 3D에서 의미 없음)
                    walk(item, iter_slot)

        try:
            walk()
        except _WaitBlocked:
            pass
        self.do_state = list(sim_do)
        self.display_do_state = list(sim_do)
        self.display_vars = dict(sim_vars)

    # ─────────── UI 생성 ───────────
    def _create_window(self):
        self.win = ctk.CTkToplevel(self.parent)
        self.win.title("🎯 3D Motion Step Viewer")
        self.win.geometry("1280x780")
        self.win.configure(fg_color=self.C_BG)
        self.win.transient(self.parent)
        self.win.protocol("WM_DELETE_WINDOW", self._close)

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
        self.auto_btn = ctk.CTkButton(btn_frame, text="연속 ▶", width=70, height=32,
                                      command=self._toggle_autoplay,
                                      fg_color="#6A5ACD", hover_color="#5143A8")
        self.auto_btn.pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="🔄 리셋", width=60, height=32,
                       command=self._reset_view,
                       fg_color="#444", hover_color="#666").pack(side="left", padx=5)

        # 본문: 3D 캔버스 + 가상 I/O 패널
        body = ctk.CTkFrame(self.win, fg_color=self.C_BG)
        body.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        self.canvas = tk.Canvas(body, bg=self.C_BG, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True, padx=(0, 5), pady=0)

        io_panel = ctk.CTkFrame(body, fg_color="#15152b", width=320, corner_radius=8)
        io_panel.pack(side="right", fill="y", padx=(5, 0), pady=0)
        io_panel.pack_propagate(False)
        self._build_io_panel(io_panel)

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

    def _close(self):
        self.autoplay = False
        if self._auto_job:
            try:
                self.win.after_cancel(self._auto_job)
            except Exception:
                pass
            self._auto_job = None
        self.win.destroy()

    def _build_io_panel(self, parent):
        header = ctk.CTkFrame(parent, fg_color="#1f1f3d", corner_radius=8)
        header.pack(fill="x", padx=8, pady=(8, 6))
        ctk.CTkLabel(header, text="가상 I/O 시뮬레이터", font=("Pretendard", 15, "bold"),
                     text_color=self.C_TEXT).pack(pady=(8, 4))

        loop_row = ctk.CTkFrame(header, fg_color="transparent")
        loop_row.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkLabel(loop_row, text="무한 Loop 표시:", text_color="#bbb",
                     font=("Pretendard", 11)).pack(side="left")
        self.loop_entry = ctk.CTkEntry(loop_row, width=48, height=26, justify="center")
        self.loop_entry.insert(0, str(self.loop_preview_count))
        self.loop_entry.pack(side="left", padx=6)
        ctk.CTkButton(loop_row, text="재계산", width=62, height=26,
                      command=self._rebuild_simulation,
                      fg_color="#455A64", hover_color="#546E7A").pack(side="left")

        ctk.CTkButton(header, text="DI/DO 초기화", height=28,
                      command=self._reset_io,
                      fg_color="#424242", hover_color="#616161").pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkLabel(parent, text="DI 입력 (외부 신호)", font=("Pretendard", 13, "bold"),
                     text_color="#81D4FA").pack(anchor="w", padx=10, pady=(8, 2))
        di_grid = ctk.CTkFrame(parent, fg_color="transparent")
        di_grid.pack(fill="x", padx=8, pady=(0, 8))
        self.di_buttons = []
        for idx in range(32):
            btn = ctk.CTkButton(di_grid, text=f"{idx:02d}", width=34, height=24,
                                font=("Consolas", 10, "bold"),
                                fg_color="#263238", hover_color="#37474F",
                                command=lambda i=idx: self._toggle_di(i))
            btn.grid(row=idx // 4, column=idx % 4, padx=2, pady=2, sticky="ew")
            self.di_buttons.append(btn)

        ctk.CTkLabel(parent, text="DO 출력 (프로그램 결과)", font=("Pretendard", 13, "bold"),
                     text_color="#A5D6A7").pack(anchor="w", padx=10, pady=(8, 2))
        do_grid = ctk.CTkFrame(parent, fg_color="transparent")
        do_grid.pack(fill="x", padx=8, pady=(0, 8))
        self.do_labels = []
        for idx in range(32):
            lbl = ctk.CTkLabel(do_grid, text=f"{idx:02d}", width=34, height=24,
                               font=("Consolas", 10, "bold"),
                               fg_color="#263238", text_color="#9E9E9E", corner_radius=5)
            lbl.grid(row=idx // 4, column=idx % 4, padx=2, pady=2, sticky="ew")
            self.do_labels.append(lbl)

        ctk.CTkLabel(parent, text="변수 / 카운터", font=("Pretendard", 13, "bold"),
                     text_color="#FFE082").pack(anchor="w", padx=10, pady=(8, 2))
        self.var_label = ctk.CTkLabel(parent, text="-", justify="left", anchor="w",
                                      text_color="#ddd", font=("Consolas", 11))
        self.var_label.pack(fill="x", padx=10, pady=(0, 8))
        self._refresh_io_widgets()

    def _toggle_di(self, idx):
        self.di_state[idx] = 0 if self.di_state[idx] else 1
        self._rebuild_simulation()

    def _reset_io(self):
        self.di_state = [0] * 32
        self.do_state = [0] * 32
        self.display_do_state = [0] * 32
        self.display_vars = {}
        self.current_step = 0
        self._rebuild_simulation()

    def _read_loop_preview_count(self):
        try:
            value = int(self.loop_entry.get()) if self.loop_entry else self.loop_preview_count
        except (TypeError, ValueError):
            value = self.loop_preview_count
        self.loop_preview_count = max(1, min(999, value))
        if self.loop_entry:
            self.loop_entry.delete(0, "end")
            self.loop_entry.insert(0, str(self.loop_preview_count))

    def _rebuild_simulation(self):
        self._read_loop_preview_count()
        self._build_steps()
        if self.current_step >= len(self.steps):
            self.current_step = max(0, len(self.steps) - 1)
        self._auto_view()
        self._refresh_io_widgets()
        self._draw()

    def _refresh_io_widgets(self, step_meta=None):
        if step_meta:
            self.display_do_state = list(step_meta.get("do", self.display_do_state))
            self.display_vars = dict(step_meta.get("vars", self.display_vars))
        for idx, btn in enumerate(getattr(self, "di_buttons", [])):
            on = bool(self.di_state[idx])
            btn.configure(fg_color="#00C853" if on else "#263238",
                          hover_color="#00A043" if on else "#37474F",
                          text_color="#111111" if on else "#B0BEC5")
        for idx, lbl in enumerate(getattr(self, "do_labels", [])):
            on = bool(self.display_do_state[idx])
            lbl.configure(fg_color="#69F0AE" if on else "#263238",
                          text_color="#101010" if on else "#9E9E9E")
        if self.var_label:
            visible = {
                key: value for key, value in sorted(self.display_vars.items())
                if str(key) not in ("0", "1")
            }
            if visible:
                text = "\n".join(f"{key}: {value:g}" for key, value in visible.items())
            else:
                text = "-"
            self.var_label.configure(text=text)

    def _toggle_autoplay(self):
        self.autoplay = not self.autoplay
        if self.auto_btn:
            self.auto_btn.configure(text="정지 ❚❚" if self.autoplay else "연속 ▶",
                                    fg_color="#D84315" if self.autoplay else "#6A5ACD")
        if self.autoplay:
            self._schedule_autoplay()
        elif self._auto_job:
            try:
                self.win.after_cancel(self._auto_job)
            except Exception:
                pass
            self._auto_job = None

    def _schedule_autoplay(self):
        if not self.autoplay:
            return
        self._auto_job = self.win.after(550, self._autoplay_step)

    def _autoplay_step(self):
        if not self.autoplay:
            return
        if self.steps:
            if self.current_step >= len(self.steps) - 1:
                self.current_step = 0
            else:
                self.current_step += 1
            self._draw()
        self._schedule_autoplay()

    def _reset_view(self):
        self._auto_view()
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self._draw()

    def _fk_points_mm(self, joint_angles):
        """Return Indy7 link points in millimeters from J1~J6 degrees."""
        if not joint_angles or len(joint_angles) < 6:
            return []
        try:
            import numpy as np
            t_mat = np.eye(4)
            points = [t_mat[:3, 3].copy()]
            for idx in range(6):
                theta = math.radians(float(joint_angles[idx])) + self.dh_params[idx]["theta_offset"]
                a = self.dh_params[idx]["a"]
                alpha = self.dh_params[idx]["alpha"]
                d = self.dh_params[idx]["d"]
                ct, st = math.cos(theta), math.sin(theta)
                ca, sa = math.cos(alpha), math.sin(alpha)
                t_i = np.array([
                    [ct, -st, 0, a],
                    [st * ca, ct * ca, -sa, -d * sa],
                    [st * sa, ct * sa, ca, d * ca],
                    [0, 0, 0, 1],
                ])
                t_mat = t_mat @ t_i
                points.append(t_mat[:3, 3].copy())
            return [[float(p[0] * 1000), float(p[1] * 1000), float(p[2] * 1000)] for p in points]
        except Exception:
            return []

    def _current_or_previous_q(self):
        if not self.steps:
            return None
        for idx in range(min(self.current_step, len(self.steps) - 1), -1, -1):
            q = self.steps[idx][3].get("q")
            if q and len(q) >= 6 and any(v != 0 for v in q):
                return q
        return None

    # ─────────── 정규화 & 투영 ───────────
    def _compute_norm_params(self):
        """모든 포인트를 수집하여 정규화 파라미터를 계산합니다."""
        all_pts = [s[1] for s in self.steps]
        for _, _, gpts, _ in self.pallet_grids:
            all_pts.extend(gpts)
        for _, _, _, meta in self.steps:
            q = meta.get("q") if isinstance(meta, dict) else None
            all_pts.extend(self._fk_points_mm(q))
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
        if not self.steps:
            c.create_text(w / 2, h / 2 - 10, text="표시할 동작이 없습니다.",
                          fill=self.C_TEXT, font=("Pretendard", 16, "bold"))
            c.create_text(w / 2, h / 2 + 18, text="오른쪽 DI 입력을 켜고 재계산해 보세요.",
                          fill="#777", font=("Pretendard", 11))
            if self.step_label:
                self.step_label.configure(text="Step 0/0")
            if self.info_label:
                self.info_label.configure(text="DI 입력 대기")
            self._refresh_io_widgets()
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

        # ── 전체 예정 궤적 + 현재까지 실제 진행 궤적 ──
        if len(self.steps) > 1:
            full_path = []
            done_path = []
            for si, (_, point, _, _) in enumerate(self.steps):
                npt = norm(point)
                sx, sy, _ = self._project(*npt)
                full_path.extend([sx, sy])
                if si <= self.current_step:
                    done_path.extend([sx, sy])
            if len(full_path) >= 4:
                c.create_line(full_path, fill=self.C_PLAN, width=1.0, dash=(2, 5))
            if len(done_path) >= 4:
                c.create_line(done_path, fill=self.C_PATH, width=2.4)

        # ── 관절값 기반 로봇 팔 형상 ──
        robot_q = self._current_or_previous_q()
        robot_pts = self._fk_points_mm(robot_q)
        if len(robot_pts) >= 2:
            arm_coords = []
            for point in robot_pts:
                npt = norm(point)
                sx, sy, _ = self._project(*npt)
                arm_coords.extend([sx, sy])
            if len(arm_coords) >= 4:
                c.create_line(arm_coords, fill=self.C_ROBOT, width=4)
            for ji, point in enumerate(robot_pts):
                npt = norm(point)
                sx, sy, _ = self._project(*npt)
                r = 5 if ji < len(robot_pts) - 1 else 8
                c.create_oval(sx-r, sy-r, sx+r, sy+r, fill=self.C_ROBOT, outline="white", width=1)
            tcp = robot_pts[-1]
            npt = norm(tcp)
            sx, sy, _ = self._project(*npt)
            c.create_text(sx + 10, sy - 12, text="Robot TCP(FK)", fill=self.C_ROBOT,
                          font=("Consolas", 9, "bold"), anchor="w")

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
            self._refresh_io_widgets(cur[3])
            self.step_label.configure(
                text=f"Step {self.current_step+1}/{len(self.steps)}: {cur[0]}"
            )
            cur_q = cur[3].get("q") if isinstance(cur[3], dict) else None
            q_text = ""
            if cur_q and len(cur_q) >= 6:
                q_text = f" | J1:{cur_q[0]:.1f} J2:{cur_q[1]:.1f} J3:{cur_q[2]:.1f}"
            self.info_label.configure(
                text=f"X:{cur[1][0]:.0f} Y:{cur[1][1]:.0f} Z:{cur[1][2]:.0f} mm{q_text}"
            )

        # ── 범례 (오른쪽 상단) ──
        legend_y = 20
        for label, color in [("Home", self.C_HOME), ("Move", self.C_MOVE),
                              ("Pick", self.C_PICK), ("Place", self.C_PLACE),
                              ("진행 궤적", self.C_PATH), ("예정 궤적", self.C_PLAN),
                              ("로봇 FK", self.C_ROBOT)]:
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
