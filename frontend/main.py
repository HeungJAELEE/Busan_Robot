import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.runtime_config import env_bool, mqtt_config, mysql_config, plc_config, robot_defaults, robot_model


def _launch_ui():
    from presentation.ui.main_window import ModernContyApp

    app = ModernContyApp()
    app.mainloop()


def _launch_legacy_orchestrator():
    from core.kernel.flow_kernel import ClaudeFlowKernel
    from infrastructure.plc.pymc_client import PyMcPlcClient
    from infrastructure.mqtt.paho_mqtt_client import PahoMqttClient
    from infrastructure.db.mysql_client import MySqlMesClient
    from core.domains.motion_management.entities import RobotEntity
    from core.application.use_cases.factory_orchestrator import FactoryAutomationUseCase
    from core.shared.domain_events import MotionCompletedEvent, MqttCommandReceivedEvent

    def on_motion_completed(event: MotionCompletedEvent):
        print(f"[Event Handler] 로봇 {event.aggregate_id} 작업 완료: {event.result_data}")

    kernel = ClaudeFlowKernel()
    plc = plc_config()
    mqtt = mqtt_config()
    mysql = mysql_config()
    robots = robot_defaults()
    default_robot_id = os.getenv("DEFAULT_ROBOT_ID", "Robot A")
    robot_ip = robots.get(default_robot_id, robots["Robot A"]).get("ip", "")

    plc_client = PyMcPlcClient(ip=plc["process_ip"], port=plc["process_port"])
    robot = RobotEntity(
        robot_id=default_robot_id,
        ip=robot_ip,
        name=robot_model(),
        config_path=os.getenv("MOTION_CONFIG_PATH", "config/motion_config.json"),
    )
    mqtt_client = PahoMqttClient(
        broker=mqtt["broker"],
        port=mqtt["port"],
        topic=os.getenv("MQTT_COMMAND_TOPIC", "robot/command"),
        event_bus=kernel.event_bus,
    )
    mes_client = MySqlMesClient(
        host=mysql["host"],
        user=mysql["user"],
        password=mysql["password"],
        database=mysql["db"],
        port=mysql["port"],
    )

    kernel.register_service("plc_client", plc_client)
    kernel.register_service("robot", robot)
    kernel.register_service("mqtt_client", mqtt_client)
    kernel.register_service("mes_client", mes_client)

    orchestrator = FactoryAutomationUseCase(
        plc_repo=kernel.get_service("plc_client"),
        robot=kernel.get_service("robot"),
        mes_repo=kernel.get_service("mes_client"),
        event_bus=kernel.event_bus,
        config_path=os.getenv("PLC_CONFIG_PATH", "config/plc_config.json"),
    )

    kernel.event_bus.subscribe(MotionCompletedEvent, on_motion_completed)
    kernel.event_bus.subscribe(MqttCommandReceivedEvent, orchestrator.handle_mqtt_command)

    mqtt_client.connect_and_start()
    try:
        orchestrator.execute_loop()
    finally:
        mqtt_client.disconnect()


def main():
    # Default path is the HMI UI. It must open without touching real hardware.
    if not env_bool("FACTORY_ORCHESTRATOR_AUTOSTART", False):
        print("[BOOT] UI-only mode. Robot/PLC/DB hardware connects only after a user button action.")
        _launch_ui()
        return

    print("[BOOT] FACTORY_ORCHESTRATOR_AUTOSTART=1: legacy PLC/MES orchestrator will connect now.")
    _launch_legacy_orchestrator()


if __name__ == "__main__":
    main()
