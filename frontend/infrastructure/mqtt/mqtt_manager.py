import paho.mqtt.client as mqtt
import json
import threading
import time

class MqttManager:
    """
    마이크로서비스 간의 통신을 담당하는 MQTT 공통 매니저
    """
    def __init__(self, broker_ip="127.0.0.1", port=1883, client_id=""):
        self.broker_ip = broker_ip
        self.port = port
        self.client_id = client_id
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)
        self.callbacks = {}
        self.connected = False
        self._loop_started = False

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        self.connected = (rc == 0)
        print(f">> [MQTT] 브로커({self.broker_ip}) 연결 성공 (코드: {rc})")
        # 등록된 토픽들 다시 구독
        for topic in self.callbacks.keys():
            self.client.subscribe(topic)

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc:
            print(f">> [MQTT] 브로커 연결 끊김 (코드: {rc})")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except:
            payload = msg.payload.decode('utf-8')

        if topic in self.callbacks:
            self.callbacks[topic](payload)

    def connect_and_loop(self):
        if self._loop_started:
            return True
        self._loop_started = True

        def _run():
            attempt = 0
            while True:
                try:
                    attempt += 1
                    self.client.connect(self.broker_ip, self.port, 60)
                    attempt = 0
                    self.client.loop_forever()
                except Exception as e:
                    self.connected = False
                    if attempt in (1, 2) or attempt % 15 == 0:
                        print(f">> [MQTT] 연결 실패: {e} — 2초 후 재시도")
                    time.sleep(2)

        threading.Thread(target=_run, daemon=True).start()
        return True

    def subscribe(self, topic, callback):
        self.callbacks[topic] = callback
        try:
            self.client.subscribe(topic)
        except Exception:
            pass

    def publish(self, topic, payload):
        if isinstance(payload, dict) or isinstance(payload, list):
            payload = json.dumps(payload, ensure_ascii=False)
        self.client.publish(topic, payload)

# 싱글톤처럼 쓸 수 있는 기본 인스턴스 (필요 시 각 모듈에서 재정의 가능)
mqtt_broker = MqttManager()
