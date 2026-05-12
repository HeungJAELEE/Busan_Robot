"""
페이로드 자동 추정 마법사 — 로봇을 여러 자세로 이동시켜 자동으로 툴 무게/무게중심 계산.
"""
import customtkinter as ctk
import threading
import time
from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
from presentation.ui.theme import Theme


class AutoPayloadDialog(ctk.CTkToplevel):
    """페이로드 자동 추정 마법사."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("⚖️ 페이로드 자동 추정")
        self.geometry("450x400")
        self.configure(fg_color=Theme.BG_BASE)
        self.grab_set()
        
        self._running = False
        self._step = 0
        self._ft_samples = []
        
        self._build_ui()
    
    def _build_ui(self):
        ctk.CTkLabel(self, text="⚖️ 페이로드 자동 추정 마법사", 
                     font=Theme.font(size=16, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(pady=15)
        
        info = ctk.CTkFrame(self, fg_color=Theme.BG_SURFACE, corner_radius=6)
        info.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(info, text="로봇이 자동으로 3가지 자세를 취하며\n"
                                "F/T 센서 데이터를 수집하여 부착된 툴의\n"
                                "무게(kg)와 무게중심(m)을 자동 계산합니다.",
                     font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY,
                     justify="left").pack(padx=15, pady=10)
        
        # 진행 상태
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=10)
        
        self.steps = []
        step_labels = [
            "1️⃣ 자세 1: 수직 하향 (Z-)",
            "2️⃣ 자세 2: 45° 기울임",
            "3️⃣ 자세 3: 수평 (Y 방향)",
            "📊 계산 및 적용"
        ]
        for label in step_labels:
            lbl = ctk.CTkLabel(self.progress_frame, text=f"⬜ {label}", 
                               font=Theme.font(size=11), text_color="#607D8B")
            lbl.pack(anchor="w", padx=10, pady=2)
            self.steps.append(lbl)
        
        # 결과
        self.result_frame = ctk.CTkFrame(self, fg_color=Theme.BG_SURFACE, corner_radius=6)
        self.result_frame.pack(fill="x", padx=15, pady=10)
        
        self.mass_lbl = ctk.CTkLabel(self.result_frame, text="질량: — kg", 
                                      font=Theme.font(size=13, weight="bold"), text_color=Theme.WARNING)
        self.mass_lbl.pack(pady=5)
        self.com_lbl = ctk.CTkLabel(self.result_frame, text="무게중심: [—, —, —] m", 
                                     font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY)
        self.com_lbl.pack(pady=3)
        
        # 버튼
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=10)
        
        self.start_btn = ctk.CTkButton(btn_frame, text="▶ 측정 시작", width=120, height=36,
                                        fg_color=Theme.SUCCESS, hover_color="#1B5E20",
                                        font=Theme.font(size=12),
                                        command=self._start_estimation)
        self.start_btn.pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="닫기", width=80, height=36,
                       fg_color=Theme.BG_SURFACE, command=self.destroy).pack(side="right", padx=5)
    
    def _update_step(self, step_idx, status="done"):
        labels = [s.cget("text")[2:] for s in self.steps]
        if status == "done":
            self.steps[step_idx].configure(text=f"✅ {labels[step_idx]}", text_color=Theme.SUCCESS)
        elif status == "running":
            self.steps[step_idx].configure(text=f"🔄 {labels[step_idx]}", text_color=Theme.WARNING)
        elif status == "error":
            self.steps[step_idx].configure(text=f"❌ {labels[step_idx]}", text_color="#FF5252")
    
    def _start_estimation(self):
        if self._running:
            return
        self._running = True
        self.start_btn.configure(state="disabled", text="측정 중...")
        threading.Thread(target=self._estimation_routine, daemon=True).start()
    
    def _estimation_routine(self):
        """
        자동 추정 루틴:
        1. 3가지 자세에서 F/T 센서 데이터 수집
        2. 무게(mg) = F/g, 무게중심 = 토크/힘 으로 계산
        """
        GRAVITY = 9.81
        ft_readings = []
        
        # 측정용 자세 (관절 각도)
        poses = [
            [0, 0, -90, 0, -90, 0],     # 수직 하향
            [0, -30, -60, 0, -90, 0],    # 45° 기울임
            [0, 0, -90, 0, 0, 0],        # 수평
        ]
        
        try:
            for i, pose in enumerate(poses):
                self._update_step(i, "running")
                
                # 자세 이동
                RobotControlUseCase.move_to_joint(pose)
                RobotControlUseCase.wait_for_move_finish(30.0)
                time.sleep(1.0)  # 안정화 대기
                
                # F/T 데이터 수집 (10회 평균)
                samples = []
                for _ in range(10):
                    ft = RobotControlUseCase.get_ft_sensor()
                    if ft and len(ft) >= 6:
                        samples.append(ft)
                    time.sleep(0.1)
                
                if samples:
                    avg = [sum(s[j] for s in samples) / len(samples) for j in range(6)]
                    ft_readings.append(avg)
                    self._update_step(i, "done")
                else:
                    self._update_step(i, "error")
                    self._running = False
                    self.start_btn.configure(state="normal", text="▶ 측정 시작")
                    return
            
            # 계산
            self._update_step(3, "running")
            
            if ft_readings:
                # 수직 하향 자세에서의 Fz로 질량 계산
                fz = abs(ft_readings[0][2])  # Z축 힘
                mass = fz / GRAVITY
                
                # 토크/힘으로 무게중심 추정 (단순화)
                fx_avg = sum(r[0] for r in ft_readings) / len(ft_readings)
                fy_avg = sum(r[1] for r in ft_readings) / len(ft_readings)
                tx_avg = sum(r[3] for r in ft_readings) / len(ft_readings)
                ty_avg = sum(r[4] for r in ft_readings) / len(ft_readings)
                
                if fz > 0.1:
                    cx = ty_avg / (mass * GRAVITY) if mass > 0.01 else 0.0
                    cy = -tx_avg / (mass * GRAVITY) if mass > 0.01 else 0.0
                    cz = 0.0  # Z 방향은 추가 자세가 필요
                else:
                    cx = cy = cz = 0.0
                
                self.mass_lbl.configure(text=f"질량: {mass:.3f} kg")
                self.com_lbl.configure(text=f"무게중심: [{cx:.4f}, {cy:.4f}, {cz:.4f}] m")
                
                # 자동 적용
                RobotControlUseCase.set_payload(mass, [cx, cy, cz])
                self._update_step(3, "done")
                print(f">> [자동추정] 질량={mass:.3f}kg, 무게중심=[{cx:.4f}, {cy:.4f}, {cz:.4f}]")
            
        except Exception as e:
            print(f">> [자동추정 에러] {e}")
            self._update_step(3, "error")
        
        self._running = False
        self.start_btn.configure(state="normal", text="▶ 재측정")
