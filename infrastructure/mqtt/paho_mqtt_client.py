import paho.mqtt.client as mqtt
from core.shared.event_bus import DomainEventBus
from core.shared.domain_events import MqttCommandReceivedEvent

class PahoMqttClient:
    """MQTT 브로커와 통신하고 이벤트를 발생시키는 인프라 구현체"""
    def __init__(self, broker: str, port: int, topic: str, event_bus: DomainEventBus):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.event_bus = event_bus
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"📡 [MQTT Infra] 연결 성공! Topic '{self.topic}' 구독 중...")
        self.client.subscribe(self.topic)

    def _on_message(self, client, userdata, msg):
        command = msg.payload.decode()
        print(f"📥 [MQTT Infra] 메시지 수신: {command}")
        
        # 도메인 이벤트 발행 (명령 수신)
        event = MqttCommandReceivedEvent("MQTT_001", command)
        self.event_bus.publish(event)

    def connect_and_start(self):
        try:
            self.client.connect(self.broker, self.port, 600)
            self.client.loop_start()  # 백그라운드 스레드에서 실행
        except Exception as e:
            print(f"❌ [MQTT Infra] 연결 실패: {e}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        print("📡 [MQTT Infra] 연결 종료")
