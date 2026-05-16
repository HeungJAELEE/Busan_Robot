import customtkinter as ctk
import threading
import time
import sys
import os
import queue
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from presentation.ui.robot_hmi.robot_hmi_view import RobotHmiView
from presentation.ui.digital_twin.digital_twin_view import DigitalTwinView
from presentation.ui.virtual_test.virtual_test_view import VirtualTestView
from presentation.ui.ai_teaching.ai_teaching_view import AITeachingView
from core.domains.robot.communication.client_manager import robot_manager
from infrastructure.mqtt.mqtt_manager import MqttManager
from core.service_manager import service_mgr
from presentation.ui.theme import Theme

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class PrintLogger:
    def __init__(self, msg_queue):
        self.msg_queue = msg_queue
    def write(self, text):
        if text.strip() or text == '\n':
            self.msg_queue.put(text)
    def flush(self): pass
    def isatty(self):
        return False

class ModernContyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Indy7 Command Center (DDD Architecture)")
        self.geometry("1400x900")
        
        # MQTT 브로커 인스턴스 (서비스 관리 패널에서 ON 할 때 연결됨)
        self.mqtt_broker = MqttManager(client_id="hmi_main")
        
        self.log_queue = queue.Queue()
        self._poll_log_queue()
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        Theme.apply_window_style(self)
        
        # 상단 네비게이션 (헤더)
        self.header = ctk.CTkFrame(self, height=60, fg_color=Theme.BG_BASE, corner_radius=0)
        self.header.grid(row=0, column=0, sticky="ew")
        
        # 좌측 상단 로고
        ctk.CTkLabel(self.header, text="⚡ INDY7 COMMAND CENTER", font=Theme.font(size=20, weight="bold", role="display"), text_color=Theme.TEXT_PRIMARY).pack(side="left", padx=20)
        
        # 중앙 페이지 탭 버튼
        tab_container = ctk.CTkFrame(self.header, fg_color="transparent")
        tab_container.pack(side="left", expand=True)
        
        # 활성/비활성 스타일 정의
        self.style_active = {"fg_color": Theme.ACCENT_PRIMARY, "text_color": Theme.TEXT_PRIMARY, "hover_color": Theme.ACCENT_HOVER}
        self.style_inactive = {"fg_color": "transparent", "text_color": Theme.TEXT_SECONDARY, "hover_color": Theme.BG_SURFACE}
        
        self.btn_page1 = ctk.CTkButton(tab_container, text="[Page 1] Auto / Monitor Mode", corner_radius=15, command=lambda: self.switch_page(1), **self.style_inactive)
        self.btn_page1.pack(side="left", padx=5)
        
        self.btn_page2 = ctk.CTkButton(tab_container, text="[Page 2] Setting / Teaching Mode", corner_radius=15, command=lambda: self.switch_page(2), **self.style_active)
        self.btn_page2.pack(side="left", padx=5)

        self.btn_page3 = ctk.CTkButton(tab_container, text="[Page 3] 로봇 점검 Data수집", corner_radius=15, command=lambda: self.switch_page(3), **self.style_inactive)
        self.btn_page3.pack(side="left", padx=5)

        self.btn_page4 = ctk.CTkButton(tab_container, text="[Page 4] AI Teaching", corner_radius=15, command=lambda: self.switch_page(4), **self.style_inactive)
        self.btn_page4.pack(side="left", padx=5)
        
        # 우측 연결 버튼
        self.conn_btn = ctk.CTkButton(self.header, text="로봇 통신 연결", fg_color=Theme.SUCCESS, command=self.toggle_connection)
        self.conn_btn.pack(side="right", padx=20)
        
        # 서비스 ON/OFF 토글 버튼
        svc_btn = ctk.CTkButton(self.header, text="🔌 서비스 관리", fg_color=Theme.ACCENT_SECONDARY, hover_color=Theme.ACCENT_HOVER, command=self._toggle_service_panel, width=120)
        svc_btn.pack(side="right", padx=5)
        
        # 하단 터미널
        self.terminal = ctk.CTkTextbox(self, height=150, fg_color=Theme.BG_SURFACE, text_color=Theme.SUCCESS, font=ctk.CTkFont(family="Consolas", size=13))
        self.terminal.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        sys.stdout = PrintLogger(self.log_queue)
        
        # ── 서비스 관리 패널 (토글로 접기/펼치기) ──
        self._svc_panel_visible = False
        self.svc_panel = ctk.CTkFrame(self, fg_color=Theme.BG_SURFACE, corner_radius=10, height=60)
        # 처음에는 숨김
        self.svc_toggle_buttons = {}
        self._build_service_panel()
        
        # 페이지 컨테이너
        self.pages_container = ctk.CTkFrame(self, fg_color="transparent")
        self.pages_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.pages_container.grid_columnconfigure(0, weight=1)
        self.pages_container.grid_rowconfigure(0, weight=1)
        
        # Page 1 (Digital Twin)
        self.page1_frame = ctk.CTkFrame(self.pages_container, fg_color="transparent")
        self.page1_frame.grid(row=0, column=0, sticky="nsew")
        self.dt_view = DigitalTwinView(self.page1_frame)
        
        # Page 2 (HMI)
        self.page2_frame = ctk.CTkFrame(self.pages_container, fg_color="transparent")
        self.page2_frame.grid(row=0, column=0, sticky="nsew")
        self.hmi_view = RobotHmiView(self.page2_frame, on_back=lambda: self.switch_page(1))

        # Page 3 (Virtual Dry Run / DB Recorder)
        self.page3_frame = ctk.CTkFrame(self.pages_container, fg_color="transparent")
        self.page3_frame.grid(row=0, column=0, sticky="nsew")
        self.virtual_test_view = VirtualTestView(self.page3_frame)

        # Page 4 (AI Natural Language / Voice Teaching)
        self.page4_frame = ctk.CTkFrame(self.pages_container, fg_color="transparent")
        self.page4_frame.grid(row=0, column=0, sticky="nsew")
        self.ai_teaching_view = AITeachingView(self.page4_frame)
        
        # 로봇 기본 설정 (연결은 하지 않음!)
        robot_manager.add_robot("Robot A", "192.168.3.7")
        robot_manager.add_robot("Robot B", "192.168.3.6")
        robot_manager.add_robot("Robot C", "192.168.3.5")
        
        # 프로그램 실행 중 폴링 일시중지 플래그
        self._program_running = False
        self._program_running_robots = set()
        self._virtual_test_sessions = {}
        self._virtual_last_sample_ts = {}
        self._virtual_snapshot_last_ts = {}
        
        # 기본 페이지 설정
        self.active_page = 2
        self.switch_page(2)
        
        # 폴링 스레드 — 연결된 로봇이면 항상 좌표 수집
        threading.Thread(target=self._poll_loop, daemon=True).start()
        
        # 서비스 상태 UI 동기화 루프
        self._poll_service_status()
        
    def _poll_log_queue(self):
        try:
            while True:
                text = self.log_queue.get_nowait()
                if hasattr(self, 'terminal') and self.terminal.winfo_exists():
                    self.terminal.insert(ctk.END, text)
                    self.terminal.see(ctk.END)
        except queue.Empty:
            pass
        finally:
            self.after(50, self._poll_log_queue)
            
    def switch_page(self, page_num):
        self.active_page = page_num
        if page_num == 1:
            self.btn_page1.configure(**self.style_active)
            self.btn_page2.configure(**self.style_inactive)
            self.btn_page3.configure(**self.style_inactive)
            self.btn_page4.configure(**self.style_inactive)
            self.page1_frame.tkraise()
        elif page_num == 2:
            self.btn_page1.configure(**self.style_inactive)
            self.btn_page2.configure(**self.style_active)
            self.btn_page3.configure(**self.style_inactive)
            self.btn_page4.configure(**self.style_inactive)
            self.page2_frame.tkraise()
        elif page_num == 3:
            self.btn_page1.configure(**self.style_inactive)
            self.btn_page2.configure(**self.style_inactive)
            self.btn_page3.configure(**self.style_active)
            self.btn_page4.configure(**self.style_inactive)
            self.page3_frame.tkraise()
        else:
            self.btn_page1.configure(**self.style_inactive)
            self.btn_page2.configure(**self.style_inactive)
            self.btn_page3.configure(**self.style_inactive)
            self.btn_page4.configure(**self.style_active)
            self.page4_frame.tkraise()

    def set_program_running(self, robot_name, is_running):
        """Track Page 1/Page 2 program execution without stopping telemetry polling."""
        if is_running:
            self._program_running_robots.add(robot_name)
        else:
            self._program_running_robots.discard(robot_name)
        self._program_running = bool(self._program_running_robots)

    def start_virtual_test_tracking(self, robot_name, session_id, target_cycles, sample_interval_ms, program_path):
        self._virtual_test_sessions[robot_name] = {
            "active": True,
            "session_id": session_id,
            "target_cycles": int(target_cycles or 0),
            "sample_interval_ms": max(20, int(sample_interval_ms or 100)),
            "program_path": program_path,
            "cycle_index": 0,
            "sample_index": 0,
            "status": "running",
        }
        self._virtual_last_sample_ts[robot_name] = 0.0

    def update_virtual_test_progress(self, robot_name, session_id, event, cycle_index, target_cycles, status):
        state = self._virtual_test_sessions.get(robot_name)
        if state and state.get("session_id") == session_id:
            state["cycle_index"] = int(cycle_index or 0)
            state["target_cycles"] = int(target_cycles or state.get("target_cycles", 0) or 0)
            state["status"] = status
            if event == "session_done":
                state["active"] = False
        payload = {
            "session_id": session_id,
            "robot_id": robot_name,
            "event": event,
            "status": status,
            "cycle_index": int(cycle_index or 0),
            "target_cycles": int(target_cycles or 0),
            "total_samples": int((state or {}).get("sample_index", 0) or 0),
            "sample_interval_ms": int((state or {}).get("sample_interval_ms", 100) or 100),
            "program_path": (state or {}).get("program_path", ""),
            "dry_run": True,
        }
        try:
            def _apply_virtual_progress(p=payload):
                if p.get("event") not in ("session_start", "session_done"):
                    self.virtual_test_view.record_virtual_event(p)
                self.virtual_test_view.update_session_progress(
                    robot_name, session_id, event, cycle_index, target_cycles, status
                )
            self.after(0, _apply_virtual_progress)
        except Exception:
            pass

    def stop_virtual_test_tracking(self, robot_name, status="stopped"):
        state = self._virtual_test_sessions.get(robot_name)
        if state:
            state["active"] = False
            state["status"] = status

    def _build_virtual_test_sample(self, robot_name, j_pos, t_pos, torque, robot_status):
        state = self._virtual_test_sessions.get(robot_name)
        if not state or not state.get("active"):
            return None
        now = time.time()
        interval_sec = float(state.get("sample_interval_ms", 100)) / 1000.0
        last = self._virtual_last_sample_ts.get(robot_name, 0.0)
        if now - last < interval_sec:
            return None
        self._virtual_last_sample_ts[robot_name] = now
        state["sample_index"] = int(state.get("sample_index", 0) or 0) + 1
        return {
            "session_id": state.get("session_id", ""),
            "robot_id": robot_name,
            "cycle_index": int(state.get("cycle_index", 0) or 0),
            "target_cycles": int(state.get("target_cycles", 0) or 0),
            "sample_index": state["sample_index"],
            "sample_interval_ms": int(state.get("sample_interval_ms", 100) or 100),
            "q": list(j_pos or [])[:6],
            "p": list(t_pos or [])[:6],
            "torque": list(torque or [])[:6],
            "busy": robot_status.get("busy", 0) if isinstance(robot_status, dict) else 0,
            "captured_at": time.time(),
        }
            
    def toggle_connection(self):
        def _bg():
            if self.active_page == 2:
                # Page 2: 현재 활성화된(Active) 로봇만 연결/해제
                active = robot_manager.get_active_robot_name()
                if not active:
                    return
                info = robot_manager.get_robot_info(active)
                is_connected = info and info.get("instance") is not None
                if is_connected:
                    print(f">> [통신] {active} 연결 해제 시도...")
                    robot_manager.disconnect(active)
                    print(f">> [성공] {active} 연결 해제 완료!")
                else:
                    print(f">> [통신] {active} 연결 시도...")
                    if robot_manager.connect(active):
                        print(f">> [성공] {active} 연결 완료!")
                    else:
                        print(f">> [실패] {active} 연결할 수 없습니다.")
            else:
                # Page 1: 전체 로봇 일괄 연결/해제
                any_connected = any(info.get("instance") for info in robot_manager.get_all_robots().values())
                if any_connected:
                    for name in list(robot_manager.get_all_robots().keys()):
                        print(f">> [통신] {name} 일괄 연결 해제 시도...")
                        robot_manager.disconnect(name)
                        print(f">> [성공] {name} 연결 해제 완료!")
                else:
                    for name, info in robot_manager.get_all_robots().items():
                        print(f">> [통신] {name} ({info['ip']}) 일괄 연결 시도...")
                        if robot_manager.connect(name):
                            print(f">> [성공] {name} 연결 완료!")
        threading.Thread(target=_bg, daemon=True).start()
        
    def _poll_loop(self):
        """
        백그라운드 폴링 루프.
        연결된 모든 로봇의 좌표를 항상 수집.
        
        IndyDCP 클라이언트 내부에 자체 lock(@socket_connect)이 있으므로,
        외부 lock을 추가하지 않는다. JOG/이동 명령이 실행되면
        IndyDCP 내부 lock에 의해 자동으로 폴링이 대기한 뒤 재개된다.
        """
        while True:
            try:
                active = robot_manager.get_active_robot_name()
                
                # 글로벌 연결 버튼 상태 동기화
                self._sync_conn_button(active)
                
                # 연결된 모든 로봇 좌표 수집 (IndyDCP 내부 lock이 충돌 방지)
                for name, info in robot_manager.get_all_robots().items():
                    inst = info.get("instance")
                    if inst is None:
                        continue
                    
                    try:
                        t_pos = inst.get_task_pos()
                        j_pos = inst.get_joint_pos()
                        
                        # 로봇 상태도 함께 수집 (movedone, busy, emergency 등)
                        robot_status = None
                        try:
                            robot_status = inst.get_robot_status()
                        except:
                            pass
                        
                        if t_pos and j_pos:
                            robot_manager.update_robot_state(name, j_pos, t_pos, robot_status)
                            
                            # 추가: 토크 값 수집 및 DB 전송
                            torque = [0]*6
                            try:
                                torque = inst.get_control_torque()
                            except:
                                pass
                                
                            status_data = {
                                "robot_id": name,
                                "q": j_pos,
                                "p": t_pos,
                                "torque": torque,
                                "busy": robot_status.get('busy', 0) if robot_status else 0
                            }
                            # DB Repository 직접 호출 대신 MQTT로 브로드캐스트
                            self.mqtt_broker.publish("robot/realtime", status_data)

                            vt_payload = self._build_virtual_test_sample(name, j_pos, t_pos, torque, robot_status)
                            if vt_payload:
                                try:
                                    self.virtual_test_view.record_virtual_sample(vt_payload)
                                    self.mqtt_broker.publish("robot/virtual_test_sample", vt_payload)
                                except Exception:
                                    pass
                            vt_state = self._virtual_test_sessions.get(name, {})
                            if self.active_page == 3 or vt_state.get("active"):
                                now = time.time()
                                last_snapshot = self._virtual_snapshot_last_ts.get(name, 0.0)
                                if now - last_snapshot >= 0.5:
                                    self._virtual_snapshot_last_ts[name] = now
                                    try:
                                        self.after(0, lambda n=name, q=j_pos, p=t_pos, tq=torque: self.virtual_test_view.update_robot_snapshot(n, q, p, tq))
                                    except Exception:
                                        pass
                            
                            # Page 1일 때만 3D 뷰어 UI 갱신
                            if self.active_page == 1:
                                t_str = f"X: {t_pos[0]:.2f}  Y: {t_pos[1]:.2f}  Z: {t_pos[2]:.2f}\nU: {t_pos[3]:.2f}  V: {t_pos[4]:.2f}  W: {t_pos[5]:.2f}"
                                j_str = f"J1: {j_pos[0]:.2f}  J2: {j_pos[1]:.2f}  J3: {j_pos[2]:.2f}\nJ4: {j_pos[3]:.2f}  J5: {j_pos[4]:.2f}  J6: {j_pos[5]:.2f}"
                                is_active = (name == active)
                                self.after(0, lambda t=t_str, j=j_str, p=t_pos, jp=j_pos, n=name, a=is_active: self._update_labels(t, j, p, jp, n, a))
                    except Exception:
                        pass
                        
            except Exception:
                pass
                
            time.sleep(0.1)
    
    def _sync_conn_button(self, active):
        """글로벌 연결 버튼의 텍스트/색상을 현재 상태에 동기화"""
        try:
            if self.active_page == 2:
                info = robot_manager.get_robot_info(active) if active else None
                is_connected = info and info.get("instance") is not None
            else:
                is_connected = any(info.get("instance") for info in robot_manager.get_all_robots().values())
            
            current_text = self.conn_btn.cget("text")
            if is_connected and current_text == "로봇 통신 연결":
                self.after(0, lambda: self.conn_btn.configure(text="로봇 연결 해제", fg_color=Theme.DANGER))
            elif not is_connected and current_text == "로봇 연결 해제":
                self.after(0, lambda: self.conn_btn.configure(text="로봇 통신 연결", fg_color=Theme.SUCCESS))
        except Exception:
            pass
            
    def _update_labels(self, t_str, j_str, t_pos, j_pos, name, is_active):
        # 현재 선택된 타겟 로봇일 경우에만 우측 텔레메트리 메인 패널 갱신
        if is_active:
            self.dt_view.task_label.configure(text=t_str)
            self.dt_view.joint_label.configure(text=j_str)
        
        # 각 로봇별 3D 뷰어 하단 미니 좌표 텍스트 갱신 (모든 로봇)
        if name in self.dt_view.robot_pos_labels:
            lbl = self.dt_view.robot_pos_labels[name]["label"]
            lbl.configure(text=f"{name} X: {t_pos[0]:.1f} Y: {t_pos[1]:.1f} Z: {t_pos[2]:.1f}")
        
        # 3D 뷰어 그래프 업데이트 (모든 연결된 로봇)
        self.dt_view.update_3d_graph(name, j_pos, t_pos)
    
    # ─────────────────────────────────────────
    # 서비스 관리 패널 (ON/OFF 토글)
    # ─────────────────────────────────────────
    
    def _build_service_panel(self):
        """서비스 토글 버튼들을 패널에 배치"""
        inner = ctk.CTkFrame(self.svc_panel, fg_color="transparent")
        inner.pack(fill="x", padx=15, pady=8)
        
        ctk.CTkLabel(inner, text="🔌 서비스 관리", font=Theme.font(size=14, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(side="left", padx=(0, 20))
        
        for key, svc in service_mgr.services.items():
            frame = ctk.CTkFrame(inner, fg_color="transparent")
            frame.pack(side="left", padx=8)
            
            indicator = ctk.CTkLabel(frame, text="⚪", font=ctk.CTkFont(size=12), width=20)
            indicator.pack(side="left")
            
            btn = ctk.CTkButton(
                frame,
                text=f"{svc.icon} {svc.name}",
                fg_color=Theme.BG_BASE,
                hover_color=Theme.ACCENT_HOVER,
                text_color=Theme.TEXT_SECONDARY,
                width=130, height=30,
                corner_radius=8,
                command=lambda k=key: self._on_service_toggle(k)
            )
            btn.pack(side="left", padx=3)
            
            self.svc_toggle_buttons[key] = {"btn": btn, "indicator": indicator}
    
    def _toggle_service_panel(self):
        """서비스 패널 접기/펼치기"""
        if self._svc_panel_visible:
            self.svc_panel.grid_forget()
            self._svc_panel_visible = False
        else:
            self.svc_panel.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
            self._svc_panel_visible = True
    
    def _on_service_toggle(self, key):
        """서비스 ON/OFF 토글"""
        is_running = service_mgr.toggle(key)
        svc = service_mgr.services[key]
        if is_running:
            print(f"▶️ [{svc.name}] 서비스 시작!")
        else:
            print(f"⏹ [{svc.name}] 서비스 중지!")
    
    def _poll_service_status(self):
        """500ms마다 서비스 상태를 UI에 반영"""
        try:
            for key, widgets in self.svc_toggle_buttons.items():
                svc = service_mgr.services[key]
                btn = widgets["btn"]
                indicator = widgets["indicator"]
                
                if svc.is_running:
                    indicator.configure(text="🟢")
                    btn.configure(fg_color=Theme.SUCCESS, text_color=Theme.TEXT_PRIMARY)
                else:
                    indicator.configure(text="🔴")
                    btn.configure(fg_color=Theme.BG_BASE, text_color=Theme.TEXT_SECONDARY)
        except Exception:
            pass
        self.after(500, self._poll_service_status)
            
if __name__ == "__main__":
    app = ModernContyApp()
    app.mainloop()
