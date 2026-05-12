from typing import Dict, Any
from core.shared.event_bus import DomainEventBus

class ClaudeFlowKernel:
    """
    모든 도메인, 리포지토리, 서비스 객체들을 등록(Registry)하고 로드하는 마이크로커널.
    DI(Dependency Injection) 컨테이너 역할도 겸합니다.
    """
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._event_bus = DomainEventBus()

    @property
    def event_bus(self) -> DomainEventBus:
        return self._event_bus

    def register_service(self, name: str, service_instance: Any):
        """커널에 서비스/리포지토리 인스턴스 등록"""
        self._services[name] = service_instance

    def get_service(self, name: str) -> Any:
        """등록된 서비스 가져오기"""
        if name not in self._services:
            raise ValueError(f"Service {name} is not registered in the kernel.")
        return self._services[name]
