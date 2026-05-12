from core.domains.plc_communication.repositories import IPlcRepository
from pymcprotocol import Type3E
from typing import List

class PyMcPlcClient(IPlcRepository):
    """
    [Infrastructure 계층] IPlcRepository 인터페이스의 실제 구현체 (Adapter).
    실제 외부 라이브러리(pymcprotocol)에 의존합니다.
    """
    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.plc = Type3E()
        self.is_connected = False

    def connect(self) -> None:
        try:
            self.plc.connect(self.ip, self.port)
            self.is_connected = True
            print("✅ [Infra] 미쓰비시 PLC 연결 성공!")
        except Exception as e:
            self.is_connected = False
            print(f"❌ [Infra] 미쓰비시 PLC 연결 실패: {e}")
            raise e

    def disconnect(self) -> None:
        if self.is_connected:
            self.plc.close()
            self.is_connected = False
            print("🔌 [Infra] PLC 연결 종료")

    def read_bit(self, address: str) -> int:
        return self.plc.batchread_bitunits(address, 1)[0]

    def write_bit(self, address: str, value: int) -> None:
        self.plc.batchwrite_bitunits(address, [value])

    def read_words(self, address: str, count: int) -> List[int]:
        return self.plc.batchread_wordunits(address, count)

    def write_words(self, address: str, data: List[int]) -> None:
        self.plc.batchwrite_wordunits(address, data)
