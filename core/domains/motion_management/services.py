from typing import Protocol
from .entities import RobotEntity

class IRobotRepository(Protocol):
    """의존성 역전을 위한 로봇 저장소 인터페이스"""
    def find_by_id(self, robot_id: str) -> RobotEntity:
        ...
    
    def save(self, robot: RobotEntity):
        ...

class MotionService:
    """모션 관련 복잡한 로직을 처리하는 도메인 서비스"""
    def __init__(self, repository: IRobotRepository):
        self.repository = repository
        
    def execute_motion(self, robot_id: str, motion_type: str, data: list):
        # 여기서는 단순화를 위해 리포지토리 없이 엔티티를 바로 사용할 수도 있지만,
        # DDD 원칙에 따라 리포지토리에서 Aggregate Root를 꺼내옵니다.
        pass
