import os
import sys
import time
import threading
from dataclasses import dataclass, field

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.infrastructure.mqtt_manager import MqttManager
from src.infrastructure.indy_utils import indydcp_client

print("🤖 [Robot Controller] 시작됨 - MSA 환경")


def _truthy(value):
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def _robot_config():
    robot_model = os.getenv("ROBOT_MODEL", os.getenv("ROBOT_NAME", "NRMK-Indy7"))
    configs = {}
    defaults = {
        "Robot A": os.getenv("ROBOT_A_IP", os.getenv("ROBOT_IP", "192.168.3.7")),
        "Robot B": os.getenv("ROBOT_B_IP", ""),
        "Robot C": os.getenv("ROBOT_C_IP", ""),
    }
    for name, ip in defaults.items():
        if ip:
            configs[name] = {"ip": ip, "model": robot_model}

    extra = os.getenv("ROBOT_CONFIG", "").strip()
    if extra:
        for item in extra.split(","):
            parts = [p.strip() for p in item.split("=")]
            if len(parts) == 2 and parts[0] and parts[1]:
                configs[parts[0]] = {"ip": parts[1], "model": robot_model}

    return configs


@dataclass
class RobotHandle:
    robot_id: str
    ip: str
    model: str
    mqtt_client: MqttManager
    inst: object = None
    connected: bool = False
    last_status: dict = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def connect(self):
        with self.lock:
            if self.connected and self.inst:
                return True
            self.inst = indydcp_client.IndyDCPClient(self.ip, self.model)
            self.connected = bool(self.inst.connect())
            self._publish_connection("connected" if self.connected else "failed")
            if not self.connected:
                self.inst = None
            return self.connected

    def disconnect(self):
        with self.lock:
            if self.inst:
                try:
                    self.inst.disconnect()
                except Exception:
                    pass
            self.inst = None
            self.connected = False
            self._publish_connection("disconnected")

    def _publish_connection(self, status, extra=None):
        payload = {
            "robot_id": self.robot_id,
            "ip": self.ip,
            "status": status,
            "connected": bool(self.connected),
            "created_at": time.time(),
        }
        if isinstance(extra, dict):
            payload.update(extra)
        self.mqtt_client.publish("robot/connection", payload)

    def publish_error(self, command_id, message):
        self.mqtt_client.publish("robot/error", {
            "command_id": command_id,
            "robot_id": self.robot_id,
            "message": message,
            "created_at": time.time(),
        })

    def publish_result(self, command_id, command_type, ok=True, message="OK"):
        self.mqtt_client.publish("robot/result", {
            "command_id": command_id,
            "robot_id": self.robot_id,
            "type": command_type,
            "ok": bool(ok),
            "message": message,
            "created_at": time.time(),
        })

    def _fault_reason(self, status):
        if not isinstance(status, dict):
            return ""
        if status.get("emergency", 0):
            return "비상정지"
        if status.get("error", 0):
            return "로봇 에러"
        if status.get("collision", 0):
            return "충돌 감지"
        return ""

    def _ensure_ready(self, command_id, allow_when_fault=False):
        if not self.connected or not self.inst:
            if not self.connect():
                self.publish_error(command_id, f"{self.robot_id} 연결 실패 ({self.ip})")
                return False
        if allow_when_fault:
            return True
        try:
            status = self.inst.get_robot_status()
        except Exception as exc:
            self.publish_error(command_id, f"상태 조회 실패: {exc}")
            return False
        fault = self._fault_reason(status)
        if fault:
            self.publish_error(command_id, f"{fault} 상태라 명령 차단")
            return False
        return True

    def execute(self, payload):
        command_id = payload.get("command_id", "")
        command_type = payload.get("type", "")
        args = payload.get("args", {})
        if not isinstance(args, dict):
            args = {}

        try:
            if command_type == "connect":
                ok = self.connect()
                self.publish_result(command_id, command_type, ok, "connected" if ok else "connect failed")
                return
            if command_type == "disconnect":
                self.disconnect()
                self.publish_result(command_id, command_type, True, "disconnected")
                return

            allow_fault = command_type in ("stop_motion", "stop_emergency", "reset_robot", "stop_current_program")
            if not self._ensure_ready(command_id, allow_when_fault=allow_fault):
                self.publish_result(command_id, command_type, False, "not ready")
                return

            with self.lock:
                self._execute_connected(command_type, args)
            self.publish_result(command_id, command_type, True, "OK")
        except Exception as exc:
            self.publish_error(command_id, f"{command_type} 실행 실패: {exc}")
            self.publish_result(command_id, command_type, False, str(exc))

    def _execute_connected(self, command_type, args):
        inst = self.inst
        if command_type == "joint_move_to":
            inst.joint_move_to(args.get("q", []))
        elif command_type == "task_move_to":
            inst.task_move_to(args.get("p", []))
        elif command_type == "joint_move_by":
            inst.joint_move_by(args.get("q", []))
        elif command_type == "task_move_by":
            inst.task_move_by(args.get("p", []))
        elif command_type == "go_home":
            inst.go_home()
        elif command_type == "go_zero":
            inst.go_zero()
        elif command_type == "stop_motion":
            inst.stop_motion()
        elif command_type == "stop_emergency":
            inst.stop_emergency()
        elif command_type == "stop_current_program":
            inst.stop_current_program()
        elif command_type == "reset_robot":
            inst.stop_motion()
            time.sleep(0.1)
            if hasattr(inst, "stop_current_program"):
                try:
                    inst.stop_current_program()
                    time.sleep(0.1)
                except Exception:
                    pass
            inst.reset_robot()
        elif command_type == "set_do":
            inst.set_do(int(args.get("idx", 0)), int(args.get("val", 0)))
        elif command_type == "set_default_tcp":
            inst.set_default_tcp(args.get("tcp", [0, 0, 0, 0, 0, 0]))
        elif command_type == "reset_default_tcp":
            inst.reset_default_tcp()
        elif command_type == "set_reference_frame":
            inst.set_reference_frame(args.get("ref", [0, 0, 0, 0, 0, 0]))
        elif command_type == "reset_reference_frame":
            inst.reset_reference_frame()
        elif command_type == "set_joint_vel_level":
            inst.set_joint_vel_level(int(args.get("level", 3)))
        elif command_type == "set_task_vel_level":
            inst.set_task_vel_level(int(args.get("level", 3)))
        elif command_type == "set_collision_level":
            inst.set_collision_level(int(args.get("level", 3)))
        elif command_type == "set_servo":
            on = bool(args.get("on", True))
            inst.set_servo([on] * 6)
        elif command_type == "set_brake":
            on = bool(args.get("on", True))
            inst.set_brake([on] * 6)
        elif command_type == "direct_teaching":
            inst.direct_teaching(bool(args.get("enable", False)))
        else:
            raise ValueError(f"지원하지 않는 command type: {command_type}")

    def poll_once(self):
        if not self.connected or not self.inst:
            return
        try:
            j_pos = self.inst.get_joint_pos()
            t_pos = self.inst.get_task_pos()
            status = self.inst.get_robot_status()
            torque = self.inst.get_control_torque()
            di = []
            do = []
            try:
                di = self.inst.get_di()
            except Exception:
                pass
            try:
                do = self.inst.get_do()
            except Exception:
                pass
            payload = {
                "robot_id": self.robot_id,
                "ip": self.ip,
                "q": j_pos or [0] * 6,
                "p": t_pos or [0] * 6,
                "torque": torque or [0] * 6,
                "di": di or [],
                "do": do or [],
                "busy": status.get("busy", 0) if isinstance(status, dict) else 0,
                "status": status or {},
                "source": "robot_controller",
                "created_at": time.time(),
            }
            self.last_status = payload
            self.mqtt_client.publish("robot/realtime", payload)
        except Exception as exc:
            self.connected = False
            self.publish_error("", f"폴링 실패: {exc}")


class RobotGateway:
    def __init__(self, mqtt_client):
        self.mqtt_client = mqtt_client
        self.robots = {
            name: RobotHandle(name, cfg["ip"], cfg["model"], mqtt_client)
            for name, cfg in _robot_config().items()
        }
        self.default_robot = os.getenv("DEFAULT_ROBOT_ID", next(iter(self.robots.keys()), "Robot A"))

    def handle_command(self, payload):
        if not isinstance(payload, dict):
            return
        robot_id = payload.get("robot_id") or self.default_robot
        handle = self.robots.get(robot_id)
        if not handle:
            self.mqtt_client.publish("robot/error", {
                "command_id": payload.get("command_id", ""),
                "robot_id": robot_id,
                "message": f"등록되지 않은 robot_id: {robot_id}",
                "created_at": time.time(),
            })
            return
        threading.Thread(target=handle.execute, args=(payload,), daemon=True).start()

    def autoconnect(self):
        if not _truthy(os.getenv("ROBOT_AUTOCONNECT", "0")):
            return
        for handle in self.robots.values():
            threading.Thread(target=handle.connect, daemon=True).start()

    def poll_loop(self):
        interval = float(os.getenv("ROBOT_POLL_INTERVAL_SEC", "0.1"))
        while True:
            for handle in self.robots.values():
                handle.poll_once()
            time.sleep(interval)


def main():
    broker_ip = os.getenv("MQTT_BROKER", "127.0.0.1")
    broker_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_client = MqttManager(broker_ip=broker_ip, port=broker_port, client_id="robot_controller")
    gateway = RobotGateway(mqtt_client)

    mqtt_client.subscribe("robot/command", gateway.handle_command)
    mqtt_client.connect_and_loop()

    print(f" -> MQTT Robot Gateway 준비: {', '.join(gateway.robots.keys()) or 'no robots'}")
    gateway.autoconnect()
    gateway.poll_loop()


if __name__ == "__main__":
    main()
