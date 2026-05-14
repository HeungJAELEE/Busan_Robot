import paho.mqtt.client as mqtt
import json
import threading

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

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        print(f">> [MQTT] 브로커({self.broker_ip}) 연결 성공 (코드: {rc})")
        # 등록된 토픽들 다시 구독
        for topic in self.callbacks.keys():
            self.client.subscribe(topic)

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except:
            payload = msg.payload.decode('utf-8')

        if topic in self.callbacks:
            self.callbacks[topic](payload)

    def connect_and_loop(self):
        try:
            self.client.connect(self.broker_ip, self.port, 60)
            threading.Thread(target=self.client.loop_forever, daemon=True).start()
        except Exception as e:
            print(f">> [MQTT] 연결 실패: {e}")

    def subscribe(self, topic, callback):
        self.callbacks[topic] = callback
        self.client.subscribe(topic)

    def publish(self, topic, payload):
        if isinstance(payload, dict) or isinstance(payload, list):
            payload = json.dumps(payload)
        self.client.publish(topic, payload)

# 싱글톤처럼 쓸 수 있는 기본 인스턴스 (필요 시 각 모듈에서 재정의 가능)
mqtt_broker = MqttManager()
