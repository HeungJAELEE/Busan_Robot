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
        
        # 로봇의 최신 상태(좌표 + 상태)를 저장할 메모장
        self._latest_states = {} 
        self._state_lock = threading.Lock()
        
    def add_robot(self, name: str, ip: str, plc_ip: str = None):
        if name not in self._robots:
            self._robots[name] = {"ip": ip, "plc_ip": plc_ip, "instance": None}
            if self._active_robot_name is None:
                self._active_robot_name = name
            return

        info = self._robots[name]
        if ip:
            info["ip"] = ip
        if plc_ip is not None:
            info["plc_ip"] = plc_ip
                
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
        
    def connect(self, name: str = None, ip: str = None) -> bool:
        name = name or self._active_robot_name
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
            from indy_utils import indydcp_client as client
            r = client.IndyDCPClient(target_ip, "NRMK-Indy7")
            is_connected = r.connect()
            if not is_connected:
                print(f">> {name} 소켓 연결 실패 (IP: {target_ip})")
                self._robots[name]["instance"] = None
                return False
                
            self._robots[name]["instance"] = r
            return True
        except Exception as e:
            print(f">> {name} 연결 실패 예외 발생: {e}")
            self._robots[name]["instance"] = None
            return False
            
    def disconnect(self, name: str = None):
        name = name or self._active_robot_name
        if name in self._robots and self._robots[name]["instance"]:
            try:
                self._robots[name]["instance"].disconnect()
                time.sleep(0.5)
            except Exception: pass
            self._robots[name]["instance"] = None
            # 상태 메모장에서도 제거
            with self._state_lock:
                self._latest_states.pop(name, None)
            
    def get_all_robots(self):
        return self._robots
        
    def update_robot_state(self, name: str, j_pos, t_pos, robot_status=None):
        """로봇 좌표 + 상태를 메모장에 기록"""
        with self._state_lock:
            self._latest_states[name] = {
                "j_pos": j_pos, 
                "t_pos": t_pos,
                "status": robot_status,  # get_robot_status() 결과
                "timestamp": time.time()
            }

    def get_robot_state(self, name: str):
        with self._state_lock:
            return self._latest_states.get(name)
    
    def is_connected(self, name: str = None) -> bool:
        """해당 로봇이 연결되어 있는지 확인"""
        name = name or self._active_robot_name
        info = self._robots.get(name)
        return info is not None and info.get("instance") is not None
    
    def get_any_connected(self) -> bool:
        """하나라도 연결된 로봇이 있는지"""
        return any(info.get("instance") for info in self._robots.values())
        
# Singleton export
robot_manager = RobotClientManager()
