from typing import Protocol, List

class IMesRepository(Protocol):
    """
    [DIP 적용] 도메인 계층이 인프라스트럭처(MySQL)에 직접 의존하지 않도록 만든 인터페이스.
    MES 시스템과의 데이터 연동 명세를 정의합니다.
    """
    def connect(self) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def log_robot_position(self, robot_id: str, motion_name: str, joint_pos: List[float]) -> None:
        """로봇의 1~6축 조인트 위치를 MES 데이터베이스에 기록합니다."""
        ...
