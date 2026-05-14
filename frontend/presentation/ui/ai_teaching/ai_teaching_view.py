import datetime
import io
import json
import os
import re
import threading
import tkinter as tk
import wave

import customtkinter as ctk

from core.domains.robot.communication.client_manager import robot_manager
from core.domains.robot.use_cases.robot_control_usecase import RobotControlUseCase
from presentation.ui.theme import Theme


class AITeachingView:
    """Page 4: natural-language/voice-assisted robot teaching surface."""

    SAFE_MAX_STEP_MM = 5.0
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

    def __init__(self, parent_tab):
        self.parent = parent_tab
        self.parent.grid_columnconfigure(0, weight=0, minsize=330)
        self.parent.grid_columnconfigure(1, weight=1)
        self.parent.grid_columnconfigure(2, weight=0, minsize=360)
        self.parent.grid_rowconfigure(0, weight=1)
        self.pending_teach = None
        self.api_key_var = tk.StringVar(value=self._load_api_key())
        self._build_ui()

    def _build_ui(self):
        left = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(left, text="AI Voice Teaching", font=Theme.font(size=20, weight="bold", role="display"),
                     text_color=Theme.WARNING).pack(anchor="w", padx=16, pady=(16, 2))
        ctk.CTkLabel(left, text="Google AI Studio API + 안전 함수 호출", font=Theme.font(size=12),
                     text_color=Theme.TEXT_SECONDARY).pack(anchor="w", padx=16, pady=(0, 12))

        robot_box = ctk.CTkFrame(left, fg_color=Theme.BG_BASE, corner_radius=8)
        robot_box.pack(fill="x", padx=14, pady=8)
        ctk.CTkLabel(robot_box, text="대상 로봇", font=Theme.font(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(10, 4))
        self.robot_sel = ctk.CTkOptionMenu(robot_box, values=["Robot A", "Robot B", "Robot C"], width=160)
        self.robot_sel.pack(fill="x", padx=10, pady=(0, 10))
        self.robot_sel.set(robot_manager.get_active_robot_name() or "Robot A")

        key_box = ctk.CTkFrame(left, fg_color=Theme.BG_BASE, corner_radius=8)
        key_box.pack(fill="x", padx=14, pady=8)
        ctk.CTkLabel(key_box, text="Google AI Studio API Key", font=Theme.font(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(10, 4))
        self.api_entry = ctk.CTkEntry(key_box, textvariable=self.api_key_var, show="*", placeholder_text="GEMINI_API_KEY")
        self.api_entry.pack(fill="x", padx=10, pady=4)
        ctk.CTkButton(key_box, text="API Key 저장", command=self._save_api_key,
                      **Theme.get_button_style("secondary")).pack(fill="x", padx=10, pady=(4, 10))

        safety = ctk.CTkFrame(left, fg_color=Theme.BG_BASE, corner_radius=8)
        safety.pack(fill="x", padx=14, pady=8)
        self.pitch_x_entry = self._entry_row(safety, "제품 X pitch(mm)", "50")
        self.pitch_y_entry = self._entry_row(safety, "제품 Y pitch(mm)", "50")
        self.pitch_z_entry = self._entry_row(safety, "층 Z pitch(mm)", "50")
        self.approach_entry = self._entry_row(safety, "접근/후퇴(mm)", "50")
        self.voice_seconds_entry = self._entry_row(safety, "음성 녹음(sec)", "4")

        center = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, corner_radius=10)
        center.grid(row=0, column=1, sticky="nsew", padx=4, pady=10)
        ctk.CTkLabel(center, text="명령 입력", font=Theme.font(size=18, weight="bold"),
                     text_color=Theme.INFO).pack(anchor="w", padx=16, pady=(16, 8))

        self.command_box = ctk.CTkTextbox(center, height=140, fg_color=Theme.BG_BASE,
                                          text_color=Theme.TEXT_PRIMARY, font=Theme.font(size=14))
        self.command_box.pack(fill="x", padx=16, pady=(0, 10))

        btns = ctk.CTkFrame(center, fg_color="transparent")
        btns.pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(btns, text="실행", command=self.execute_command,
                      **Theme.get_button_style("success")).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btns, text="마이크 녹음", command=self.record_voice_command,
                      **Theme.get_button_style("primary")).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="현재 좌표 읽기", command=self.read_pose,
                      **Theme.get_button_style("secondary")).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="정지", command=self.stop_robot,
                      **Theme.get_button_style("danger")).pack(side="right", padx=6)

        self.log_box = ctk.CTkTextbox(center, fg_color=Theme.BG_BASE, text_color=Theme.TEXT_PRIMARY,
                                      font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.pack(fill="both", expand=True, padx=16, pady=(10, 16))

        right = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SURFACE, corner_radius=10)
        right.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(right, text="지원 명령", font=Theme.font(size=18, weight="bold"),
                     text_color=Theme.WARNING).pack(anchor="w", padx=16, pady=(16, 8))
        help_text = (
            "음성은 [마이크 녹음] 버튼 또는 macOS 받아쓰기로\n"
            "입력할 수 있습니다. 마이크 녹음은 API Key가 필요합니다.\n\n"
            "이동:\n"
            "- 1mm x축으로 이동\n"
            "- z축 2mm 올려\n"
            "- y축 -1mm 이동\n\n"
            "티칭:\n"
            "- 여기에 pick 위치 저장해\n"
            "- 여기에 place 위치 저장해\n"
            "- 2바이 2로 하고 4층이야\n"
            "- 제품 50x50x30 2x2 4층\n\n"
            "안전 제한:\n"
            "- 상대 이동 1회 최대 5mm\n"
            "- 현재 선택 로봇만 제어\n"
            "- 로봇 에러/충돌/busy면 차단"
        )
        ctk.CTkLabel(right, text=help_text, anchor="w", justify="left",
                     text_color=Theme.TEXT_SECONDARY, font=Theme.font(size=12)).pack(fill="x", padx=16, pady=8)

    def _entry_row(self, parent, label, default):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text=label, width=130, anchor="w", font=Theme.font(size=11, weight="bold")).pack(side="left")
        entry = ctk.CTkEntry(row, height=28)
        entry.insert(0, str(default))
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def _config_path(self):
        return os.path.join(os.path.expanduser("~"), ".indy7_hmi_ai_teaching.json")

    def _load_api_key(self):
        env_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if env_key:
            return env_key
        try:
            with open(self._config_path(), "r", encoding="utf-8") as f:
                return json.load(f).get("gemini_api_key", "")
        except Exception:
            return ""

    def _save_api_key(self):
        key = self.api_key_var.get().strip()
        try:
            with open(self._config_path(), "w", encoding="utf-8") as f:
                json.dump({"gemini_api_key": key}, f, ensure_ascii=False, indent=2)
            self._log("API Key를 사용자 홈 설정에 저장했습니다.")
        except Exception as exc:
            self._log(f"API Key 저장 실패: {exc}")

    def _selected_robot(self):
        robot = self.robot_sel.get() or "Robot A"
        robot_manager.set_active_robot(robot)
        return robot

    def _log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_box.insert(ctk.END, f"[{timestamp}] {message}\n")
        self.log_box.see(ctk.END)
        print(f">> [AI Teaching] {message}")

    def _log_async(self, message):
        self.parent.after(0, lambda: self._log(message))

    def execute_command(self):
        text = self.command_box.get("1.0", ctk.END).strip()
        if not text:
            return
        threading.Thread(target=self._execute_command_bg, args=(text,), daemon=True).start()

    def record_voice_command(self):
        threading.Thread(target=self._record_voice_bg, daemon=True).start()

    def _record_voice_bg(self):
        key = self.api_key_var.get().strip()
        if not key:
            self._log_async("마이크 음성 명령은 Google AI Studio API Key가 필요합니다.")
            return
        try:
            import sounddevice as sd
        except Exception as exc:
            self._log_async(f"마이크 녹음 패키지가 없습니다. pip install sounddevice 후 다시 시도하세요: {exc}")
            return

        sample_rate = 16000
        seconds = max(1.0, min(10.0, self._entry_float(self.voice_seconds_entry, 4)))
        try:
            self._log_async(f"{seconds:g}초 동안 말해주세요.")
            audio = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
            sd.wait()
            wav_bytes = self._to_wav_bytes(audio.tobytes(), sample_rate)
            action = self._parse_audio_with_gemini(wav_bytes)
            if not action:
                self._log_async("음성 명령을 해석하지 못했습니다.")
                return
            transcript = action.get("transcript") or "음성 명령"
            self.parent.after(0, lambda a=action, t=transcript: self._execute_action(a, t))
        except Exception as exc:
            self._log_async(f"마이크 음성 처리 실패: {exc}")

    def _execute_command_bg(self, text):
        action = self._parse_with_gemini(text) or self._parse_local(text)
        self.parent.after(0, lambda: self._execute_action(action, text))

    def _gemini_parse_prompt(self, command_text=None):
        base = (
            "Convert the Korean robot teaching command into compact JSON only. "
            "Allowed actions: move_relative, save_pick, save_place, set_pallet, read_pose, stop, unknown. "
            "Fields: action, transcript, axis, distance_mm, m, n, l, product_x_mm, product_y_mm, product_z_mm. "
            "Rules: never invent coordinates; if the user asks for a small move, set axis and distance_mm; "
            "if the user says pick/place save here, use save_pick/save_place; "
            "if the user answers pallet shape like 2x2 and 4 floors, use set_pallet. "
        )
        if command_text:
            return base + "Command: " + command_text
        return base + "Listen to the audio and return only the JSON command."

    def _parse_with_gemini(self, text):
        key = self.api_key_var.get().strip()
        if not key:
            return None
        try:
            from google import genai
            client = genai.Client(api_key=key)
            return self._generate_gemini_json(client, self._gemini_parse_prompt(text))
        except Exception as exc:
            self.parent.after(0, lambda: self._log(f"Gemini 해석 실패, 로컬 해석으로 전환: {exc}"))
            return None

    def _parse_audio_with_gemini(self, wav_bytes):
        key = self.api_key_var.get().strip()
        if not key:
            return None
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=key)
            return self._generate_gemini_json(client, [
                self._gemini_parse_prompt(),
                types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav"),
            ])
        except Exception as exc:
            self._log_async(f"Gemini 음성 해석 실패: {exc}")
            return None

    def _generate_gemini_json(self, client, contents):
        models = [self.GEMINI_MODEL]
        if self.GEMINI_MODEL != "gemini-2.5-flash":
            models.append("gemini-2.5-flash")
        last_exc = None
        for model in models:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config={"response_mime_type": "application/json"},
                )
                return json.loads(response.text)
            except Exception as exc:
                last_exc = exc
        raise last_exc

    def _parse_local(self, text):
        s = text.strip().lower()
        if self.pending_teach and self._contains_pallet_size(s):
            action = self._parse_pallet_size(s)
            action["action"] = "set_pallet"
            return action
        if "정지" in s or "멈춰" in s or "stop" in s:
            return {"action": "stop"}
        if "좌표" in s and ("읽" in s or "확인" in s or "현재" in s):
            return {"action": "read_pose"}
        if "pick" in s and "저장" in s:
            return {"action": "save_pick"}
        if "place" in s and "저장" in s:
            return {"action": "save_place"}
        move = self._parse_move(s)
        if move:
            return move
        return {"action": "unknown"}

    def _parse_move(self, s):
        amount_match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*(?:mm|미리|밀리)", s)
        axis = None
        for candidate in ("x", "y", "z"):
            if candidate in s or f"{candidate}축" in s:
                axis = candidate.upper()
                break
        if not amount_match or not axis:
            return None
        distance = float(amount_match.group(1))
        if axis == "Z" and any(word in s for word in ("내려", "아래", "down")):
            distance = -abs(distance)
        if any(word in s for word in ("마이너스", "음수", "minus")):
            distance = -abs(distance)
        return {"action": "move_relative", "axis": axis, "distance_mm": distance}

    def _contains_pallet_size(self, s):
        return bool(re.search(r"\d+\s*(?:바이|x|×|by)\s*\d+", s) or re.search(r"\d+\s*층", s))

    def _parse_pallet_size(self, s):
        product = re.search(r"제품\s*(\d+(?:\.\d+)?)\s*(?:x|×|by)\s*(\d+(?:\.\d+)?)(?:\s*(?:x|×|by)\s*(\d+(?:\.\d+)?))?", s)
        pallet_source = s
        if product:
            pallet_source = (s[:product.start()] + " " + s[product.end():]).strip()
        stack = re.search(r"(\d+)\s*(?:x|×|by)\s*(\d+)\s*(?:x|×|by)\s*(\d+)", pallet_source)
        grid = re.search(r"(\d+)\s*(?:바이|x|×|by)\s*(\d+)", pallet_source)
        layer = re.search(r"(\d+)\s*층", pallet_source)
        return {
            "m": int((stack or grid).group(1)) if (stack or grid) else 1,
            "n": int((stack or grid).group(2)) if (stack or grid) else 1,
            "l": int(layer.group(1)) if layer else int(stack.group(3)) if stack else 1,
            "product_x_mm": float(product.group(1)) if product else self._entry_float(self.pitch_x_entry, 50),
            "product_y_mm": float(product.group(2)) if product else self._entry_float(self.pitch_y_entry, 50),
            "product_z_mm": float(product.group(3)) if product and product.group(3) else self._entry_float(self.pitch_z_entry, 50),
        }

    def _execute_action(self, action, original_text):
        action_name = (action or {}).get("action", "unknown")
        if action_name == "move_relative":
            self._move_relative(action)
        elif action_name == "save_pick":
            self._capture_teach_point("pick")
        elif action_name == "save_place":
            self._capture_teach_point("place")
        elif action_name == "set_pallet":
            self._finish_pending_teach(action)
        elif action_name == "read_pose":
            self.read_pose()
        elif action_name == "stop":
            self.stop_robot()
        else:
            self._log(f"명령을 이해하지 못했습니다: {original_text}")

    def _move_relative(self, action):
        robot = self._selected_robot()
        axis = str(action.get("axis", "")).upper()
        try:
            distance = float(action.get("distance_mm", 0))
        except (TypeError, ValueError):
            self._log("이동 거리를 해석하지 못했습니다.")
            return
        if axis not in ("X", "Y", "Z"):
            self._log("상대 이동은 X/Y/Z 축만 허용합니다.")
            return
        if abs(distance) > self.SAFE_MAX_STEP_MM:
            self._log(f"안전 제한: 1회 이동은 최대 {self.SAFE_MAX_STEP_MM:g}mm입니다.")
            return
        ok = RobotControlUseCase.jog_axis(axis, distance, robot)
        self._log(f"{robot} {axis}축 {distance:g}mm 상대 이동 {'전송' if ok else '실패'}")

    def read_pose(self):
        robot = self._selected_robot()
        p = RobotControlUseCase.get_task_pos(robot)
        q = RobotControlUseCase.get_joint_pos(robot)
        self._log(f"{robot} P={self._fmt(p, 3)}")
        self._log(f"{robot} Q={self._fmt(q, 2)}")

    def stop_robot(self):
        robot = self._selected_robot()
        RobotControlUseCase.request_stop(robot)
        RobotControlUseCase.stop_robot(robot)
        self._log(f"{robot} 정지 요청 전송")

    def _capture_teach_point(self, kind):
        robot = self._selected_robot()
        p = RobotControlUseCase.get_task_pos(robot)
        q = RobotControlUseCase.get_joint_pos(robot)
        if not p or all(abs(float(v or 0.0)) < 1e-9 for v in p[:3]):
            self._log("현재 좌표를 읽지 못했습니다. 로봇 연결과 좌표 값을 확인하세요.")
            return
        self.pending_teach = {"kind": kind, "robot": robot, "p": p, "q": q}
        self._log(f"{robot} 현재 위치를 {kind.upper()} 후보로 잡았습니다: P={self._fmt(p, 3)}")
        self._log("제품 pitch와 팔레트 배열을 알려주세요. 예: 제품 50x50x30, 2바이 2로 하고 4층")

    def _finish_pending_teach(self, action):
        if not self.pending_teach:
            self._log("먼저 '여기에 pick 위치 저장해'처럼 기준 위치를 잡아주세요.")
            return
        data = dict(self.pending_teach)
        data.update({
            "m": max(1, int(action.get("m", 1) or 1)),
            "n": max(1, int(action.get("n", 1) or 1)),
            "l": max(1, int(action.get("l", 1) or 1)),
            "product_x_mm": float(action.get("product_x_mm", self._entry_float(self.pitch_x_entry, 50))),
            "product_y_mm": float(action.get("product_y_mm", self._entry_float(self.pitch_y_entry, 50))),
            "product_z_mm": float(action.get("product_z_mm", self._entry_float(self.pitch_z_entry, 50))),
        })
        path = self._append_teaching_node(data)
        self._log(f"{data['kind'].upper()} {data['m']}x{data['n']}x{data['l']} 티칭 노드를 저장했습니다.")
        self._log(f"저장 파일: {path}")
        self.pending_teach = None

    def _append_teaching_node(self, data):
        robot = data["robot"]
        path = self._program_path(robot)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        program = self._load_or_create_program(path)
        nodes = program.setdefault("program", [])
        config = self._ensure_config_node(nodes)
        self._ensure_variables_node(nodes)
        new_id = max([int(n.get("id", 0) or 0) for n in nodes] + [2]) + 1
        kind = data["kind"]
        node_type = 201 if kind == "pick" else 202
        pallet_id = f"AI_{kind.upper()}_{new_id}"
        m, n, l = data["m"], data["n"], data["l"]
        p_data = self._make_pallet_data(data, pallet_id)
        if m * n * l > 1:
            config.setdefault("palletInfo", []).append({
                "id": pallet_id,
                "name": pallet_id,
                "m": m,
                "n": n,
                "l": l,
                "points": p_data["points"],
            })
        target_type = 1 if m * n * l > 1 else 0
        approach_mm = self._entry_float(self.approach_entry, 50)
        node = {
            "id": new_id,
            "enable": True,
            "type": node_type,
            "pId": 0,
            "name": f"AI {kind.upper()} {m}x{n}x{l}",
            "toolId": 1,
            "sensName": "",
            "approach": self._approach_block(approach_mm, direction=0),
            "retract": self._approach_block(approach_mm, direction=1),
            "target": {
                "type": target_type,
                "boundary": {"velLevel": 5, "accLevel": 5},
                "pallet": {"palletId": pallet_id} if target_type == 1 else {},
                "point": {"q": data["q"], "p": data["p"]},
                "refFrame": {"type": 1, "tref": [0, 0, 0, 0, 0, 0]},
                "tcp": [0, 0, 0, 0, 0, 0],
            },
            "q": data["q"],
            "p": data["p"],
            "target_type": target_type,
            "p_data": p_data if target_type == 1 else {},
            "target_pallet_id": pallet_id if target_type == 1 else "",
            "target_pallet_name": pallet_id if target_type == 1 else "",
        }
        nodes.append(node)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(program, f, ensure_ascii=False, indent=4)
        return path

    def _program_path(self, robot):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        return os.path.join(base_dir, "user_programs", robot.replace(" ", "_"), "program.json")

    def _load_or_create_program(self, path):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("info", {"name": "ExportedProgram"})
                    data.setdefault("wpList", [])
                    data.setdefault("moveList", [])
                    data.setdefault("program", [])
                    return data
            except Exception as exc:
                self._log(f"기존 프로그램 로드 실패, 새 파일로 시작: {exc}")
        return {"info": {"name": "ExportedProgram"}, "wpList": [], "program": [], "moveList": []}

    def _ensure_config_node(self, nodes):
        config = next((n for n in nodes if n.get("type") == 999), None)
        if config is None:
            config = {
                "id": 1,
                "enable": True,
                "type": 999,
                "pId": 0,
                "toolInfo": [],
                "palletInfo": [],
                "visionInfo": {"useVision": False},
                "indyCareInfo": {},
                "conveyorConfigInfo": {"conveyorConfig": []},
                "collisionPolicy": {"policy": 0, "time": 2},
            }
            nodes.insert(0, config)
        config.setdefault("palletInfo", [])
        return config

    def _ensure_variables_node(self, nodes):
        var_node = next((n for n in nodes if n.get("type") == 2), None)
        if var_node is None:
            nodes.insert(1 if nodes else 0, {"id": 2, "enable": True, "type": 2, "pId": 0, "varList": []})

    def _make_pallet_data(self, data, pallet_id):
        p1 = [float(v or 0.0) for v in data["p"][:6]]
        q = [float(v or 0.0) for v in data["q"][:6]]
        unit = 1.0 if max(abs(v) for v in p1[:3]) > 10.0 else 0.001
        dx = float(data["product_x_mm"]) * unit * max(data["m"] - 1, 0)
        dy = float(data["product_y_mm"]) * unit * max(data["n"] - 1, 0)
        dz = float(data["product_z_mm"]) * unit * max(data["l"] - 1, 0)
        p2 = list(p1); p2[0] += dx
        p3 = list(p1); p3[1] += dy
        p4 = list(p1); p4[2] += dz
        points = [
            {"name": f"{pallet_id}_P1", "q": q, "p": p1},
            {"name": f"{pallet_id}_P2", "q": q, "p": p2},
            {"name": f"{pallet_id}_P3", "q": q, "p": p3},
            {"name": f"{pallet_id}_P4", "q": q, "p": p4},
        ]
        return {"size": [data["m"], data["n"], data["l"]], "points": points}

    @staticmethod
    def _approach_block(distance_mm, direction):
        return {
            "direction": direction,
            "boundary": {"velLevel": 5, "accLevel": 5},
            "distance": float(distance_mm) / 1000.0,
            "waitTime": 0,
            "waitFor": {"type": 0, "time": 0},
        }

    @staticmethod
    def _fmt(values, digits):
        return "[" + ", ".join(f"{float(v or 0.0):.{digits}f}" for v in list(values or [])[:6]) + "]"

    @staticmethod
    def _entry_float(entry, default):
        try:
            return float(entry.get().strip())
        except Exception:
            return float(default)

    @staticmethod
    def _to_wav_bytes(pcm_bytes, sample_rate):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm_bytes)
        return buf.getvalue()
