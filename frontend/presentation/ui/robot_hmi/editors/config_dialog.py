import customtkinter as ctk
from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
from presentation.ui.theme import Theme


class RobotConfigDialog(ctk.CTkToplevel):
    """
    로봇 설정 다이얼로그 — 페이로드, TCP, 작업공간 제한, 임피던스 파라미터 설정.
    """
    
    def __init__(self, parent, robot_name_provider=None):
        super().__init__(parent)
        self.robot_name_provider = robot_name_provider
        self.title("⚙️ 로봇 설정")
        self.geometry("500x620")
        self.resizable(False, False)
        self.configure(fg_color=Theme.BG_BASE)
        
        self.grab_set()
        self._build_ui()

    def _selected_robot_name(self):
        try:
            if callable(self.robot_name_provider):
                name = self.robot_name_provider()
                if name:
                    return name
        except Exception:
            pass
        return None
    
    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color=Theme.BG_BASE)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ===== 1. 페이로드 설정 =====
        self._section(scroll, "📦 페이로드 설정")
        
        pf = ctk.CTkFrame(scroll, fg_color=Theme.BG_SURFACE, corner_radius=6)
        pf.pack(fill="x", padx=5, pady=3)
        
        row1 = ctk.CTkFrame(pf, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row1, text="질량 (kg):", font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY).pack(side="left")
        self.mass_entry = ctk.CTkEntry(row1, width=80, placeholder_text="0.0")
        self.mass_entry.pack(side="left", padx=5)
        
        row2 = ctk.CTkFrame(pf, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(row2, text="무게중심 (m):", font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY).pack(side="left")
        self.com_x = ctk.CTkEntry(row2, width=60, placeholder_text="cx")
        self.com_x.pack(side="left", padx=2)
        self.com_y = ctk.CTkEntry(row2, width=60, placeholder_text="cy")
        self.com_y.pack(side="left", padx=2)
        self.com_z = ctk.CTkEntry(row2, width=60, placeholder_text="cz")
        self.com_z.pack(side="left", padx=2)
        
        ctk.CTkButton(pf, text="적용", width=60, height=28, fg_color=Theme.SUCCESS,
                       command=self._apply_payload).pack(pady=5)
        
        # ===== 2. TCP 설정 =====
        self._section(scroll, "🎯 TCP (Tool Center Point) 설정")
        
        tf = ctk.CTkFrame(scroll, fg_color=Theme.BG_SURFACE, corner_radius=6)
        tf.pack(fill="x", padx=5, pady=3)
        
        tcp_row = ctk.CTkFrame(tf, fg_color="transparent")
        tcp_row.pack(fill="x", padx=10, pady=5)
        
        self.tcp_entries = []
        for label in ["X", "Y", "Z", "Rx", "Ry", "Rz"]:
            ctk.CTkLabel(tcp_row, text=f"{label}:", font=Theme.font(size=10), text_color=Theme.TEXT_SECONDARY).pack(side="left")
            e = ctk.CTkEntry(tcp_row, width=55, placeholder_text="0.0")
            e.pack(side="left", padx=2)
            self.tcp_entries.append(e)
        
        tcp_btns = ctk.CTkFrame(tf, fg_color="transparent")
        tcp_btns.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(tcp_btns, text="적용", width=60, height=28, fg_color=Theme.SUCCESS,
                       command=self._apply_tcp).pack(side="left", padx=3)
        ctk.CTkButton(tcp_btns, text="초기화", width=60, height=28, fg_color=Theme.DANGER,
                       command=self._reset_tcp).pack(side="left", padx=3)
        ctk.CTkButton(tcp_btns, text="현재값 읽기", width=80, height=28, fg_color="#1565C0",
                       command=self._read_current_tcp).pack(side="left", padx=3)
        
        # ===== 3. 작업공간 제한 =====
        self._section(scroll, "🚧 작업 공간 제한 (Safety Zone)")
        
        wf = ctk.CTkFrame(scroll, fg_color=Theme.BG_SURFACE, corner_radius=6)
        wf.pack(fill="x", padx=5, pady=3)
        
        min_row = ctk.CTkFrame(wf, fg_color="transparent")
        min_row.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(min_row, text="최소값 (m):", font=Theme.font(size=10), text_color=Theme.TEXT_SECONDARY).pack(side="left")
        self.ws_min = []
        for label in ["X_min", "Y_min", "Z_min"]:
            e = ctk.CTkEntry(min_row, width=65, placeholder_text=label)
            e.pack(side="left", padx=2)
            self.ws_min.append(e)
        
        max_row = ctk.CTkFrame(wf, fg_color="transparent")
        max_row.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(max_row, text="최대값 (m):", font=Theme.font(size=10), text_color=Theme.TEXT_SECONDARY).pack(side="left")
        self.ws_max = []
        for label in ["X_max", "Y_max", "Z_max"]:
            e = ctk.CTkEntry(max_row, width=65, placeholder_text=label)
            e.pack(side="left", padx=2)
            self.ws_max.append(e)
        
        ws_btns = ctk.CTkFrame(wf, fg_color="transparent")
        ws_btns.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(ws_btns, text="활성화", width=60, height=28, fg_color=Theme.WARNING,
                       command=lambda: self._apply_workspace(True)).pack(side="left", padx=3)
        ctk.CTkButton(ws_btns, text="비활성화", width=70, height=28, fg_color=Theme.BG_SURFACE,
                       command=lambda: self._apply_workspace(False)).pack(side="left", padx=3)
        
        # ===== 4. 임피던스 제어 =====
        self._section(scroll, "🧲 임피던스 제어 (Force Compliance)")
        
        imp_f = ctk.CTkFrame(scroll, fg_color=Theme.BG_SURFACE, corner_radius=6)
        imp_f.pack(fill="x", padx=5, pady=3)
        
        s_row = ctk.CTkFrame(imp_f, fg_color="transparent")
        s_row.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(s_row, text="강성 (N/m):", font=Theme.font(size=10), text_color=Theme.TEXT_SECONDARY).pack(side="left")
        self.stiffness_entries = []
        for ax in ["Kx", "Ky", "Kz"]:
            e = ctk.CTkEntry(s_row, width=55, placeholder_text=ax)
            e.insert(0, "1000")
            e.pack(side="left", padx=2)
            self.stiffness_entries.append(e)
        
        d_row = ctk.CTkFrame(imp_f, fg_color="transparent")
        d_row.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(d_row, text="감쇠 (Ns/m):", font=Theme.font(size=10), text_color=Theme.TEXT_SECONDARY).pack(side="left")
        self.damping_entries = []
        for ax in ["Dx", "Dy", "Dz"]:
            e = ctk.CTkEntry(d_row, width=55, placeholder_text=ax)
            e.insert(0, "50")
            e.pack(side="left", padx=2)
            self.damping_entries.append(e)
        
        imp_btns = ctk.CTkFrame(imp_f, fg_color="transparent")
        imp_btns.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(imp_btns, text="파라미터 적용", width=90, height=28, fg_color="#6A1B9A",
                       command=self._apply_impedance).pack(side="left", padx=3)
        ctk.CTkButton(imp_btns, text="임피던스 ON", width=80, height=28, fg_color=Theme.SUCCESS,
                       command=lambda: RobotControlUseCase.start_impedance_mode(self._selected_robot_name())).pack(side="left", padx=3)
        ctk.CTkButton(imp_btns, text="임피던스 OFF", width=80, height=28, fg_color=Theme.DANGER,
                       command=lambda: RobotControlUseCase.stop_impedance_mode(self._selected_robot_name())).pack(side="left", padx=3)
        
        # ===== 5. 사용자 변수 =====
        self._section(scroll, "📝 사용자 변수")
        
        vf = ctk.CTkFrame(scroll, fg_color=Theme.BG_SURFACE, corner_radius=6)
        vf.pack(fill="x", padx=5, pady=3)
        
        var_row = ctk.CTkFrame(vf, fg_color="transparent")
        var_row.pack(fill="x", padx=10, pady=5)
        self.var_name_entry = ctk.CTkEntry(var_row, width=80, placeholder_text="변수명")
        self.var_name_entry.pack(side="left", padx=2)
        self.var_op_combo = ctk.CTkComboBox(var_row, values=["=", "+=", "-=", "*=", "/="], width=60)
        self.var_op_combo.set("=")
        self.var_op_combo.pack(side="left", padx=2)
        self.var_val_entry = ctk.CTkEntry(var_row, width=80, placeholder_text="값")
        self.var_val_entry.pack(side="left", padx=2)
        ctk.CTkButton(var_row, text="실행", width=50, height=28, fg_color=Theme.SUCCESS,
                       command=self._apply_variable).pack(side="left", padx=3)
        
        self.var_display = ctk.CTkLabel(vf, text="변수 없음", font=Theme.font(size=10), 
                                         text_color=Theme.TEXT_SECONDARY, wraplength=400)
        self.var_display.pack(padx=10, pady=5)
        self._refresh_variables()
    
    def _section(self, parent, title):
        ctk.CTkLabel(parent, text=title, font=Theme.font(size=13, weight="bold"),
                     text_color=Theme.TEXT_PRIMARY).pack(anchor="w", padx=5, pady=(10, 2))
    
    def _apply_payload(self):
        try:
            mass = float(self.mass_entry.get() or 0)
            cx = float(self.com_x.get() or 0)
            cy = float(self.com_y.get() or 0)
            cz = float(self.com_z.get() or 0)
            RobotControlUseCase.set_payload(mass, [cx, cy, cz], self._selected_robot_name())
        except ValueError:
            print(">> [설정] 숫자를 입력하세요.")
    
    def _apply_tcp(self):
        try:
            tcp = [float(e.get() or 0) for e in self.tcp_entries]
            RobotControlUseCase.set_tcp(tcp, self._selected_robot_name())
        except ValueError:
            print(">> [설정] 숫자를 입력하세요.")
    
    def _reset_tcp(self):
        RobotControlUseCase.reset_tcp(self._selected_robot_name())
        for e in self.tcp_entries:
            e.delete(0, "end")
            e.insert(0, "0.0")
    
    def _read_current_tcp(self):
        p = RobotControlUseCase.get_task_pos(self._selected_robot_name())
        if p and len(p) >= 6:
            for i, e in enumerate(self.tcp_entries):
                e.delete(0, "end")
                e.insert(0, f"{p[i]:.4f}")
    
    def _apply_workspace(self, enable):
        try:
            min_pos = [float(e.get() or -1.0) for e in self.ws_min]
            max_pos = [float(e.get() or 1.0) for e in self.ws_max]
            RobotControlUseCase.set_workspace_limit(min_pos, max_pos, enable, self._selected_robot_name())
        except ValueError:
            print(">> [설정] 숫자를 입력하세요.")
    
    def _apply_impedance(self):
        try:
            stiffness = [float(e.get() or 1000) for e in self.stiffness_entries]
            stiffness += [100, 100, 100]  # 회전축 기본값
            damping = [float(e.get() or 50) for e in self.damping_entries]
            damping += [10, 10, 10]
            RobotControlUseCase.set_impedance(stiffness, damping, self._selected_robot_name())
        except ValueError:
            print(">> [설정] 숫자를 입력하세요.")
    
    def _apply_variable(self):
        name = self.var_name_entry.get().strip()
        op = self.var_op_combo.get()
        try:
            val = float(self.var_val_entry.get() or 0)
        except:
            val = 0.0
        if name:
            RobotControlUseCase.math_operation(name, op, val)
            self._refresh_variables()
    
    def _refresh_variables(self):
        vars_dict = RobotControlUseCase.get_all_variables()
        if vars_dict:
            txt = " | ".join([f"{k}={v}" for k, v in vars_dict.items()])
            self.var_display.configure(text=txt)
        else:
            self.var_display.configure(text="변수 없음")
