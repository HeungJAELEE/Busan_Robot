from typing import Protocol, List

class IPlcRepository(Protocol):
    """
    [DIP 적용] 도메인 계층이 인프라스트럭처에 직접 의존하지 않도록 만든 인터페이스(Port).
    인프라 계층(infrastructure/plc)은 이 인터페이스를 구현해야 합니다.
    """
    def connect(self) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def read_bit(self, address: str) -> int:
        ...

    def write_bit(self, address: str, value: int) -> None:
        ...

    def read_words(self, address: str, count: int) -> List[int]:
        ...

    def write_words(self, address: str, data: List[int]) -> None:
        ...
