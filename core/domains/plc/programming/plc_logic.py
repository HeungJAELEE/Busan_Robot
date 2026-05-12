from core.domains.plc.communication.plc_manager import plc_manager

class PlcProgrammingLogic:
    """
    PLC 비즈니스 로직 및 DI/DO 메모리 맵핑을 담당하는 프로그래밍 모듈
    """
    def __init__(self):
        self.manager = plc_manager
        
    def write_bit(self, address: str, value: int) -> bool:
        if not self.manager.is_connected():
            return False
            
        with self.manager.get_lock():
            try:
                self.manager.get_client().batchwrite_bitunits(address, [value])
                return True
            except Exception as e:
                print(f"❌ [PLC 쓰기 에러] {address}: {e}")
                return False
                
    def read_bit(self, address: str) -> int:
        if not self.manager.is_connected():
            return -1
            
        with self.manager.get_lock():
            try:
                res = self.manager.get_client().batchread_bitunits(address, 1)
                return res[0]
            except Exception as e:
                print(f"❌ [PLC 읽기 에러] {address}: {e}")
                return -1

    def trigger_interlock(self, address: str) -> bool:
        """안전 인터락 강제 트리거"""
        return self.write_bit(address, 1)
        
    def release_interlock(self, address: str) -> bool:
        """안전 인터락 해제"""
        return self.write_bit(address, 0)

plc_logic = PlcProgrammingLogic()
