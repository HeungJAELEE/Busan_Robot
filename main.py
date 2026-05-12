from core.kernel.flow_kernel import ClaudeFlowKernel
from infrastructure.plc.pymc_client import PyMcPlcClient
from infrastructure.mqtt.paho_mqtt_client import PahoMqttClient
from infrastructure.db.mysql_client import MySqlMesClient
from core.domains.motion_management.entities import RobotEntity
from core.application.use_cases.factory_orchestrator import FactoryAutomationUseCase
from core.shared.domain_events import MotionCompletedEvent, MqttCommandReceivedEvent

def on_motion_completed(event: MotionCompletedEvent):
    """이벤트 버스를 통해 수신된 이벤트 핸들러 예시"""
    print(f"🎉 [Event Handler] 로봇 {event.aggregate_id}의 작업이 완료되었습니다! (결과: {event.result_data})")

def main():
    # 1. 커널 (DI 컨테이너 및 레지스트리) 초기화
    kernel = ClaudeFlowKernel()

    # 2. 도메인 및 인프라 구현체 초기화
    plc_client = PyMcPlcClient(ip="192.168.3.100", port=1025)
    robot = RobotEntity(robot_id="INDY_001", ip="192.168.3.2", name="NRMK-Indy7", config_path="config/motion_config.json")
    mqtt_client = PahoMqttClient(broker="192.168.3.63", port=1884, topic="robot/command", event_bus=kernel.event_bus)
    mes_client = MySqlMesClient(host="192.168.3.50", user="mes_user", password="mes_password", database="factory_mes", port=3306)

    # 3. 커널에 서비스 등록 (Microkernel Pattern)
    kernel.register_service("plc_client", plc_client)
    kernel.register_service("robot", robot)
    kernel.register_service("mqtt_client", mqtt_client)
    kernel.register_service("mes_client", mes_client)

    # 4. Application Use Case 초기화 (의존성 주입)
    orchestrator = FactoryAutomationUseCase(
        plc_repo=kernel.get_service("plc_client"),
        robot=kernel.get_service("robot"),
        mes_repo=kernel.get_service("mes_client"),
        event_bus=kernel.event_bus,
        config_path="config/plc_config.json"
    )

    # 5. 이벤트 구독 설정 (Event-Driven Communication)
    kernel.event_bus.subscribe(MotionCompletedEvent, on_motion_completed)
    kernel.event_bus.subscribe(MqttCommandReceivedEvent, orchestrator.handle_mqtt_command)

    # 6. 인프라 백그라운드 서비스 시작 (MQTT)
    mqtt_client.connect_and_start()

    # 7. 주 비즈니스 루프(PLC 모니터링 및 MES 연동) 실행 (메인 스레드 점유)
    try:
        orchestrator.execute_loop()
    finally:
        mqtt_client.disconnect()

if __name__ == "__main__":
    main()
