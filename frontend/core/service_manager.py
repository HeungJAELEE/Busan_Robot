"""
서비스 매니저 — 백엔드 마이크로서비스를 UI에서 ON/OFF 토글로 제어
각 서비스는 Python 백그라운드 스레드로 실행되며, 도커 없이도 동작합니다.
"""
import threading
import time
import os
import json


class ServiceRunner:
    """개별 서비스의 실행 상태를 관리하는 래퍼"""
    def __init__(self, name, icon, run_func, description=""):
        self.name = name
        self.icon = icon
        self.description = description
        self._run_func = run_func
        self._thread = None
        self._stop_event = threading.Event()
        self.is_running = False
        self.status_message = "⚪ 대기"

    def start(self):
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._safe_run, daemon=True)
        self._thread.start()
        self.is_running = True
        self.status_message = "🟢 실행 중"

    def stop(self):
        self._stop_event.set()
        self.is_running = False
        self.status_message = "🔴 중지됨"

    def _safe_run(self):
        try:
            self._run_func(self._stop_event)
        except Exception as e:
            self.status_message = f"⚠️ 에러: {str(e)[:30]}"
            self.is_running = False


# ─────────────────────────────────────────────
# 각 서비스별 실행 함수 (stop_event로 안전하게 종료)
# ─────────────────────────────────────────────

def _run_mqtt_broker_check(stop_event):
    """MQTT 브로커 연결 상태 체크 (실제 Mosquitto 서버가 필요)"""
    import paho.mqtt.client as mqtt
    print("📮 [MQTT] 브로커 연결 확인 중...")
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "service_check")
        client.connect("127.0.0.1", 1883, 10)
        print("📮 [MQTT] ✅ 브로커 연결 성공 (127.0.0.1:1883)")
        client.loop_start()
        while not stop_event.is_set():
            time.sleep(1)
        client.loop_stop()
        client.disconnect()
        print("📮 [MQTT] 연결 해제 완료")
    except Exception as e:
        print(f"📮 [MQTT] ❌ 브로커 연결 실패: {e}")
        print("📮 [MQTT] → Mosquitto 서버가 실행 중인지 확인하세요")
        raise


def _run_plc_bridge(stop_event):
    """PLC 브리지 — 미쓰비시 PLC master 신호 감시"""
    print("⚙️ [PLC Bridge] 서비스 시작...")
    plc_ip = os.getenv("PLC_PROCESS_IP", os.getenv("PLC_IP", "192.168.3.150"))
    plc_port = int(os.getenv("PLC_PROCESS_PORT", os.getenv("PLC_PORT", "2000")))
    start_device = os.getenv("PLC_PROCESS_START_DEVICE", "X11")
    stop_device = os.getenv("PLC_PROCESS_STOP_DEVICE", "X12")
    complete_device = os.getenv("PLC_ROBOT_COMPLETE_DEVICE", "X145")
    print(f"⚙️ [PLC Bridge] PLC IP: {plc_ip}:{plc_port} (읽기 전용 감시)")
    
    try:
        import pymcprotocol
        pymc3e = pymcprotocol.Type3E()
        pymc3e.setaccessopt(commtype="binary")
        pymc3e.connect(plc_ip, plc_port)
        print(f"⚙️ [PLC Bridge] ✅ PLC 연결 성공!")
        prev_values = {}
        while not stop_event.is_set():
            for label, device in (
                ("공정 시작", start_device),
                ("공정 정지", stop_device),
                ("로봇 완료", complete_device),
            ):
                val = bool(pymc3e.batchread_bitunits(headdevice=device, readsize=1)[0])
                if prev_values.get(device) != val:
                    print(f"⚙️ [PLC Bridge] {label} {device}: {int(val)}")
                    prev_values[device] = val
            time.sleep(0.1)
        pymc3e.close()
    except ImportError:
        print("⚙️ [PLC Bridge] pymcprotocol 미설치 → 시뮬레이션 모드")
        while not stop_event.is_set():
            time.sleep(1)
    except Exception as e:
        print(f"⚙️ [PLC Bridge] ❌ 연결 실패: {e}")
        print("⚙️ [PLC Bridge] → 시뮬레이션 모드로 전환")
        while not stop_event.is_set():
            time.sleep(1)


def _run_vision_yolo(stop_event):
    """Vision YOLO — 카메라 캡처 시뮬레이션"""
    print("👁 [Vision YOLO] 서비스 시작...")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("👁 [Vision YOLO] ✅ 카메라 연결 성공!")
            while not stop_event.is_set():
                ret, frame = cap.read()
                if ret:
                    # TODO: YOLO 추론 로직 추가
                    pass
                time.sleep(0.1)
            cap.release()
        else:
            print("👁 [Vision YOLO] ❌ 카메라 없음 → 시뮬레이션 모드")
            while not stop_event.is_set():
                time.sleep(1)
    except ImportError:
        print("👁 [Vision YOLO] opencv 미설치 → 시뮬레이션 모드")
        while not stop_event.is_set():
            time.sleep(1)


def _run_db_worker(stop_event):
    """DB Worker — MySQL 연결 확인"""
    print("🗄 [DB Worker] 서비스 시작...")
    db_host = os.getenv("DB_HOST", "192.168.3.141")
    print(f"🗄 [DB Worker] DB Host: {db_host}")
    
    try:
        import pymysql
        conn = pymysql.connect(
            host=db_host, user=os.getenv("DB_USER", "guest"),
            password=os.getenv("DB_PASS", "guest1234"),
            database=os.getenv("DB_NAME", "faictory_mes"), connect_timeout=5
        )
        print("🗄 [DB Worker] ✅ DB 연결 성공!")
        while not stop_event.is_set():
            time.sleep(1)
        conn.close()
    except ImportError:
        print("🗄 [DB Worker] PyMySQL 미설치 → 시뮬레이션 모드")
        while not stop_event.is_set():
            time.sleep(1)
    except Exception as e:
        print(f"🗄 [DB Worker] ❌ DB 연결 실패: {e}")
        print("🗄 [DB Worker] → 시뮬레이션 모드로 전환")
        while not stop_event.is_set():
            time.sleep(1)


def _run_digital_twin(stop_event):
    """Digital Twin — 웹소켓 서버"""
    print("🌍 [Digital Twin] 서비스 시작...")
    try:
        import asyncio
        import websockets
        
        connected = set()
        
        async def handler(ws, path):
            connected.add(ws)
            print(f"🌍 [Digital Twin] 클라이언트 접속 (총 {len(connected)})")
            try:
                async for msg in ws:
                    pass
            finally:
                connected.discard(ws)
        
        async def serve():
            server = await websockets.serve(handler, "0.0.0.0", 8080)
            print("🌍 [Digital Twin] ✅ 웹소켓 서버 실행 (ws://0.0.0.0:8080)")
            while not stop_event.is_set():
                await asyncio.sleep(0.5)
            server.close()
        
        asyncio.run(serve())
    except ImportError:
        print("🌍 [Digital Twin] websockets 미설치 → 시뮬레이션 모드")
        while not stop_event.is_set():
            time.sleep(1)
    except Exception as e:
        print(f"🌍 [Digital Twin] ❌ 에러: {e}")
        while not stop_event.is_set():
            time.sleep(1)


# ─────────────────────────────────────────────
# 서비스 매니저 (전역 싱글톤)
# ─────────────────────────────────────────────

class ServiceManager:
    """모든 백엔드 서비스를 중앙 관리"""
    def __init__(self):
        self.services = {
            "mqtt":         ServiceRunner("MQTT Broker",     "📮", _run_mqtt_broker_check, "메시지 브로커 연결"),
            "plc":          ServiceRunner("PLC Bridge",      "⚙️", _run_plc_bridge,       "미쓰비시 PLC 통신"),
            "vision":       ServiceRunner("Vision YOLO",     "👁", _run_vision_yolo,       "카메라 YOLO 추론"),
            "db":           ServiceRunner("DB Worker",       "🗄", _run_db_worker,         "MySQL DB 연결"),
            "digital_twin": ServiceRunner("Digital Twin",    "🌍", _run_digital_twin,      "웹소켓 3D 서버"),
        }

    def toggle(self, key):
        svc = self.services[key]
        if svc.is_running:
            svc.stop()
        else:
            svc.start()
        return svc.is_running

    def stop_all(self):
        for svc in self.services.values():
            if svc.is_running:
                svc.stop()


# 전역 인스턴스
service_mgr = ServiceManager()
