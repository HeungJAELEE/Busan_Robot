import threading
import time
import json
from typing import Optional
from core.runtime_config import env_str, plc_config, robot_model

try:
    from pymcprotocol import Type3E
except ImportError:
    Type3E = None

try:
    from indy_utils import indydcp_client as client
except ImportError:
    client = None

class ContyExecutor:
    """
    Execution Engine that integrates PLC 4-Phase Handshake and Native JSON Program Execution on Indy.
    Follows the 260303_test_plc_pc_robot.py specification.
    """
    def __init__(self, robot_ip: str, plc_ip: str, plc_port: int = None, robot_name: str = None):
        config = plc_config()
        self.robot_ip = robot_ip
        self.plc_ip = plc_ip or config["process_ip"]
        self.plc_port = plc_port or config["process_port"]
        self.robot_name = robot_name or robot_model()
        
        self.indy: Optional[client.IndyDCPClient] = None
        self.plc: Optional[Type3E] = None
        
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        self.state_callback = None  # Add UI Callback

        # PLC Addresses
        self.ADDR_START = env_str("PLC_CYCLE_START_DEVICE", config["start_device"])
        self.ADDR_BUSY = env_str("PLC_ROBOT_BUSY_DEVICE", "M200")
        self.ADDR_COMPLETE = env_str("PLC_CYCLE_COMPLETE_DEVICE", "M101")
        self.ADDR_ACK = env_str("PLC_ACK_DEVICE", "M105")
        self.ADDR_ALARM = env_str("PLC_ALARM_DEVICE", "M102")

    def connect(self) -> bool:
        try:
            print(f">> [Executor] 로봇({self.robot_ip}) 연결 시도...")
            self.indy = client.IndyDCPClient(self.robot_ip, self.robot_name)
            self.indy.connect()
            print(">> [Executor] 로봇 연결 성공!")
        except Exception as e:
            print(f">> [Executor] 로봇 연결 실패: {e}")
            return False

        if Type3E is None:
            print(">> [Executor] 경고: pymcprotocol 패키지가 설치되지 않아 PLC 연동을 우회합니다.")
            return True
            
        try:
            print(f">> [Executor] PLC({self.plc_ip}:{self.plc_port}) 연결 시도...")
            self.plc = Type3E()
            self.plc.connect(self.plc_ip, self.plc_port)
            print(">> [Executor] PLC 연결 성공!")
        except Exception as e:
            print(f">> [Executor] PLC 연결 실패 (PLC 없이 단독 실행 모드로 전환합니다): {e}")
            self.plc = None

        return True

    def disconnect(self):
        self.stop()
        if self.indy:
            try:
                self.indy.disconnect()
            except Exception: pass
        if self.plc:
            try:
                self.plc.close()
            except Exception: pass
        print(">> [Executor] 모든 하드웨어 연결 종료.")

    def start_auto_mode(self, json_string: str):
        if self._running:
            print(">> [Executor] 이미 자동 모드가 실행 중입니다.")
            return
            
        self._running = True
        self._worker_thread = threading.Thread(target=self._auto_loop, args=(json_string,), daemon=True)
        self._worker_thread.start()

    def stop(self):
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)

    def _motion_done_check(self, timeout=30):
        """Monitor robot status for completion or timeout."""
        start_time = time.time()
        while self._running:
            status = self.indy.get_robot_status()
            
            if status.get("movedone") == 1:
                return True
                
            if status.get("error") == 1 or status.get("collision") == 1:
                print(">> [Executor] 로봇 에러/충돌 감지!")
                return False

            if time.time() - start_time > timeout:
                print(">> [Executor] 모션 타임아웃 발생!")
                return False

            time.sleep(0.1)
        return False

    def _wait_for_program_finish(self, timeout=300):
        """Wait for the native JSON program to finish executing on the robot controller."""
        print(">> [Executor] 로봇 네이티브 JSON 실행 대기 중...")
        start_time = time.time()
        
        # Give it a moment to actually start
        time.sleep(0.5) 
        
        while self._running:
            try:
                prog_state = self.indy.get_program_state()
                if prog_state.get('running') == 0:
                    return True
            except Exception as e:
                print(f">> [Executor] 상태 폴링 오류: {e}")
                
            if time.time() - start_time > timeout:
                print(">> [Executor] 프로그램 실행 타임아웃 발생!")
                return False
                
            time.sleep(0.1)
        return False

    def _notify_state(self, signal_name: str, state: int):
        if self.state_callback:
            try:
                self.state_callback(signal_name, state)
            except Exception as e:
                print(f">> [Executor] Callback error: {e}")

    def _plc_read(self, addr: str) -> int:
        if not self.plc: return 1 # Mock PLC input if no PLC
        try:
            val = self.plc.batchread_bitunits(addr, 1)[0]
            return val
        except Exception as e:
            print(f">> [Executor] PLC Read Error: {e}")
            return 0

    def _plc_write(self, addr: str, val: int):
        if not self.plc: return
        try:
            self.plc.batchwrite_bitunits(addr, [val])
            self._notify_state(addr, val)
        except Exception as e:
            print(f">> [Executor] PLC Write Error: {e}")

    def _auto_loop(self, json_string: str):
        print("\n>> [Executor] 🚀 자동 실행 모드 시작! (PLC M100 대기 중...)")
        
        while self._running:
            try:
                start_signal = self._plc_read(self.ADDR_START)
                if getattr(self, '_last_start_signal', None) != start_signal:
                    self._notify_state(self.ADDR_START, start_signal)
                    self._last_start_signal = start_signal
                
                if start_signal == 1:
                    print("\n>> [Executor] 🟢 Cycle Start (M100) 감지!")
                    
                    # Phase 1 : Busy ON
                    self._plc_write(self.ADDR_BUSY, 1)
                    
                    # 로봇 제어기에 JSON 전송 및 네이티브 실행
                    print(">> [Executor] JSON 프로그램을 제어기로 전송 및 실행...")
                    self.indy.set_and_start_json_program(json_string)
                    
                    # 실행 완료 대기
                    success = self._wait_for_program_finish()
                    
                    if success:
                        print(">> [Executor] 🏁 로봇 동작 완전 종료 (Motion Complete)")
                        # Phase 2 : Complete ON
                        self._plc_write(self.ADDR_COMPLETE, 1)
                    else:
                        print(">> [Executor] 🚨 프로그램 실행 실패 또는 알람 발생")
                        self._plc_write(self.ADDR_ALARM, 1)
                        self._plc_write(self.ADDR_BUSY, 0)
                        continue

                    # Phase 3 : PLC Ack 대기
                    print(">> [Executor] ⏳ PLC Ack (M105) 대기 중...")
                    while self._running:
                        ack_signal = self._plc_read(self.ADDR_ACK)
                        if getattr(self, '_last_ack_signal', None) != ack_signal:
                            self._notify_state(self.ADDR_ACK, ack_signal)
                            self._last_ack_signal = ack_signal
                        if ack_signal == 1:
                            break
                        time.sleep(0.1)
                        
                    print(">> [Executor] 📥 PLC Ack 수신 완료")

                    # Phase 4 : 신호 정리
                    self._plc_write(self.ADDR_COMPLETE, 0)
                    self._plc_write(self.ADDR_BUSY, 0)
                    
                    # Start OFF 될 때까지 대기
                    while self._plc_read(self.ADDR_START) == 1 and self._running:
                        time.sleep(0.1)
                        
                    print(">> [Executor] 🔵 사이클 정상 종료. 다음 M100 대기...")
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f">> [Executor] 🚨 자동 모드 루프 예외 발생: {e}")
                time.sleep(1.0)
                
        print(">> [Executor] 자동 실행 모드 종료.")
