import time
import threading
from core.domains.robot.communication.client_manager import robot_manager
from core.domains.robot.programming_pendant.math_utils import generate_grid, retractionPick

stop_event = threading.Event()

def move_done_check():
    time.sleep(0.2)
    robot = robot_manager.get_active_instance()
    if not robot: return
    
    while True:
        if stop_event.is_set():
            robot.stop_motion()
            time.sleep(0.5)
            raise InterruptedError("강제 중단되었습니다.")
            
        status = robot.get_robot_status()
        if status.get('error') == 1 or status.get('collision') == 1:
            print("\n🚨 [경고] 로봇 에러(또는 충돌)가 감지되었습니다! 에러를 초기화합니다.")
            robot.reset_robot()
            time.sleep(2.0)
            raise InterruptedError("로봇 에러 발생으로 인해 동작이 취소되었습니다.")
            
        if status['movedone'] == 1:
            break
        time.sleep(0.1)

def stoppable_sleep(duration):
    start = time.time()
    robot = robot_manager.get_active_instance()
    while time.time() - start < duration:
        if stop_event.is_set():
            if robot: robot.stop_motion()
            time.sleep(0.5)
            raise InterruptedError("강제 중단되었습니다.")
        time.sleep(0.1)
