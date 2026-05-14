"""
비주얼 팔레타이징 마법사 — 2D Canvas에서 박스 배열을 시각적으로 설계.
다양한 패턴 지원 + PickPlaceEditor 연동.
"""
import customtkinter as ctk
import tkinter as tk
from presentation.ui.theme import Theme


class PalletizingWizardDialog(ctk.CTkToplevel):
    """팔레타이징 배치 설계 마법사."""
    
    def __init__(self, parent, callback=None, init_data=None):
        super().__init__(parent)
        self.title("🧱 팔레타이징 마법사")
        self.geometry("720x580")
        self.configure(fg_color=Theme.BG_BASE)
        self.callback = callback  # 결과 반환 콜백
        
        self.rows = 3
        self.cols = 3
        self.layers = 1
        self.box_w = 150  # mm
        self.box_h = 100  # mm
        self.gap = 10     # mm
        self.pattern = "normal"
        
        # 초기 데이터가 있으면 적용
        if init_data:
            self.cols = init_data.get("cols", self.cols)
            self.rows = init_data.get("rows", self.rows)
            self.layers = init_data.get("layers", self.layers)
            self.box_w = init_data.get("box_w", self.box_w)
            self.box_h = init_data.get("box_h", self.box_h)
            self.gap = init_data.get("gap", self.gap)
            self.pattern = init_data.get("pattern", self.pattern)
        
        self._build_ui()
        self.after(100, self._draw_layout)
    
    def _build_ui(self):
        # 컨트롤 패널
        ctrl = ctk.CTkFrame(self, fg_color=Theme.BG_SURFACE, height=140)
        ctrl.pack(fill="x", padx=5, pady=5)
        
        row1 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(row1, text="가로(열):", font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY).pack(side="left")
        self.col_entry = ctk.CTkEntry(row1, width=50)
        self.col_entry.insert(0, str(self.cols))
        self.col_entry.pack(side="left", padx=3)
        
        ctk.CTkLabel(row1, text="세로(행):", font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY).pack(side="left", padx=(10,0))
        self.row_entry = ctk.CTkEntry(row1, width=50)
        self.row_entry.insert(0, str(self.rows))
        self.row_entry.pack(side="left", padx=3)
        
        ctk.CTkLabel(row1, text="층:", font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY).pack(side="left", padx=(10,0))
        self.layer_entry = ctk.CTkEntry(row1, width=50)
        self.layer_entry.insert(0, str(self.layers))
        self.layer_entry.pack(side="left", padx=3)
        
        row2 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=3)
        
        ctk.CTkLabel(row2, text="박스 가로(mm):", font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY).pack(side="left")
        self.bw_entry = ctk.CTkEntry(row2, width=60)
        self.bw_entry.insert(0, str(int(self.box_w)))
        self.bw_entry.pack(side="left", padx=3)
        
        ctk.CTkLabel(row2, text="세로(mm):", font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY).pack(side="left", padx=(10,0))
        self.bh_entry = ctk.CTkEntry(row2, width=60)
        self.bh_entry.insert(0, str(int(self.box_h)))
        self.bh_entry.pack(side="left", padx=3)
        
        ctk.CTkLabel(row2, text="간격(mm):", font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY).pack(side="left", padx=(10,0))
        self.gap_entry = ctk.CTkEntry(row2, width=50)
        self.gap_entry.insert(0, str(int(self.gap)))
        self.gap_entry.pack(side="left", padx=3)
        
        row3 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row3.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(row3, text="배치 패턴:", font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY).pack(side="left")
        pattern_values = ["일반(Z형)", "지그재그", "교차(90°)", "S자형", "외곽나선", "중앙확산"]
        self.pattern_sel = ctk.CTkOptionMenu(row3, values=pattern_values, width=110,
                                              fg_color=Theme.BG_BASE, button_color=Theme.ACCENT_PRIMARY,
                                              command=self._on_pattern_change)
        # 초기 패턴 설정
        pmap_rev = {"normal": "일반(Z형)", "zigzag": "지그재그", "cross": "교차(90°)", 
                    "snake": "S자형", "spiral": "외곽나선", "center_out": "중앙확산"}
        self.pattern_sel.set(pmap_rev.get(self.pattern, "일반(Z형)"))
        self.pattern_sel.pack(side="left", padx=5)
        
        ctk.CTkButton(row3, text="미리보기", width=70, height=28, 
                       fg_color=Theme.ACCENT_PRIMARY, hover_color=Theme.ACCENT_HOVER,
                       command=self._draw_layout).pack(side="left", padx=5)
        ctk.CTkButton(row3, text="✅ 적용", width=70, height=28, 
                       fg_color=Theme.SUCCESS, hover_color=Theme.SUCCESS_HOVER,
                       command=self._apply).pack(side="left", padx=5)
        
        # 현재 배치 정보
        self.info_lbl = ctk.CTkLabel(ctrl, text=f"총 {self.rows*self.cols*self.layers}개 ({self.cols}×{self.rows}×{self.layers}층)", 
                                      font=Theme.font(size=11), text_color=Theme.WARNING)
        self.info_lbl.pack(pady=2)
        
        # Canvas (2D 팔레트 뷰)
        canvas_frame = ctk.CTkFrame(self, fg_color=Theme.BG_SURFACE)
        canvas_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, bg=Theme.BG_SURFACE, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
    
    def _on_pattern_change(self, val):
        pmap = {"일반(Z형)": "normal", "지그재그": "zigzag", "교차(90°)": "cross",
                "S자형": "snake", "외곽나선": "spiral", "중앙확산": "center_out"}
        self.pattern = pmap.get(val, "normal")
        self._draw_layout()
    
    def _get_visit_order(self, rows, cols):
        """패턴에 따른 셀 방문 순서 반환. 각 항목은 (row, col)."""
        if self.pattern == "zigzag":
            order = []
            for r in range(rows):
                if r % 2 == 0:
                    order.extend([(r, c) for c in range(cols)])
                else:
                    order.extend([(r, c) for c in range(cols - 1, -1, -1)])
            return order
        
        elif self.pattern == "snake":
            # S자형: 열 우선으로 내려갔다 올라갔다
            order = []
            for c in range(cols):
                if c % 2 == 0:
                    order.extend([(r, c) for r in range(rows)])
                else:
                    order.extend([(r, c) for r in range(rows - 1, -1, -1)])
            return order
        
        elif self.pattern == "spiral":
            # 외곽 나선형 (시계방향)
            order = []
            top, bottom, left, right = 0, rows - 1, 0, cols - 1
            while top <= bottom and left <= right:
                for c in range(left, right + 1): order.append((top, c))
                top += 1
                for r in range(top, bottom + 1): order.append((r, right))
                right -= 1
                if top <= bottom:
                    for c in range(right, left - 1, -1): order.append((bottom, c))
                    bottom -= 1
                if left <= right:
                    for r in range(bottom, top - 1, -1): order.append((r, left))
                    left += 1
            return order
        
        elif self.pattern == "center_out":
            # 중앙에서 바깥으로 확산
            import math
            center_r, center_c = (rows - 1) / 2.0, (cols - 1) / 2.0
            cells = [(r, c) for r in range(rows) for c in range(cols)]
            cells.sort(key=lambda rc: math.sqrt((rc[0] - center_r)**2 + (rc[1] - center_c)**2))
            return cells
        
        else:  # normal (Z형) 또는 cross
            return [(r, c) for r in range(rows) for c in range(cols)]
    
    def _draw_layout(self):
        try:
            self.cols = int(self.col_entry.get())
            self.rows = int(self.row_entry.get())
            self.layers = int(self.layer_entry.get())
            self.box_w = float(self.bw_entry.get())
            self.box_h = float(self.bh_entry.get())
            self.gap = float(self.gap_entry.get())
        except ValueError:
            return
        
        total = self.rows * self.cols * self.layers
        virtual_cols = max(1, self.cols * 2 - 1)
        virtual_rows = max(1, self.rows * 2 - 1)
        self.info_lbl.configure(
            text=(
                f"총 {total}개 ({self.cols}×{self.rows}×{self.layers}층) | "
                f"가상 격자 {virtual_cols}×{virtual_rows} "
                f"(제품 {self.cols}×{self.rows} + 갭 {max(0, self.cols-1)}×{max(0, self.rows-1)})"
            )
        )
        
        self.canvas.delete("all")
        
        cw = self.canvas.winfo_width() or 600
        ch = self.canvas.winfo_height() or 350
        
        pallet_w = self.cols * self.box_w + (self.cols - 1) * self.gap
        pallet_h = self.rows * self.box_h + (self.rows - 1) * self.gap
        
        margin = 40
        scale = min((cw - 2 * margin) / max(pallet_w, 1), (ch - 2 * margin) / max(pallet_h, 1))
        scale = min(scale, 2.0)
        
        ox = (cw - pallet_w * scale) / 2
        oy = (ch - pallet_h * scale) / 2
        
        # 팔레트 외곽선
        self.canvas.create_rectangle(ox - 5, oy - 5, 
                                      ox + pallet_w * scale + 5, oy + pallet_h * scale + 5,
                                      outline="#455A64", width=2, dash=(4, 4))
        self.canvas.create_text(ox + pallet_w * scale / 2, oy - 15, 
                                text=f"팔레트 ({pallet_w:.0f} × {pallet_h:.0f} mm)", 
                                fill=Theme.TEXT_SECONDARY, font=("", 10))
        
        # 방문 순서 가져오기
        visit_order = self._get_visit_order(self.rows, self.cols)
        
        # 색상 팔레트
        colors = ["#4CAF50", "#FF9800", "#9C27B0", "#00BCD4", "#E91E63", 
                  "#3F51B5", "#009688", "#FF5722", "#607D8B", "#CDDC39"]
        
        # 셀 중심 좌표 계산
        cell_centers = {}
        for idx, (row, col) in enumerate(visit_order):
            bx = ox + col * (self.box_w + self.gap) * scale
            by = oy + row * (self.box_h + self.gap) * scale
            bw = self.box_w * scale
            bh = self.box_h * scale
            
            # 교차 패턴: 홀수 셀 90° 회전
            if self.pattern == "cross" and (row + col) % 2 == 1:
                bw, bh = bh, bw
            
            color = colors[idx % len(colors)]
            self.canvas.create_rectangle(bx, by, bx + bw, by + bh, 
                                          fill=color, outline=Theme.TEXT_PRIMARY, width=1)
            self.canvas.create_text(bx + bw / 2, by + bh / 2, 
                                    text=str(idx + 1), fill="white", font=("", 9, "bold"))
            
            cell_centers[(row, col)] = (bx + bw / 2, by + bh / 2)
        
        # 순서 화살표 그리기
        for i in range(len(visit_order) - 1):
            r1, c1 = visit_order[i]
            r2, c2 = visit_order[i + 1]
            x1, y1 = cell_centers[(r1, c1)]
            x2, y2 = cell_centers[(r2, c2)]
            self.canvas.create_line(x1, y1, x2, y2, fill="#FFEB3B", width=2, arrow=tk.LAST, arrowshape=(8, 10, 4))
    
    def _apply(self):
        """설계된 팔레타이징 배열을 PickPlaceEditor로 반환."""
        try:
            self.cols = int(self.col_entry.get())
            self.rows = int(self.row_entry.get())
            self.layers = int(self.layer_entry.get())
            self.box_w = float(self.bw_entry.get())
            self.box_h = float(self.bh_entry.get())
            self.gap = float(self.gap_entry.get())
        except ValueError:
            return
            
        result = {
            "rows": self.rows, "cols": self.cols, "layers": self.layers,
            "box_w": self.box_w, "box_h": self.box_h, "gap": self.gap,
            "pattern": self.pattern, "total": self.rows * self.cols * self.layers,
            "visit_order": self._get_visit_order(self.rows, self.cols)
        }
        print(f">> [팔레타이징] 배치 적용: {self.cols}×{self.rows}×{self.layers}층 = {result['total']}개, 패턴={self.pattern}")
        if self.callback:
            self.callback(result)
        self.destroy()
