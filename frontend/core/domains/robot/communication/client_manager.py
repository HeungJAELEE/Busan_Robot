import threading
import time
import os
import uuid

try:
    from core.runtime_config import env_float, env_str
except Exception:
    def env_float(name, default):
        try:
            return float(os.getenv(name, default))
        except (TypeError, ValueError):
            return float(default)

    def env_str(name, default=""):
        return os.getenv(name, default)


def _gateway_mode():
    return env_str("ROBOT_CONTROL_MODE", "auto").strip().lower()


class GatewayRobotProxy:
    """MQTT Robot Controller를 실제 IndyDCP 인스턴스처럼 쓰기 위한 얇은 프록시."""

    def __init__(self, robot_name, manager):
        self.robot_name = robot_name
        self.manager = manager
        self.is_gateway_proxy = True
        self.last_command_id = ""

    def _publish(self, command_type, args=None):
        try:
            from infrastructure.mqtt.mqtt_manager import mqtt_broker
            if not getattr(mqtt_broker, "connected", False):
                mqtt_broker.connect_and_loop()
                wait_sec = max(env_float("HMI_MQTT_CONNECT_WAIT_SEC", 3.0), 1.0)
                deadline = time.time() + wait_sec
                while time.time() < deadline and not getattr(mqtt_broker, "connected", False):
                    time.sleep(0.05)
            if not getattr(mqtt_broker, "connected", False):
                print(f">> [Gateway] MQTT 브로커 미연결로 {command_type} 발행을 보류합니다.")
                return False
            session_id = env_str("ROBOT_COMMAND_SESSION_ID", "").strip()
            command_id = uuid.uuid4().hex
            if session_id:
                command_id = f"{session_id}:{command_id}"
            self.last_command_id = command_id
            self.manager.prepare_gateway_command(command_id)
            return mqtt_broker.publish("robot/command", {
                "command_id": command_id,
                "robot_id": self.robot_name,
                "type": command_type,
                "args": args or {},
                "created_at": time.time(),
                "source": "frontend_gateway_proxy",
            })
        except Exception as exc:
            print(f">> [Gateway] {command_type} 발행 실패: {exc}")
            return False

    def connect(self):
        return self._publish("connect")

    def disconnect(self):
        return self._publish("disconnect")

    def joint_move_to(self, q):
        return self._publish("joint_move_to", {"q": list(q or [])[:6]})

    def task_move_to(self, p):
        return self._publish("task_move_to", {"p": list(p or [])[:6]})

    def joint_move_by(self, q):
        return self._publish("joint_move_by", {"q": list(q or [])[:6]})

    def task_move_by(self, p):
        return self._publish("task_move_by", {"p": list(p or [])[:6]})

    def go_home(self):
        return self._publish("go_home")

    def go_zero(self):
        return self._publish("go_zero")

    def stop_motion(self):
        return self._publish("stop_motion")

    def stop_emergency(self):
        return self._publish("stop_emergency")

    def stop_current_program(self):
        return self._publish("stop_current_program")

    def reset_robot(self, **kwargs):
        args = {k: v for k, v in kwargs.items() if v is not None}
        return self._publish("reset_robot", args)

    def set_do(self, idx, val):
        return self._publish("set_do", {"idx": int(idx), "val": int(val)})

    def set_default_tcp(self, tcp):
        return self._publish("set_default_tcp", {"tcp": list(tcp or [])[:6]})

    def reset_default_tcp(self):
        return self._publish("reset_default_tcp")

    def set_reference_frame(self, ref):
        return self._publish("set_reference_frame", {"ref": list(ref or [])[:6]})

    def reset_reference_frame(self):
        return self._publish("reset_reference_frame")

    def set_joint_vel_level(self, level):
        return self._publish("set_joint_vel_level", {"level": int(level)})

    def set_task_vel_level(self, level):
        return self._publish("set_task_vel_level", {"level": int(level)})

    def set_collision_level(self, level):
        return self._publish("set_collision_level", {"level": int(level)})

    def set_servo(self, arr):
        return self._publish("set_servo", {"on": bool((arr or [True])[0])})

    def set_brake(self, arr):
        return self._publish("set_brake", {"on": bool((arr or [True])[0])})

    def direct_teaching(self, mode):
        return self._publish("direct_teaching", {"enable": bool(mode)})

    def get_robot_status(self):
        state = self.manager.get_robot_state(self.robot_name) or {}
        return state.get("status") or {}

    def get_joint_pos(self):
        state = self.manager.get_robot_state(self.robot_name) or {}
        return state.get("j_pos") or [0.0] * 6

    def get_task_pos(self):
        state = self.manager.get_robot_state(self.robot_name) or {}
        return state.get("t_pos") or [0.0] * 6

    def get_control_torque(self):
        state = self.manager.get_robot_state(self.robot_name) or {}
        return state.get("torque") or [0.0] * 6

    def get_di(self):
        state = self.manager.get_robot_state(self.robot_name) or {}
        return state.get("di") or []

    def get_do(self):
        state = self.manager.get_robot_state(self.robot_name) or {}
        return state.get("do") or []

    def wait_for_last_result(self, timeout_sec=240.0):
        if not self.last_command_id:
            return None
        return self.manager.wait_gateway_result(self.last_command_id, timeout_sec)

class RobotClientManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(RobotClientManager, cls).__new__(cls, *args, **kwargs)
                cls._instance._initialize()
            return cls._instance
            
    def _initialize(self):
        self._robots = {}
        self._active_robot_name = None
        self._robot_lock = threading.Lock()
        
        # 로봇의 최신 상태(좌표 + 상태)를 저장할 메모장
        self._latest_states = {} 
        self._state_lock = threading.Lock()
        self._gateway_results = {}
        self._gateway_errors = {}
        self._gateway_result_lock = threading.Lock()
        self._gateway_result_listeners_ready = False

    def should_use_gateway(self) -> bool:
        mode = _gateway_mode()
        if mode in ("mqtt", "gateway", "online"):
            return True
        if mode in ("direct", "offline", "local"):
            return False
        try:
            from infrastructure.mqtt.mqtt_manager import mqtt_broker
            return bool(getattr(mqtt_broker, "connected", False))
        except Exception:
            return False

    def _ensure_gateway_result_listeners(self):
        if self._gateway_result_listeners_ready:
            return
        try:
            from infrastructure.mqtt.mqtt_manager import mqtt_broker
            mqtt_broker.subscribe("robot/result", self._on_gateway_result)
            mqtt_broker.subscribe("robot/error", self._on_gateway_error)
            self._gateway_result_listeners_ready = True
        except Exception as exc:
            print(f">> [Gateway] 결과 구독 설정 실패: {exc}")

    def prepare_gateway_command(self, command_id: str):
        self._ensure_gateway_result_listeners()
        if not command_id:
            return
        with self._gateway_result_lock:
            self._gateway_results.pop(command_id, None)
            self._gateway_errors.pop(command_id, None)

    def _on_gateway_result(self, payload):
        if not isinstance(payload, dict):
            return
        command_id = payload.get("command_id", "")
        if not command_id:
            return
        with self._gateway_result_lock:
            self._gateway_results[command_id] = payload

    def _on_gateway_error(self, payload):
        if not isinstance(payload, dict):
            return
        command_id = payload.get("command_id", "")
        if not command_id:
            return
        with self._gateway_result_lock:
            self._gateway_errors[command_id] = payload

    def wait_gateway_result(self, command_id: str, timeout_sec: float = 240.0):
        self._ensure_gateway_result_listeners()
        timeout_sec = max(float(timeout_sec or 0.0), 1.0)
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            with self._gateway_result_lock:
                result = self._gateway_results.get(command_id)
                error = self._gateway_errors.get(command_id)
            if result:
                return result
            if error:
                return {
                    "command_id": command_id,
                    "ok": False,
                    "message": error.get("message", "robot/error"),
                    "error": error,
                }
            time.sleep(0.05)
        return {
            "command_id": command_id,
            "ok": False,
            "message": f"gateway result timeout({timeout_sec:g}s)",
            "motion_state": "timeout",
        }
        
    def add_robot(self, name: str, ip: str, plc_ip: str = None):
        if name not in self._robots:
            self._robots[name] = {"ip": ip, "plc_ip": plc_ip, "instance": None}
            if self._active_robot_name is None:
                self._active_robot_name = name
            return

        info = self._robots[name]
        if ip:
            info["ip"] = ip
        if plc_ip is not None:
            info["plc_ip"] = plc_ip
                
    def get_robot_info(self, name: str) -> dict:
        return self._robots.get(name)
        
    def set_active_robot(self, name: str):
        if name in self._robots:
            self._active_robot_name = name
            
    def get_active_robot_name(self) -> str:
        return self._active_robot_name
        
    def get_active_instance(self):
        if self._active_robot_name and self._active_robot_name in self._robots:
            return self._robots[self._active_robot_name]["instance"]
        return None
        
    def get_lock(self):
        return self._robot_lock
        
    def connect(self, name: str = None, ip: str = None) -> bool:
        name = name or self._active_robot_name
        if name not in self._robots:
            return False
        if ip:
            self._robots[name]["ip"] = ip
            
        target_ip = self._robots[name]["ip"]

        if self.should_use_gateway():
            proxy = GatewayRobotProxy(name, self)
            if not proxy.connect():
                self._robots[name]["instance"] = None
                print(f">> [Gateway] {name} MQTT Robot Controller 연결 요청 실패")
                return False
            timeout = env_float("ROBOT_GATEWAY_CONNECT_TIMEOUT_SEC", 8.0)
            result = proxy.wait_for_last_result(timeout)
            if not result or not result.get("ok"):
                self._robots[name]["instance"] = None
                message = (result or {}).get("message", "응답 없음")
                print(f">> [Gateway] {name} 연결 확인 실패: {message}")
                return False
            self._robots[name]["instance"] = proxy
            print(f">> [Gateway] {name} 로봇 통신은 Docker Robot Controller로 위임합니다.")
            return True
        
        # Disconnect if already connected
        if self._robots[name]["instance"] is not None:
            try:
                self._robots[name]["instance"].disconnect()
                time.sleep(0.5)
            except Exception: pass
            
        try:
            from indy_utils import indydcp_client as client
            r = client.IndyDCPClient(target_ip, "NRMK-Indy7")
            is_connected = r.connect()
            if not is_connected:
                print(f">> {name} 소켓 연결 실패 (IP: {target_ip})")
                self._robots[name]["instance"] = None
                return False
                
            self._robots[name]["instance"] = r
            return True
        except Exception as e:
            print(f">> {name} 연결 실패 예외 발생: {e}")
            self._robots[name]["instance"] = None
            return False
            
    def disconnect(self, name: str = None):
        name = name or self._active_robot_name
        if name in self._robots and self._robots[name]["instance"]:
            try:
                self._robots[name]["instance"].disconnect()
                time.sleep(0.5)
            except Exception: pass
            self._robots[name]["instance"] = None
            # 상태 메모장에서도 제거
            with self._state_lock:
                self._latest_states.pop(name, None)
            
    def get_all_robots(self):
        return self._robots
        
    def update_robot_state(self, name: str, j_pos, t_pos, robot_status=None, torque=None, di=None, do=None, source=None):
        """로봇 좌표 + 상태를 메모장에 기록"""
        with self._state_lock:
            self._latest_states[name] = {
                "j_pos": j_pos, 
                "t_pos": t_pos,
                "status": robot_status,  # get_robot_status() 결과
                "torque": torque,
                "di": di,
                "do": do,
                "source": source,
                "timestamp": time.time()
            }

    def mark_connection_status(self, name: str, connected: bool, status: str = "", ip: str = ""):
        """Gateway 연결 이벤트를 UI 연결 상태와 최신 상태 캐시에 반영."""
        if not name:
            return
        if name not in self._robots and ip:
            self.add_robot(name, ip)
        if name in self._robots and self.should_use_gateway():
            if connected and self._robots[name].get("instance") is None:
                self._robots[name]["instance"] = GatewayRobotProxy(name, self)
            elif not connected:
                self._robots[name]["instance"] = None
        with self._state_lock:
            current = self._latest_states.get(name, {})
            robot_status = dict(current.get("status") or {})
            robot_status["gateway_connected"] = 1 if connected else 0
            robot_status["gateway_status"] = status
            current["status"] = robot_status
            current["source"] = "robot_controller"
            current["timestamp"] = time.time()
            self._latest_states[name] = current

    def get_robot_state(self, name: str):
        with self._state_lock:
            return self._latest_states.get(name)
    
    def is_connected(self, name: str = None) -> bool:
        """해당 로봇이 연결되어 있는지 확인"""
        name = name or self._active_robot_name
        info = self._robots.get(name)
        return info is not None and info.get("instance") is not None
    
    def get_any_connected(self) -> bool:
        """하나라도 연결된 로봇이 있는지"""
        return any(info.get("instance") for info in self._robots.values())
        
# Singleton export
robot_manager = RobotClientManager()
