import sys
import os
import time
import json
import threading
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.infrastructure.mqtt_manager import MqttManager

try:
    import websockets
except ImportError:
    print(">> websockets 모듈이 필요합니다. (pip install websockets)")
    websockets = None

print("🌍 [Digital Twin] 시작됨 - MSA 환경")

connected_clients = set()

async def ws_handler(websocket, path):
    """웹 브라우저 클라이언트가 접속하면 소켓 유지"""
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)

def on_realtime_data(payload):
    """로봇 실시간 데이터를 받아 웹소켓 클라이언트들에게 브로드캐스트"""
    if websockets and connected_clients:
        message = json.dumps(payload)
        # asyncio loop thread-safe 호출
        for ws in connected_clients:
            asyncio.run_coroutine_threadsafe(ws.send(message), loop)

def start_mqtt():
    broker_ip = os.getenv("MQTT_BROKER", "127.0.0.1")
    broker_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_client = MqttManager(broker_ip=broker_ip, port=broker_port, client_id="digital_twin")
    mqtt_client.subscribe("robot/realtime", on_realtime_data)
    mqtt_client.connect_and_loop()

def main():
    global loop
    loop = asyncio.get_event_loop()
    websocket_port = int(os.getenv("DIGITAL_TWIN_PORT", "8080"))
    
    # MQTT는 백그라운드 스레드로 실행
    threading.Thread(target=start_mqtt, daemon=True).start()

    if websockets is None:
        print(" -> 웹소켓 서버를 열 수 없습니다. 더미 모드로 동작합니다.")
        while True:
            time.sleep(1)

    print(f" -> 3D 뷰어용 웹소켓 스트리밍 서버 오픈 (ws://0.0.0.0:{websocket_port})")
    start_server = websockets.serve(ws_handler, "0.0.0.0", websocket_port)
    loop.run_until_complete(start_server)
    loop.run_forever()

if __name__ == "__main__":
    main()
