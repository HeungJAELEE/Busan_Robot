import threading
import time
from core.runtime_config import plc_config

class PlcManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(PlcManager, cls).__new__(cls, *args, **kwargs)
                cls._instance._initialize()
            return cls._instance
            
    def _initialize(self):
        self._plc = None
        self._is_connected = False
        self._plc_lock = threading.Lock()
        
    def connect(self, ip: str = None, port: int = None) -> bool:
        config = plc_config()
        ip = ip or config["process_ip"]
        port = port or config["process_port"]
        if self._is_connected:
            self.disconnect()
            
        try:
            from pymcprotocol import Type3E
            self._plc = Type3E()
            self._plc.connect(ip, port)
            self._is_connected = True
            print(f"✅ [PLC 통신] {ip}:{port} 연결 성공")
            return True
        except Exception as e:
            self._is_connected = False
            print(f"❌ [PLC 통신] {ip}:{port} 연결 실패: {e}")
            return False
            
    def disconnect(self):
        if self._is_connected and self._plc:
            try:
                self._plc.close()
            except Exception: pass
        self._is_connected = False
        self._plc = None
        
    def is_connected(self) -> bool:
        return self._is_connected
        
    def get_lock(self):
        return self._plc_lock
        
    def get_client(self):
        return self._plc

plc_manager = PlcManager()
