import threading
from core.domains.robot.communication.client_manager import robot_manager

class RobotControlUseCase:
    """
    로봇 기동 제어 Use Case (도메인 서비스).
    UI 계층이 인프라(IndyDCP 클라이언트)의 생(Raw) 메서드에 직접 결합되지 않도록
    기동 로직을 캡슐화합니다.
    """
    
    @staticmethod
    def set_velocity_level(level: int, is_joint: bool = True):
        """
        로봇의 이동 속도 레벨(1~9)을 설정합니다.
        """
        inst = robot_manager.get_active_instance()
        if not inst:
            return False
        try:
            if is_joint:
                inst.set_joint_vel_level(level)
            else:
                inst.set_task_vel_level(level)
            return True
        except Exception as e:
            print(f">> [RobotControlUseCase] 속도 설정 에러: {e}")
            return False

    @staticmethod
    def jog_axis(axis: str, step_amount: float):
        """
        조그 기동: 주어진 축에 대해 지정된 양만큼 이동합니다.
        - J1~J6: 각도(degree)
        - X~Rz: 거리(m) 또는 각도(degree)
        """
        inst = robot_manager.get_active_instance()
        if not inst:
            return False
            
        try:
            if axis in ["J1", "J2", "J3", "J4", "J5", "J6"]:
                q = [0.0] * 6
                idx = ["J1", "J2", "J3", "J4", "J5", "J6"].index(axis)
                q[idx] = step_amount
                threading.Thread(target=inst.joint_move_by, args=(q,), daemon=True).start()
                return True
                
            elif axis in ["X", "Y", "Z", "Rx", "Ry", "Rz"]:
                p = [0.0] * 6
                idx = ["X", "Y", "Z", "Rx", "Ry", "Rz"].index(axis)
                # X, Y, Z는 IndyDCP상 단위가 미터(m)일 수 있으므로 mm로 입력받은 값을 변환
                p[idx] = step_amount * 0.001 if idx < 3 else step_amount
                threading.Thread(target=inst.task_move_by, args=(p,), daemon=True).start()
                return True
        except Exception as e:
            print(f">> [RobotControlUseCase] 조그 기동 에러: {e}")
            
        return False
        
    @staticmethod
    def move_to_joint(q: list):
        """
        저장된 6축 관절 좌표로 절대 이동합니다.
        """
        if not q or len(q) < 6: return False
        
        inst = robot_manager.get_active_instance()
        if not inst:
            return False
            
        try:
            threading.Thread(target=inst.joint_move_to, args=(q,), daemon=True).start()
            return True
        except Exception as e:
            print(f">> [RobotControlUseCase] 관절 기동 에러: {e}")
            return False


    @staticmethod
    def execute_pick_place_sequence(target_p: list, approach_dist_mm: float, approach_dir: str, retract_dist_mm: float, retract_dir: str):
        """
        Pick/Place 동작을 OOD 패턴으로 캡슐화한 메서드.
        주어진 타겟(target_p)에 대해: 투입위치(Approach) -> 정위치(Target) -> 배출위치(Retract)
        순서대로 이동을 수행합니다. 팔레타이징의 개별 포인트(P1, P2, P3 등)에도 동일하게 적용 가능합니다.
        """
        if not target_p or len(target_p) < 6: return False
        
        inst = robot_manager.get_active_instance()
        if not inst:
            print(">> 로봇 인스턴스가 활성화되지 않았습니다.")
            return False
            
        import time
        import copy
        
        from core.domains.robot.use_cases.motion_math import MotionMath
        
        def _sequence_thread():
            app_p = MotionMath.compute_offset_position(target_p, approach_dist_mm, approach_dir)
            ret_p = MotionMath.compute_offset_position(target_p, retract_dist_mm, retract_dir)

            
            print(f">> [OOD] 1. 투입 위치(Approach) 이동: {app_p[:3]}")
            inst.task_move_to(app_p)
            time.sleep(2.0) # 실제로는 move_done_check()가 필요하나 시뮬레이션 편의상 sleep 적용
            
            print(f">> [OOD] 2. 정위치(Target) 이동: {target_p[:3]}")
            inst.task_move_to(target_p)
            time.sleep(2.0)
            
            print(f">> [OOD] 3. 배출 위치(Retract) 이동: {ret_p[:3]}")
            inst.task_move_to(ret_p)
            
        threading.Thread(target=_sequence_thread, daemon=True).start()
        return True

    @staticmethod
    def move_to_task(p: list):

        """
        저장된 TCP Task 좌표로 절대 이동합니다.
        """
        if not p or len(p) < 6: return False
        
        inst = robot_manager.get_active_instance()
        if not inst:
            return False
            
        try:
            threading.Thread(target=inst.task_move_to, args=(p,), daemon=True).start()
            return True
        except Exception as e:
            print(f">> [RobotControlUseCase] 태스크 기동 에러: {e}")
            return False

    @staticmethod
    def stop_robot():
        inst = robot_manager.get_active_instance()
        if inst:
            try:
                threading.Thread(target=inst.stop_motion, daemon=True).start()
            except:
                pass
