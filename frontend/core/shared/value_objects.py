from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class MotionDataVO:
    """모션 작업에 필요한 데이터를 담는 밸류 객체 (Value Object)"""
    coordinates: List[float] # Joint angles [j1, j2, j3, j4, j5, j6]
    
    @property
    def is_valid(self) -> bool:
        return len(self.coordinates) == 6

@dataclass(frozen=True)
class PlcAddressVO:
    """PLC 어드레스를 나타내는 밸류 객체"""
    address: str
    
    @property
    def is_bit(self) -> bool:
        return self.address.upper().startswith('M')
        
    @property
    def is_word(self) -> bool:
        return self.address.upper().startswith('D')
