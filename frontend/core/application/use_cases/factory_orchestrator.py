import time
import json
from core.domains.motion_management.entities import RobotEntity
from core.domains.plc_communication.repositories import IPlcRepository
from core.domains.mes_integration.repositories import IMesRepository
from core.shared.event_bus import DomainEventBus
from core.shared.domain_events import MqttCommandReceivedEvent

class FactoryAutomationUseCase:
    """
    [Application 계층] 공장 자동화의 주된 비즈니스 흐름(Use Case)을 지휘합니다.
    JSON 설정을 읽어 PLC 주소를 세팅하고, 연속 루프(M100) 및 MES 연동 로직을 처리합니다.
    """
    def __init__(self, 
                 plc_repo: IPlcRepository, 
                 robot: RobotEntity, 
                 mes_repo: IMesRepository,
                 event_bus: DomainEventBus,
                 config_path: str = "config/plc_config.json"):
        self.plc = plc_repo
        self.robot = robot
        self.mes = mes_repo
        self.event_bus = event_bus
        self.config_path = config_path

        # PLC 주소 설정 로드
        self.plc_config = self._load_config()
        self.ADDR_START = self.plc_config.get("cycle_start", "M100")
        self.ADDR_RUNNING = self.plc_config.get("cycle_complete", "M101") # 동작 중/완료 신호

    def _load_config(self) -> dict:
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                return data.get("addresses", {})
        except Exception as e:
            print(f"⚠️ [App UseCase] PLC 설정 파일 로드 실패: {e}")
            return {"cycle_start": "M100", "cycle_complete": "M101"}

    def handle_mqtt_command(self, event: MqttCommandReceivedEvent):
        """MQTT로 들어온 비동기 명령 처리기"""
        cmd = event.command.strip()
        print(f"🎮 [App UseCase] MQTT 원격 명령 수신: {cmd}")
        if cmd == "1":
            self.robot.go_home()
        elif cmd == "2":
            self.robot.go_zero()

    def _execute_continuous_loop(self):
        print(f"🔔 [App UseCase] 연속 동작 시작 ({self.ADDR_START} ON 감지)")
        
        # M100이 살아있는 동안 무한 반복
        while self.plc.read_bit(self.ADDR_START) == 1:
            # 1. 유리창 케이스 조립 (회전 포함)
            print("▶️ 공정 1: 장난감 자동차 유리 조립")
            success = self.robot.perform_pick_and_place_glass()
            if success:
                # MES 로깅 (1~6축 좌표)
                current_pos = self.robot.get_current_joint_pos()
                self.mes.log_robot_position(self.robot.robot_id, "Pick&Place_Glass", current_pos)
            
            # M100이 중간에 꺼지면 즉시 중단
            if self.plc.read_bit(self.ADDR_START) == 0:
                break
                
            # 2. 유리창 케이스 투입/배출
            print("▶️ 공정 2: 유리창 케이스 투입 배출")
            success = self.robot.perform_pick_and_place_case()
            if success:
                current_pos = self.robot.get_current_joint_pos()
                self.mes.log_robot_position(self.robot.robot_id, "Pick&Place_Case", current_pos)

            # 도메인에서 발행된 이벤트들(MotionCompletedEvent 등) 버스에 태우기
            for event in self.robot.get_uncommitted_events():
                self.event_bus.publish(event)
                
            time.sleep(0.1)

        # 동작이 완전히 완료(또는 중단)되면 M101 끄기
        print(f"✅ [App UseCase] 동작 종료. {self.ADDR_RUNNING} OFF")
        self.plc.write_bit(self.ADDR_RUNNING, 0)


    def execute_loop(self):
        """무한 반복되는 핵심 공장 자동화 루프"""
        self.plc.connect()
        self.robot.connect()
        self.mes.connect()
        print("🚀 [App UseCase] 공장 자동화 연속 루프가 시작되었습니다.")

        try:
            while True:
                # M100 체크
                if self.plc.read_bit(self.ADDR_START) == 1:
                    # 동작 중임을 알리기 위해 M101을 ON 시켜둘 수 있음 (사용자 요구사항에 따라 조율)
                    # "동작이 완료되면 M101이 꺼지고" 라고 하셨으니 시작할 땐 켜는 것으로 추론
                    self.plc.write_bit(self.ADDR_RUNNING, 1)
                    
                    self._execute_continuous_loop()
                
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n👋 [App UseCase] 사용자에 의해 시스템이 종료됩니다.")
        except Exception as e:
            print(f"\n❌ [App UseCase] 에러 발생: {e}")
        finally:
            self.mes.disconnect()
            self.robot.disconnect()
            self.plc.disconnect()
