import threading
import time

class RobotClientManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(RobotClientManager, cls).__new__(cls, *args, **kwargs)
                cls._instance._initialize()
            return cls._instance
            
    def _initialize(self):
        self._robots = {}
        self._active_robot_name = None
        self._robot_lock = threading.Lock()
        
    def add_robot(self, name: str, ip: str, plc_ip: str = None):
        if name not in self._robots:
            self._robots[name] = {"ip": ip, "plc_ip": plc_ip, "instance": None}
            if self._active_robot_name is None:
                self._active_robot_name = name
                
    def get_robot_info(self, name: str) -> dict:
        return self._robots.get(name)
        
    def set_active_robot(self, name: str):
        if name in self._robots:
            self._active_robot_name = name
            
    def get_active_robot_name(self) -> str:
        return self._active_robot_name
        
    def get_active_instance(self):
        if self._active_robot_name and self._active_robot_name in self._robots:
            return self._robots[self._active_robot_name]["instance"]
        return None
        
    def get_lock(self):
        return self._robot_lock
        
    def connect(self, name: str, ip: str = None) -> bool:
        if name not in self._robots:
            return False
        if ip:
            self._robots[name]["ip"] = ip
            
        target_ip = self._robots[name]["ip"]
        
        # Disconnect if already connected
        if self._robots[name]["instance"] is not None:
            try:
                self._robots[name]["instance"].disconnect()
                time.sleep(0.5)
            except Exception: pass
            
        try:
            # Lazy import to avoid circular dependencies
            from indy_utils import indydcp_client as client
            r = client.IndyDCPClient(target_ip, "NRMK-Indy7")
            r.connect()
            self._robots[name]["instance"] = r
            return True
        except Exception as e:
            print(f">> {name} 연결 실패: {e}")
            self._robots[name]["instance"] = None
            return False
            
    def disconnect(self, name: str):
        if name in self._robots and self._robots[name]["instance"]:
            try:
                self._robots[name]["instance"].disconnect()
                time.sleep(0.5)
            except Exception: pass
            self._robots[name]["instance"] = None
            
    def get_all_robots(self):
        return self._robots
        
# Singleton export
robot_manager = RobotClientManager()
