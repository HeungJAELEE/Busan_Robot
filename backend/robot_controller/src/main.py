import os
import queue
import sys
import time
import threading
from dataclasses import dataclass, field

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.infrastructure.mqtt_manager import MqttManager
from src.infrastructure.indy_utils import indydcp_client

print("🤖 [Robot Controller] 시작됨 - MSA 환경")


MOTION_COMMANDS = {
    "joint_move_to",
    "task_move_to",
    "joint_move_by",
    "task_move_by",
    "go_home",
    "go_zero",
}
JOG_COMMANDS = {
    "jog_joint_move_by",
    "jog_task_move_by",
}
QUERY_COMMANDS = {
    "get_default_tcp",
    "get_robot_status",
    "get_di",
    "get_do",
}
TARGET_STATUS_KEY = {
    "go_home": "home",
    "go_zero": "zero",
}
IMMEDIATE_COMMANDS = {
    "stop_motion",
    "stop_emergency",
    "stop_current_program",
    "reset_robot",
    "disconnect",
}


def _truthy(value):
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def _env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return float(default)


def _env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return int(default)


def _robot_config():
    robot_model = os.getenv("ROBOT_MODEL", os.getenv("ROBOT_NAME", "NRMK-Indy7"))
    configs = {}
    defaults = {
        "Robot A": os.getenv("ROBOT_A_IP", os.getenv("ROBOT_IP", "")),
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

    def publish_result(self, command_id, command_type, ok=True, message="OK", extra=None):
        payload = {
            "command_id": command_id,
            "robot_id": self.robot_id,
            "type": command_type,
            "ok": bool(ok),
            "message": message,
            "created_at": time.time(),
        }
        if isinstance(extra, dict):
            payload.update(extra)
        self.mqtt_client.publish("robot/result", payload)

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

    def _fault_flags(self, status):
        if not isinstance(status, dict):
            return ["상태 조회 실패"]
        faults = []
        if status.get("emergency", 0):
            faults.append("비상정지")
        if status.get("collision", 0):
            faults.append("충돌 감지")
        if status.get("error", 0):
            faults.append("로봇 에러")
        if status.get("resetting", 0):
            faults.append("리셋중")
        return faults

    def _call_locked(self, fn_name, *args):
        with self.lock:
            fn = getattr(self.inst, fn_name, None)
            if not fn:
                return None
            return fn(*args)

    def _status_locked(self):
        return self._call_locked("get_robot_status") or {}

    def _ensure_ready(self, command_id, allow_when_fault=False):
        if not self.connected or not self.inst:
            if not self.connect():
                self.publish_error(command_id, f"{self.robot_id} 연결 실패 ({self.ip})")
                return False
        if allow_when_fault:
            return True
        try:
            status = self._status_locked()
        except Exception as exc:
            self.publish_error(command_id, f"상태 조회 실패: {exc}")
            return False
        fault = self._fault_reason(status)
        if fault:
            self.publish_error(command_id, f"{fault} 상태라 명령 차단")
            return False
        return True

    def _motion_snapshot(self):
        with self.lock:
            status = self.inst.get_robot_status()
            q = []
            p = []
            try:
                q = self.inst.get_joint_pos() or []
            except Exception:
                q = []
            try:
                p = self.inst.get_task_pos() or []
            except Exception:
                p = []
        return {"status": status or {}, "q": list(q or []), "p": list(p or [])}

    def _max_abs_delta(self, before, after, key):
        try:
            left = before.get(key) or []
            right = after.get(key) or []
            return max([abs(float(a) - float(b)) for a, b in zip(left, right)] or [0.0])
        except Exception:
            return 0.0

    def _wait_for_motion_complete(self, command_type, before):
        timeout = _env_float("ROBOT_MOVE_TIMEOUT_SEC", 180.0)
        poll_sec = max(_env_float("ROBOT_MOVE_POLL_SEC", 0.05), 0.02)
        joint_eps = _env_float("ROBOT_ACTUAL_JOINT_DELTA_EPS", 0.01)
        task_eps = _env_float("ROBOT_ACTUAL_TASK_DELTA_EPS", 0.0005)
        target_key = TARGET_STATUS_KEY.get(command_type)
        before_status = before.get("status") or {}
        before_target = bool(target_key and before_status.get(target_key, 0))
        observed_busy = False
        last = before
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                status = self._status_locked()
            except Exception as exc:
                return False, {
                    "motion_state": "status_read_failed",
                    "target_reached": False,
                    "actual_motion": False,
                    "error": str(exc),
                }

            last = {"status": status or {}, "q": last.get("q") or [], "p": last.get("p") or []}
            fault = self._fault_reason(status)
            if fault:
                return False, {
                    "motion_state": "fault",
                    "target_reached": False,
                    "actual_motion": observed_busy,
                    "fault": fault,
                    "status": status,
                }

            if status.get("busy", 0):
                observed_busy = True

            target_reached = True
            if target_key:
                target_reached = bool(status.get(target_key, 0))

            if status.get("busy", 0) == 0 and status.get("movedone", 0) and target_reached:
                try:
                    after = self._motion_snapshot()
                except Exception:
                    after = {"status": status or {}, "q": [], "p": []}
                joint_delta = self._max_abs_delta(before, after, "q")
                task_delta = self._max_abs_delta(before, after, "p")
                actual_motion = bool(
                    observed_busy
                    or joint_delta >= joint_eps
                    or task_delta >= task_eps
                )
                if before_target and not actual_motion:
                    motion_state = "already_at_target"
                else:
                    motion_state = "completed"
                return True, {
                    "motion_state": motion_state,
                    "target_reached": True,
                    "actual_motion": actual_motion,
                    "observed_busy": observed_busy,
                    "joint_delta_max": joint_delta,
                    "task_delta_max": task_delta,
                    "status": after.get("status") or status,
                    "q": after.get("q") or [],
                    "p": after.get("p") or [],
                }

            time.sleep(poll_sec)

        return False, {
            "motion_state": "timeout",
            "target_reached": False,
            "actual_motion": observed_busy,
            "observed_busy": observed_busy,
            "timeout_sec": timeout,
            "status": last.get("status") or {},
        }

    def _reset_fault_sequence(self, args):
        attempts = max(int(args.get("attempts", 4) or 4), 1)
        settle_sec = max(float(args.get("settle_sec", 0.25) or 0.25), 0.05)
        wait_sec = max(float(args.get("wait_sec", 4.0) or 4.0), 0.5)
        poll_sec = max(float(args.get("poll_sec", 0.2) or 0.2), 0.05)
        steps = []

        try:
            before = self._status_locked()
        except Exception as exc:
            before = {}
            steps.append({"step": "pre_status", "ok": False, "error": str(exc)})

        for fn_name in ("stop_motion", "stop_current_program"):
            try:
                ret = self._call_locked(fn_name)
                steps.append({"step": fn_name, "ok": ret in (None, 0), "ret": ret})
            except Exception as exc:
                steps.append({"step": fn_name, "ok": False, "error": str(exc)})
            time.sleep(settle_sec)

        last_status = before
        for attempt in range(1, attempts + 1):
            try:
                ret = self._call_locked("reset_robot")
                steps.append({"step": "reset_robot", "attempt": attempt, "ok": ret in (None, 0), "ret": ret})
            except Exception as exc:
                steps.append({"step": "reset_robot", "attempt": attempt, "ok": False, "error": str(exc)})

            deadline = time.time() + wait_sec
            while time.time() < deadline:
                time.sleep(poll_sec)
                try:
                    last_status = self._status_locked()
                except Exception as exc:
                    steps.append({"step": "status_after_reset", "attempt": attempt, "ok": False, "error": str(exc)})
                    continue

                faults = self._fault_flags(last_status)
                if not faults:
                    return {
                        "ok": True,
                        "message": "reset cleared",
                        "attempts": attempt,
                        "before_status": before,
                        "status": last_status,
                        "steps": steps,
                    }

                if not last_status.get("resetting", 0) and time.time() + poll_sec >= deadline:
                    break

        emg_info = None
        try:
            if hasattr(self.inst, "get_last_emergency_info"):
                emg_info = self._call_locked("get_last_emergency_info")
        except Exception as exc:
            emg_info = {"error": str(exc)}

        faults = self._fault_flags(last_status)
        message = "reset did not clear fault"
        if faults:
            message += ": " + ", ".join(faults)
        return {
            "ok": False,
            "message": message,
            "attempts": attempts,
            "before_status": before,
            "status": last_status,
            "faults": faults,
            "emergency_info": emg_info,
            "steps": steps,
        }

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

            allow_fault = command_type in (
                "stop_motion",
                "stop_emergency",
                "reset_robot",
                "stop_current_program",
            ) or command_type in QUERY_COMMANDS
            if not self._ensure_ready(command_id, allow_when_fault=allow_fault):
                self.publish_result(command_id, command_type, False, "not ready")
                return

            if command_type == "reset_robot":
                result = self._reset_fault_sequence(args)
                ok = bool(result.get("ok"))
                self.publish_result(command_id, command_type, ok, result.get("message", "reset"), result)
                if not ok:
                    self.publish_error(command_id, result.get("message", "reset failed"))
                return

            if command_type in QUERY_COMMANDS:
                with self.lock:
                    value = self._execute_connected(command_type, args)
                self.publish_result(command_id, command_type, True, "OK", {"value": value})
                return

            before = None
            if command_type in MOTION_COMMANDS:
                try:
                    before = self._motion_snapshot()
                except Exception as exc:
                    self.publish_error(command_id, f"이동 전 상태 조회 실패: {exc}")
                    self.publish_result(command_id, command_type, False, "pre-motion status failed")
                    return

            with self.lock:
                command_error = self._execute_connected(command_type, args)
            if command_error:
                self.publish_error(command_id, f"{command_type} 명령 실패: {command_error}")
                self.publish_result(command_id, command_type, False, f"command error: {command_error}")
                return

            if command_type in JOG_COMMANDS:
                self.publish_result(command_id, command_type, True, "jog command sent")
                return

            if command_type in MOTION_COMMANDS:
                ok, completion = self._wait_for_motion_complete(command_type, before or {})
                message = completion.get("motion_state", "completed" if ok else "motion failed")
                self.publish_result(command_id, command_type, ok, message, completion)
                if not ok:
                    self.publish_error(command_id, f"{command_type} 완료 확인 실패: {completion}")
                return

            self.publish_result(command_id, command_type, True, "OK")
        except Exception as exc:
            self.publish_error(command_id, f"{command_type} 실행 실패: {exc}")
            self.publish_result(command_id, command_type, False, str(exc))

    def _execute_connected(self, command_type, args):
        inst = self.inst
        if command_type == "joint_move_to":
            return inst.joint_move_to(args.get("q", []))
        elif command_type == "task_move_to":
            return inst.task_move_to(args.get("p", []))
        elif command_type == "joint_move_by":
            return inst.joint_move_by(args.get("q", []))
        elif command_type == "task_move_by":
            return inst.task_move_by(args.get("p", []))
        elif command_type == "jog_joint_move_by":
            return inst.joint_move_by(args.get("q", []))
        elif command_type == "jog_task_move_by":
            return inst.task_move_by(args.get("p", []))
        elif command_type == "go_home":
            return inst.go_home()
        elif command_type == "go_zero":
            return inst.go_zero()
        elif command_type == "stop_motion":
            return inst.stop_motion()
        elif command_type == "stop_emergency":
            return inst.stop_emergency()
        elif command_type == "stop_current_program":
            return inst.stop_current_program()
        elif command_type == "reset_robot":
            return inst.reset_robot()
        elif command_type == "set_do":
            return inst.set_do(int(args.get("idx", 0)), int(args.get("val", 0)))
        elif command_type == "set_default_tcp":
            return inst.set_default_tcp(args.get("tcp", [0, 0, 0, 0, 0, 0]))
        elif command_type == "get_default_tcp":
            return inst.get_default_tcp()
        elif command_type == "get_robot_status":
            return inst.get_robot_status()
        elif command_type == "get_di":
            return inst.get_di()
        elif command_type == "get_do":
            return inst.get_do()
        elif command_type == "reset_default_tcp":
            return inst.reset_default_tcp()
        elif command_type == "set_reference_frame":
            return inst.set_reference_frame(args.get("ref", [0, 0, 0, 0, 0, 0]))
        elif command_type == "reset_reference_frame":
            return inst.reset_reference_frame()
        elif command_type == "set_joint_vel_level":
            return inst.set_joint_vel_level(int(args.get("level", 3)))
        elif command_type == "set_task_vel_level":
            return inst.set_task_vel_level(int(args.get("level", 3)))
        elif command_type == "set_collision_level":
            return inst.set_collision_level(int(args.get("level", 3)))
        elif command_type == "set_servo":
            on = bool(args.get("on", True))
            return inst.set_servo([on] * 6)
        elif command_type == "set_brake":
            on = bool(args.get("on", True))
            return inst.set_brake([on] * 6)
        elif command_type == "direct_teaching":
            return inst.direct_teaching(bool(args.get("enable", False)))
        else:
            raise ValueError(f"지원하지 않는 command type: {command_type}")

    def poll_once(self):
        if not self.connected or not self.inst:
            return
        if not self.lock.acquire(timeout=0.02):
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
        finally:
            self.lock.release()


class RobotGateway:
    def __init__(self, mqtt_client):
        self.mqtt_client = mqtt_client
        self.robots = {
            name: RobotHandle(name, cfg["ip"], cfg["model"], mqtt_client)
            for name, cfg in _robot_config().items()
        }
        self.default_robot = os.getenv("DEFAULT_ROBOT_ID", next(iter(self.robots.keys()), "Robot A"))
        self.queue_maxsize = max(_env_int("ROBOT_COMMAND_QUEUE_MAXSIZE", 200), 1)
        self.queues = {
            name: queue.Queue(maxsize=self.queue_maxsize)
            for name in self.robots.keys()
        }
        self._start_command_workers()

    def _start_command_workers(self):
        for robot_id, handle in self.robots.items():
            thread = threading.Thread(
                target=self._command_worker,
                args=(robot_id, handle),
                daemon=True,
                name=f"robot-command-worker-{robot_id}",
            )
            thread.start()

    def _publish_acceptance(self, payload, accepted, message, queue_size=0):
        self.mqtt_client.publish("robot/accepted", {
            "command_id": payload.get("command_id", ""),
            "robot_id": payload.get("robot_id") or self.default_robot,
            "type": payload.get("type", ""),
            "accepted": bool(accepted),
            "message": message,
            "queue_size": int(queue_size),
            "created_at": time.time(),
        })

    def _clear_pending_commands(self, robot_id):
        q = self.queues.get(robot_id)
        if not q:
            return 0
        cleared = 0
        while True:
            try:
                q.get_nowait()
                q.task_done()
                cleared += 1
            except queue.Empty:
                break
        return cleared

    def _command_worker(self, robot_id, handle):
        q = self.queues[robot_id]
        while True:
            payload = q.get()
            try:
                handle.execute(payload)
            except Exception as exc:
                handle.publish_error(payload.get("command_id", ""), f"큐 명령 실행 실패: {exc}")
                handle.publish_result(payload.get("command_id", ""), payload.get("type", ""), False, str(exc))
            finally:
                q.task_done()

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
        payload["robot_id"] = robot_id
        command_type = payload.get("type", "")

        if command_type in IMMEDIATE_COMMANDS:
            cleared = self._clear_pending_commands(robot_id)
            self._publish_acceptance(payload, True, f"immediate command; cleared {cleared} pending", 0)
            threading.Thread(target=handle.execute, args=(payload,), daemon=True).start()
            return

        q = self.queues[robot_id]
        try:
            q.put_nowait(payload)
        except queue.Full:
            self._publish_acceptance(payload, False, "robot command queue full", q.qsize())
            handle.publish_error(payload.get("command_id", ""), "로봇 명령 큐가 가득 차서 명령 거부")
            handle.publish_result(payload.get("command_id", ""), command_type, False, "queue full")
            return

        self._publish_acceptance(payload, True, "queued", q.qsize())

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
