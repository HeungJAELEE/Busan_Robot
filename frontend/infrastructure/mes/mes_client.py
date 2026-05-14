import time
import threading
from core.shared.event_store import global_event_store

class MesClient:
    """
    Mock MES (Manufacturing Execution System) Client.
    Listens to EventStore for Job Completed events and sends them to the remote MES server.
    """
    def __init__(self, mes_url="http://192.168.3.200:8080/api/v1/telemetry"):
        self.mes_url = mes_url
        self._running = False
        self._thread = None
        self._last_processed_idx = 0
        
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._poll_events, daemon=True)
        self._thread.start()
        print(f">> 🏭 [MES] MES 연동 클라이언트 시작됨 (Target: {self.mes_url})")
        
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            
    def _poll_events(self):
        while self._running:
            all_events = global_event_store.get_all_events()
            new_events = all_events[self._last_processed_idx:]
            
            for event in new_events:
                # MES에는 궤적(Trail) 데이터는 너무 많으므로 생략하고, 주요 상태만 전송 (예: 상태 변경, 에러)
                if event.event_type in ["JobStarted", "JobCompleted", "ErrorDetected"]:
                    self._send_to_mes(event)
                    
            self._last_processed_idx = len(all_events)
            
            # Non-blocking sleep loop
            for _ in range(20):
                if not self._running: break
                time.sleep(0.1)
            
    def _send_to_mes(self, event):
        # Requests 모듈로 HTTP POST 전송을 모사
        payload = {
            "robot_id": event.aggregate_id,
            "status": event.event_type,
            "timestamp": event.timestamp,
            "details": event.data
        }
        print(f">> 📤 [MES 송신] 데이터 전송 완료: {payload}")

# 싱글톤 인스턴스
mes_client = MesClient()
