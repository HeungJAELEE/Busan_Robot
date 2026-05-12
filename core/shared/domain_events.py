from abc import ABC
import uuid
from datetime import datetime

class DomainEvent(ABC):
    """모든 도메인 이벤트의 최상위 추상 클래스"""
    def __init__(self, aggregate_id: str):
        self.event_id = str(uuid.uuid4())
        self.aggregate_id = aggregate_id
        self.occurred_on = datetime.now()
        self.event_version = 1

class PlcDataReceivedEvent(DomainEvent):
    """PLC로부터 작업 지시 데이터를 수신했을 때 발생하는 이벤트"""
    def __init__(self, aggregate_id: str, data: list):
        super().__init__(aggregate_id)
        self.data = data

class MotionCompletedEvent(DomainEvent):
    """로봇 모션(Pick & Place 등)이 성공적으로 완료되었을 때 발생하는 이벤트"""
    def __init__(self, aggregate_id: str, result_data: list):
        super().__init__(aggregate_id)
        self.result_data = result_data

class MqttCommandReceivedEvent(DomainEvent):
    """MQTT를 통해 로봇 명령을 수신했을 때 발생하는 이벤트"""
    def __init__(self, aggregate_id: str, command: str):
        super().__init__(aggregate_id)
        self.command = command
