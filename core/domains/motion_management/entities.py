import time
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from core.shared.value_objects import MotionDataVO
from core.shared.domain_events import MotionCompletedEvent

class RobotState(Enum):
    DISCONNECTED = "DISCONNECTED"
    IDLE = "IDLE"
    MOVING = "MOVING"
    ERROR = "ERROR"

@dataclass(frozen=True)
class Waypoint:
    j1: float = 0.0
    j2: float = 0.0
    j3: float = 0.0
    j4: float = 0.0
    j5: float = 0.0
    j6: float = 0.0

    def to_list(self) -> List[float]:
        return [self.j1, self.j2, self.j3, self.j4, self.j5, self.j6]

class RobotEntity:
    """
    Pure Domain Entity representing a Robot's identity and state.
    It holds no infrastructure logic (no IndyDCPClient).
    """
    def __init__(self, robot_id: str, ip: str, name: str, config_path: str = "config/motion_config.json"):
        self.robot_id = robot_id
        self.ip = ip
        self.name = name
        self.state: RobotState = RobotState.DISCONNECTED
        self.current_pose: Optional[Waypoint] = None
        self._uncommitted_events: List[Any] = []
        self.config_path = config_path
        self.motion_config = self._load_config()

    def _load_config(self) -> dict:
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ [Motion Domain] 설정 파일 로드 실패: {e}")
            return {}

    def change_state(self, new_state: RobotState):
        """Update robot state according to state machine rules"""
        # Here we could add Ouroboros-style strict transition validation
        if self.state == RobotState.ERROR and new_state == RobotState.MOVING:
            raise ValueError("Cannot move from ERROR state directly. Must reset first.")
        self.state = new_state

    def update_pose(self, new_pose: Waypoint):
        self.current_pose = new_pose

    def get_uncommitted_events(self) -> List[Any]:
        events = self._uncommitted_events.copy()
        self._uncommitted_events.clear()
        return events

    def add_event(self, event: Any):
        self._uncommitted_events.append(event)
