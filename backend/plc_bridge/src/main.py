import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from src.infrastructure.mqtt_manager import MqttManager

try:
    import pymcprotocol
except ImportError:
    print(">> pymcprotocol 모듈이 필요합니다. (pip install pymcprotocol)")
    pymcprotocol = None


print("⚙️ [PLC Bridge] 시작됨 - PLC master / robot DI monitor mode")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class SignalWatch:
    signal: str
    source: str
    device: str
    topic: str
    station_id: str = ""
    description: str = ""


class PlcConnection:
    def __init__(self, name: str, ip: str, port: int, reconnect_interval: float = 3.0):
        self.name = name
        self.ip = ip
        self.port = port
        self.reconnect_interval = reconnect_interval
        self.client = None
        self.last_attempt = 0.0

    def ensure_connected(self) -> bool:
        if self.client is not None:
            return True
        now = time.time()
        if now - self.last_attempt < self.reconnect_interval:
            return False
        self.last_attempt = now
        try:
            client = pymcprotocol.Type3E()
            client.setaccessopt(commtype="binary")
            client.connect(self.ip, self.port)
            self.client = client
            print(f" -> PLC 연결 성공: {self.name} ({self.ip}:{self.port})")
            return True
        except Exception as e:
            print(f" -> PLC 연결 대기: {self.name} ({self.ip}:{self.port}) - {e}")
            self.client = None
            return False

    def close(self):
        if self.client is None:
            return
        try:
            self.client.close()
        except Exception:
            pass
        self.client = None

    def read_bit(self, device: str) -> Optional[bool]:
        if not self.ensure_connected():
            return None
        try:
            result = self.client.batchread_bitunits(headdevice=device, readsize=1)
            return bool(result[0])
        except Exception as e:
            print(f" -> PLC 읽기 실패: {self.name} {device} - {e}")
            self.close()
            return None


def _parse_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _build_connections() -> Dict[str, PlcConnection]:
    default_port = _parse_int("PLC_PORT", 2000)
    process_ip = os.getenv("PLC_PROCESS_IP", os.getenv("PLC_IP", "192.168.3.150"))
    process_port = _parse_int("PLC_PROCESS_PORT", default_port)
    monitor_ip = os.getenv("PLC_MONITOR_IP", "192.168.3.160")
    monitor_port = _parse_int("PLC_MONITOR_PORT", default_port)

    connections = {
        "process": PlcConnection("process", process_ip, process_port),
        "monitor": PlcConnection("monitor", monitor_ip, monitor_port),
    }
    return connections


def _done_watches() -> Iterable[SignalWatch]:
    raw_map = os.getenv("PLC_DONE_SIGNAL_MAP", "PLC150:M1150,PLC130:M1130,PLC120:M1120")
    for item in [chunk.strip() for chunk in raw_map.split(",") if chunk.strip()]:
        if ":" not in item:
            print(f" -> PLC_DONE_SIGNAL_MAP 항목 무시: {item}")
            continue
        station_id, device = [part.strip() for part in item.split(":", 1)]
        yield SignalWatch(
            signal="process_done",
            source="monitor",
            device=device,
            topic="plc/process/done",
            station_id=station_id,
            description=f"{station_id} 공정 종료",
        )


def _build_watches() -> list[SignalWatch]:
    process_start = os.getenv("PLC_PROCESS_START_DEVICE", "X11")
    process_stop = os.getenv("PLC_PROCESS_STOP_DEVICE", "X12")
    robot_complete = os.getenv("PLC_ROBOT_COMPLETE_DEVICE", "X145")
    robot_start_output = os.getenv("PLC_ROBOT_START_OUTPUT", "Y160")
    robot_start_di = os.getenv("ROBOT_START_DI", "DI0")

    watches = [
        SignalWatch(
            signal="process_start",
            source="process",
            device=process_start,
            topic="plc/process/start",
            description="공정 시작 입력",
        ),
        SignalWatch(
            signal="process_stop",
            source="process",
            device=process_stop,
            topic="plc/process/stop",
            description="공정 정지 입력",
        ),
        SignalWatch(
            signal="robot_complete",
            source="process",
            device=robot_complete,
            topic="plc/robot/complete",
            description="로봇 완료 신호",
        ),
    ]
    watches.extend(_done_watches())

    print(" -> PLC 신호 맵")
    print(f"    공정 시작: {process_start}")
    print(f"    공정 정지: {process_stop}")
    print(f"    로봇 시작 배선: PLC {robot_start_output} -> Robot {robot_start_di}")
    print(f"    로봇 완료: {robot_complete}")
    for watch in watches:
        if watch.signal == "process_done":
            print(f"    종료 DB: {watch.station_id} {watch.device}")
    return watches


def _publish_event(mqtt_client: MqttManager, watch: SignalWatch, value: bool, edge: str, plc: PlcConnection):
    payload = {
        "signal": watch.signal,
        "station_id": watch.station_id,
        "device": watch.device,
        "value": 1 if value else 0,
        "edge": edge,
        "source": watch.source,
        "plc_name": plc.name,
        "plc_ip": plc.ip,
        "plc_port": plc.port,
        "description": watch.description,
        "ts": _now_iso(),
    }
    mqtt_client.publish("plc/signal", payload)
    if edge == "rising":
        mqtt_client.publish(watch.topic, payload)
        print(f">> [PLC] {watch.topic} {watch.device}=ON ({watch.station_id or watch.signal})")


def main():
    broker_ip = os.getenv("MQTT_BROKER", "127.0.0.1")
    broker_port = _parse_int("MQTT_PORT", 1883)
    poll_interval = _env_float("PLC_SCAN_INTERVAL_SEC", 0.1)
    publish_initial_state = _env_bool("PLC_PUBLISH_INITIAL_STATE", True)

    mqtt_client = MqttManager(broker_ip=broker_ip, port=broker_port, client_id="plc_bridge")
    mqtt_client.connect_and_loop()

    if pymcprotocol is None:
        print(" -> PLC 통신 라이브러리가 없어 대기 모드로 동작합니다.")
        while True:
            time.sleep(1)

    connections = _build_connections()
    watches = _build_watches()
    previous: Dict[str, Optional[bool]] = {watch.signal + watch.device: None for watch in watches}

    print(f" -> MQTT 브로커: {broker_ip}:{broker_port}")
    print(f" -> PLC 스캔 주기: {poll_interval:.3f}s")
    print(" -> 읽기 전용 모드: PLC가 메인 제어권을 가지며, 이 서비스는 신호를 감시/기록만 합니다.")

    while True:
        for watch in watches:
            plc = connections.get(watch.source)
            if plc is None:
                continue
            current = plc.read_bit(watch.device)
            if current is None:
                continue

            key = watch.signal + watch.device
            before = previous.get(key)
            if before is None:
                previous[key] = current
                if publish_initial_state:
                    _publish_event(mqtt_client, watch, current, "initial", plc)
                continue

            if current == before:
                continue

            previous[key] = current
            edge = "rising" if current else "falling"
            _publish_event(mqtt_client, watch, current, edge, plc)

        time.sleep(poll_interval)


if __name__ == "__main__":
    main()
