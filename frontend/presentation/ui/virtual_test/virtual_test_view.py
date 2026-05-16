import datetime
import json
import os
import queue
import threading
import time
import tkinter as tk
import tkinter.filedialog as fd

import customtkinter as ctk

from core.domains.robot.communication.client_manager import robot_manager
from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
from presentation.ui.robot_hmi.robot_hmi_view import ProgramTreeEditor
from presentation.ui.theme import Theme


class VirtualTestRecorder:
    """Asynchronous MySQL writer for robot diagnostic collection sessions."""

    def __init__(self):
        self.conn = None
        self.queue = queue.Queue(maxsize=50000)
        self.worker = None
        self.running = False
        self.lock = threading.Lock()
        self.last_error = ""

    def is_connected(self):
        return self.conn is not None

    def connect(self, host, port, user, password, database):
        try:
            import pymysql
            conn = pymysql.connect(
                host=host,
                port=int(port),
                user=user,
                password=password,
                database=database,
                charset="utf8mb4",
                autocommit=True,
                connect_timeout=5,
            )
            self.conn = conn
            self._ensure_tables()
            self._start_worker()
            self.last_error = ""
            return True, "MySQL 연결 성공"
        except Exception as exc:
            self.conn = None
            self.last_error = str(exc)
            return False, f"MySQL 연결 실패: {exc}"

    def _ensure_tables(self):
        queries = [
            """
            CREATE TABLE IF NOT EXISTS robot_virtual_test_sessions (
                session_id VARCHAR(96) PRIMARY KEY,
                robot_id VARCHAR(64) NOT NULL,
                program_path TEXT,
                target_cycles INT DEFAULT 0,
                sample_interval_ms INT DEFAULT 100,
                dry_run TINYINT DEFAULT 1,
                status VARCHAR(32) DEFAULT 'running',
                started_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                finished_at DATETIME(3) NULL,
                total_samples INT DEFAULT 0,
                note TEXT
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS robot_virtual_test_samples (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(96) NOT NULL,
                robot_id VARCHAR(64) NOT NULL,
                cycle_index INT DEFAULT 0,
                sample_index BIGINT DEFAULT 0,
                busy TINYINT DEFAULT 0,
                q1 DOUBLE, q2 DOUBLE, q3 DOUBLE, q4 DOUBLE, q5 DOUBLE, q6 DOUBLE,
                x DOUBLE, y DOUBLE, z DOUBLE, rx DOUBLE, ry DOUBLE, rz DOUBLE,
                tq1 DOUBLE, tq2 DOUBLE, tq3 DOUBLE, tq4 DOUBLE, tq5 DOUBLE, tq6 DOUBLE,
                captured_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                INDEX idx_virtual_session_cycle (session_id, cycle_index),
                INDEX idx_virtual_robot_time (robot_id, captured_at)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS robot_virtual_test_events (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(96) NOT NULL,
                robot_id VARCHAR(64) NOT NULL,
                event_type VARCHAR(64) NOT NULL,
                cycle_index INT DEFAULT 0,
                payload LONGTEXT,
                created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                INDEX idx_virtual_event_session (session_id, event_type)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """,
        ]
        with self.conn.cursor() as cursor:
            for query in queries:
                cursor.execute(query)

    def _start_worker(self):
        if self.worker and self.worker.is_alive():
            return
        self.running = True
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def _enqueue(self, kind, payload):
        if not self.conn:
            return
        try:
            self.queue.put_nowait((kind, dict(payload)))
        except queue.Full:
            self.last_error = "MySQL 기록 큐가 가득 찼습니다."

    def start_session(self, payload):
        self._enqueue("session_start", payload)

    def finish_session(self, payload):
        self._enqueue("session_finish", payload)

    def record_event(self, payload):
        self._enqueue("event", payload)

    def record_sample(self, payload):
        self._enqueue("sample", payload)

    def _ping(self):
        if self.conn:
            self.conn.ping(reconnect=True)

    @staticmethod
    def _six(values):
        result = list(values or [])[:6]
        while len(result) < 6:
            result.append(0.0)
        return [float(v or 0.0) for v in result]

    def _worker_loop(self):
        while self.running:
            try:
                kind, payload = self.queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._ping()
                if kind == "sample":
                    self._insert_sample(payload)
                elif kind == "event":
                    self._insert_event(payload)
                elif kind == "session_start":
                    self._upsert_session(payload)
                    self._insert_event({**payload, "event": "session_start"})
                elif kind == "session_finish":
                    self._finish_session(payload)
                    self._insert_event({**payload, "event": payload.get("event", "session_done")})
                self.last_error = ""
            except Exception as exc:
                self.last_error = str(exc)
            finally:
                self.queue.task_done()

    def _upsert_session(self, payload):
        query = """
            INSERT INTO robot_virtual_test_sessions
              (session_id, robot_id, program_path, target_cycles, sample_interval_ms, dry_run, status, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              robot_id=VALUES(robot_id),
              program_path=VALUES(program_path),
              target_cycles=VALUES(target_cycles),
              sample_interval_ms=VALUES(sample_interval_ms),
              dry_run=VALUES(dry_run),
              status=VALUES(status),
              note=VALUES(note)
        """
        values = (
            payload.get("session_id"),
            payload.get("robot_id"),
            payload.get("program_path", ""),
            int(payload.get("target_cycles", 0) or 0),
            int(payload.get("sample_interval_ms", 100) or 100),
            1 if payload.get("dry_run", True) else 0,
            payload.get("status", "running"),
            payload.get("note", ""),
        )
        with self.conn.cursor() as cursor:
            cursor.execute(query, values)

    def _finish_session(self, payload):
        query = """
            UPDATE robot_virtual_test_sessions
               SET status=%s, finished_at=NOW(3), total_samples=%s, note=%s
             WHERE session_id=%s
        """
        values = (
            payload.get("status", "completed"),
            int(payload.get("total_samples", 0) or 0),
            payload.get("note", ""),
            payload.get("session_id"),
        )
        with self.conn.cursor() as cursor:
            cursor.execute(query, values)

    def _insert_event(self, payload):
        query = """
            INSERT INTO robot_virtual_test_events
              (session_id, robot_id, event_type, cycle_index, payload)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (
            payload.get("session_id", ""),
            payload.get("robot_id", ""),
            payload.get("event", payload.get("event_type", "event")),
            int(payload.get("cycle_index", 0) or 0),
            json.dumps(payload, ensure_ascii=False),
        )
        with self.conn.cursor() as cursor:
            cursor.execute(query, values)

    def _insert_sample(self, payload):
        q = self._six(payload.get("q"))
        p = self._six(payload.get("p"))
        tq = self._six(payload.get("torque"))
        query = """
            INSERT INTO robot_virtual_test_samples
              (session_id, robot_id, cycle_index, sample_index, busy,
               q1, q2, q3, q4, q5, q6,
               x, y, z, rx, ry, rz,
               tq1, tq2, tq3, tq4, tq5, tq6)
            VALUES
              (%s, %s, %s, %s, %s,
               %s, %s, %s, %s, %s, %s,
               %s, %s, %s, %s, %s, %s,
               %s, %s, %s, %s, %s, %s)
        """
        values = (
            payload.get("session_id", ""),
            payload.get("robot_id", ""),
            int(payload.get("cycle_index", 0) or 0),
            int(payload.get("sample_index", 0) or 0),
            int(payload.get("busy", 0) or 0),
            *q,
            *p,
            *tq,
        )
        with self.conn.cursor() as cursor:
            cursor.execute(query, values)


class LocalVirtualTestStore:
    """Local JSONL writer for robot diagnostic collection sessions."""

    def __init__(self, base_dir=None):
        default_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs", "robot_diagnostic_data"))
        self.base_dir = base_dir or default_dir
        self.sessions = {}
        self.lock = threading.Lock()
        os.makedirs(self.base_dir, exist_ok=True)

    def set_base_dir(self, base_dir):
        if not base_dir:
            return
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def session_dir(self, session_id):
        safe_session = "".join(ch if ch.isalnum() or ch in ("_", "-", ".") else "_" for ch in str(session_id))
        return os.path.join(self.base_dir, safe_session)

    def start_session(self, payload):
        session_id = payload.get("session_id")
        if not session_id:
            return ""
        with self.lock:
            path = self.session_dir(session_id)
            os.makedirs(path, exist_ok=True)
            meta = dict(payload)
            meta["local_session_dir"] = path
            meta["local_started_at"] = datetime.datetime.now().isoformat(timespec="milliseconds")
            with open(os.path.join(path, "metadata.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            self.sessions[session_id] = path
            self.record_event({**payload, "event": "session_start", "local_session_dir": path})
            return path

    def finish_session(self, payload):
        session_id = payload.get("session_id")
        if not session_id:
            return
        with self.lock:
            path = self.sessions.get(session_id) or self.session_dir(session_id)
            os.makedirs(path, exist_ok=True)
            data = dict(payload)
            data["local_finished_at"] = datetime.datetime.now().isoformat(timespec="milliseconds")
            with open(os.path.join(path, "finish.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._append_jsonl(path, "events.jsonl", {**data, "event": data.get("event", "session_done")})
            self.sessions.pop(session_id, None)

    def record_event(self, payload):
        session_id = payload.get("session_id")
        if not session_id:
            return
        with self.lock:
            path = self.sessions.get(session_id) or self.session_dir(session_id)
            os.makedirs(path, exist_ok=True)
            self._append_jsonl(path, "events.jsonl", payload)

    def record_sample(self, payload):
        session_id = payload.get("session_id")
        if not session_id:
            return
        with self.lock:
            path = self.sessions.get(session_id) or self.session_dir(session_id)
            os.makedirs(path, exist_ok=True)
            self._append_jsonl(path, "samples.jsonl", payload)

    @staticmethod
    def _append_jsonl(path, filename, payload):
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with open(os.path.join(path, filename), "a", encoding="utf-8") as f:
            f.write(line + "\n")


class VirtualTestView:
    def __init__(self, parent_tab):
        self.parent = parent_tab
        self.parent.grid_columnconfigure(0, weight=0, minsize=320)
        self.parent.grid_columnconfigure(1, weight=1)
        self.parent.grid_columnconfigure(2, weight=0, minsize=360)
        self.parent.grid_rowconfigure(0, weight=1)

        self.recorder = VirtualTestRecorder()
        self.local_store = LocalVirtualTestStore()
        self.runners = {}
        self.runner_hosts = {}
        self.status_labels = {}
        self.cycle_labels = {}
        self.sample_labels = {}
        self.snapshot_labels = {}
        self.session_ids = {}
        self.session_samples = {}
        self.local_recording_enabled = True
        self.db_recording_enabled = True
        self.virtual_di_vars = {idx: tk.IntVar(value=0) for idx in range(32)}
        self.virtual_di_buttons = {}

        self._build_ui()
        self._poll_runner_status()

    def _build_ui(self):
        left = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(left, text="로봇 점검 Data수집", font=Theme.font(size=20, weight="bold", role="display"),
                     text_color=Theme.WARNING).pack(anchor="w", padx=16, pady=(16, 2))
        ctk.CTkLabel(left, text="점검 Dry Run + Torque/Position Recorder", font=Theme.font(size=12),
                     text_color=Theme.TEXT_SECONDARY).pack(anchor="w", padx=16, pady=(0, 12))

        settings = ctk.CTkFrame(left, fg_color=Theme.BG_BASE, corner_radius=8)
        settings.pack(fill="x", padx=14, pady=8)
        self.target_entry = self._entry_row(settings, "목표 반복", "100")
        self.interval_entry = self._entry_row(settings, "샘플(ms)", "100")

        di_box = ctk.CTkFrame(left, fg_color=Theme.BG_BASE, corner_radius=8)
        di_box.pack(fill="x", padx=14, pady=(4, 8))
        di_head = ctk.CTkFrame(di_box, fg_color="transparent")
        di_head.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(di_head, text="가상 DI 입력", font=Theme.font(size=13, weight="bold"),
                     text_color=Theme.INFO).pack(side="left")
        ctk.CTkButton(di_head, text="ALL ON", width=58, height=24,
                      command=lambda: self._set_all_virtual_di(1),
                      **Theme.get_button_style("success")).pack(side="right", padx=2)
        ctk.CTkButton(di_head, text="ALL OFF", width=64, height=24,
                      command=lambda: self._set_all_virtual_di(0),
                      **Theme.get_button_style("secondary")).pack(side="right", padx=2)
        ctk.CTkButton(di_head, text="대기 DI", width=64, height=24,
                      command=self._apply_wait_di_from_programs,
                      **Theme.get_button_style("primary")).pack(side="right", padx=2)

        grid = ctk.CTkFrame(di_box, fg_color="transparent")
        grid.pack(fill="x", padx=8, pady=(0, 10))
        for idx in range(32):
            btn = ctk.CTkButton(
                grid,
                text=f"DI{idx:02d}",
                width=54,
                height=24,
                font=Theme.font(size=10, weight="bold"),
                command=lambda i=idx: self._toggle_virtual_di(i),
            )
            btn.grid(row=idx // 4, column=idx % 4, padx=2, pady=2, sticky="ew")
            self.virtual_di_buttons[idx] = btn
            self._refresh_virtual_di_button(idx)
        for col in range(4):
            grid.grid_columnconfigure(col, weight=1)

        robot_box = ctk.CTkFrame(left, fg_color="transparent")
        robot_box.pack(fill="x", padx=12, pady=8)

        for robot in ["Robot A", "Robot B", "Robot C"]:
            row = ctk.CTkFrame(robot_box, fg_color=Theme.BG_BASE, corner_radius=8)
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=robot, width=72, anchor="w", font=Theme.font(size=13, weight="bold")).pack(side="left", padx=(10, 4), pady=9)
            status = ctk.CTkLabel(row, text="대기", width=64, text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=11))
            status.pack(side="left", padx=4)
            ctk.CTkButton(row, text="시작", width=58, height=28, command=lambda r=robot: self.start_robot_test(r),
                          **Theme.get_button_style("success")).pack(side="left", padx=3)
            ctk.CTkButton(row, text="정지", width=58, height=28, command=lambda r=robot: self.stop_robot_test(r),
                          **Theme.get_button_style("danger")).pack(side="left", padx=3)
            self.status_labels[robot] = status

        center = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, corner_radius=10)
        center.grid(row=0, column=1, sticky="nsew", padx=4, pady=10)
        ctk.CTkLabel(center, text="실시간 패턴 기록", font=Theme.font(size=18, weight="bold"),
                     text_color=Theme.INFO).pack(anchor="w", padx=16, pady=(16, 8))

        self.session_label = ctk.CTkLabel(center, text="세션 대기 중", anchor="w", justify="left",
                                          font=Theme.font(size=12), text_color=Theme.TEXT_SECONDARY)
        self.session_label.pack(fill="x", padx=16, pady=(0, 8))

        for robot in ["Robot A", "Robot B", "Robot C"]:
            card = ctk.CTkFrame(center, fg_color=Theme.BG_BASE, corner_radius=8)
            card.pack(fill="x", padx=16, pady=7)
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(10, 3))
            ctk.CTkLabel(top, text=robot, font=Theme.font(size=14, weight="bold")).pack(side="left")
            cycle = ctk.CTkLabel(top, text="Cycle 0/0", font=Theme.font(size=12), text_color=Theme.WARNING)
            cycle.pack(side="right")
            sample = ctk.CTkLabel(card, text="Samples 0", anchor="w", font=Theme.font(size=11),
                                  text_color=Theme.TEXT_SECONDARY)
            sample.pack(fill="x", padx=12)
            snapshot = ctk.CTkLabel(card, text="J: -\nP: -\nTQ: -", anchor="w", justify="left",
                                    font=ctk.CTkFont(family="Consolas", size=11), text_color=Theme.TEXT_PRIMARY)
            snapshot.pack(fill="x", padx=12, pady=(4, 10))
            self.cycle_labels[robot] = cycle
            self.sample_labels[robot] = sample
            self.snapshot_labels[robot] = snapshot

        right = ctk.CTkScrollableFrame(self.parent, fg_color=Theme.BG_SURFACE, corner_radius=10)
        right.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(right, text="저장 설정", font=Theme.font(size=18, weight="bold"),
                     text_color=Theme.WARNING).pack(anchor="w", padx=16, pady=(16, 8))

        self.local_enabled_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(right, text="로컬 JSONL 저장", variable=self.local_enabled_var,
                      progress_color=Theme.SUCCESS,
                      command=self._sync_local_recording_enabled).pack(anchor="w", padx=16, pady=(0, 6))

        local_box = ctk.CTkFrame(right, fg_color=Theme.BG_BASE, corner_radius=8)
        local_box.pack(fill="x", padx=14, pady=(4, 12))
        ctk.CTkButton(local_box, text="저장 위치 선택", command=self.choose_local_dir,
                      **Theme.get_button_style("secondary")).pack(fill="x", padx=10, pady=(10, 6))
        self.local_path_label = ctk.CTkLabel(local_box, text=self.local_store.base_dir, anchor="w", justify="left",
                                             font=ctk.CTkFont(family="Consolas", size=10),
                                             text_color=Theme.TEXT_SECONDARY, wraplength=300)
        self.local_path_label.pack(fill="x", padx=10, pady=(0, 10))

        self.db_enabled_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(right, text="MySQL 실시간 기록", variable=self.db_enabled_var,
                      progress_color=Theme.SUCCESS,
                      command=self._sync_db_recording_enabled).pack(anchor="w", padx=16, pady=(0, 8))

        form = ctk.CTkFrame(right, fg_color=Theme.BG_BASE, corner_radius=8)
        form.pack(fill="x", padx=14, pady=8)
        self.db_host_entry = self._entry_row(form, "Host", os.getenv("DB_HOST", "192.168.3.45"))
        self.db_port_entry = self._entry_row(form, "Port", os.getenv("DB_PORT", "3306"))
        self.db_user_entry = self._entry_row(form, "User", os.getenv("DB_USER", "guest"))
        self.db_pass_entry = self._entry_row(form, "Pass", os.getenv("DB_PASS", "guest1234"), show="*")
        self.db_name_entry = self._entry_row(form, "DB", os.getenv("DB_NAME", "faictory_mes"))

        ctk.CTkButton(right, text="DB 연결 확인", command=self.connect_db,
                      **Theme.get_button_style("primary")).pack(fill="x", padx=16, pady=(8, 4))
        self.db_status_label = ctk.CTkLabel(right, text="DB 미확인", anchor="w", justify="left",
                                            font=Theme.font(size=11), text_color=Theme.TEXT_SECONDARY)
        self.db_status_label.pack(fill="x", padx=16, pady=(2, 10))

        table_info = (
            "저장 테이블(내부명)\n"
            "robot_virtual_test_sessions\n"
            "robot_virtual_test_samples\n"
            "robot_virtual_test_events"
        )
        ctk.CTkLabel(right, text=table_info, anchor="w", justify="left",
                     font=ctk.CTkFont(family="Consolas", size=11),
                     text_color=Theme.TEXT_SECONDARY).pack(fill="x", padx=16, pady=8)

    def _entry_row(self, parent, label, default, show=None):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(row, text=label, width=82, anchor="w", font=Theme.font(size=12, weight="bold")).pack(side="left")
        entry = ctk.CTkEntry(row, height=30, show=show)
        entry.pack(side="left", fill="x", expand=True)
        entry.insert(0, str(default))
        return entry

    def connect_db(self):
        self._sync_db_recording_enabled()
        ok, msg = self.recorder.connect(
            self.db_host_entry.get().strip(),
            self.db_port_entry.get().strip(),
            self.db_user_entry.get().strip(),
            self.db_pass_entry.get(),
            self.db_name_entry.get().strip(),
        )
        self.db_status_label.configure(text=msg, text_color=Theme.SUCCESS if ok else Theme.DANGER)
        print(f">> [로봇 점검 Data수집] {msg}")
        return ok

    def choose_local_dir(self):
        selected = fd.askdirectory(
            title="로봇 점검 Data수집 로컬 저장 위치 선택",
            initialdir=self.local_store.base_dir,
        )
        if not selected:
            return
        self.local_store.set_base_dir(selected)
        self.local_path_label.configure(text=self.local_store.base_dir)
        print(f">> [로봇 점검 Data수집] 로컬 저장 위치: {self.local_store.base_dir}")

    def _sync_local_recording_enabled(self):
        try:
            self.local_recording_enabled = bool(self.local_enabled_var.get())
        except Exception:
            self.local_recording_enabled = True

    def _sync_db_recording_enabled(self):
        try:
            self.db_recording_enabled = bool(self.db_enabled_var.get())
        except Exception:
            self.db_recording_enabled = True

    def _get_runner(self, robot):
        runner = self.runners.get(robot)
        if runner:
            return runner
        host = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.runner_hosts[robot] = host
        runner = ProgramTreeEditor(host)
        runner.current_robot = robot
        self.runners[robot] = runner
        return runner

    def _target_cycles(self):
        try:
            return int(self.target_entry.get().strip())
        except (TypeError, ValueError):
            return 100

    def _sample_interval_ms(self):
        try:
            return max(20, int(self.interval_entry.get().strip()))
        except (TypeError, ValueError):
            return 100

    def _virtual_di_payload(self):
        return {str(idx): int(var.get() or 0) for idx, var in self.virtual_di_vars.items()}

    def _toggle_virtual_di(self, idx):
        var = self.virtual_di_vars[idx]
        var.set(0 if int(var.get() or 0) else 1)
        self._refresh_virtual_di_button(idx)

    def _set_all_virtual_di(self, value):
        for idx, var in self.virtual_di_vars.items():
            var.set(1 if value else 0)
            self._refresh_virtual_di_button(idx)

    def _frontend_root(self):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

    def _program_path_for_robot(self, robot):
        runner = self.runners.get(robot)
        if runner:
            return runner.get_current_program_path(robot)
        base_dir = self._frontend_root()
        cfg_path = os.path.join(base_dir, "user_programs", "_custom_paths.json")
        try:
            with open(cfg_path, "r", encoding="utf-8-sig") as f:
                custom_paths = json.load(f)
            if isinstance(custom_paths, dict) and custom_paths.get(robot):
                return custom_paths[robot]
        except Exception:
            pass
        return os.path.join(base_dir, "user_programs", robot.replace(" ", "_"), "program.json")

    def _collect_wait_di_from_program(self, path):
        required = {}
        if not path or not os.path.exists(path):
            return required
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as exc:
            print(f">> [로봇 점검 Data수집] 대기 DI 로드 실패: {path} / {exc}")
            return required
        for raw in data.get("program", []) or []:
            if not isinstance(raw, dict) or raw.get("type") != 28:
                continue
            for key in ("diList", "endtoolDiList"):
                for cond in raw.get(key, []) or []:
                    if not isinstance(cond, dict):
                        continue
                    try:
                        idx = int(cond.get("idx", 0))
                        value = 1 if int(cond.get("value", 1) or 0) else 0
                    except (TypeError, ValueError):
                        continue
                    if 0 <= idx < 32:
                        required[idx] = value
        return required

    def _apply_wait_di_from_programs(self):
        for idx, var in self.virtual_di_vars.items():
            var.set(0)
        required = {}
        sources = []
        for robot in ["Robot A", "Robot B", "Robot C"]:
            path = self._program_path_for_robot(robot)
            robot_required = self._collect_wait_di_from_program(path)
            if robot_required:
                sources.append(f"{robot}:{','.join(f'DI{k:02d}' for k in sorted(robot_required))}")
            required.update(robot_required)
        for idx, value in required.items():
            self.virtual_di_vars[idx].set(value)
        for idx in self.virtual_di_vars:
            self._refresh_virtual_di_button(idx)
        msg = ", ".join(sources) if sources else "대기 DI 없음"
        print(f">> [로봇 점검 Data수집] 대기 DI 프리셋 적용: {msg}")

    def _refresh_virtual_di_button(self, idx):
        btn = self.virtual_di_buttons.get(idx)
        if not btn:
            return
        is_on = bool(self.virtual_di_vars[idx].get())
        btn.configure(
            text=f"DI{idx:02d}",
            fg_color=Theme.SUCCESS if is_on else "#555555",
            hover_color=Theme.SUCCESS_HOVER if is_on else "#666666",
            text_color=Theme.TEXT_PRIMARY if is_on else Theme.TEXT_SECONDARY,
        )

    def start_robot_test(self, robot):
        info = robot_manager.get_robot_info(robot)
        if not info or info.get("instance") is None:
            self._set_status(robot, "미연결", Theme.DANGER)
            print(f">> [로봇 점검 Data수집] {robot} 연결이 필요합니다.")
            return

        self._sync_local_recording_enabled()
        self._sync_db_recording_enabled()
        if self.db_recording_enabled and not self.recorder.is_connected():
            self.connect_db()

        runner = self._get_runner(robot)
        if runner.is_execution_running():
            print(f">> [로봇 점검 Data수집] {robot} 수집이 이미 실행 중입니다.")
            return

        target_cycles = self._target_cycles()
        interval_ms = self._sample_interval_ms()
        safe_robot = robot.replace(" ", "_")
        session_id = f"RD_{safe_robot}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        program_path = runner.get_current_program_path(robot)
        payload = {
            "session_id": session_id,
            "robot_id": robot,
            "target_cycles": target_cycles,
            "sample_interval_ms": interval_ms,
            "program_path": program_path,
            "dry_run": True,
            "virtual_di_mode": "manual",
            "virtual_di": self._virtual_di_payload(),
            "status": "running",
            "note": "Page3 robot diagnostic data collection",
        }

        app = self.parent.winfo_toplevel()
        if hasattr(app, "start_virtual_test_tracking"):
            app.start_virtual_test_tracking(robot, session_id, target_cycles, interval_ms, program_path)
        local_path = ""
        if self.local_recording_enabled:
            local_path = self.local_store.start_session(payload)
            payload["local_session_dir"] = local_path
        if self.recorder.is_connected() and self.db_recording_enabled:
            self.recorder.start_session(payload)

        self.session_ids[robot] = session_id
        self.session_samples[session_id] = 0
        self._set_status(robot, "기록중", Theme.SUCCESS)
        self._set_cycle(robot, 0, target_cycles)
        self._set_samples(robot, 0)
        local_msg = f"\n로컬: {local_path}" if local_path else ""
        self.session_label.configure(text=f"최근 세션: {session_id}\n프로그램: {program_path}{local_msg}")

        print(f">> [로봇 점검 Data수집] {robot} Dry Run 시작: {target_cycles}회, {interval_ms}ms")
        runner.run_program_for_robot(robot, dry_run=True, virtual_test=payload)

    def stop_robot_test(self, robot):
        print(f">> [로봇 점검 Data수집] {robot} 정지 요청")
        RobotControlUseCase.request_stop(robot)
        runner = self.runners.get(robot)
        if runner:
            runner.current_robot = robot
            runner._stop_execution()
        app = self.parent.winfo_toplevel()
        if hasattr(app, "stop_virtual_test_tracking"):
            app.stop_virtual_test_tracking(robot, "stopped")
        self._set_status(robot, "정지", Theme.WARNING)

    def update_session_progress(self, robot, session_id, event, cycle_index, target_cycles, status):
        if event in ("cycle_start", "cycle_done", "session_done"):
            self._set_cycle(robot, cycle_index, target_cycles)
        if event == "session_done":
            total = self.session_samples.get(session_id, 0)
            finish_payload = {
                "session_id": session_id,
                "robot_id": robot,
                "event": event,
                "status": status,
                "cycle_index": cycle_index,
                "total_samples": total,
                "note": f"finished with status={status}",
            }
            if self.local_recording_enabled:
                self.local_store.finish_session(finish_payload)
            if self.recorder.is_connected() and self.db_recording_enabled:
                self.recorder.finish_session({
                    **finish_payload,
                })
            self._set_status(robot, "완료" if status == "completed" else status, Theme.SUCCESS if status == "completed" else Theme.WARNING)
        elif event == "cycle_start":
            self._set_status(robot, "기록중", Theme.SUCCESS)

    def update_robot_snapshot(self, robot, q, p, torque):
        def _fmt(values, digits=2):
            return ", ".join(f"{float(v):.{digits}f}" for v in list(values or [])[:6])
        label = self.snapshot_labels.get(robot)
        if label:
            label.configure(text=f"J: {_fmt(q, 2)}\nP: {_fmt(p, 3)}\nTQ: {_fmt(torque, 2)}")

    def record_virtual_sample(self, payload):
        session_id = payload.get("session_id", "")
        robot = payload.get("robot_id", "")
        if not session_id:
            return
        count = self.session_samples.get(session_id, 0) + 1
        self.session_samples[session_id] = count
        payload["sample_index"] = count
        if self.local_recording_enabled:
            self.local_store.record_sample(payload)
        if self.recorder.is_connected() and self.db_recording_enabled:
            self.recorder.record_sample(payload)
        try:
            self.parent.after(0, lambda r=robot, c=count: self._set_samples(r, c))
        except Exception:
            pass

    def record_virtual_event(self, payload):
        if self.local_recording_enabled:
            self.local_store.record_event(payload)
        if self.recorder.is_connected() and self.db_recording_enabled:
            self.recorder.record_event(payload)

    def _set_status(self, robot, text, color):
        label = self.status_labels.get(robot)
        if label:
            try:
                label.configure(text=text, text_color=color)
            except Exception:
                pass

    def _set_cycle(self, robot, current, target):
        label = self.cycle_labels.get(robot)
        if label:
            total = "무한" if int(target or 0) <= 0 else str(target)
            label.configure(text=f"Cycle {int(current or 0)}/{total}")

    def _set_samples(self, robot, count):
        label = self.sample_labels.get(robot)
        if label:
            label.configure(text=f"Samples {int(count or 0)}")

    def _poll_runner_status(self):
        for robot, runner in list(self.runners.items()):
            if runner.is_execution_running():
                self._set_status(robot, "기록중", Theme.SUCCESS)
        try:
            self.parent.after(500, self._poll_runner_status)
        except Exception:
            pass
