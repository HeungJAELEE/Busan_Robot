import threading
import time
from core.domains.robot.communication.client_manager import robot_manager

class RobotControlUseCase:
    """
    로봇 기동 제어 Use Case (도메인 서비스).
    
    IndyDCP 클라이언트 내부에 @socket_connect 데코레이터가 자체 lock을 가지고 있으므로,
    외부에서 추가 lock을 사용하지 않는다. 폴링 스레드와 명령 스레드는
    IndyDCP 내부 lock에 의해 자동으로 순차 처리된다.
    
    [인터락] 펜던트(Conty)가 제어권을 가진 상태에서는 HMI의 이동 명령을 차단한다.
    """
    
    # 글로벌 정지 플래그 (wait_for_move_finish 에서 즉시 반환용)
    _global_stop = False
    _stop_requests = {}
    _command_lock = threading.Lock()
    _motion_gate_until = {}
    _control_gate_until = {}
    _collision_gate = {}
    DEFAULT_MOVE_TIMEOUT_SEC = 240.0
    
    # =========================================================================
    # 0. 인터락 (Interlock) — 제어권 충돌 방지
    # =========================================================================
    
    @staticmethod
    def _active_name(name: str = None) -> str:
        return name or robot_manager.get_active_robot_name()

    @staticmethod
    def _get_instance(name: str = None):
        if name:
            info = robot_manager.get_robot_info(name)
            return info.get("instance") if info else None
        return robot_manager.get_active_instance()

    @staticmethod
    def _claim_gate(gate: dict, name: str, action_name: str, min_gap_sec: float) -> bool:
        now = time.monotonic()
        with RobotControlUseCase._command_lock:
            until = gate.get(name, 0.0)
            if now < until:
                remain = until - now
                print(f">> 🚫 [{action_name}] 명령 보호 중입니다. {remain:.1f}초 후 다시 시도하세요.")
                return False
            gate[name] = now + min_gap_sec
        return True

    @staticmethod
    def _clear_motion_gate(name: str = None):
        name = RobotControlUseCase._active_name(name)
        if not name:
            return
        with RobotControlUseCase._command_lock:
            RobotControlUseCase._motion_gate_until[name] = 0.0

    @staticmethod
    def request_stop(name: str = None):
        """Request a program/motion wait stop. Named requests do not stop other robots."""
        with RobotControlUseCase._command_lock:
            if name:
                RobotControlUseCase._stop_requests[name] = True
            else:
                RobotControlUseCase._global_stop = True

    @staticmethod
    def clear_stop_request(name: str = None):
        with RobotControlUseCase._command_lock:
            if name:
                RobotControlUseCase._stop_requests[name] = False
            else:
                RobotControlUseCase._global_stop = False

    @staticmethod
    def is_stop_requested(name: str = None) -> bool:
        with RobotControlUseCase._command_lock:
            if name:
                return bool(RobotControlUseCase._stop_requests.get(name, False))
            return bool(RobotControlUseCase._global_stop)

    @staticmethod
    def check_interlock(name: str = None) -> tuple:
        """
        로봇이 HMI로부터 이동 명령을 수신할 수 있는 상태인지 확인.
        Returns: (safe: bool, reason: str)
        - safe=True: 명령 전송 가능
        - safe=False: 차단 (reason에 사유 포함)
        """
        inst = RobotControlUseCase._get_instance(name)
        if not inst:
            return (False, "로봇이 연결되지 않았습니다.")
        
        try:
            status = inst.get_robot_status()
        except Exception as e:
            return (False, f"상태 조회 실패: {e}")
        
        # 1. 비상정지 상태
        if status.get('emergency', 0):
            return (False, "비상정지 상태입니다. 리셋 후 시도하세요.")
        
        # 2. 에러 상태
        if status.get('error', 0):
            return (False, "로봇 에러 상태입니다. 리셋 후 시도하세요.")
        
        # 3. 충돌 감지 상태
        if status.get('collision', 0):
            return (False, "충돌이 감지되었습니다. 리셋 후 시도하세요.")
        
        # 4. 다이렉트 티칭 모드 (펜던트가 제어권 보유)
        if status.get('teaching', 0) or status.get('teaching_mode', 0) or status.get('direct_teaching', 0):
            return (False, "⚠️ 펜던트에서 다이렉트 티칭 중입니다. 티칭 종료 후 시도하세요.")
        
        # 5. 이미 동작 중 (다른 명령 실행 중)
        if status.get('busy', 0):
            return (False, "로봇이 현재 동작 중입니다. 완료 후 시도하세요.")
        
        return (True, "OK")
    
    @staticmethod
    def _guard_motion(action_name: str = "이동", name: str = None) -> bool:
        """
        이동 명령 전 인터락 체크. 차단 시 터미널에 경고 출력.
        Returns: True=안전(진행 가능), False=차단
        """
        safe, reason = RobotControlUseCase.check_interlock(name)
        if not safe:
            print(f">> 🚫 [{action_name}] 인터락 차단: {reason}")
            return False
        return True
    
    # =========================================================================
    # 1. 상태 조회 (동기 — UI에서 직접 호출 금지, 폴링 전용)
    # =========================================================================
    
    @staticmethod
    def get_robot_status(name: str = None) -> dict:
        """
        로봇 상태 조회: ready, emergency, collision, error, busy, movedone, home, zero 등
        폴링 루프에서 호출하여 메모장에 기록용.
        """
        if name:
            info = robot_manager.get_robot_info(name)
            inst = info.get("instance") if info else None
        else:
            inst = robot_manager.get_active_instance()
        if not inst:
            return {}
        try:
            return inst.get_robot_status()
        except Exception as e:
            print(f">> [상태 조회 에러] {e}")
            return {}
    
    @staticmethod
    def is_move_finished(name: str = None) -> bool:
        """MoveDoneCheck: 로봇이 이동을 완료했는지 확인"""
        status = RobotControlUseCase.get_robot_status(name)
        return bool(status.get('movedone', 0))
    
    @staticmethod
    def is_robot_ready(name: str = None) -> bool:
        """로봇이 명령 수신 가능 상태인지 확인"""
        status = RobotControlUseCase.get_robot_status(name)
        return bool(status.get('ready', 0))
    
    @staticmethod
    def is_robot_busy(name: str = None) -> bool:
        """로봇이 현재 동작 중인지 확인"""
        status = RobotControlUseCase.get_robot_status(name)
        return bool(status.get('busy', 0))
    
    @staticmethod
    def is_emergency(name: str = None) -> bool:
        """비상정지 상태인지 확인"""
        status = RobotControlUseCase.get_robot_status(name)
        return bool(status.get('emergency', 0))
    
    @staticmethod
    def is_collision(name: str = None) -> bool:
        """충돌 감지 상태인지 확인"""
        status = RobotControlUseCase.get_robot_status(name)
        return bool(status.get('collision', 0))

    @staticmethod
    def _fault_reason(status: dict) -> str:
        if not isinstance(status, dict):
            return ""
        if status.get('emergency', 0):
            return "비상정지"
        if status.get('error', 0):
            return "로봇 에러"
        if status.get('collision', 0):
            return "충돌 감지"
        return ""
    
    @staticmethod
    def wait_for_move_finish(timeout_sec: float = None, name: str = None) -> bool:
        """
        이동 완료까지 블로킹 대기 (타임아웃 포함).
        반드시 백그라운드 스레드에서만 호출할 것!
        """
        inst = RobotControlUseCase._get_instance(name)
        if not inst:
            return False
        timeout_sec = max(float(timeout_sec or 0.0), RobotControlUseCase.DEFAULT_MOVE_TIMEOUT_SEC)
        if getattr(inst, "is_gateway_proxy", False):
            result = inst.wait_for_last_result(timeout_sec)
            if result and result.get("ok") and result.get("target_reached", True):
                return True
            print(f">> [경고] Gateway 이동 완료 확인 실패: {result}")
            return False
        start = time.time()
        while (time.time() - start) < timeout_sec:
            # 로봇별 정지 플래그 체크 — A 정지가 B/C 실행을 끊지 않도록 분리
            if RobotControlUseCase.is_stop_requested(name):
                return False
            try:
                # get_joint_pos 호출로 소켓 통신 → 응답 헤더에서 robot_status 자동 갱신
                inst.get_joint_pos()
                status = inst.get_robot_status()
                fault_reason = RobotControlUseCase._fault_reason(status)
                if fault_reason:
                    RobotControlUseCase.request_stop(name)
                    try:
                        inst.stop_motion()
                    except Exception:
                        pass
                    print(f">> [N.G] {fault_reason} 상태 감지 — 이동 대기 중단")
                    return False
                if status.get('movedone', 0) and not status.get('busy', 0):
                    return True
            except:
                pass
            time.sleep(0.1)
        print(f">> [경고] 이동 완료 대기 타임아웃 ({timeout_sec}초)")
        return False
    
    # =========================================================================
    # 2. 속도/파라미터 설정
    # =========================================================================

    @staticmethod
    def set_velocity_level(level: int, is_joint: bool = True, name: str = None):
        """로봇의 이동 속도 레벨(1~9)을 설정합니다."""
        name = RobotControlUseCase._active_name(name)
        inst = RobotControlUseCase._get_instance(name)
        if not inst:
            return False
        try:
            def _do():
                try:
                    if is_joint:
                        inst.set_joint_vel_level(level)
                    else:
                        inst.set_task_vel_level(level)
                except Exception as e:
                    print(f">> [속도 설정 에러] {e}")
            threading.Thread(target=_do, daemon=True).start()
            return True
        except Exception as e:
            print(f">> [RobotControlUseCase] 속도 설정 에러: {e}")
            return False

    @staticmethod
    def set_collision_level(level: int, name: str = None):
        """충돌 감도 레벨(1~5) 설정. 높을수록 민감."""
        name = RobotControlUseCase._active_name(name)
        inst = RobotControlUseCase._get_instance(name)
        if not inst:
            return False
        now = time.monotonic()
        with RobotControlUseCase._command_lock:
            last_level, until = RobotControlUseCase._collision_gate.get(name, (None, 0.0))
            if last_level == level and now < until:
                return True
            RobotControlUseCase._collision_gate[name] = (level, now + 0.5)
        def _do():
            try:
                inst.set_collision_level(level)
                print(f">> [설정] 충돌 감도: {level}")
            except Exception as e:
                print(f">> [에러] 충돌 감도 설정 실패: {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    @staticmethod
    def set_blend_radius(radius: float, is_joint: bool = True, name: str = None):
        """블렌딩 반경 설정. Joint: 0~23 deg, Task: 0.02~0.2 m"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst:
            return False
        def _do():
            try:
                if is_joint:
                    inst.set_joint_blend_radius(radius)
                else:
                    inst.set_task_blend_radius(radius)
                print(f">> [설정] 블렌딩 반경: {radius}")
            except Exception as e:
                print(f">> [에러] 블렌딩 설정 실패: {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 3. 기본 모션 명령
    # =========================================================================

    @staticmethod
    def jog_axis(axis: str, step_amount: float, name: str = None):
        """조그 기동: 주어진 축에 대해 지정된 양만큼 이동."""
        name = RobotControlUseCase._active_name(name)
        if not RobotControlUseCase._guard_motion("조그", name):
            return False
        if not RobotControlUseCase._claim_gate(RobotControlUseCase._motion_gate_until, name, "조그", 0.08):
            return False
        inst = RobotControlUseCase._get_instance(name)
        if not inst:
            return False
        try:
            def _run(fn, arg):
                try:
                    fn(arg)
                except Exception as e:
                    print(f">> [조그 에러] {e}")

            if axis in ["J1", "J2", "J3", "J4", "J5", "J6"]:
                q = [0.0] * 6
                idx = ["J1", "J2", "J3", "J4", "J5", "J6"].index(axis)
                q[idx] = step_amount
                threading.Thread(target=_run, args=(inst.joint_move_by, q), daemon=True).start()
                return True
            elif axis in ["X", "Y", "Z", "Rx", "Ry", "Rz"]:
                p = [0.0] * 6
                idx = ["X", "Y", "Z", "Rx", "Ry", "Rz"].index(axis)
                p[idx] = step_amount * 0.001 if idx < 3 else step_amount
                threading.Thread(target=_run, args=(inst.task_move_by, p), daemon=True).start()
                return True
        except Exception as e:
            print(f">> [조그 에러] {e}")
        return False
        
    @staticmethod
    def move_to_joint(q: list, name: str = None):
        """저장된 6축 관절 좌표로 절대 이동."""
        if not q or len(q) < 6: return False
        name = RobotControlUseCase._active_name(name)
        if not RobotControlUseCase._guard_motion("관절 이동", name):
            return False
        if not RobotControlUseCase._claim_gate(RobotControlUseCase._motion_gate_until, name, "관절 이동", 0.8):
            return False
        inst = RobotControlUseCase._get_instance(name)
        if not inst:
            return False
        if getattr(inst, "is_gateway_proxy", False):
            return inst.joint_move_to(q)
        try:
            threading.Thread(target=inst.joint_move_to, args=(q,), daemon=True).start()
            return True
        except Exception as e:
            print(f">> [관절 기동 에러] {e}")
            return False

    @staticmethod
    def move_to_task(p: list, name: str = None):
        """저장된 TCP Task 좌표로 절대 이동."""
        if not p or len(p) < 6: return False
        name = RobotControlUseCase._active_name(name)
        if not RobotControlUseCase._guard_motion("태스크 이동", name):
            return False
        if not RobotControlUseCase._claim_gate(RobotControlUseCase._motion_gate_until, name, "태스크 이동", 0.8):
            return False
        inst = RobotControlUseCase._get_instance(name)
        if not inst:
            return False
        if getattr(inst, "is_gateway_proxy", False):
            return inst.task_move_to(p)
        try:
            threading.Thread(target=inst.task_move_to, args=(p,), daemon=True).start()
            return True
        except Exception as e:
            print(f">> [태스크 기동 에러] {e}")
            return False

    @staticmethod
    def move_j(q: list, name: str = None):
        """move_to_joint의 별칭"""
        return RobotControlUseCase.move_to_joint(q, name)

    @staticmethod
    def move_l(p: list, name: str = None):
        """move_to_task의 별칭"""
        return RobotControlUseCase.move_to_task(p, name)

    @staticmethod
    def go_home(name: str = None):
        """홈 위치(Home Position)로 이동"""
        name = RobotControlUseCase._active_name(name)
        if not RobotControlUseCase._guard_motion("Home 이동", name):
            return False
        if not RobotControlUseCase._claim_gate(RobotControlUseCase._motion_gate_until, name, "Home 이동", 0.8):
            return False
        inst = RobotControlUseCase._get_instance(name)
        if not inst:
            return False
        if getattr(inst, "is_gateway_proxy", False):
            return inst.go_home()
        threading.Thread(target=inst.go_home, daemon=True).start()
        return True

    @staticmethod
    def go_zero(name: str = None):
        """제로 위치(Zero Position)로 이동"""
        name = RobotControlUseCase._active_name(name)
        if not RobotControlUseCase._guard_motion("Zero 이동", name):
            return False
        if not RobotControlUseCase._claim_gate(RobotControlUseCase._motion_gate_until, name, "Zero 이동", 0.8):
            return False
        inst = RobotControlUseCase._get_instance(name)
        if not inst:
            return False
        if getattr(inst, "is_gateway_proxy", False):
            return inst.go_zero()
        threading.Thread(target=inst.go_zero, daemon=True).start()
        return True

    # =========================================================================
    # 4. 정지 / 비상정지 / 리셋
    # =========================================================================

    @staticmethod
    def stop_robot(name: str = None):
        """현재 동작 정지"""
        name = RobotControlUseCase._active_name(name)
        RobotControlUseCase._clear_motion_gate(name)
        inst = RobotControlUseCase._get_instance(name)
        if inst:
            try:
                threading.Thread(target=inst.stop_motion, daemon=True).start()
                return True
            except:
                pass
        return False

    @staticmethod
    def emergency_stop(name: str = None):
        """비상 정지 (전 축 즉시 정지)"""
        name = RobotControlUseCase._active_name(name)
        RobotControlUseCase._clear_motion_gate(name)
        inst = RobotControlUseCase._get_instance(name)
        if inst:
            try:
                threading.Thread(target=inst.stop_emergency, daemon=True).start()
                return True
            except:
                pass
        return False

    @staticmethod
    def reset_robot(name: str = None):
        """로봇 에러 리셋 (충돌/비상정지 후 복구)"""
        name = RobotControlUseCase._active_name(name)
        RobotControlUseCase._clear_motion_gate(name)
        inst = RobotControlUseCase._get_instance(name)
        if inst:
            RobotControlUseCase.request_stop(name)
            try:
                def _do():
                    try:
                        def _status():
                            try:
                                return inst.get_robot_status()
                            except Exception:
                                return {}

                        def _fault_text(status):
                            if not isinstance(status, dict):
                                return "상태 조회 실패"
                            faults = []
                            if status.get("emergency", 0):
                                faults.append("비상정지")
                            if status.get("collision", 0):
                                faults.append("충돌")
                            if status.get("error", 0):
                                faults.append("로봇 에러")
                            if status.get("resetting", 0):
                                faults.append("리셋중")
                            return ", ".join(faults)

                        before = _status()
                        print(f">> [리셋] {name} 복구 시퀀스 시작: {_fault_text(before) or 'fault 없음'}")

                        if getattr(inst, "is_gateway_proxy", False) and hasattr(inst, "wait_for_last_result"):
                            inst.reset_robot(attempts=5, wait_sec=5.0, settle_sec=0.3, poll_sec=0.25)
                            result = inst.wait_for_last_result(35.0)
                            status = (result or {}).get("status") or {}
                            if result and result.get("ok"):
                                print(f">> [리셋] {name} Gateway 리셋 완료: {_fault_text(status) or 'fault 없음'}")
                            else:
                                print(f">> [리셋 경고] {name} Gateway 리셋 실패/미확인: {result}")
                            return

                        for fn_name in ("stop_motion", "stop_current_program"):
                            fn = getattr(inst, fn_name, None)
                            if not fn:
                                continue
                            try:
                                fn()
                                time.sleep(0.15)
                            except Exception:
                                pass

                        last_status = before
                        for attempt in range(1, 4):
                            try:
                                ret = inst.reset_robot()
                                if ret not in (None, 0):
                                    print(f">> [리셋 경고] reset_robot #{attempt} 응답 코드={ret}")
                            except Exception as e:
                                print(f">> [리셋 에러] reset_robot #{attempt} 실패: {e}")

                            deadline = time.time() + 3.0
                            while time.time() < deadline:
                                time.sleep(0.25)
                                last_status = _status()
                                if not last_status.get("resetting", 0):
                                    break

                            fault_msg = _fault_text(last_status)
                            if not fault_msg:
                                print(f">> [리셋] {name} 에러/충돌 리셋 완료")
                                break
                            print(f">> [리셋 확인] #{attempt} 후 상태 유지: {fault_msg}")
                        else:
                            print(f">> [리셋 경고] {name} 리셋 명령 후에도 fault가 남아있습니다. APK 리셋 또는 전원/서보 상태 확인이 필요합니다.")
                    except Exception as e:
                        print(f">> [리셋 에러] {e}")
                    finally:
                        RobotControlUseCase.clear_stop_request(name)
                threading.Thread(target=_do, daemon=True).start()
                return True
            except Exception as e:
                print(f">> [리셋 에러] {e}")
        return False

    # =========================================================================
    # 5. 서보 / 브레이크 / 다이렉트 티칭
    # =========================================================================

    @staticmethod
    def set_servo(on: bool = True, name: str = None):
        """서보 ON/OFF (6축 전체)"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        arr = [on] * 6
        def _do():
            try:
                inst.set_servo(arr)
                print(f">> [서보] {'ON' if on else 'OFF'}")
            except Exception as e:
                print(f">> [서보 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    @staticmethod
    def set_brake(on: bool = True, name: str = None):
        """브레이크 ON/OFF (6축 전체)"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        arr = [on] * 6
        def _do():
            try:
                inst.set_brake(arr)
                print(f">> [브레이크] {'ON' if on else 'OFF'}")
            except Exception as e:
                print(f">> [브레이크 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    @staticmethod
    def direct_teaching(enable: bool, name: str = None):
        """다이렉트 티칭 모드 ON/OFF"""
        name = RobotControlUseCase._active_name(name)
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        try:
            status = inst.get_robot_status()
            if enable:
                fault_reason = RobotControlUseCase._fault_reason(status)
                if fault_reason:
                    print(f">> 🚫 [다이렉트 티칭] {fault_reason} 상태에서는 시작할 수 없습니다.")
                    return False
                if status.get("busy", 0):
                    print(">> 🚫 [다이렉트 티칭] 로봇 동작 중에는 시작할 수 없습니다.")
                    return False
                if status.get("direct_teaching", 0):
                    print(">> [다이렉트 티칭] 이미 ON 상태입니다.")
                    return True
            elif not status.get("direct_teaching", 0) and not status.get("teaching", 0):
                print(">> [다이렉트 티칭] 이미 OFF 상태입니다.")
                return True
        except Exception as e:
            print(f">> [다이렉트 티칭 상태 확인 에러] {e}")
            return False
        if not RobotControlUseCase._claim_gate(RobotControlUseCase._control_gate_until, name, "다이렉트 티칭", 0.6):
            return False
        def _do():
            try:
                inst.direct_teaching(enable)
                print(f">> [다이렉트 티칭] {'시작' if enable else '종료'}")
            except Exception as e:
                print(f">> [다이렉트 티칭 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 6. Digital I/O (DO, DI, Endtool)
    # =========================================================================

    @staticmethod
    def set_do(idx: int, val: int, name: str = None):
        """Digital Output 설정 (0: OFF, 1: ON)"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        def _do():
            try:
                inst.set_do(idx, val)
            except Exception as e:
                print(f">> [DO 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    @staticmethod
    def get_di(name: str = None) -> list:
        """Digital Input 32채널 읽기 (동기 — 폴링용)"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return []
        try:
            return inst.get_di()
        except Exception as e:
            print(f">> [DI 읽기 에러] {e}")
            return []

    @staticmethod
    def get_do(name: str = None) -> list:
        """Digital Output 상태 읽기 (동기 — 폴링용)"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return []
        try:
            return inst.get_do()
        except Exception as e:
            print(f">> [DO 읽기 에러] {e}")
            return []

    @staticmethod
    def set_endtool_do(endtool_type: int, val: int, name: str = None):
        """엔드툴 Digital Output 설정 (0:NPN, 1:PNP, 2:Not use, 3:eModi)"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        def _do():
            try:
                inst.set_endtool_do(endtool_type, val)
            except Exception as e:
                print(f">> [EndTool DO 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 7. Analog I/O
    # =========================================================================

    @staticmethod
    def set_ao(idx: int, val: int, name: str = None):
        """Analog Output 설정"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        def _do():
            try:
                inst.set_ao(idx, val)
            except Exception as e:
                print(f">> [AO 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    @staticmethod
    def get_ai(idx: int, name: str = None) -> int:
        """Analog Input 1채널 읽기 (동기)"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return 0
        try:
            return inst.get_ai(idx)
        except Exception as e:
            print(f">> [AI 읽기 에러] {e}")
            return 0

    # =========================================================================
    # 8. TCP / Reference Frame 설정
    # =========================================================================

    @staticmethod
    def set_tcp(tcp: list, name: str = None):
        """Tool Center Point 설정 [X, Y, Z, Rx, Ry, Rz]"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst or len(tcp) < 6: return False
        def _do():
            try:
                inst.set_default_tcp(tcp)
                print(f">> [TCP] 설정 완료: {tcp[:3]}")
            except Exception as e:
                print(f">> [TCP 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    @staticmethod
    def reset_tcp(name: str = None):
        """Tool Center Point 초기화"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        def _do():
            try:
                inst.reset_default_tcp()
                print(">> [TCP] 초기화 완료")
            except Exception as e:
                print(f">> [TCP 초기화 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    @staticmethod
    def set_reference_frame(ref: list, name: str = None):
        """기준 좌표계 설정 [X, Y, Z, Rx, Ry, Rz]"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst or len(ref) < 6: return False
        def _do():
            try:
                inst.set_reference_frame(ref)
                print(f">> [기준좌표계] 설정 완료: {ref[:3]}")
            except Exception as e:
                print(f">> [기준좌표계 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    @staticmethod
    def reset_reference_frame(name: str = None):
        """기준 좌표계 초기화"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        def _do():
            try:
                inst.reset_reference_frame()
                print(">> [기준좌표계] 초기화 완료")
            except Exception as e:
                print(f">> [기준좌표계 초기화 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 9. 웨이포인트 이동 (다중 경유점)
    # =========================================================================

    @staticmethod
    def execute_waypoint_move(waypoints: list, is_joint: bool = True, blend_radius: float = 0, name: str = None):
        """
        다중 경유점 이동 실행.
        waypoints: [[j1,j2,...,j6], [j1,j2,...,j6], ...] 또는 [[x,y,z,rx,ry,rz], ...]
        """
        inst = RobotControlUseCase._get_instance(name)
        if not inst or not waypoints: return False
        
        def _do():
            try:
                if is_joint:
                    inst.joint_waypoint_clean()
                    for wp in waypoints:
                        inst.joint_waypoint_append(wp, blend_radius=blend_radius)
                    inst.joint_waypoint_execute()
                else:
                    inst.task_waypoint_clean()
                    for wp in waypoints:
                        inst.task_waypoint_append(wp, blend_radius=blend_radius)
                    inst.task_waypoint_execute()
                print(f">> [웨이포인트] {len(waypoints)}개 포인트 이동 실행")
            except Exception as e:
                print(f">> [웨이포인트 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 10. Pick & Place 시퀀스 (MoveDoneCheck 포함)
    # =========================================================================

    @staticmethod
    def execute_pick_place_sequence(target_p: list, approach_dist_mm: float, approach_dir: str, retract_dist_mm: float, retract_dir: str, name: str = None):
        """
        Pick/Place 동작 시퀀스: 투입(Approach) → 정위치(Target) → 배출(Retract)
        각 단계마다 MoveDoneCheck로 이동 완료 확인 후 다음 단계 진행.
        """
        if not target_p or len(target_p) < 6: return False
        inst = RobotControlUseCase._get_instance(name)
        if not inst:
            print(">> 로봇 인스턴스가 활성화되지 않았습니다.")
            return False
            
        from core.domains.robot.use_cases.motion_math import MotionMath
        
        def _sequence_thread():
            try:
                app_p = MotionMath.compute_offset_position(target_p, approach_dist_mm, approach_dir)
                ret_p = MotionMath.compute_offset_position(target_p, retract_dist_mm, retract_dir)

                # 1단계: 투입위치(Approach)
                print(f">> [OOD] 1. 투입 위치(Approach) 이동: {[f'{v:.2f}' for v in app_p[:3]]}")
                inst.task_move_to(app_p)
                if not RobotControlUseCase.wait_for_move_finish(name=name):
                    print(">> [OOD] 투입위치 이동 타임아웃!")
                    return
                
                # 2단계: 정위치(Target)
                print(f">> [OOD] 2. 정위치(Target) 이동: {[f'{v:.2f}' for v in target_p[:3]]}")
                inst.task_move_to(target_p)
                if not RobotControlUseCase.wait_for_move_finish(name=name):
                    print(">> [OOD] 정위치 이동 타임아웃!")
                    return
                
                # 3단계: 배출위치(Retract)
                print(f">> [OOD] 3. 배출 위치(Retract) 이동: {[f'{v:.2f}' for v in ret_p[:3]]}")
                inst.task_move_to(ret_p)
                if not RobotControlUseCase.wait_for_move_finish(name=name):
                    print(">> [OOD] 배출위치 이동 타임아웃!")
                    return
                    
                print(">> [OOD] ✅ Pick/Place 시퀀스 완료!")
            except Exception as e:
                print(f">> [OOD 시퀀스 에러] {e}")
                
        threading.Thread(target=_sequence_thread, daemon=True).start()
        return True

    # =========================================================================
    # 11. 프로그램 제어 (Conty 프로그램)
    # =========================================================================

    @staticmethod
    def start_program(name: str = None):
        """현재 로드된 프로그램 실행"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        threading.Thread(target=inst.start_current_program, daemon=True).start()
        return True

    @staticmethod
    def pause_program(name: str = None):
        """현재 실행 중인 프로그램 일시정지"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        threading.Thread(target=inst.pause_current_program, daemon=True).start()
        return True

    @staticmethod
    def resume_program(name: str = None):
        """일시정지된 프로그램 재개"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        threading.Thread(target=inst.resume_current_program, daemon=True).start()
        return True

    @staticmethod
    def stop_program(name: str = None):
        """현재 프로그램 정지"""
        RobotControlUseCase.request_stop(name)
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        threading.Thread(target=inst.stop_current_program, daemon=True).start()
        return True

    @staticmethod
    def run_json_program(json_string: str, name: str = None):
        """JSON 프로그램을 로봇에 전송하고 실행"""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        def _do():
            try:
                inst.set_and_start_json_program(json_string)
                print(">> [JSON 프로그램] 전송 및 실행 시작")
            except Exception as e:
                print(f">> [JSON 프로그램 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 12. 역기구학 (Inverse Kinematics)
    # =========================================================================

    @staticmethod
    def get_inverse_kinematics(task_pos: list, init_q: list = None) -> list:
        """
        역기구학 계산: Task 좌표 → Joint 좌표 변환.
        init_q: 초기 관절 값 (None이면 현재 관절 위치 사용)
        동기 호출 — 백그라운드에서만 사용할 것.
        """
        inst = robot_manager.get_active_instance()
        if not inst: return []
        try:
            if init_q is None:
                init_q = inst.get_joint_pos()
            return inst.get_inv_kin(task_pos, init_q)
        except Exception as e:
            print(f">> [역기구학 에러] {e}")
            return []

    # =========================================================================
    # 13. Direct Variable (PLC 변수 읽기/쓰기)
    # =========================================================================

    @staticmethod
    def read_direct_variable(dv_type: int, dv_addr: int):
        """
        Direct Variable 읽기.
        dv_type: 0=BYTE, 1=WORD, 2=DWORD, 3=LWORD, 4=FLOAT, 5=DFLOAT, 10=MODBUS
        """
        inst = robot_manager.get_active_instance()
        if not inst: return None
        try:
            return inst.read_direct_variable(dv_type, dv_addr)
        except Exception as e:
            print(f">> [DV 읽기 에러] {e}")
            return None

    @staticmethod
    def write_direct_variable(dv_type: int, dv_addr: int, val):
        """Direct Variable 쓰기."""
        inst = robot_manager.get_active_instance()
        if not inst: return False
        def _do():
            try:
                inst.write_direct_variable(dv_type, dv_addr, val)
            except Exception as e:
                print(f">> [DV 쓰기 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 14. F/T 센서 (Force/Torque)
    # =========================================================================

    @staticmethod
    def get_ft_sensor() -> list:
        """F/T 센서 값 읽기 [Fx, Fy, Fz, Tx, Ty, Tz] (동기)"""
        inst = robot_manager.get_active_instance()
        if not inst: return []
        try:
            return inst.get_robot_ft()
        except Exception as e:
            print(f">> [F/T 센서 에러] {e}")
            return []

    # =========================================================================
    # 15. 감속 모드
    # =========================================================================

    @staticmethod
    def set_reduced_mode(enable: bool, ratio: float = 0.5):
        """
        감속 모드 ON/OFF 및 감속 비율(0.0~1.0) 설정.
        안전 영역 진입 시 사용.
        """
        inst = robot_manager.get_active_instance()
        if not inst: return False
        def _do():
            try:
                inst.set_reduced_mode(enable)
                if enable:
                    inst.set_reduced_speed_ratio(ratio)
                print(f">> [감속모드] {'ON' if enable else 'OFF'} (비율: {ratio})")
            except Exception as e:
                print(f">> [감속모드 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 16. 고급 모션 — Move C (원호 이동)
    # =========================================================================

    @staticmethod
    def move_c(via_p: list, target_p: list):
        """
        원호 보간 이동 (Move Circular).
        via_p: 경유점 [X,Y,Z,Rx,Ry,Rz]
        target_p: 목표점 [X,Y,Z,Rx,Ry,Rz]
        시작점은 현재 위치.
        """
        if not RobotControlUseCase._guard_motion("원호 이동"): return False
        inst = robot_manager.get_active_instance()
        if not inst: return False
        def _do():
            try:
                inst.task_move_c(via_p, target_p)
                print(f">> [Move C] 원호 이동 실행 via={via_p[:3]}, target={target_p[:3]}")
            except Exception as e:
                print(f">> [Move C 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 17. 고급 모션 — Move By (상대 위치 이동)
    # =========================================================================

    @staticmethod
    def move_by_task(offset: list):
        """
        현재 위치 기준 상대 이동 (Task 공간).
        offset: [dx, dy, dz, drx, dry, drz] (m, deg)
        """
        if not RobotControlUseCase._guard_motion("상대 이동"): return False
        inst = robot_manager.get_active_instance()
        if not inst: return False
        def _do():
            try:
                inst.task_move_by(offset)
                print(f">> [Move By] 상대 이동: dx={offset[0]:.3f}, dy={offset[1]:.3f}, dz={offset[2]:.3f}")
            except Exception as e:
                print(f">> [Move By 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    @staticmethod
    def move_by_joint(offset: list):
        """
        현재 위치 기준 상대 이동 (Joint 공간).
        offset: [dj1, dj2, ..., dj6] (deg)
        """
        if not RobotControlUseCase._guard_motion("관절 상대 이동"): return False
        inst = robot_manager.get_active_instance()
        if not inst: return False
        def _do():
            try:
                inst.joint_move_by(offset)
            except Exception as e:
                print(f">> [Joint Move By 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 18. 페이로드 및 무게중심 설정
    # =========================================================================

    @staticmethod
    def set_payload(mass: float, center_of_mass: list = None, name: str = None):
        """
        로봇 끝단 페이로드(질량) 및 무게중심 설정.
        mass: kg
        center_of_mass: [cx, cy, cz] (m) — None이면 [0,0,0]
        """
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        if center_of_mass is None:
            center_of_mass = [0.0, 0.0, 0.0]
        def _do():
            try:
                inst.set_payload(mass, center_of_mass)
                print(f">> [페이로드] 질량: {mass}kg, 무게중심: {center_of_mass}")
            except Exception as e:
                print(f">> [페이로드 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 19. 작업 공간 제한 (Safety Zone)
    # =========================================================================

    @staticmethod
    def set_workspace_limit(min_pos: list, max_pos: list, enable: bool = True, name: str = None):
        """
        작업 공간 직교 좌표 제한.
        min_pos: [x_min, y_min, z_min] (m)
        max_pos: [x_max, y_max, z_max] (m)
        """
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        def _do():
            try:
                inst.set_cartesian_limit(min_pos, max_pos, enable)
                print(f">> [작업공간] {'활성화' if enable else '비활성화'}: min={min_pos}, max={max_pos}")
            except Exception as e:
                print(f">> [작업공간 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    @staticmethod
    def set_joint_limit(min_q: list, max_q: list, enable: bool = True):
        """
        관절 각도 제한.
        min_q/max_q: [j1_min, ..., j6_min] / [j1_max, ..., j6_max] (deg)
        """
        inst = robot_manager.get_active_instance()
        if not inst: return False
        def _do():
            try:
                inst.set_joint_limit(min_q, max_q, enable)
                print(f">> [관절제한] {'활성화' if enable else '비활성화'}")
            except Exception as e:
                print(f">> [관절제한 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 20. 임피던스 제어 (Impedance / Compliance)
    # =========================================================================

    @staticmethod
    def set_impedance(stiffness: list, damping: list, name: str = None):
        """
        임피던스 파라미터 설정 (6축).
        stiffness: [kx, ky, kz, krx, kry, krz] — 강성 (N/m, Nm/rad)
        damping: [dx, dy, dz, drx, dry, drz] — 감쇠 (Ns/m, Nms/rad)
        """
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        def _do():
            try:
                inst.set_impedance_param(stiffness, damping)
                print(f">> [임피던스] 강성={stiffness[:3]}, 감쇠={damping[:3]}")
            except Exception as e:
                print(f">> [임피던스 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    @staticmethod
    def start_impedance_mode(name: str = None):
        """임피던스 제어 모드 시작."""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        def _do():
            try:
                inst.start_impedance_mode()
                print(">> [임피던스] 제어 모드 시작")
            except Exception as e:
                print(f">> [임피던스 시작 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    @staticmethod
    def stop_impedance_mode(name: str = None):
        """임피던스 제어 모드 종료."""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        def _do():
            try:
                inst.stop_impedance_mode()
                print(">> [임피던스] 제어 모드 종료")
            except Exception as e:
                print(f">> [임피던스 종료 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 21. 힘 제어 (Force Control)
    # =========================================================================

    @staticmethod
    def set_force_control(axis: int, target_force: float, enable: bool = True):
        """
        특정 축 방향으로 일정 힘을 가하며 이동.
        axis: 0=X, 1=Y, 2=Z, 3=Rx, 4=Ry, 5=Rz
        target_force: 목표 힘 (N) 또는 토크 (Nm)
        """
        inst = robot_manager.get_active_instance()
        if not inst: return False
        def _do():
            try:
                force_vec = [0.0] * 6
                force_vec[axis] = target_force
                inst.set_force_control(force_vec, enable)
                axis_names = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
                print(f">> [힘제어] {axis_names[axis]}축 목표: {target_force}N {'ON' if enable else 'OFF'}")
            except Exception as e:
                print(f">> [힘제어 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 22. 엔드툴 I/O (End-Tool DI/DO)
    # =========================================================================

    @staticmethod
    def get_endtool_di(name: str = None) -> list:
        """엔드툴 Digital Input 읽기 (동기)."""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return []
        try:
            return inst.get_endtool_di()
        except Exception as e:
            print(f">> [EndTool DI 에러] {e}")
            return []

    @staticmethod
    def set_endtool_do_port(port: int, val: int, name: str = None):
        """엔드툴 특정 포트 DO 설정."""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        def _do():
            try:
                inst.set_endtool_do(port, val)
                print(f">> [EndTool DO] Port {port} = {'ON' if val else 'OFF'}")
            except Exception as e:
                print(f">> [EndTool DO 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 23. Modbus TCP 통신
    # =========================================================================

    @staticmethod
    def modbus_read_register(addr: int, count: int = 1) -> list:
        """
        Modbus TCP 홀딩 레지스터 읽기 (동기).
        addr: 시작 주소
        count: 읽을 레지스터 수
        """
        inst = robot_manager.get_active_instance()
        if not inst: return []
        try:
            return inst.read_direct_variable(10, addr)  # 10 = MODBUS type
        except Exception as e:
            print(f">> [Modbus 읽기 에러] {e}")
            return []

    @staticmethod
    def modbus_write_register(addr: int, val: int):
        """Modbus TCP 홀딩 레지스터 쓰기."""
        inst = robot_manager.get_active_instance()
        if not inst: return False
        def _do():
            try:
                inst.write_direct_variable(10, addr, val)  # 10 = MODBUS type
                print(f">> [Modbus] 주소 {addr} = {val}")
            except Exception as e:
                print(f">> [Modbus 쓰기 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 24. 컨베이어 트래킹
    # =========================================================================

    @staticmethod
    def start_conveyor_sync(encoder_port: int = 0, direction: int = 0):
        """
        컨베이어 트래킹 동기화 시작.
        encoder_port: 엔코더 입력 포트
        direction: 0=정방향, 1=역방향
        """
        inst = robot_manager.get_active_instance()
        if not inst: return False
        def _do():
            try:
                inst.start_conveyor_tracking(encoder_port, direction)
                print(f">> [컨베이어] 트래킹 시작 (포트: {encoder_port})")
            except Exception as e:
                print(f">> [컨베이어 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    @staticmethod
    def stop_conveyor_sync():
        """컨베이어 트래킹 동기화 종료."""
        inst = robot_manager.get_active_instance()
        if not inst: return False
        def _do():
            try:
                inst.stop_conveyor_tracking()
                print(">> [컨베이어] 트래킹 종료")
            except Exception as e:
                print(f">> [컨베이어 종료 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 25. 서브 프로그램 호출
    # =========================================================================

    @staticmethod
    def call_sub_program(json_path: str, name: str = None):
        """
        외부 JSON 프로그램 파일을 로드하여 로봇에서 실행.
        json_path: .json 파일 경로
        """
        import json as _json
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return False
        def _do():
            try:
                with open(json_path, 'r', encoding='utf-8-sig') as f:
                    prog_data = _json.load(f)
                prog_str = _json.dumps(prog_data, ensure_ascii=False)
                inst.set_and_start_json_program(prog_str)
                print(f">> [서브프로그램] 실행: {json_path}")
            except Exception as e:
                print(f">> [서브프로그램 에러] {e}")
        threading.Thread(target=_do, daemon=True).start()
        return True

    # =========================================================================
    # 26. 사용자 변수 관리 (HMI 내부)
    # =========================================================================

    _user_variables = {}
    _robot_variables = {}

    @classmethod
    def _variable_store(cls, robot_name: str = None) -> dict:
        if robot_name:
            return cls._robot_variables.setdefault(robot_name, {})
        return cls._user_variables

    @classmethod
    def set_variable(cls, name: str, value: float, robot_name: str = None):
        """사용자 변수 설정."""
        cls._variable_store(robot_name)[name] = value

    @classmethod
    def get_variable(cls, name: str, default: float = 0.0, robot_name: str = None) -> float:
        """사용자 변수 읽기."""
        return cls._variable_store(robot_name).get(name, default)

    @classmethod
    def get_all_variables(cls, robot_name: str = None) -> dict:
        """전체 사용자 변수 딕셔너리 반환."""
        return cls._variable_store(robot_name).copy()

    @classmethod
    def math_operation(cls, var_name: str, operator: str, value: float, robot_name: str = None):
        """변수 수학 연산 (+=, -=, *=, /=, =)."""
        store = cls._variable_store(robot_name)
        current = store.get(var_name, 0.0)
        if operator == "=":
            store[var_name] = value
        elif operator == "+=" or operator == "+":
            store[var_name] = current + value
        elif operator == "-=" or operator == "-":
            store[var_name] = current - value
        elif operator == "*=" or operator == "*":
            store[var_name] = current * value
        elif operator == "/=" or operator == "/":
            store[var_name] = current / value if value != 0 else current
        print(f">> [변수] {var_name} = {store[var_name]}")

    @classmethod
    def eval_condition(cls, var_name: str, operator: str, value: float, robot_name: str = None) -> bool:
        """조건문 평가."""
        current = cls._variable_store(robot_name).get(var_name, 0.0)
        if operator == "==": return current == value
        elif operator == "!=": return current != value
        elif operator == ">": return current > value
        elif operator == "<": return current < value
        elif operator == ">=": return current >= value
        elif operator == "<=": return current <= value
        return False

    # =========================================================================
    # 27. 좌표 읽기 (동기)
    # =========================================================================

    @staticmethod
    def get_joint_pos(name: str = None) -> list:
        """현재 관절 각도 읽기 [j1, ..., j6] (deg)."""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return [0.0] * 6
        try:
            return inst.get_joint_pos()
        except:
            return [0.0] * 6

    @staticmethod
    def get_task_pos(name: str = None) -> list:
        """현재 TCP 좌표 읽기 [x,y,z,rx,ry,rz]."""
        inst = RobotControlUseCase._get_instance(name)
        if not inst: return [0.0] * 6
        try:
            return inst.get_task_pos()
        except:
            return [0.0] * 6

    # =========================================================================
    # 28. 스택 탐색 (Stack Search) — F/T 센서 기반
    # =========================================================================

    @staticmethod
    def stack_search(axis: int = 2, direction: int = -1, force_threshold: float = 10.0,
                     step_mm: float = 1.0, max_steps: int = 200, speed_ratio: float = 0.3):
        """
        스택 탐색: 지정된 축(기본 Z) 방향으로 천천히 이동하다가
        F/T 센서의 힘이 threshold를 초과하면 멈추고 현재 위치를 반환.
        
        axis: 0=X, 1=Y, 2=Z
        direction: 1=양, -1=음
        force_threshold: 감지 기준 힘 (N)
        step_mm: 한 번에 이동하는 거리 (mm)
        max_steps: 최대 탐색 횟수
        
        Returns: 감지된 위치 [x,y,z,rx,ry,rz] 또는 빈 리스트
        """
        inst = robot_manager.get_active_instance()
        if not inst: return []
        
        result = [None]
        
        def _search():
            try:
                step_m = step_mm / 1000.0 * direction
                axis_names = ["X", "Y", "Z"]
                print(f">> [스택탐색] {axis_names[axis]}축 방향 탐색 시작 (임계값: {force_threshold}N)")
                
                for i in range(max_steps):
                    ft = inst.get_robot_ft()
                    if ft and len(ft) > axis:
                        current_force = abs(ft[axis])
                        if current_force >= force_threshold:
                            pos = inst.get_task_pos()
                            print(f">> [스택탐색] ✅ 접촉 감지! 힘={current_force:.1f}N, 위치={[f'{v:.4f}' for v in pos[:3]]}")
                            result[0] = pos
                            return
                    
                    offset = [0.0] * 6
                    offset[axis] = step_m
                    inst.task_move_by(offset)
                    time.sleep(0.05)
                
                print(f">> [스택탐색] ❌ 최대 탐색 거리 도달 ({max_steps * step_mm}mm)")
                result[0] = []
            except Exception as e:
                print(f">> [스택탐색 에러] {e}")
                result[0] = []
        
        t = threading.Thread(target=_search, daemon=True)
        t.start()
        t.join(timeout=60.0)
        return result[0] if result[0] is not None else []

    # =========================================================================
    # 29. 나선형 탐색 (Spiral Search) — Peg-in-Hole
    # =========================================================================

    @staticmethod
    def spiral_search(z_force: float = 10.0, xy_force_threshold: float = 3.0,
                      radius_mm: float = 5.0, step_deg: float = 15.0, 
                      push_mm: float = 0.5, max_loops: int = 10):
        """
        나선형 탐색: Z축으로 일정한 힘을 주면서 XY 평면에서 나선형으로 탐색.
        구멍에 핀이 들어가면 Z축 위치가 갑자기 변하는 것으로 삽입 성공을 감지.
        
        z_force: Z축 아래쪽 가압력 (N)
        xy_force_threshold: XY 접촉 판단 임계값 (N)
        radius_mm: 나선 최대 반경 (mm)
        step_deg: 각도 스텝 (deg)
        push_mm: Z축 아래쪽 미세 이동량 (mm)
        max_loops: 최대 나선 바퀴 수
        
        Returns: 삽입 성공 위치 또는 빈 리스트
        """
        import math
        inst = robot_manager.get_active_instance()
        if not inst: return []
        
        result = [None]
        
        def _search():
            try:
                start_pos = inst.get_task_pos()
                start_z = start_pos[2]
                print(f">> [나선탐색] 시작 위치 Z={start_z:.4f}m, 반경={radius_mm}mm")
                
                total_steps = int(360 / step_deg * max_loops)
                for step in range(total_steps):
                    angle_rad = math.radians(step * step_deg)
                    # 나선 반경이 점점 커짐
                    progress = step / total_steps
                    r = (radius_mm / 1000.0) * progress
                    
                    dx = r * math.cos(angle_rad) - (r * math.cos(angle_rad - math.radians(step_deg)) if step > 0 else 0)
                    dy = r * math.sin(angle_rad) - (r * math.sin(angle_rad - math.radians(step_deg)) if step > 0 else 0)
                    dz = -(push_mm / 1000.0) * 0.01  # 미세 Z 가압
                    
                    inst.task_move_by([dx, dy, dz, 0, 0, 0])
                    time.sleep(0.03)
                    
                    # 삽입 감지: Z 위치가 갑자기 push_mm 이상 내려가면 성공
                    cur_pos = inst.get_task_pos()
                    if cur_pos[2] < start_z - (push_mm * 2 / 1000.0):
                        print(f">> [나선탐색] ✅ 삽입 성공! 위치={[f'{v:.4f}' for v in cur_pos[:3]]}")
                        result[0] = cur_pos
                        return
                
                print(f">> [나선탐색] ❌ 탐색 실패 (최대 반경 도달)")
                result[0] = []
            except Exception as e:
                print(f">> [나선탐색 에러] {e}")
                result[0] = []
        
        t = threading.Thread(target=_search, daemon=True)
        t.start()
        t.join(timeout=120.0)
        return result[0] if result[0] is not None else []
