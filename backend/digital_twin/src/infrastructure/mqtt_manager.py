import paho.mqtt.client as mqtt
import json
import threading
import time

class MqttManager:
    def __init__(self, broker_ip="127.0.0.1", port=1883, client_id=""):
        self.broker_ip = broker_ip
        self.port = port
        self.client_id = client_id
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id)
        self.callbacks = {}
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        for topic in self.callbacks.keys():
            self.client.subscribe(topic)

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try: payload = json.loads(msg.payload.decode('utf-8'))
        except: payload = msg.payload.decode('utf-8')
        if topic in self.callbacks: self.callbacks[topic](payload)

    def connect_and_loop(self):
        while True:
            try:
                self.client.connect(self.broker_ip, self.port, 60)
                break
            except Exception as e:
                print(f">> [MQTT] 연결 실패 {self.broker_ip}:{self.port} - {e}. 2초 후 재시도")
                time.sleep(2)
        threading.Thread(target=self.client.loop_forever, daemon=True).start()

    def subscribe(self, topic, callback):
        self.callbacks[topic] = callback
        self.client.subscribe(topic)

    def publish(self, topic, payload):
        if isinstance(payload, dict) or isinstance(payload, list): payload = json.dumps(payload)
        self.client.publish(topic, payload)
