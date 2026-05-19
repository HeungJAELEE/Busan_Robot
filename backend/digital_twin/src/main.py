import asyncio
import json
import os
import sys
import threading
import time
from pathlib import Path

from aiohttp import WSMsgType, web

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from src.infrastructure.mqtt_manager import MqttManager


print("🌍 [Digital Twin] 시작됨 - Web Monitor + MQTT bridge")

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "web"
ROBOT_IDS = ("Robot A", "Robot B", "Robot C")

connected_clients = set()
latest_robot_data = {}
latest_connections = {}
latest_events = []
event_lock = threading.Lock()
main_loop = None


def _json_default(value):
    try:
        return float(value)
    except Exception:
        return str(value)


def _remember_event(topic, payload):
    with event_lock:
        latest_events.append({
            "topic": topic,
            "payload": payload,
            "created_at": time.time(),
        })
        del latest_events[:-80]


async def _broadcast(topic, payload):
    if not connected_clients:
        return
    message = json.dumps({"topic": topic, "payload": payload}, ensure_ascii=False, default=_json_default)
    dead = []
    for ws in list(connected_clients):
        try:
            await ws.send_str(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connected_clients.discard(ws)


def _schedule_broadcast(topic, payload):
    if main_loop is None:
        return
    asyncio.run_coroutine_threadsafe(_broadcast(topic, payload), main_loop)


def _on_realtime_data(payload):
    robot_id = str(payload.get("robot_id", "Unknown")) if isinstance(payload, dict) else "Unknown"
    if isinstance(payload, dict):
        latest_robot_data[robot_id] = payload
    _schedule_broadcast("robot/realtime", payload)


def _on_connection(payload):
    robot_id = str(payload.get("robot_id", "Unknown")) if isinstance(payload, dict) else "Unknown"
    if isinstance(payload, dict):
        latest_connections[robot_id] = payload
    _remember_event("robot/connection", payload)
    _schedule_broadcast("robot/connection", payload)


def _on_event(topic):
    def handler(payload):
        _remember_event(topic, payload)
        _schedule_broadcast(topic, payload)
    return handler


def _mqtt_thread():
    broker_ip = os.getenv("MQTT_BROKER", "127.0.0.1")
    broker_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_client = MqttManager(broker_ip=broker_ip, port=broker_port, client_id="digital_twin_web")
    mqtt_client.subscribe("robot/realtime", _on_realtime_data)
    mqtt_client.subscribe("robot/connection", _on_connection)
    mqtt_client.subscribe("robot/accepted", _on_event("robot/accepted"))
    mqtt_client.subscribe("robot/result", _on_event("robot/result"))
    mqtt_client.subscribe("robot/error", _on_event("robot/error"))
    mqtt_client.subscribe("robot/task_done", _on_event("robot/task_done"))
    mqtt_client.subscribe("plc/process/start", _on_event("plc/process/start"))
    mqtt_client.subscribe("plc/process/stop", _on_event("plc/process/stop"))
    mqtt_client.subscribe("plc/process/done", _on_event("plc/process/done"))
    mqtt_client.connect_and_loop()
    while True:
        time.sleep(60)


def _snapshot():
    return {
        "topic": "digital_twin/snapshot",
        "payload": {
            "robots": {robot_id: latest_robot_data.get(robot_id, {}) for robot_id in ROBOT_IDS},
            "connections": {robot_id: latest_connections.get(robot_id, {}) for robot_id in ROBOT_IDS},
            "events": list(latest_events[-20:]),
            "server_time": time.time(),
        },
    }


async def index(request):
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await websocket_handler(request)
    return web.FileResponse(STATIC_DIR / "index.html")


async def health(request):
    return web.json_response(_snapshot()["payload"], dumps=lambda data: json.dumps(data, ensure_ascii=False, default=_json_default))


async def websocket_handler(request):
    ws = web.WebSocketResponse(heartbeat=25)
    await ws.prepare(request)
    connected_clients.add(ws)
    await ws.send_str(json.dumps(_snapshot(), ensure_ascii=False, default=_json_default))

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT and msg.data.strip().lower() == "snapshot":
                await ws.send_str(json.dumps(_snapshot(), ensure_ascii=False, default=_json_default))
            elif msg.type == WSMsgType.ERROR:
                break
    finally:
        connected_clients.discard(ws)
    return ws


async def run_server():
    global main_loop
    main_loop = asyncio.get_running_loop()
    threading.Thread(target=_mqtt_thread, daemon=True, name="digital-twin-mqtt").start()

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/ws", websocket_handler)
    app.router.add_get("/health", health)
    app.router.add_static("/static", STATIC_DIR, show_index=False)

    port = int(os.getenv("DIGITAL_TWIN_PORT", "8080"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f" -> 웹 모니터 오픈: http://0.0.0.0:{port}")
    print(f" -> WebSocket: ws://0.0.0.0:{port}/ws")
    await asyncio.Event().wait()


def main():
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
